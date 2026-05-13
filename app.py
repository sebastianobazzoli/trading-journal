import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS TERMINAL (ROBUSTO) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; min-width: 280px !important; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; }
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
        .panel { border: 1px solid #1A1A1A; padding: 15px; background: #0A0A0A; margin-bottom: 10px; }
        header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"DATABASE_CONNECTION_ERROR: {e}")
    st.stop()

# --- 4. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

# --- 5. NAVIGAZIONE ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; margin-bottom:30px;'>TERMINAL ACCESS</div>", unsafe_allow_html=True)
    if st.button("[01] DASHBOARD"): st.session_state.page = 'DASHBOARD'
    if st.button("[02] TRADE_LOG"): st.session_state.page = 'TRADE'
    if st.button("[03] VAULT_SETUP"): st.session_state.page = 'VAULT'
    st.divider()
    st.markdown(f"<div style='color:#333; font-size:10px;'>STATUS: CONNECTED<br>{datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# Caricamento dati globale
bal = get_data("balances")
trades = get_data("trades")

# --- 6. LOGICA PAGINE ---

if st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_SETTINGS")
    with st.form("v_form"):
        c1, c2 = st.columns(2)
        name = c1.text_input("ACCOUNT_NAME")
        curr = c2.selectbox("CURRENCY", ["USD", "EUR", "BTC", "USDT"])
        amount = st.number_input("INITIAL_BALANCE", min_value=0.0)
        if st.form_submit_button("COMMIT_SYNC"):
            supabase.table("balances").upsert({"portfolio": name, "currency": curr, "amount": amount}).execute()
            st.success("VAULT_UPDATED")
            st.rerun()
    if not bal.empty:
        st.table(bal)

elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    if bal.empty:
        st.warning("INITIALIZE VAULT FIRST")
    else:
        with st.form("t_form"):
            c1, c2, c3 = st.columns(3)
            p_sel = c1.selectbox("PORTFOLIO", bal['portfolio'].unique())
            asset = c2.text_input("TICKER")
            side = c3.selectbox("SIDE", ["LONG", "SHORT"])
            
            c4, c5, c6 = st.columns(3)
            entry = c4.number_input("ENTRY", format="%.5f")
            exit_p = c5.number_input("EXIT", format="%.5f")
            status = c6.selectbox("STATUS", ["OPEN", "CLOSED"])
            
            if st.form_submit_button("EXECUTE_ORDER"):
                profit = (exit_p - entry) if (status == "CLOSED" and side == "LONG") else (entry - exit_p if status == "CLOSED" else 0)
                # Salva Trade
                supabase.table("trades").insert({
                    "portfolio": p_sel, "asset": asset, "profit": profit, 
                    "currency": "USD", "status": status, "date": str(datetime.date.today())
                }).execute()
                # Aggiorna Saldo se chiuso
                if status == "CLOSED":
                    current = bal[(bal['portfolio']==p_sel)]['amount'].sum() # Semplificato per test
                    supabase.table("balances").update({"amount": current + profit}).eq("portfolio", p_sel).execute()
                st.success("TRADE_SYNCED")
                st.rerun()

else: # DASHBOARD
    st.markdown("### / MAIN_MONITOR")
    if bal.empty:
        st.info("WELCOME. GO TO [03] VAULT_SETUP TO START.")
    else:
        # Mini Tickers
        t_cols = st.columns(3)
        for i, t in enumerate(["^GSPC", "^IXIC", "BTC-USD"]):
            with t_cols[i]:
                val = yf.Ticker(t).history(period="1d")['Close'].iloc[-1]
                st.markdown(f"<div class='panel'><span style='color:#555; font-size:10px;'>{t}</span><br><b style='font-size:18px;'>{val:,.2f}</b></div>", unsafe_allow_html=True)
        
        # Saldi
        st.markdown("<br>", unsafe_allow_html=True)
        for p in bal['portfolio'].unique():
            st.markdown(f"<div class='panel'><span style='color:#0070FF;'>ACCOUNT: {p}</span>", unsafe_allow_html=True)
            p_data = bal[bal['portfolio'] == p]
            for _, r in p_data.iterrows():
                st.write(f"{r['amount']:,.2f} {r['currency']}")
            st.markdown("</div>", unsafe_allow_html=True)
