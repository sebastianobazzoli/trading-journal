import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- SETUP & TERMINAL THEME ---
st.set_page_config(page_title="TERMINAL X", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;700&display=swap');
        :root { --term-bg: #050505; --term-green: #00FF41; --term-red: #FF3131; --border: #1A1A1A; }
        * { font-family: 'Roboto Mono', monospace !important; }
        .stApp { background-color: var(--term-bg); color: #CCCCCC; }
        [data-testid="stSidebar"] { background-color: #0A0A0A !important; border-right: 1px solid var(--border); }
        .panel { border: 1px solid var(--border); padding: 15px; background: #0D0D0D; border-radius: 4px; margin-bottom: 10px; }
        .stButton>button { border: 1px solid #333; background: transparent; color: #888; border-radius: 2px; text-transform: uppercase; font-size: 11px; }
        .stButton>button:hover { border-color: #0070FF; color: white; }
        header, footer { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION ---
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_data(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- NAVIGATION ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'

with st.sidebar:
    st.markdown("<h1 style='color:white; font-size:16px; margin-bottom:25px;'>TERMINAL_OS v3.0</h1>", unsafe_allow_html=True)
    if st.button("01 DASHBOARD", use_container_width=True): st.session_state.page = 'DASHBOARD'
    if st.button("02 EXECUTION", use_container_width=True): st.session_state.page = 'TRADE'
    if st.button("03 HEATMAP", use_container_width=True): st.session_state.page = 'HEATMAP'
    st.markdown("<hr style='border-color:#222'>", unsafe_allow_html=True)
    if st.button("04 VAULT (WALLET SETUP)", use_container_width=True): st.session_state.page = 'VAULT'

# --- LOGIC: VAULT (MANAGEMENT) ---
if st.session_state.page == 'VAULT':
    st.markdown("<h2 style='color:white; font-size:14px;'>/ROOT/VAULT_MANAGER</h2>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        with st.form("vault_form"):
            st.write("INIZIALIZZA RISERVE LIQUIDITA")
            c1, c2, c3 = st.columns(3)
            v_name = c1.text_input("NOME PORTAFOGLIO (es. BINANCE, IBKR)")
            v_curr = c2.selectbox("VALUTA", ["EUR", "USD", "GBP", "BTC", "USDT"])
            v_amount = c3.number_input("DEPOSITO INIZIALE", min_value=0.0)
            
            if st.form_submit_button("SYNC TO CLOUD"):
                # Upsert saldo iniziale
                res = supabase.table("balances").select("*").eq("portfolio", v_name).eq("currency", v_curr).execute()
                if res.data:
                    supabase.table("balances").update({"amount": v_amount}).eq("portfolio", v_name).eq("currency", v_curr).execute()
                else:
                    supabase.table("balances").insert({"portfolio": v_name, "currency": v_curr, "amount": v_amount}).execute()
                st.success("VAULT UPDATED")
        st.markdown("</div>", unsafe_allow_html=True)

# --- LOGIC: TRADE (EXECUTION) ---
elif st.session_state.page == 'TRADE':
    st.markdown("<h2 style='color:white; font-size:14px;'>/ROOT/EXECUTION_ENGINE</h2>", unsafe_allow_html=True)
    bal = get_data("balances")
    
    with st.form("exec_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        p_sel = col1.selectbox("SELECT PORTFOLIO", bal['portfolio'].unique() if not bal.empty else ["EMPTY"])
        c_sel = col2.selectbox("SETTLEMENT CCY", ["EUR", "USD", "BTC", "USDT"])
        status = col3.selectbox("ORDER STATUS", ["OPEN", "CLOSED"])
        
        col4, col5, col6 = st.columns(3)
        asset = col4.text_input("TICKER")
        entry = col5.number_input("ENTRY PRICE", format="%.5f")
        exit_p = col6.number_input("EXIT PRICE (0 IF OPEN)", format="%.5f")
        
        if st.form_submit_button("EXECUTE"):
            # Se chiuso, calcola profitto e aggiorna liquidità
            profit = 0
            if status == "CLOSED":
                profit = (exit_p - entry) if entry != 0 else 0
                # Update saldo nel vault
                res = supabase.table("balances").select("*").eq("portfolio", p_sel).eq("currency", c_sel).execute()
                if res.data:
                    new_val = float(res.data[0]['amount']) + profit
                    supabase.table("balances").update({"amount": new_val}).eq("portfolio", p_sel).eq("currency", c_sel).execute()
            
            supabase.table("trades").insert({
                "portfolio": p_sel, "asset": asset, "profit": profit, 
                "currency": c_sel, "status": status, "date": str(datetime.date.today())
            }).execute()
            st.success("TRADE LOGGED")

# --- LOGIC: DASHBOARD (TERMINAL VIEW) ---
elif st.session_state.page == 'DASHBOARD':
    st.markdown("<h2 style='color:white; font-size:14px;'>/ROOT/LIVE_MONITOR</h2>", unsafe_allow_html=True)
    
    bal = get_data("balances")
    trades = get_data("trades")
    
    # 1. VISUALIZZAZIONE VAULT LIVE
    if not bal.empty:
        st.write("LIQUIDITA CORRENTE (REALE)")
        b_cols = st.columns(len(bal['portfolio'].unique()))
        for i, p_name in enumerate(bal['portfolio'].unique()):
            with b_cols[i]:
                st.markdown(f"<div class='panel'><div style='font-size:10px; color:#555'>{p_name}</div>", unsafe_allow_html=True)
                p_subset = bal[bal['portfolio'] == p_name]
                for _, row in p_subset.iterrows():
                    st.markdown(f"<div style='color:white; font-weight:700'>{row['amount']:,.2f} <span style='color:#0070FF'>{row['currency']}</span></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

    # 2. TRADE APERTI (NON INFLUENZANO IL SALDO FINCHÉ NON CHIUSI)
    if not trades.empty:
        open_trades = trades[trades['status'] == 'OPEN']
        if not open_trades.empty:
            st.write("POSIZIONI APERTE (MARK TO MARKET)")
            st.dataframe(open_trades[['asset', 'portfolio', 'currency', 'date']], use_container_width=True)

    # 3. GRAFICO RENDIMENTO VS SP500 (COME PRIMA)
    # ... [Includi qui il codice del grafico dell'interazione precedente] ...
