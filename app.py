import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(
    page_title="TERMINAL_X", 
    layout="wide", 
    initial_sidebar_state="expanded" 
)

# --- 2. CSS ISTITUZIONALE (Senza Emoji) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;700&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #050505 !important;
            font-family: 'Roboto Mono', monospace !important;
        }

        [data-testid="stSidebar"] {
            background-color: #080808 !important;
            border-right: 1px solid #1A1A1A !important;
            min-width: 280px !important;
        }

        /* Navigazione Alfanumerica stile Terminale */
        [data-testid="stSidebar"] .stButton button {
            background-color: transparent !important;
            border: 1px solid #222 !important;
            color: #888 !important;
            border-radius: 0px !important;
            text-align: left !important;
            font-size: 12px !important;
            letter-spacing: 1px !important;
            margin-bottom: -1px !important; /* Effetto lista compatta */
        }

        [data-testid="stSidebar"] .stButton button:hover {
            color: #00FF41 !important;
            border-color: #00FF41 !important;
            background-color: #00FF4105 !important;
        }

        .panel { 
            border: 1px solid #1A1A1A; 
            padding: 18px; 
            background: #0A0A0A; 
            border-radius: 2px; 
        }

        .status-dot {
            height: 8px; width: 8px; border-radius: 50%; display: inline-block; margin-right: 5px;
        }
        
        header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"AUTH_ERROR: {e}")
    st.stop()

# --- 4. LOGICA NAVIGAZIONE ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

with st.sidebar:
    st.markdown("""
        <div style='padding: 10px 0px 40px 0px;'>
            <div style='color:#00FF41; font-weight:700; font-size:16px;'>TERMINAL ACCESS</div>
            <div style='color:#444; font-size:9px;'>ID: PRO-USR-9921 | SECURE_MODE</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Navigazione codificata
    if st.button(" [01] MAIN_DASHBOARD", use_container_width=True):
        st.session_state.page = 'DASHBOARD'
        st.rerun()
    if st.button(" [02] TRADE_EXECUTION", use_container_width=True):
        st.session_state.page = 'TRADE'
        st.rerun()
    if st.button(" [03] RISK_HEATMAP", use_container_width=True):
        st.session_state.page = 'HEATMAP'
        st.rerun()
    
    st.markdown("<div style='height: 45vh;'></div>", unsafe_allow_html=True)
    
    if st.button(" [04] VAULT_SETTINGS", use_container_width=True):
        st.session_state.page = 'VAULT'
        st.rerun()
    
    st.markdown("""
        <div style='border-top: 1px solid #1A1A1A; padding-top: 20px; color:#333; font-size:9px;'>
            SYSTEM_STATUS: <span style='color:#00FF41;'>CONNECTED</span><br>
            LATENCY: 12ms
        </div>
    """, unsafe_allow_html=True)

# --- 5. LOGICA PAGINE ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

if st.session_state.page == 'VAULT':
    st.markdown("<h3 style='color:white; font-size:14px; border-bottom: 1px solid #222; padding-bottom:10px;'>/ PORTFOLIO_VAULT / CONFIGURATION</h3>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        with st.form("vault_form"):
            c1, c2 = st.columns(2)
            p_name = c1.text_input("IDENTIFIER (e.g. IBKR_01)")
            p_curr = c2.selectbox("CURRENCY_BASE", ["USD", "EUR", "BTC", "USDT"])
            p_amount = st.number_input("INITIAL_LIQUIDITY", min_value=0.0)
            if st.form_submit_button("COMMIT_CHANGES"):
                supabase.table("balances").upsert({"portfolio": p_name, "currency": p_curr, "amount": p_amount}).execute()
                st.toast("DATA_SYNC_COMPLETE")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.page == 'DASHBOARD':
    st.markdown("<h3 style='color:white; font-size:14px; border-bottom: 1px solid #222; padding-bottom:10px;'>/ MARKET_DATA / AGGREGATED_VIEW</h3>", unsafe_allow_html=True)
    
    bal = get_data("balances")
    
    if bal.empty:
        st.markdown("<div style='color:#444; padding:20px;'>NO_RECORDS_FOUND. INITIALIZE_VAULT_REQUIRED.</div>", unsafe_allow_html=True)
    else:
        # Griglia Saldi stile Bloomberg (Senza icone, solo testo e linee)
        st.markdown("<div style='color:#888; font-size:10px; margin-bottom:10px;'>CONSOLIDATED_BALANCES:</div>", unsafe_allow_html=True)
        for p in bal['portfolio'].unique():
            cols = st.columns(4)
            p_subset = bal[bal['portfolio'] == p]
            with cols[0]:
                st.markdown(f"<div style='color:#0070FF; font-weight:700;'>{p}</div>", unsafe_allow_html=True)
            for idx, r in enumerate(p_subset.iloc):
                if idx+1 < 4:
                    with cols[idx+1]:
                        st.markdown(f"""
                            <div style='border-left: 1px solid #1A1A1A; padding-left:10px;'>
                                <div style='color:#555; font-size:9px;'>{r['currency']}</div>
                                <div style='color:white; font-size:16px; font-weight:700;'>{r['amount']:,.2f}</div>
                            </div>
                        """, unsafe_allow_html=True)
