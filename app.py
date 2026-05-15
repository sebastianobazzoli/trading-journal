import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONNESSIONE ---
@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 3. CSS PROFESSIONALE (RIPRISTINO TOTALE) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        .block-container { padding-top: 4rem !important; padding-left: 2rem !important; padding-right: 2rem !important; max-width: 100% !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; padding-top: 2rem !important; }
        
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; width: 100% !important; text-align: left !important; padding: 10px 15px !important; }
        .stButton>button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
        
        /* Forza la tabella a non avere scroll orizzontale */
        [data-testid="stDataEditor"] div { font-size: 11px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

# --- 5. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-bottom:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

trades = get_data("trades")
bal = get_data("balances")

# --- 6. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    market_tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC/USD": "BTC-USD", "GOLD": "GC=F"}
    t_cols = st.columns(len(market_tickers))
    for i, (name, sym) in enumerate(market_tickers.items()):
        try:
            tk = yf.Ticker(sym).history(period="2d")
            price, change = tk['Close'].iloc[-1], ((tk['Close'].iloc[-1]/tk['Close'].iloc[-2])-1)*100
            color = "#00FF41" if change > 0 else "#FF3131"
            with t_cols[i]:
                st.markdown(f"<div class='panel'><div class='ticker-label'>{name}</div><div style='font-size:18px; font-weight:700; color:{color}'>{price:,.2f} <span style='font-size:10px;'>{change:+.2f}%</span></div></div>", unsafe_allow_html=True)
        except: pass
    
    st.markdown("<br>", unsafe_allow_html=True)
    if not trades.empty:
        t_df = trades[trades['status'] == 'CLOSED'].copy()
        if not t_df.empty:
            t_df['date'] = pd.to_datetime(t_df['date'])
            t_df = t_df.sort_values('date')
            t_df['cum_pnl'] = pd.to_numeric(t_df['profit']).cumsum()
            fig = go.Figure(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines+markers', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
            st.plotly_chart(fig, use_container_width=True)

# --- 7. PAGINA: TRADE EXECUTION ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    # Inserimento rapido
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        with st.form("quick_trade", clear_on_submit=True):
            f1, f2, f3, f4, f5, f6 = st.columns(6)
            asset = f1.text_input("TICKER")
            side = f2.selectbox("SIDE", ["LONG", "SHORT"])
            shares = f3.number_input("QTY", min_value=0.0)
            entry = f4.number_input("ENTRY")
            lev = f5.number_input("LEV", min_value=1.0, value=1.0)
            fees = f6.number_input("FEE", min_value=0.0)
            if st.form_submit_button("OPEN_POSITION") and asset:
                cost = ((entry * shares) / lev) + fees
                supabase.table("trades").insert({"asset": asset, "side": side, "shares": shares, "entry_price": entry, "leverage": lev, "fees": fees, "cost": cost, "status": "OPEN", "date": str(datetime.date.today()), "profit": 0, "pnl_perc": 0, "instrument": "Stock", "currency": "USD"}).execute()
                st.rerun()

    if not trades.empty:
        # Arrotondamento e Colori
        for c in ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'fees', 'cost']:
            trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)

        def style_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            return styles

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM // ALL_VISIBLE_NO_SCROLL</div>", unsafe_allow_html=True)
        
        # Tabella Unica FIT-TO-SCREEN
        edited_trades = st.data_editor(
            trades.style.apply(style_ledger, axis=None), 
            use_container_width=True, hide_index=True, num_rows="dynamic",
            disabled=["id", "cost", "date", "profit", "pnl_perc"], 
            column_config={
                "asset": st.column_config.TextColumn("TKR", width=50),
                "status": st.column_config.SelectboxColumn("STAT", options=["OPEN", "CLOSED"], width=65),
                "side": st.column_config.TextColumn("S", width=40),
                "shares": st.column_config.NumberColumn("QTY", width=60),
                "entry_price": st.column_config.NumberColumn("IN", width=65),
                "exit_price": st.column_config.NumberColumn("OUT", width=65),
                "profit": st.column_config.NumberColumn("P&L", width=70),
                "pnl_perc": st.column_config.NumberColumn("%", width=60),
                "fees": st.column_config.NumberColumn("FEE", width=50),
                "leverage": st.column_config.NumberColumn("LV", width=40)
            },
            key="terminal_ledger_v1"
        )
        
        if st.button("SYNC_AND_CALCULATE"):
            try:
                # 1. Elimina righe rimosse
                ids_del = set(trades['id']) - set(edited_trades['id'])
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                
                # 2. Ricalcola ogni riga (P&L = (Out - In) * Qty - Fees)
                for idx, row in edited_trades.iterrows():
                    p_in, p_out, qta, comm = float(row['entry_price']), float(row['exit_price']), float(row['shares']), float(row['fees'])
                    costo_margine = float(row['cost'])
                    pnl_netto, pnl_perc = 0.0, 0.0
                    
                    if p_out > 0:
                        m = 1 if row['side'] == "LONG" else -1
                        pnl_netto = ((p_out - p_in) * qta * m) - comm
                        if costo_margine > 0: pnl_perc = (pnl_netto / costo_margine) * 100
                    
                    supabase.table("trades").update({
                        "status": row['status'], "exit_price": round(p_out, 2), 
                        "profit": round(pnl_netto, 2), "pnl_perc": round(pnl_perc, 2),
                        "close_date": str(datetime.date.today()) if row['status'] == "CLOSED" else None
                    }).eq("id", row['id']).execute()
                st.rerun()
            except: st.error("Errore durante la sincronizzazione.")

# --- 8. PAGINA: VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES")
    if not bal.empty: st.dataframe(bal, use_container_width=True, hide_index=True)
