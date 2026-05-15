import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONNESSIONE ---
@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 3. CSS PROFESSIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        .block-container { padding-top: 4rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; max-width: 100% !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; padding-top: 2rem !important; }
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; width: 100% !important; text-align: left !important; padding: 10px 15px !important; }
        .stButton>button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
        [data-testid="stDataEditor"] div { font-size: 11px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

# --- 5. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-bottom:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

trades = get_data("trades")

# --- 6. TRADE EXECUTION ---
if st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=True):
        with st.form("advanced_trade", clear_on_submit=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            asset = r1c1.text_input("TICKER")
            side = r1c2.selectbox("SIDE", ["LONG", "SHORT"])
            shares = r1c3.number_input("QUANTITÀ", min_value=0.0, step=0.01)
            entry = r1c4.number_input("ENTRY PRICE", min_value=0.0)
            
            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            exit_p = r2c1.number_input("EXIT PRICE", min_value=0.0, value=0.0)
            open_d = r2c2.date_input("OPEN DATE", value=datetime.date.today())
            close_d = r2c3.date_input("CLOSE DATE", value=None)
            lev = r2c4.number_input("LEVERAGE", min_value=1.0, value=1.0)
            
            if st.form_submit_button("REGISTRA POSIZIONE"):
                # LOGICA STATO AUTOMATICA
                status = "CHIUSA" if exit_p > 0 else "APERTA"
                final_close_date = None
                if exit_p > 0:
                    final_close_date = str(close_d) if close_d else str(datetime.date.today())
                
                cost = round((entry * shares) / lev, 2)
                pnl_netto, pnl_perc = 0.0, 0.0
                
                if exit_p > 0:
                    m = 1 if side == "LONG" else -1
                    pnl_netto = round(((exit_p - entry) * shares * m), 2)
                    pnl_perc = round((pnl_netto / cost * 100), 2) if cost > 0 else 0.0
                
                supabase.table("trades").insert({
                    "asset": asset, "side": side, "shares": round(shares, 2), "entry_price": round(entry, 2),
                    "exit_price": round(exit_p, 2), "status": status, "date": str(open_d),
                    "close_date": final_close_date, "leverage": lev, "cost": cost,
                    "profit": pnl_netto, "pnl_perc": pnl_perc,
                    "instrument": "Stock", "currency": "USD"
                }).execute()
                st.rerun()

    if not trades.empty:
        # Arrotondamento forzato display
        num_cols = ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'cost']
        for c in num_cols:
            if c in trades.columns:
                trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)

        # Ordinamento: APERTE in alto
        trades = trades.sort_values(by="status", ascending=False)

        def style_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            styles['status'] = df['status'].apply(lambda x: 'color: #00FF41; font-weight: bold' if x == "APERTA" else 'color: #555')
            return styles

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM // AUTO_STATUS_LOGIC</div>", unsafe_allow_html=True)
        
        edited_trades = st.data_editor(
            trades.style.apply(style_ledger, axis=None), 
            use_container_width=True, hide_index=True, num_rows="dynamic",
            disabled=["id", "cost", "profit", "pnl_perc", "status"], # Status disabilitato perché calcolato
            column_config={
                "asset": st.column_config.TextColumn("TKR", width=50),
                "side": st.column_config.TextColumn("S", width=40),
                "shares": st.column_config.NumberColumn("QTY", format="%.2f", width=60),
                "entry_price": st.column_config.NumberColumn("IN", format="%.2f", width=65),
                "exit_price": st.column_config.NumberColumn("OUT", format="%.2f", width=65),
                "cost": st.column_config.NumberColumn("COSTO", format="%.2f", width=75),
                "profit": st.column_config.NumberColumn("P&L", format="%.2f", width=75),
                "pnl_perc": st.column_config.NumberColumn("%", format="%.2f%%", width=65),
                "status": st.column_config.TextColumn("STATO", width=80)
            },
            key="terminal_v6"
        )
        
        if st.button("SYNC"):
            try:
                ids_del = set(trades['id']) - set(edited_trades['id'])
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                
                for idx, row in edited_trades.iterrows():
                    p_in, p_out, qta = float(row['entry_price']), float(row['exit_price']), float(row['shares'])
                    
                    # LOGICA AUTOMATICA: Se OUT > 0 allora CHIUSA
                    nuovo_stato = "CHIUSA" if p_out > 0 else "APERTA"
                    
                    capitale = round((p_in * qta) / float(row['leverage']), 2)
                    pnl_n, pnl_p = 0.0, 0.0
                    
                    if p_out > 0:
                        m = 1 if row['side'] == "LONG" else -1
                        pnl_n = round(((p_out - p_in) * qta * m), 2)
                        pnl_p = round((pnl_n / capitale * 100), 2) if capitale > 0 else 0.0
                    
                    supabase.table("trades").update({
                        "exit_price": round(p_out, 2), 
                        "status": nuovo_stato, 
                        "cost": capitale,
                        "profit": pnl_n, 
                        "pnl_perc": pnl_p,
                        "close_date": str(row['close_date']) if p_out > 0 else None
                    }).eq("id", row['id']).execute()
                st.rerun()
            except Exception as e: st.error(f"Sync Error: {e}")
