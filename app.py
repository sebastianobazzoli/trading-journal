import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE INTEGRALE ---
# initial_sidebar_state="expanded" FORZA l'apertura del menu
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS BLOOMBERG (PULITO) ---
# Ho rimosso il "visibility: hidden" dall'header per evitare che si blocchi il menu
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Sfondo Nero Totale */
        .stApp { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        
        /* Sidebar Stile Terminale */
        [data-testid="stSidebar"] { 
            background-color: #080808 !important; 
            border-right: 1px solid #1A1A1A !important; 
            min-width: 280px !important; 
        }

        /* Pulsanti Alfanumerici */
        .stButton>button { 
            background-color: transparent !important; 
            border: 1px solid #222 !important; 
            color: #888 !important; 
            border-radius: 0px !important; 
            text-align: left !important; 
            width: 100%;
            margin-bottom: 5px;
        }
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
        
        /* Pannelli Dati */
        .panel { border: 1px solid #1A1A1A; padding: 15px; background: #0A0A0A; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

if supabase is None:
    st.error("CONFIG_ERROR: Controlla SUPABASE_URL e SUPABASE_KEY nei Secrets di Streamlit.")
    st.stop()

# --- 4. NAVIGAZIONE ROBUSTA ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

# La Sidebar deve essere definita qui per essere sempre renderizzata
with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; margin-bottom:30px;'>TERMINAL_OS / ACCESS_GRANTED</div>", unsafe_allow_html=True)
    
    if st.button("[01] MONITOR_DASHBOARD"):
        st.session_state.page = 'DASHBOARD'
        st.rerun()
        
    if st.button("[02] EXECUTION_LOG"):
        st.session_state.page = 'TRADE'
        st.rerun()
        
    if st.button("[03] VAULT_RESERVES"):
        st.session_state.page = 'VAULT'
        st.rerun()

# --- 5. LOGICA PAGINE ---

def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

if st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_SETUP")
    with st.form("v_form"):
        st.write("Configura Riserve di Liquidità")
        n = st.text_input("ACCOUNT_NAME")
        c = st.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"])
        a = st.number_input("INITIAL_CAPITAL", min_value=0.0)
        if st.form_submit_button("COMMIT_SYNC"):
            supabase.table("balances").upsert({"portfolio": n, "currency": c, "amount": a}, on_conflict="portfolio,currency").execute()
            st.success("SYNC_OK")
            st.rerun()

elif st.session_state.page == 'TRADE':
    st.markdown("### / TRADE_EXECUTION")
    bal = get_data("balances")
    if bal.empty:
        st.warning("Esegui prima il setup del VAULT [03].")
    else:
        with st.form("t_form"):
            p_sel = st.selectbox("ACCOUNT", bal['portfolio'].unique())
            asset = st.text_input("TICKER")
            side = st.selectbox("SIDE", ["LONG", "SHORT"])
            entry = st.number_input("ENTRY_PRICE", format="%.5f")
            exit_p = st.number_input("EXIT_PRICE", format="%.5f")
            status = st.selectbox("STATUS", ["OPEN", "CLOSED"])
            
            if st.form_submit_button("EXECUTE"):
                profit = (exit_p - entry) if (status == "CLOSED" and side == "LONG") else (entry - exit_p if status == "CLOSED" else 0)
                # Inserimento Trade
                supabase.table("trades").insert({"portfolio": p_sel, "asset": asset, "profit": profit, "currency": "USD", "status": status, "date": str(datetime.date.today())}).execute()
                # Aggiornamento Saldo
                if status == "CLOSED":
                    current_liq = bal[(bal['portfolio'] == p_sel)]['amount'].sum()
                    supabase.table("balances").update({"amount": current_liq + profit}).eq("portfolio", p_sel).execute()
                st.success("TRADE_LOGGED")
                st.rerun()

else: # DASHBOARD
    st.markdown("### / LIVE_SYSTEM_MONITOR")
    bal = get_data("balances")
    if bal.empty:
        st.info("SISTEMA VUOTO. Inizializzare VAULT [03] per caricare i dati.")
    else:
        cols = st.columns(len(bal['portfolio'].unique()))
        for i, p_name in enumerate(bal['portfolio'].unique()):
            with cols[i]:
                st.markdown(f"<div class='panel'><div style='color:#555; font-size:10px;'>{p_name}</div>", unsafe_allow_html=True)
                p_subset = bal[bal['portfolio'] == p_name]
                for _, row in p_subset.iterrows():
                    st.markdown(f"<div style='font-size:20px; font-weight:700;'>{row['amount']:,.2f} <span style='color:#0070FF; font-size:12px;'>{row['currency']}</span></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
