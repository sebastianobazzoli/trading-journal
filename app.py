import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: #00FF41 !important; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; padding: 10px 15px !important; font-size: 12px !important; }
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 4. FUNZIONI DATI ---
def get_data(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- 5. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

# --- 6. LOGICA TRADE (TABELLA MODIFICABILE) ---
if st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG / INTERACTIVE_LEDGER")
    
    # Form di inserimento rapido (già esistente)
    with st.expander("NEW_ENTRY_FORM", expanded=False):
        # ... (Mantieni qui il form di inserimento che abbiamo scritto nell'ultimo script)
        pass

    # --- LEDGER MODIFICABILE ---
    df_trades = get_data("trades")
    
    if not df_trades.empty:
        st.markdown("<div style='color:#555; font-size:10px; margin-bottom:5px;'>EDIT_MODE: Modifica lo stato o i prezzi direttamente nella tabella e clicca fuori per salvare.</div>", unsafe_allow_html=True)
        
        # Rendiamo la colonna 'id' non modificabile poiché è la chiave primaria
        edited_df = st.data_editor(
            df_trades,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # Nasconde l'ID per sicurezza o lo rende bloccato
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"], required=True),
                "side": st.column_config.SelectboxColumn("SIDE", options=["LONG", "SHORT"]),
                "instrument": st.column_config.SelectboxColumn("TYPE", options=["Stock", "CFD", "ETF", "Crypto", "Forex"])
            },
            disabled=["id", "cost", "notional", "profit", "pnl_perc", "date"], # Impedisce la modifica manuale dei calcoli
            key="trades_editor"
        )

        # Logica di salvataggio modifiche
        if st.button("SAVE_CHANGES_TO_DATABASE"):
            # Identifichiamo cosa è cambiato confrontando i due dataframe
            # In un'app reale si userebbe st.session_state.trades_editor["edited_rows"]
            for index, row in edited_df.iterrows():
                # Ricalcolo automatico P&L se l'utente ha inserito il prezzo di uscita
                if row['status'] == "CLOSED" and row['exit_price'] > 0:
                    pnl = (((row['exit_price'] - row['entry_price']) * row['shares']) if row['side'] == "LONG" else ((row['entry_price'] - row['exit_price']) * row['shares'])) - row['fees']
                    pnl_p = (pnl / row['cost']) * 100 if row['cost'] > 0 else 0
                    row['profit'] = pnl
                    row['pnl_perc'] = pnl_p

                # Update su Supabase usando l'ID univoco
                supabase.table("trades").update({
                    "status": row['status'],
                    "exit_price": row['exit_price'],
                    "profit": row['profit'],
                    "pnl_perc": row['pnl_perc'],
                    "close_date": str(row['close_date'])
                }).eq("id", row['id']).execute()
            
            st.success("DATABASE_SYNCHRONIZED")
            st.rerun()
    else:
        st.info("NO_TRADES_TO_DISPLAY")

# --- (Mantieni DASHBOARD e VAULT come nell'ultimo script completo) ---
