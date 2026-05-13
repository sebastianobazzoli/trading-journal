import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS TERMINAL: LOOK ISTITUZIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; transition: none !important; }
        
        /* Posizionamento fisso del tasto sidebar */
        [data-testid="stSidebarCollapseByFrame"] { color: #00FF41 !important; top: 10px !important; left: 10px !important; }

        /* Stile Pannelli Dashboard */
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; height: 100%; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .ticker-price { font-size: 18px; font-weight: 700; margin-top: 4px; }
        
        /* Bottoni Sidebar */
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; padding: 10px 15px !important; font-size: 12px !important; }
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
        
        header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'

def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#444; font-size:9px; margin-bottom:40px;'>v.4.2 // MULTICURRENCY_ENGINE</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASH", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] EXECUTION_LOG", on_click=set_page, args=('TRADE',))
    st.button("[03] HEATMAP_RISK", on_click=set_page, args=('HEATMAP',))
    st.markdown("<div style='height: 40vh;'></div>", unsafe_allow_html=True)
    st.button("[04] VAULT_SETUP", on_click=set_page, args=('VAULT',))

# --- 5. LOGICA DASHBOARD (ORGANIZZAZIONE ORIGINALE) ---

if st.session_state.page == 'DASHBOARD':
    # --- RIGA 1: TICKER WALL (Dati Reali) ---
    market_tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC/USD": "BTC-USD", "GOLD": "GC=F"}
    t_cols = st.columns(len(market_tickers))
    
    for i, (name, sym) in enumerate(market_tickers.items()):
        try:
            ticker_data = yf.Ticker(sym).history(period="2d")
            price = ticker_data['Close'].iloc[-1]
            change = ((price / ticker_data['Close'].iloc[-2]) - 1) * 100
            color = "#00FF41" if change > 0 else "#FF3131"
            with t_cols[i]:
                st.markdown(f"""
                    <div class="panel">
                        <div class="ticker-label">{name}</div>
                        <div class="ticker-price" style="color:{color}">{price:,.2f} <span style="font-size:10px;">{change:+.2f}%</span></div>
                    </div>
                """, unsafe_allow_html=True)
        except: pass

    st.markdown("<br>", unsafe_allow_html=True)

    # --- RIGA 2: VAULT MONITOR (Multicurrency) ---
    st.markdown("<div style='color:#555; font-size:10px; margin-bottom:10px;'>CONSOLIDATED_VAULT_RESERVES:</div>", unsafe_allow_html=True)
    
    res = supabase.table("balances").select("*").execute()
    bal = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not bal.empty:
        for p_name in bal['portfolio'].unique():
            st.markdown(f"<div style='border-left: 2px solid #0070FF; padding-left: 15px; margin-bottom:10px; color:white; font-size:12px; font-weight:700;'>{p_name}</div>", unsafe_allow_html=True)
            p_subset = bal[bal['portfolio'] == p_name]
            # Grid dinamica per le valute del portafoglio
            v_cols = st.columns(4) 
            for j, (_, row) in enumerate(p_subset.iterrows()):
                with v_cols[j % 4]:
                    st.markdown(f"""
                        <div class="panel">
                            <div class="ticker-label">{row['currency']}</div>
                            <div class="ticker-price">{row['amount']:,.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("NO_RECORDS. ACCESS [04] VAULT_SETUP.")

# --- PAGINA VAULT (LOGICA DI AGGIORNAMENTO) ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_MANAGER")
    with st.form("v_form"):
        c1, c2, c3 = st.columns(3)
        p_name = c1.text_input("ACCOUNT_ID")
        p_curr = c2.selectbox("CURRENCY", ["USD", "EUR", "GBP", "BTC", "USDT"])
        p_amt = c3.number_input("INITIAL_CAPITAL", min_value=0.0)
        if st.form_submit_button("SYNC_TO_CLOUD"):
            supabase.table("balances").upsert({"portfolio": p_name, "currency": p_curr, "amount": p_amt}, on_conflict="portfolio,currency").execute()
            st.rerun()
