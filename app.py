import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- SETUP & TERMINAL THEME ---
st.set_page_config(page_title="TERMINAL X", layout="wide")

# CSS di emergenza: garantisce che il testo sia visibile anche in caso di errori parziali
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;700&display=swap');
        :root { --term-bg: #050505; --term-green: #00FF41; --term-red: #FF3131; --border: #1A1A1A; }
        * { font-family: 'Roboto Mono', monospace !important; }
        .stApp { background-color: var(--term-bg); color: #CCCCCC; }
        [data-testid="stSidebar"] { background-color: #0A0A0A !important; border-right: 1px solid var(--border); visibility: visible !important; }
        .panel { border: 1px solid var(--border); padding: 15px; background: #0D0D0D; border-radius: 4px; margin-bottom: 10px; }
        header, footer { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- DB CONNECTION CON ERROR HANDLING ---
try:
    url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"ERRORE CONFIGURAZIONE SECRETS: {e}")
    st.stop()

def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.warning(f"DATABASE OFFLINE O TABELLA '{table}' MANCANTE")
        return pd.DataFrame()

# --- NAVIGATION ---
# Inizializziamo sempre la pagina per evitare NameError
if 'page' not in st.session_state: 
    st.session_state.page = 'DASHBOARD'

# SIDEBAR: Deve essere renderizzata subito per essere sempre visibile
with st.sidebar:
    st.markdown("<h1 style='color:white; font-size:16px; margin-bottom:25px;'>TERMINAL_OS v3.0</h1>", unsafe_allow_html=True)
    if st.button("01 DASHBOARD", use_container_width=True): 
        st.session_state.page = 'DASHBOARD'
        st.rerun()
    if st.button("02 EXECUTION", use_container_width=True): 
        st.session_state.page = 'TRADE'
        st.rerun()
    if st.button("03 HEATMAP", use_container_width=True): 
        st.session_state.page = 'HEATMAP'
        st.rerun()
    st.markdown("<hr style='border-color:#222'>", unsafe_allow_html=True)
    if st.button("04 VAULT (WALLET SETUP)", use_container_width=True): 
        st.session_state.page = 'VAULT'
        st.rerun()

# --- CARICAMENTO DATI ---
bal = get_data("balances")
trades = get_data("trades")

# --- LOGICA PAGINE ---

if st.session_state.page == 'VAULT':
    st.markdown("<h2 style='color:white; font-size:14px;'>/ROOT/VAULT_MANAGER</h2>", unsafe_allow_html=True)
    with st.form("vault_form"):
        st.write("INIZIALIZZA RISERVE LIQUIDITA")
        c1, c2, c3 = st.columns(3)
        v_name = c1.text_input("NOME PORTAFOGLIO")
        v_curr = c2.selectbox("VALUTA", ["EUR", "USD", "GBP", "BTC", "USDT"])
        v_amount = c3.number_input("DEPOSITO INIZIALE", min_value=0.0)
        if st.form_submit_button("SYNC TO CLOUD"):
            # Logica di update semplificata
            supabase.table("balances").upsert({"portfolio": v_name, "currency": v_curr, "amount": v_amount}, on_conflict="portfolio,currency").execute()
            st.success("VAULT UPDATED")
            st.rerun()

elif st.session_state.page == 'TRADE':
    st.markdown("<h2 style='color:white; font-size:14px;'>/ROOT/EXECUTION_ENGINE</h2>", unsafe_allow_html=True)
    if bal.empty:
        st.warning("Configura prima un portafoglio nel VAULT.")
    else:
        with st.form("exec_form"):
            col1, col2, col3 = st.columns(3)
            p_sel = col1.selectbox("PORTFOLIO", bal['portfolio'].unique())
            c_sel = col2.selectbox("CCY", ["EUR", "USD", "BTC", "USDT"])
            status = col3.selectbox("STATUS", ["OPEN", "CLOSED"])
            
            asset = st.text_input("TICKER")
            entry = st.number_input("ENTRY", format="%.5f")
            exit_p = st.number_input("EXIT", format="%.5f")
            
            if st.form_submit_button("EXECUTE"):
                profit = (exit_p - entry) if status == "CLOSED" else 0
                supabase.table("trades").insert({"portfolio": p_sel, "asset": asset, "profit": profit, "currency": c_sel, "status": status, "date": str(datetime.date.today())}).execute()
                if status == "CLOSED":
                    # Aggiorna saldo
                    current_liq = bal[(bal['portfolio']==p_sel) & (bal['currency']==c_sel)]['amount'].iloc[0]
                    supabase.table("balances").update({"amount": current_liq + profit}).eq("portfolio", p_sel).eq("currency", c_sel).execute()
                st.success("DONE")
                st.rerun()

else: # Default DASHBOARD
    st.markdown("<h2 style='color:white; font-size:14px;'>/ROOT/LIVE_MONITOR</h2>", unsafe_allow_html=True)
    if not bal.empty:
        cols = st.columns(len(bal['portfolio'].unique()))
        for i, p_name in enumerate(bal['portfolio'].unique()):
            with cols[i]:
                st.markdown(f"<div class='panel'><div style='font-size:10px; color:#555'>{p_name}</div>", unsafe_allow_html=True)
                p_subset = bal[bal['portfolio'] == p_name]
                for _, row in p_subset.iterrows():
                    st.markdown(f"<div style='color:white; font-weight:700'>{row['amount']:,.2f} <span style='color:#0070FF'>{row['currency']}</span></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Nessun dato nel Vault. Vai alla sezione 04.")
