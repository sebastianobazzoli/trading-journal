import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CSS ISTITUZIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; padding: 10px 15px !important; font-size: 12px !important; }
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
        header { visibility: hidden; }
        /* Stile Tabelle */
        [data-testid="stDataFrame"] { border: 1px solid #1A1A1A; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
@st.cache_resource
def init_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

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
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASH", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_SETUP", on_click=set_page, args=('VAULT',))

# --- 6. PAGINA TRADE EXECUTION (MIGLIORATA) ---
if st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG / DETAILED_ENTRY")
    
    bal = get_data("balances")
    
    if bal.empty:
        st.warning("CONFIG_VAULT_REQUIRED_BEFORE_EXECUTION")
    else:
        # --- FORM DI INSERIMENTO ---
        with st.form("advanced_trade_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            asset = c1.text_input("TICKER (Asset)")
            instrument = c2.selectbox("INSTRUMENT", ["Stock", "CFD", "ETF", "Crypto", "Forex"])
            shares = c3.number_input("SHARES / SIZE", min_value=0.0, format="%.4f")
            leverage = c4.number_input("LEVERAGE (1 = No Leva)", min_value=1.0, value=1.0)

            c5, c6, c7, c8 = st.columns(4)
            currency = c5.selectbox("CURRENCY", ["USD", "EUR", "BTC", "USDT"])
            # Filtra conti in base alla valuta selezionata
            available_accounts = bal[bal['currency'] == currency]['portfolio'].unique()
            account = c6.selectbox("ACCOUNT / PORTFOLIO", available_accounts if len(available_accounts)>0 else ["No Account for this CCY"])
            status = c7.selectbox("STATUS", ["OPEN", "CLOSED"])
            side = c8.selectbox("SIDE", ["LONG", "SHORT"])

            c9, c10, c11, c12 = st.columns(4)
            open_date = c9.date_input("OPEN_DATE", datetime.date.today())
            close_date = c10.date_input("CLOSE_DATE", datetime.date.today())
            entry_price = c11.number_input("AVG_ENTRY_PRICE", format="%.5f")
            exit_price = c12.number_input("AVG_EXIT_PRICE (0 if Open)", format="%.5f")

            c13, c14 = st.columns(2)
            fees = c13.number_input("COMMISSIONS / FEES", min_value=0.0, format="%.2f")
            
            # --- CALCOLI AUTOMATICI ---
            # Costo = (Prezzo * Shares) / Leva + Commissioni
            cost = ((entry_price * shares) / leverage) + fees
            # Controvalore = Prezzo * Shares
            notional = entry_price * shares
            
            if st.form_submit_button("COMMIT_TRADE_TO_LEDGER"):
                # Calcolo P&L se Chiuso
                pnl = 0
                pnl_perc = 0
                if status == "CLOSED":
                    pnl = ((exit_price - entry_price) * shares) if side == "LONG" else ((entry_price - exit_price) * shares)
                    pnl = pnl - fees
                    pnl_perc = (pnl / cost) * 100 if cost > 0 else 0

                trade_payload = {
                    "asset": asset, "instrument": instrument, "shares": shares, "leverage": leverage,
                    "currency": currency, "portfolio": account, "status": status, "side": side,
                    "open_date": str(open_date), "close_date": str(close_date),
                    "entry_price": entry_price, "exit_price": exit_price,
                    "fees": fees, "cost": cost, "notional": notional,
                    "profit": pnl, "pnl_perc": pnl_perc, "date": str(datetime.date.today())
                }
                
                supabase.table("trades").insert(trade_payload).execute()
                
                # Aggiornamento automatico del Vault se il trade è chiuso
                if status == "CLOSED":
                    current_liq = bal[(bal['portfolio'] == account) & (bal['currency'] == currency)]['amount'].iloc[0]
                    supabase.table("balances").update({"amount": current_liq + pnl}).eq("portfolio", account).eq("currency", currency).execute()
                
                st.success(f"TRADE_LOGGED: {asset} // PnL: {pnl:.2f} {currency}")
                st.rerun()

    # --- TABELLA STORICO COMPLETA ---
    st.markdown("### / HISTORICAL_LEDGER")
    df_trades = get_data("trades")
    if not df_trades.empty:
        # Riordino colonne per chiarezza terminale
        cols_order = ["asset", "instrument", "status", "side", "shares", "leverage", "currency", "portfolio", "entry_price", "exit_price", "cost", "notional", "profit", "pnl_perc", "open_date", "close_date"]
        st.dataframe(df_trades[cols_order], use_container_width=True, hide_index=True)
    else:
        st.info("LEDGER_EMPTY")

# --- MANTENERE LE ALTRE PAGINE (DASHBOARD E VAULT) COME PRIMA ---
elif st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    # ... (Codice dashboard precedente) ...
