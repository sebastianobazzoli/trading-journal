import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- CSS PROFESSIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: #00FF41 !important; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; width: 100%; font-size: 12px !important; }
    </style>
""", unsafe_allow_html=True)

# --- NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

# --- CARICAMENTO DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

bal = get_data("balances")
trades = get_data("trades")

# --- PAGINA TRADE EXECUTION ---
if st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        with st.form("t_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3); asset = f1.text_input("TICKER"); instr = f2.selectbox("INSTRUMENT", ["Stock", "CFD", "ETF", "Crypto"]); shares = f3.number_input("SHARES", min_value=0.0)
            f4, f5, f6 = st.columns(3); curr = f4.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); acc = f5.selectbox("ACCOUNT", bal['portfolio'].unique() if not bal.empty else ["-"]); side = f6.selectbox("SIDE", ["LONG", "SHORT"])
            f7, f8, f9 = st.columns(3); entry = f7.number_input("ENTRY_PRICE"); lev = f8.number_input("LEVERAGE", min_value=1.0, value=1.0); fees = f9.number_input("FEES")
            if st.form_submit_button("OPEN_POSITION"):
                cost = ((entry * shares) / lev) + fees
                supabase.table("trades").insert({"asset": asset, "instrument": instr, "shares": shares, "leverage": lev, "currency": curr, "portfolio": acc, "side": side, "entry_price": entry, "fees": fees, "cost": cost, "notional": entry * shares, "status": "OPEN", "date": str(datetime.date.today()), "profit": 0, "pnl_perc": 0}).execute()
                st.rerun()

    if not trades.empty:
        # Formattazione condizionale
        def color_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            return styles

        st.markdown("<div class='ticker-label'>UNIFIED_LEDGER (EDIT STATUS & EXIT PMC)</div>", unsafe_allow_html=True)
        
        # Rendiamo 'profit' e 'pnl_perc' leggibili nell'editor per vedere il risultato
        edited_trades = st.data_editor(
            trades.style.apply(color_ledger, axis=None), 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            disabled=["id", "cost", "notional", "date", "profit", "pnl_perc"], 
            column_config={
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"]),
                "exit_price": st.column_config.NumberColumn("EXIT_PRICE (PMC)", format="%.4f"),
                "profit": st.column_config.NumberColumn("P&L NETTO", format="%.2f"),
                "pnl_perc": st.column_config.NumberColumn("P&L %", format="%.2f%%")
            },
            key="terminal_editor_final"
        )
        
        if st.button("SYNC_AND_RECALCULATE"):
            try:
                # Cancellazione righe rimosse
                ids_orig = set(trades['id']); ids_new = set(edited_trades['id']); ids_del = ids_orig - ids_new
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()

                for idx, row in edited_trades.iterrows():
                    p_in = float(row['entry_price'])
                    p_out = float(row['exit_price'])
                    qta = float(row['shares'])
                    comm = float(row['fees'])
                    capitale = float(row['cost'])
                    
                    # LOGICA SEMPRE ATTIVA: Se p_out > 0, calcola il P&L anche se OPEN
                    pnl_netto = 0.0
                    pnl_perc = 0.0
                    
                    if p_out > 0:
                        direzione = 1 if row['side'] == "LONG" else -1
                        pnl_netto = ((p_out - p_in) * qta * direzione) - comm
                        if capitale > 0:
                            pnl_perc = (pnl_netto / capitale) * 100
                    
                    supabase.table("trades").update({
                        "status": row['status'], 
                        "exit_price": round(p_out, 4), 
                        "profit": round(pnl_netto, 2), 
                        "pnl_perc": round(pnl_perc, 2),
                        "close_date": str(datetime.date.today()) if row['status'] == "CLOSED" else None
                    }).eq("id", row['id']).execute()
                
                st.success("SYNC COMPLETE"); st.rerun()
            except Exception as e: st.error(f"SYNC_ERROR: {e}")

# --- DASHBOARD (SOLO TRADE CHIUSI NEL GRAFICO) ---
elif st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    if not trades.empty:
        t_df = trades[trades['status'] == 'CLOSED'].copy()
        if not t_df.empty:
            t_df['date'] = pd.to_datetime(t_df['date'])
            t_df = t_df.sort_values('date')
            t_df['cum_pnl'] = pd.to_numeric(t_df['profit']).cumsum()
            fig = go.Figure(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines+markers', line=dict(color='#00FF41')))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
            st.plotly_chart(fig, use_container_width=True)        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

# --- 5. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

# Caricamento Dati
bal = get_data("balances")
trades = get_data("trades")

# --- 6. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    market_tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC/USD": "BTC-USD", "GOLD": "GC=F"}
    t_cols = st.columns(len(market_tickers))
    for i, (name, sym) in enumerate(market_tickers.items()):
        try:
            tk = yf.Ticker(sym).history(period="2d")
            price, change = tk['Close'].iloc[-1], ((tk['Close'].iloc[-1]/tk['Close'].iloc[-2])-1)*100
            color = "#00FF41" if change > 0 else "#FF3131"
            with t_cols[i]:
                st.markdown(f"<div class='panel'><div class='ticker-label'>{name}</div><div class='ticker-price' style='color:{color}'>{price:,.2f} <span style='font-size:10px;'>{change:+.2f}%</span></div></div>", unsafe_allow_html=True)
        except: pass

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("<div class='ticker-label'>EQUITY_CURVE (REALIZED P&L)</div>", unsafe_allow_html=True)
        if not trades.empty:
            t_df = trades[trades['status'] == 'CLOSED'].copy()
            if not t_df.empty:
                t_df['date'] = pd.to_datetime(t_df['date'])
                t_df = t_df.sort_values('date')
                t_df['cum_pnl'] = pd.to_numeric(t_df['profit']).cumsum()
                fig = go.Figure(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines+markers', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

# --- 7. PAGINA: TRADE EXECUTION (LOGICA CALCOLO RICHIESTA) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        with st.form("t_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3); asset = f1.text_input("TICKER"); instr = f2.selectbox("INSTRUMENT", ["Stock", "CFD", "ETF", "Crypto"]); shares = f3.number_input("SHARES", min_value=0.0)
            f4, f5, f6 = st.columns(3); curr = f4.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); acc = f5.selectbox("ACCOUNT", bal['portfolio'].unique() if not bal.empty else ["-"]); side = f6.selectbox("SIDE", ["LONG", "SHORT"])
            f7, f8, f9 = st.columns(3); entry = f7.number_input("ENTRY_PRICE (PMC)"); lev = f8.number_input("LEVERAGE", min_value=1.0, value=1.0); fees = f9.number_input("FEES (COMMISSIONI)")
            if st.form_submit_button("OPEN_POSITION"):
                # Calcolo capitale investito reale (Costo) considerando la leva
                cost = ((entry * shares) / lev) + fees
                notional = entry * shares
                supabase.table("trades").insert({
                    "asset": asset, "instrument": instr, "shares": shares, "leverage": lev, "currency": curr, 
                    "portfolio": acc, "side": side, "entry_price": entry, "fees": fees, "cost": cost, 
                    "notional": notional, "status": "OPEN", "date": str(datetime.date.today()), "profit": 0, "pnl_perc": 0
                }).execute()
                st.rerun()

    if not trades.empty:
        # Funzione colore testo
        def color_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            return styles

        st.markdown("<div class='ticker-label'>UNIFIED_LEDGER (EDIT STATUS & EXIT PRICE)</div>", unsafe_allow_html=True)
        
        edited_trades = st.data_editor(
            trades.style.apply(color_ledger, axis=None), 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            disabled=["id", "cost", "notional", "date", "profit", "pnl_perc"], 
            column_config={
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"]),
                "exit_price": st.column_config.NumberColumn("EXIT_PRICE (PMC)", format="%.4f"),
                "profit": st.column_config.NumberColumn("P&L NETTO", format="%.2f"),
                "pnl_perc": st.column_config.NumberColumn("P&L %", format="%.2f%%")
            },
            key="terminal_editor_fixed"
        )
        
        if st.button("SYNC_AND_RECALCULATE"):
            try:
                # 1. Rimozione righe cancellate
                ids_orig = set(trades['id']); ids_new = set(edited_trades['id']); ids_del = ids_orig - ids_new
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()

                # 2. Ricalcolo Matematico richiesto
                for idx, row in edited_trades.iterrows():
                    # PMC Ingresso/Uscita, Shares, Fees, Cost (Margine)
                    p_in = float(row['entry_price'])
                    p_out = float(row['exit_price'])
                    qta = float(row['shares'])
                    comm = float(row['fees'])
                    capitale_investito = float(row['cost']) # Margine reale usato all'apertura
                    
                    pnl_netto = 0.0
                    pnl_perc = 0.0

                    if row['status'] == "CLOSED" and p_out > 0:
                        # FORMULA P&L NETTO: (PMC Uscita - PMC Ingresso) * Shares - Commissioni
                        direzione = 1 if row['side'] == "LONG" else -1
                        pnl_netto = ((p_out - p_in) * qta * direzione) - comm
                        
                        # FORMULA P&L%: Profitto / Capitale Investito Reale (Margine)
                        # Questa formula tiene conto automaticamente della leva perché 'cost' è già stato diviso per la leva
                        if capitale_investito > 0:
                            pnl_perc = (pnl_netto / capitale_investito) * 100
                    
                    # Update Database arrotondato
                    supabase.table("trades").update({
                        "status": row['status'], 
                        "exit_price": round(p_out, 4), 
                        "profit": round(pnl_netto, 2), 
                        "pnl_perc": round(pnl_perc, 2),
                        "close_date": str(datetime.date.today()) if row['status'] == "CLOSED" else None
                    }).eq("id", row['id']).execute()
                
                st.success("TERMINAL SYNCED"); st.rerun()
            except Exception as e: st.error(f"SYNC_ERROR: {e}")

# --- 8. PAGINA: VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES")
    # ... (Stessa logica Vault dei messaggi precedenti)
