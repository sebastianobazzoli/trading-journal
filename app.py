import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="auto")

# --- 2. CSS RESPONSIVE & ISTITUZIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Reset e Font */
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #050505 !important; 
            font-family: 'Roboto Mono', monospace !important; 
            color: #CCC; 
        }

        /* Sidebar Responsive */
        [data-testid="stSidebar"] { 
            background-color: #080808 !important; 
            border-right: 1px solid #1A1A1A !important; 
        }

        /* Gestione larghezza per schermi grandi */
        @media (min-width: 992px) {
            [data-testid="stSidebar"] { min-width: 300px !important; }
        }

        /* Adattamento per Mobile */
        @media (max-width: 991px) {
            [data-testid="stSidebar"] { min-width: 100% !important; }
        }

        /* Bottoni Menu */
        .stButton>button { 
            background-color: transparent !important; 
            border: 1px solid #222 !important; 
            color: #888 !important; 
            border-radius: 0px !important; 
            text-align: left !important; 
            width: 100%;
            padding: 12px 15px !important;
            margin-bottom: 5px;
            font-size: 13px !important;
        }
        .stButton>button:hover { 
            color: #00FF41 !important; 
            border-color: #00FF41 !important; 
            background-color: #00FF4105 !important;
        }

        /* Pannelli Grid Responsive */
        .panel { 
            border: 1px solid #1A1A1A; 
            padding: 15px; 
            background: #0A0A0A; 
            margin-bottom: 10px; 
            height: 100%;
        }

        /* Nascondi elementi inutili per pulizia */
        header { visibility: visible !important; background: transparent !important; }
        [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; margin-bottom:20px; font-size:18px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#444; font-size:10px; margin-bottom:30px;'>NETWORK_STATUS: ENCRYPTED</div>", unsafe_allow_html=True)
    
    # Navigazione
    if st.button("[01] MONITOR_DASH"):
        st.session_state.page = 'DASHBOARD'
        st.rerun()
    if st.button("[02] TRADE_EXEC"):
        st.session_state.page = 'TRADE'
        st.rerun()
    if st.button("[03] HEATMAP_RISK"):
        st.session_state.page = 'HEATMAP'
        st.rerun()
    
    st.markdown("<div style='height: 30vh;'></div>", unsafe_allow_html=True)
    
    if st.button("[04] VAULT_RESERVES"):
        st.session_state.page = 'VAULT'
        st.rerun()

# --- 5. LOGICA PAGINE ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

if st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_SETUP")
    with st.form("v_form"):
        n = st.text_input("ACCOUNT_ID")
        c = st.selectbox("CURRENCY", ["USD", "EUR", "BTC", "USDT"])
        a = st.number_input("CAPITAL", min_value=0.0)
        if st.form_submit_button("COMMIT_SYNC"):
            supabase.table("balances").upsert({"portfolio": n, "currency": c, "amount": a}, on_conflict="portfolio,currency").execute()
            st.rerun()

elif st.session_state.page == 'DASHBOARD':
    st.markdown("### / TERMINAL_OVERVIEW")
    bal = get_data("balances")
    
    if bal.empty:
        st.info("SISTEMA_VUOTO. Inizializzare VAULT [04].")
    else:
        # Layout Responsive delle card
        st.markdown("<div style='color:#555; font-size:10px; margin-bottom:15px;'>CONSOLIDATED_RESERVES:</div>", unsafe_allow_html=True)
        
        # Grid dinamica: 1 colonna su mobile, N su desktop
        portfolios = bal['portfolio'].unique()
        cols = st.columns(min(len(portfolios), 3))
        
        for i, p_name in enumerate(portfolios):
            col_idx = i % 3
            with cols[col_idx]:
                st.markdown(f"<div class='panel'>", unsafe_allow_html=True)
                st.markdown(f"<div style='color:#0070FF; font-size:12px; font-weight:700;'>{p_name}</div>", unsafe_allow_html=True)
                p_subset = bal[bal['portfolio'] == p_name]
                for _, row in p_subset.iterrows():
                    st.markdown(f"<div style='font-size:20px; font-weight:700; color:white;'>{row['amount']:,.2f} <span style='color:#444; font-size:12px;'>{row['currency']}</span></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

# Aggiungi qui le altre pagine (Trade, Heatmap) seguendo la stessa logica
