import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE & CONNESSIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 2. CSS PROFESSIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        .block-container { padding-top: 4rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; max-width: 100% !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; padding-top: 2rem !important; }
        .panel { border: 1px solid #1A1A1A; padding: 15px; background: #0A0A0A; border-radius: 2px; margin-bottom: 10px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        
        /* Bottoni Professionali */
        div.stButton > button {
            background-color: #0A0A0A !important; color: #888 !important; border: 1px solid #1A1A1A !important;
            border-radius: 2px !important; padding: 6px 20px !important; font-family: 'Roboto Mono', monospace !important;
            font-size: 11px !important; text-transform: uppercase !important; transition: all 0.2s ease !important;
        }
        div.stButton > button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CARICAMENTO DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

trades = get_data("trades")
settings = get_data("balances") # Tabella per i saldi iniziali dei conti

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-bottom:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] SYSTEM_SETTINGS", on_click=set_page, args=('SETTINGS',))

# --- 5. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    
    # --- LOGICA CALCOLO RENDIMENTO PESATO ---
    if not settings.empty and not trades.empty:
        # Calcolo Equity Curve (SaldO Iniziale + Profitti Chiusi)
        initial_capital = settings['initial_balance'].astype(float).sum()
        closed_trades = trades[trades['status'] == 'CHIUSA'].copy()
        closed_trades['close_date'] = pd.to_datetime(closed_trades['close_date'])
        closed_trades = closed_trades.sort_values('close_date')
        closed_trades['cum_profit'] = closed_trades['profit'].astype(float).cumsum()
        closed_trades['portfolio_value'] = initial_capital + closed_trades['cum_profit']
        closed_trades['port_return'] = (closed_trades['portfolio_value'] / initial_capital - 1) * 100

        # Recupero Benchmarks (S&P 500)
        benchmark = yf.Ticker("^GSPC").history(start=closed_trades['close_date'].min(), end=datetime.date.today())
        benchmark['bench_return'] = (benchmark['Close'] / benchmark['Close'].iloc[0] - 1) * 100

        # Grafico Comparativo
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=closed_trades['close_date'], y=closed_trades['port_return'], name="PORTFOLIO", line=dict(color='#00FF41', width=2)))
        fig.add_trace(go.Scatter(x=benchmark.index, y=benchmark['bench_return'], name="S&P 500", line=dict(color='#555', width=1, dash='dot')))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            height=400, margin=dict(l=0,r=0,t=20,b=0),
            legend=dict(font=dict(size=10, color="#888"), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor='#1A1A1A', tickfont=dict(color='#555')),
            yaxis=dict(gridcolor='#1A1A1A', tickfont=dict(color='#555'), title="Return %")
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- CARD CONTI (RE-ADJUSTED) ---
        st.markdown("<div class='ticker-label'>VAULT_RESERVES // REAL-TIME LIQUIDITY</div>", unsafe_allow_html=True)
        cols = st.columns(len(settings))
        for i, row in settings.iterrows():
            # Calcolo profitto specifico per questo conto
            acc_name = row['account_name']
            acc_initial = float(row['initial_balance'])
            acc_profit = trades[(trades['portfolio'] == acc_name) & (trades['status'] == 'CHIUSA')]['profit'].sum()
            acc_margin_used = trades[(trades['portfolio'] == acc_name) & (trades['status'] == 'APERTA')]['cost'].sum()
            
            current_bal = acc_initial + acc_profit
            available_liq = current_bal - acc_margin_used
            
            with cols[i]:
                st.markdown(f"""
                    <div class='panel'>
                        <div class='ticker-label'>{acc_name} ({row['currency']})</div>
                        <div style='font-size:20px; font-weight:700; color:#CCC;'>{current_bal:,.2f}</div>
                        <div style='font-size:10px; color:#555;'>AVAILABLE LIQ: <span style='color:#00FF41;'>{available_liq:,.2f}</span></div>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Configura i saldi iniziali in SETTINGS per attivare la Dashboard.")

# --- 6. PAGINA: TRADE EXECUTION (NON MODIFICATA) ---
elif st.session_state.page == 'TRADE':
    # ... (Qui rimane esattamente il codice V7 della chat precedente)
    st.markdown("### / EXECUTION_LOG")
    # [Codice Tabella e Form invariato come richiesto]

# --- 7. PAGINA: SETTINGS (NUOVA) ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    st.markdown("<div class='ticker-label'>ACCOUNT_INITIALIZATION</div>", unsafe_allow_html=True)
    
    with st.form("set_balance"):
        c1, c2, c3, c4 = st.columns(4)
        acc_name = c1.text_input("NOME CONTO (es. Main, Binance)")
        curr = c2.selectbox("VALUTA", ["USD", "EUR", "BTC"])
        init_bal = c3.number_input("SALDO INIZIALE", min_value=0.0)
        if st.form_submit_button("SALVA CONFIGURAZIONE"):
            if acc_name:
                supabase.table("balances").insert({
                    "account_name": acc_name, "currency": curr, "initial_balance": init_bal
                }).execute()
                st.rerun()

    if not settings.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.data_editor(settings, use_container_width=True, hide_index=True, key="settings_editor")
