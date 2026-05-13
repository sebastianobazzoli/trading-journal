import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE PAGINA (Deve essere la prima istruzione) ---
st.set_page_config(page_title="TERMINAL X", layout="wide")

# --- 2. CSS MINIMALISTA (Rimosso tutto ciò che può nascondere elementi) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;700&display=swap');
        * { font-family: 'Roboto Mono', monospace !important; }
        .stApp { background-color: #050505; color: #CCCCCC; }
        /* Forza la visibilità della sidebar */
        [data-testid="stSidebar"] { 
            background-color: #0A0A0A !important; 
            border-right: 1px solid #1A1A1A;
            visibility: visible !important;
            display: block !important;
        }
        .panel { border: 1px solid #1A1A1A; padding: 15px; background: #0D0D0D; border-radius: 4px; margin-bottom: 10px; }
        header, footer { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE DATABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Errore critico nei Secrets: {e}")
    st.stop()

# --- 4. NAVIGAZIONE (Spostata in alto per precedenza di rendering) ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

# Definizione Sidebar
with st.sidebar:
    st.markdown("<h2 style='color:white; font-size:16px;'>TERMINAL_OS</h2>", unsafe_allow_html=True)
    st.divider()
    
    # Pulsanti di navigazione con logica di aggiornamento immediato
    if st.button("01 DASHBOARD", use_container_width=True):
        st.session_state.page = 'DASHBOARD'
        st.rerun()
    if st.button("02 EXECUTION", use_container_width=True):
        st.session_state.page = 'TRADE'
        st.rerun()
    if st.button("03 HEATMAP", use_container_width=True):
        st.session_state.page = 'HEATMAP'
        st.rerun()
    if st.button("04 VAULT SETUP", use_container_width=True):
        st.session_state.page = 'VAULT'
        st.rerun()

# --- 5. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 6. LOGICA PAGINE ---
bal = get_data("balances")
trades = get_data("trades")

if st.session_state.page == 'VAULT':
    st.title("Vault Management")
    with st.form("vault_form"):
        c1, c2, c3 = st.columns(3)
        v_name = c1.text_input("Nome Portafoglio")
        v_curr = c2.selectbox("Valuta", ["EUR", "USD", "BTC", "USDT"])
        v_amount = c3.number_input("Deposito", min_value=0.0)
        if st.form_submit_button("Sincronizza"):
            supabase.table("balances").upsert({
                "portfolio": v_name, "currency": v_curr, "amount": v_amount
            }).execute()
            st.success("Bilancio aggiornato")
            st.rerun()

elif st.session_state.page == 'TRADE':
    st.title("Execution Engine")
    if bal.empty:
        st.warning("Configura un portafoglio nel Vault prima di procedere.")
    else:
        with st.form("trade_form"):
            p_sel = st.selectbox("Portfolio", bal['portfolio'].unique())
            c_sel = st.selectbox("Currency", ["EUR", "USD", "BTC", "USDT"])
            asset = st.text_input("Ticker")
            status = st.selectbox("Status", ["OPEN", "CLOSED"])
            entry = st.number_input("Entry Price", format="%.5f")
            exit_p = st.number_input("Exit Price", format="%.5f")
            
            if st.form_submit_button("Invia Ordine"):
                profit = (exit_p - entry) if status == "CLOSED" else 0
                supabase.table("trades").insert({
                    "portfolio": p_sel, "asset": asset, "profit": profit, 
                    "currency": c_sel, "status": status, "date": str(datetime.date.today())
                }).execute()
                
                if status == "CLOSED" and profit != 0:
                    current = bal[(bal['portfolio']==p_sel) & (bal['currency']==c_sel)]['amount'].iloc[0]
                    supabase.table("balances").update({"amount": current + profit}).eq("portfolio", p_sel).eq("currency", c_sel).execute()
                st.success("Trade registrato")
                st.rerun()

else: # DASHBOARD
    st.title("Terminal Dashboard")
    if not bal.empty:
        cols = st.columns(len(bal['portfolio'].unique()))
        for i, p_name in enumerate(bal['portfolio'].unique()):
            with cols[i]:
                st.markdown(f"<div class='panel'><p style='color:#555; font-size:10px;'>{p_name}</p>", unsafe_allow_html=True)
                subset = bal[bal['portfolio'] == p_name]
                for _, r in subset.iterrows():
                    st.markdown(f"<p style='color:white; font-weight:700;'>{r['amount']:,.2f} <span style='color:#0070FF;'>{r['currency']}</span></p>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Nessun dato trovato. Accedi al VAULT SETUP per inizializzare i portafogli.")
