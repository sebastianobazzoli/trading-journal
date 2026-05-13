import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE PAGINA (Forza l'espansione della Sidebar) ---
st.set_page_config(
    page_title="TERMINAL X", 
    layout="wide", 
    initial_sidebar_state="expanded"  # Forza l'apertura all'avvio
)

# --- 2. CSS TERMINAL (Semplificato per evitare conflitti) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;700&display=swap');
        
        /* Tema Scuro Generale */
        .stApp { background-color: #050505; color: #CCCCCC; font-family: 'Roboto Mono', monospace !important; }
        
        /* Stile Sidebar */
        [data-testid="stSidebar"] {
            background-color: #0A0A0A !important;
            border-right: 1px solid #1A1A1A;
            min-width: 260px !important;
        }

        /* Pannelli Dashboard */
        .panel { 
            border: 1px solid #1A1A1A; 
            padding: 20px; 
            background: #0D0D0D; 
            border-radius: 4px; 
            margin-bottom: 15px; 
        }

        /* Bottoni Navigazione */
        .stButton>button {
            border: 1px solid #333 !important;
            background-color: transparent !important;
            color: #AAA !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 12px;
            transition: 0.3s;
        }
        .stButton>button:hover {
            border-color: #0070FF !important;
            color: white !important;
            background-color: #0070FF10 !important;
        }

        /* Nasconde Header Streamlit ma lascia visibile il bottone Sidebar */
        header { visibility: hidden; }
        .st-emotion-cache-16idsys p { font-family: 'Roboto Mono', monospace !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE DATABASE ---
try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Errore Secret: {e}")
    st.stop()

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

with st.sidebar:
    st.markdown("<h2 style='color:white; font-size:18px; font-weight:700; margin-bottom:20px;'>TERMINAL_OS</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#555; font-size:10px; margin-bottom:30px;'>STLY: INSTITUTIONAL DARK</p>", unsafe_allow_html=True)
    
    if st.button("01 DASHBOARD", use_container_width=True):
        st.session_state.page = 'DASHBOARD'
        st.rerun()
    if st.button("02 EXECUTION", use_container_width=True):
        st.session_state.page = 'TRADE'
        st.rerun()
    if st.button("03 HEATMAP", use_container_width=True):
        st.session_state.page = 'HEATMAP'
        st.rerun()
    
    st.markdown("<div style='height: 40vh;'></div>", unsafe_allow_html=True) # Spazio verticale
    
    if st.button("04 VAULT SETUP", use_container_width=True):
        st.session_state.page = 'VAULT'
        st.rerun()

# --- 5. LOGICA PAGINE ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

bal = get_data("balances")

if st.session_state.page == 'VAULT':
    st.markdown("<h1 style='font-size:24px;'>04 VAULT_CONFIG</h1>", unsafe_allow_html=True)
    with st.form("vault_form"):
        col1, col2 = st.columns(2)
        v_name = col1.text_input("Portfolio Name")
        v_curr = col2.selectbox("Currency", ["USD", "EUR", "BTC", "USDT"])
        v_amount = st.number_input("Initial Balance")
        if st.form_submit_button("SYNC_VAULT"):
            supabase.table("balances").upsert({"portfolio": v_name, "currency": v_curr, "amount": v_amount}).execute()
            st.success("VAULT_SYNCED")
            st.rerun()

elif st.session_state.page == 'TRADE':
    st.markdown("<h1 style='font-size:24px;'>02 TRADE_EXECUTION</h1>", unsafe_allow_html=True)
    # Form trade... (logica precedente)

else: # DASHBOARD
    st.markdown("<h1 style='font-size:24px; color:white;'>01 LIVE_MONITOR</h1>", unsafe_allow_html=True)
    if not bal.empty:
        cols = st.columns(len(bal['portfolio'].unique()))
        for i, p_name in enumerate(bal['portfolio'].unique()):
            with cols[i]:
                st.markdown(f"""
                <div class="panel">
                    <div style="font-size:10px; color:#555; font-weight:700;">ACCOUNT: {p_name}</div>
                """, unsafe_allow_html=True)
                subset = bal[bal['portfolio'] == p_name]
                for _, r in subset.iterrows():
                    st.markdown(f"<div style='font-size:20px; font-weight:700; color:white;'>{r['amount']:,.2f} <span style='color:#0070FF; font-size:12px;'>{r['currency']}</span></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
