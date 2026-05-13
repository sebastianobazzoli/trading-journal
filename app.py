import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(
    page_title="TERMINAL_X", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. CSS AVANZATO: FIX POSITIONING ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Sfondo e Font */
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #050505 !important; 
            font-family: 'Roboto Mono', monospace !important; 
            color: #CCC; 
        }

        /* FIX SIDEBAR: Posizione fissa e larghezza costante */
        [data-testid="stSidebar"] {
            background-color: #080808 !important;
            border-right: 1px solid #1A1A1A !important;
            transition: none !important; /* Rimuove lo scivolamento fastidioso */
        }

        /* STILIZZAZIONE FRECCETTE E BOTTONI DI SISTEMA */
        /* Rendiamo il tasto di apertura/chiusura più discreto e allineato */
        [data-testid="stSidebarCollapseByFrame"] {
            color: #00FF41 !important; /* Colore verde terminale */
            background-color: transparent !important;
            top: 10px !important;
            left: 10px !important;
        }

        /* Bottoni Navigazione */
        .stButton>button { 
            background-color: transparent !important; 
            border: 1px solid #222 !important; 
            color: #888 !important; 
            border-radius: 0px !important; 
            text-align: left !important; 
            width: 100%;
            padding: 10px 15px !important;
            font-size: 13px !important;
        }
        .stButton>button:hover { 
            color: #00FF41 !important; 
            border-color: #00FF41 !important;
        }

        /* Pannelli Dashboard */
        .panel { 
            border: 1px solid #1A1A1A; 
            padding: 15px; 
            background: #0A0A0A; 
            margin-bottom: 10px;
        }

        /* Header e Decorazioni inutili */
        header { background: rgba(0,0,0,0) !important; }
        [data-testid="stHeader"] { height: 0px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE SUPABASE ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

# Funzione per cambiare pagina
def set_page(name):
    st.session_state.page = name

# Rendering Sidebar
with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#444; font-size:9px; margin-bottom:40px;'>v.4.1 // SECURE_SYNC</div>", unsafe_allow_html=True)
    
    st.button("[01] MONITOR_DASH", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_LOG", on_click=set_page, args=('TRADE',))
    st.button("[03] RISK_HEATMAP", on_click=set_page, args=('HEATMAP',))
    
    st.markdown("<div style='height: 40vh;'></div>", unsafe_allow_html=True)
    
    st.button("[04] VAULT_CONFIG", on_click=set_page, args=('VAULT',))

# --- 5. LOGICA PAGINE ---
def fetch_balances():
    res = supabase.table("balances").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

if st.session_state.page == 'DASHBOARD':
    st.markdown("### / CONSOLIDATED_VIEW")
    bal = fetch_balances()
    
    if not bal.empty:
        # Layout pulito dei saldi
        for portfolio in bal['portfolio'].unique():
            st.markdown(f"<div style='color:#555; font-size:10px; margin-top:20px;'>ACCOUNT: {portfolio}</div>", unsafe_allow_html=True)
            p_data = bal[bal['portfolio'] == portfolio]
            cols = st.columns(len(p_data))
            for i, (_, row) in enumerate(p_data.iterrows()):
                with cols[i]:
                    st.markdown(f"""
                        <div class="panel">
                            <div style="color:#444; font-size:10px;">{row['currency']}</div>
                            <div style="color:white; font-size:22px; font-weight:700;">{row['amount']:,.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.warning("NO DATA FOUND. ACCESS VAULT [04].")

elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_SETUP")
    # Logica inserimento già implementata...
