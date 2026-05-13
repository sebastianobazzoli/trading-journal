import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE AGGRESSIVA ---
st.set_page_config(
    page_title="TERMINAL X", 
    layout="wide", 
    initial_sidebar_state="expanded" 
)

# --- 2. CSS RADICALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;700&display=swap');
        
        /* Forza sfondo e font ovunque */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #050505 !important;
            font-family: 'Roboto Mono', monospace !important;
        }

        /* Forza la Sidebar a essere visibile e larga */
        [data-testid="stSidebar"] {
            background-color: #0A0A0A !important;
            border-right: 1px solid #1A1A1A !important;
            min-width: 300px !important;
            z-index: 999999 !important;
            visibility: visible !important;
        }

        /* Rendi i bottoni della sidebar giganti e cliccabili */
        [data-testid="stSidebar"] .stButton button {
            background-color: #111 !important;
            border: 1px solid #333 !important;
            color: #00FF41 !important;
            padding: 15px !important;
            text-align: left !important;
            font-size: 14px !important;
        }

        .panel { 
            border: 1px solid #1A1A1A; 
            padding: 20px; 
            background: #0D0D0D; 
            border-radius: 4px; 
        }

        /* Nascondi header ma tieni il pulsante di sblocco sidebar */
        header { background: rgba(0,0,0,0) !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Errore Secrets: {e}")
    st.stop()

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

# SIDEBAR FORZATA
with st.sidebar:
    st.markdown("<h1 style='color:white; font-size:22px; margin-bottom:10px;'>TERMINAL X</h1>", unsafe_allow_html=True)
    st.markdown("<div style='color:#444; font-size:10px; margin-bottom:40px;'>CORE_SYSTEM_ACTIVE</div>", unsafe_allow_html=True)
    
    if st.button("📊 01 DASHBOARD", use_container_width=True):
        st.session_state.page = 'DASHBOARD'
        st.rerun()
    if st.button("⌨️ 02 EXECUTION", use_container_width=True):
        st.session_state.page = 'TRADE'
        st.rerun()
    if st.button("🔥 03 HEATMAP", use_container_width=True):
        st.session_state.page = 'HEATMAP'
        st.rerun()
    
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    if st.button("⚙️ 04 VAULT SETUP", use_container_width=True):
        st.session_state.page = 'VAULT'
        st.rerun()

# --- 5. LOGICA PAGINE ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

# CARICAMENTO DATI
bal = get_data("balances")

if st.session_state.page == 'VAULT':
    st.markdown("<h2 style='color:#0070FF;'>[04] VAULT_CONFIGURATION</h2>", unsafe_allow_html=True)
    st.write("Configura qui la tua liquidità iniziale per attivare i grafici.")
    with st.form("vault_form"):
        p_name = st.text_input("Nome Portafoglio (es. IBKR)")
        p_curr = st.selectbox("Valuta", ["USD", "EUR", "BTC"])
        p_amount = st.number_input("Capitale Iniziale", min_value=0.0)
        if st.form_submit_button("SYNC TO CLOUD"):
            supabase.table("balances").upsert({"portfolio": p_name, "currency": p_curr, "amount": p_amount}).execute()
            st.success("Sincronizzazione completata!")
            st.rerun()

elif st.session_state.page == 'TRADE':
    st.markdown("<h2 style='color:#0070FF;'>[02] EXECUTION_LOG</h2>", unsafe_allow_html=True)
    # Form trade...

else: # DASHBOARD
    st.markdown("<h2 style='color:#00FF41;'>[01] LIVE_MONITOR</h2>", unsafe_allow_html=True)
    
    if bal.empty:
        st.markdown("""
            <div class='panel' style='border-color: #333; margin-top: 50px;'>
                <p style='color: #888;'>Nessun dato rilevato nel database.</p>
                <p style='color: #444;'>Usa il menu a sinistra e vai su <b>04 VAULT SETUP</b> per iniziare.</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Qui va la logica dei grafici e dei saldi che abbiamo scritto prima
        st.write("Dati caricati. Visualizzazione in corso...")
        # (Codice dashboard già fornito)
