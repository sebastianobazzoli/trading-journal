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
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_db()

# --- 3. CSS ---
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
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 5. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

# Caricamento dati
bal = get_data("balances")
trades = get_data("trades")

# --- 6. LOGICA TRADE (FIX ERRORI DATA) ---
if st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        with st.form("t_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3); asset = f1.text_input("TICKER"); instr = f2.selectbox("INSTRUMENT", ["Stock", "CFD", "ETF", "Crypto"]); shares = f3.number_input("SHARES", min_value=0.0, format="%.4f")
            f4, f5, f6 = st.columns(3); curr = f4.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); acc = f5.selectbox("ACCOUNT", bal['portfolio'].unique() if not bal.empty else ["-"]); side = f6.selectbox("SIDE", ["LONG", "SHORT"])
            f7, f8, f9 = st.columns(3); entry = f7.number_input("ENTRY", format="%.5f"); lev = f8.number_input("LEVERAGE", min_value=1.0, value=1.0); fees = f9.number_input("FEES", min_value=0.0)
            if st.form_submit_button("COMMIT_NEW_TRADE"):
                cost = ((entry * shares) / lev) + fees
                supabase.table("trades").insert({
                    "asset": asset, "instrument": instr, "shares": shares, "leverage": lev, "currency": curr, 
                    "portfolio": acc, "side": side, "entry_price": entry, "fees": fees, "cost": cost, 
                    "notional": entry * shares, "status": "OPEN", "date": str(datetime.date.today())
                }).execute()
                st.rerun()

    if not trades.empty:
        # --- FIX CRITICO PER LE DATE ---
        # Convertiamo le colonne date in oggetti datetime.date per la compatibilità con st.data_editor
        if 'date' in trades.columns:
            trades['date'] = pd.to_datetime(trades['date']).dt.date
        if 'close_date' in trades.columns:
            trades['close_date'] = pd.to_datetime(trades['close_date']).dt.date
        else:
            trades['close_date'] = None

        st.markdown("<div class='ticker-label'>INTERACTIVE_LEDGER</div>", unsafe_allow_html=True)
        
        edited_trades = st.data_editor(
            trades, 
            use_container_width=True, 
            hide_index=True, 
            disabled=["id", "cost", "notional", "profit", "pnl_perc", "date"], 
            column_config={
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"]),
                "close_date": st.column_config.DateColumn("CLOSE_DATE", format="YYYY-MM-DD"),
                "date": st.column_config.DateColumn("OPEN_DATE", format="YYYY-MM-DD")
            }
        )
        
        if st.button("SAVE_LEDGER_CHANGES"):
            try:
                for idx, row in edited_trades.iterrows():
                    pnl, p_perc = row.get('profit', 0), row.get('pnl_perc', 0)
                    
                    # Ricalcolo se chiuso
                    if row['status'] == "CLOSED" and row['exit_price'] > 0:
                        pnl = (((row['exit_price'] - row['entry_price']) * row['shares']) if row['side'] == "LONG" else ((row['entry_price'] - row['exit_price']) * row['shares'])) - row['fees']
                        p_perc = (pnl / row['cost']) * 100 if row['cost'] > 0 else 0
                    
                    update_payload = {
                        "status": row['status'], 
                        "exit_price": row['exit_price'], 
                        "profit": pnl, 
                        "pnl_perc": p_perc,
                        "close_date": str(row['close_date']) if row['close_date'] and not pd.isna(row['close_date']) else None
                    }
                    
                    supabase.table("trades").update(update_payload).eq("id", row['id']).execute()
                st.success("SYNCED_SUCCESSFULLY")
                st.rerun()
            except Exception as e:
                st.error(f"UPDATE_ERROR: {e}")

# --- 7. PAGINA: DASHBOARD (RIPRISTINATA) ---
elif st.session_state.page == 'DASHBOARD':
    # Market Tickers
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

    # Equity Curve
    if not trades.empty:
        st.markdown("<div class='ticker-label'>EQUITY_CURVE</div>", unsafe_allow_html=True)
        t_df = trades.copy()
        t_df['date'] = pd.to_datetime(t_df['date'])
        t_df = t_df.sort_values('date')
        t_df['cum_pnl'] = t_df['profit'].cumsum()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(showgrid=True, gridcolor='#1A1A1A'), yaxis=dict(showgrid=True, gridcolor='#1A1A1A'))
        st.plotly_chart(fig, use_container_width=True)

# --- 8. PAGINA: VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES")
    with st.form("v_form"):
        v1, v2, v3 = st.columns(3); n = v1.text_input("ACCOUNT"); c = v2.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); a = v3.number_input("BALANCE")
        if st.form_submit_button("SYNC_VAULT"):
            supabase.table("balances").upsert({"portfolio": n, "currency": c, "amount": a}, on_conflict="portfolio,currency").execute()
            st.rerun()
    if not bal.empty: st.dataframe(bal, use_container_width=True, hide_index=True)
