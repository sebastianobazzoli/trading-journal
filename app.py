import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONNESSIONE ---
@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 3. CSS PROFESSIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: #00FF41 !important; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .ticker-price { font-size: 18px; font-weight: 700; margin-top: 4px; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; padding: 10px 15px !important; font-size: 12px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        return df
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
    # Ticker Wall
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
            # Filtriamo solo i chiusi con profitto calcolato
            t_df = trades[trades['status'] == 'CLOSED'].copy()
            if not t_df.empty:
                t_df['date'] = pd.to_datetime(t_df['date'])
                t_df = t_df.sort_values('date')
                t_df['cum_pnl'] = pd.to_numeric(t_df['profit']).cumsum()
                fig = go.Figure(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines+markers', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(showgrid=True, gridcolor='#1A1A1A'), yaxis=dict(showgrid=True, gridcolor='#1A1A1A'))
                st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("<div class='ticker-label'>ASSET_ALLOCATION</div>", unsafe_allow_html=True)
        if not trades.empty:
            alloc = trades.groupby('instrument')['notional'].sum().reset_index()
            fig_pie = px.pie(alloc, values='notional', names='instrument', hole=.4, color_discrete_sequence=px.colors.sequential.Greens_r)
            fig_pie.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_pie, use_container_width=True)

# --- 7. PAGINA: TRADE EXECUTION ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        with st.form("t_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3); asset = f1.text_input("TICKER"); instr = f2.selectbox("INSTRUMENT", ["Stock", "CFD", "ETF", "Crypto"]); shares = f3.number_input("SHARES", min_value=0.0)
            f4, f5, f6 = st.columns(3); curr = f4.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); acc = f5.selectbox("ACCOUNT", bal['portfolio'].unique() if not bal.empty else ["-"]); side = f6.selectbox("SIDE", ["LONG", "SHORT"])
            f7, f8, f9 = st.columns(3); entry = f7.number_input("ENTRY"); lev = f8.number_input("LEVERAGE", min_value=1.0, value=1.0); fees = f9.number_input("FEES")
            if st.form_submit_button("OPEN_POSITION"):
                cost = ((entry * shares) / lev) + fees
                supabase.table("trades").insert({"asset": asset, "instrument": instr, "shares": shares, "leverage": lev, "currency": curr, "portfolio": acc, "side": side, "entry_price": entry, "fees": fees, "cost": cost, "notional": entry * shares, "status": "OPEN", "date": str(datetime.date.today()), "profit": 0, "pnl_perc": 0}).execute()
                st.rerun()

    if not trades.empty:
        # Formattazione condizionale del testo
        def color_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            return styles

        st.markdown("<div class='ticker-label'>UNIFIED_LEDGER (EDIT STATUS & EXIT TO RECALCULATE)</div>", unsafe_allow_html=True)
        
        # Editor Unico
        edited_trades = st.data_editor(
            trades.style.apply(color_ledger, axis=None), 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            disabled=["id", "cost", "notional", "date", "profit", "pnl_perc"], 
            column_config={
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"]),
                "exit_price": st.column_config.NumberColumn("EXIT_PRICE", format="%.2f"),
                "shares": st.column_config.NumberColumn("SHARES", format="%.2f"),
                "entry_price": st.column_config.NumberColumn("ENTRY_PRICE", format="%.2f"),
                "profit": st.column_config.NumberColumn("P&L NETTO", format="%.2f"),
                "pnl_perc": st.column_config.NumberColumn("P&L %", format="%.2f%%")
            },
            key="terminal_editor_v5"
        )
        
        if st.button("SYNC_AND_RECALCULATE_RENDIMENT"):
            try:
                # 1. Cancellazione righe rimosse
                ids_orig = set(trades['id']); ids_new = set(edited_trades['id']); ids_del = ids_orig - ids_new
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()

                # 2. Ciclo di ricalcolo matematico puro
                for idx, row in edited_trades.iterrows():
                    # Forziamo la conversione numerica per ogni riga per evitare errori di tipo
                    entry = float(row['entry_price'])
                    exit_p = float(row['exit_price'])
                    qty = float(row['shares'])
                    fees = float(row['fees'])
                    cost_basis = float(row['cost'])
                    
                    pnl_realizzato = 0.0
                    perc_realizzata = 0.0

                    if row['status'] == "CLOSED" and exit_p > 0:
                        # Formula: ((Prezzo Uscita - Prezzo Entrata) * Quantità) * Direzione - Commissioni
                        direzione = 1 if row['side'] == "LONG" else -1
                        pnl_realizzato = ((exit_p - entry) * qty * direzione) - fees
                        perc_realizzata = (pnl_realizzato / cost_basis * 100) if cost_basis > 0 else 0.0
                    
                    # Aggiornamento database con valori arrotondati
                    supabase.table("trades").update({
                        "status": row['status'], 
                        "exit_price": round(exit_p, 2), 
                        "profit": round(pnl_realizzato, 2), 
                        "pnl_perc": round(perc_realizzata, 2),
                        "close_date": str(datetime.date.today()) if row['status'] == "CLOSED" else None
                    }).eq("id", row['id']).execute()
                
                st.success("TERMINAL SYNCED: Rendimento calcolato con precisione decimale."); st.rerun()
            except Exception as e: st.error(f"SYNC_ERROR: {e}")

# --- 8. PAGINA: VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES")
    with st.form("v_form"):
        v1, v2, v3 = st.columns(3); n = v1.text_input("ACCOUNT"); c = v2.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); a = v3.number_input("BALANCE")
        if st.form_submit_button("SYNC_VAULT"):
            supabase.table("balances").upsert({"portfolio": n, "currency": c, "amount": a}, on_conflict="portfolio,currency").execute()
            st.rerun()
    if not bal.empty: st.dataframe(bal, use_container_width=True, hide_index=True)
