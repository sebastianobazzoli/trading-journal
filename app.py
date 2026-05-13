import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- CONNESSIONE ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: #00FF41 !important; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; padding: 10px 15px !important; font-size: 12px !important; }
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
    </style>
""", unsafe_allow_html=True)

# --- NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

# --- LOGICA TRADE ---
if st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    # Recupero dati
    res = supabase.table("trades").select("*").execute()
    df_trades = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    if not df_trades.empty:
        # PROTEZIONE KEYERROR: Se la colonna non esiste nel DB, la creiamo vuota nel DF per non far crashare l'editor
        if 'close_date' not in df_trades.columns:
            df_trades['close_date'] = None

        st.markdown("<div style='color:#555; font-size:10px;'>MODIFICA I DATI E SALVA:</div>", unsafe_allow_html=True)
        
        # Editor Interattivo
        edited_df = st.data_editor(
            df_trades,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, 
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"]),
                "close_date": st.column_config.DateColumn("CLOSE_DATE")
            },
            disabled=["id", "cost", "notional", "profit", "pnl_perc", "date"],
            key="trades_editor"
        )

        if st.button("COMMIT_CHANGES_TO_DATABASE"):
            try:
                for index, row in edited_df.iterrows():
                    # Calcolo P&L dinamico se chiuso
                    p_pnl = row['profit']
                    p_perc = row['pnl_perc']
                    
                    if row['status'] == "CLOSED" and row['exit_price'] > 0:
                        p_pnl = (((row['exit_price'] - row['entry_price']) * row['shares']) if row['side'] == "LONG" else ((row['entry_price'] - row['exit_price']) * row['shares'])) - row['fees']
                        p_perc = (p_pnl / row['cost']) * 100 if row['cost'] > 0 else 0

                    # Update
                    supabase.table("trades").update({
                        "status": row['status'],
                        "exit_price": row['exit_price'],
                        "profit": p_pnl,
                        "pnl_perc": p_perc,
                        "close_date": str(row['close_date']) if row['close_date'] else None
                    }).eq("id", row['id']).execute()
                
                st.success("SYNC_COMPLETE")
                st.rerun()
            except Exception as e:
                st.error(f"UPDATE_ERROR: {e}")
    else:
        st.info("NO_TRADES_FOUND")

# --- DASHBOARD (Semplificata) ---
elif st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    st.write("Dati in caricamento...")
    # (Inserire qui la logica dei ticker e grafici dei messaggi precedenti)
