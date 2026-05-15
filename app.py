import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
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
        df = pd.DataFrame(res.data)
        return df if not df.empty else pd.DataFrame()
    except: return pd.DataFrame()

trades = get_data("trades")
settings = get_data("balances")

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
    
    # Verifica che le colonne necessarie esistano per evitare il KeyError
    if not settings.empty and 'initial_balance' in settings.columns:
        initial_capital = pd.to_numeric(settings['initial_balance']).sum()
        
        # Logica Equity Curve
        if not trades.empty and 'status' in trades.columns:
            closed_trades = trades[trades['status'] == 'CHIUSA'].copy()
            if not closed_trades.empty:
                closed_trades['close_date'] = pd.to_datetime(closed_trades['close_date'])
                closed_trades = closed_trades.sort_values('close_date')
                closed_trades['cum_profit'] = pd.to_numeric(closed_trades['profit']).cumsum()
                closed_trades['port_return'] = ((initial_capital + closed_trades['cum_profit']) / initial_capital - 1) * 100

                # Benchmark
                try:
                    bench = yf.Ticker("^GSPC").history(start=closed_trades['close_date'].min(), end=datetime.date.today())
                    bench['bench_return'] = (bench['Close'] / bench['Close'].iloc[0] - 1) * 100
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=closed_trades['close_date'], y=closed_trades['port_return'], name="PORTFOLIO", line=dict(color='#00FF41', width=2)))
                    fig.add_trace(go.Scatter(x=bench.index, y=bench['bench_return'], name="S&P 500", line=dict(color='#555', width=1, dash='dot')))
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(l=0,r=0,t=20,b=0),
                                    legend=dict(font=dict(size=10, color="#888"), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                    xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
                    st.plotly_chart(fig, use_container_width=True)
                except: st.warning("Impossibile caricare i dati benchmark.")

        # Card Conti
        st.markdown("<div class='ticker-label'>VAULT_RESERVES // REAL-TIME LIQUIDITY</div>", unsafe_allow_html=True)
        cols = st.columns(len(settings))
        for i, row in settings.iterrows():
            acc_name = row['account_name']
            acc_initial = float(row['initial_balance'])
            # Filtro profitti e margini
            acc_profit = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['status'] == 'CHIUSA')]['profit']).sum() if not trades.empty else 0
            acc_margin = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['status'] == 'APERTA')]['cost']).sum() if not trades.empty else 0
            
            current_val = acc_initial + acc_profit
            available = current_val - acc_margin
            
            with cols[i]:
                st.markdown(f"""<div class='panel'><div class='ticker-label'>{acc_name} ({row['currency']})</div>
                <div style='font-size:20px; font-weight:700;'>{current_val:,.2f}</div>
                <div style='font-size:10px; color:#555;'>LIQUIDITÀ: <span style='color:#00FF41;'>{available:,.2f}</span></div></div>""", unsafe_allow_html=True)
    else:
        st.info("Configura i saldi iniziali in SETTINGS. Assicurati che la colonna su Supabase si chiami 'initial_balance'.")

# --- 6. PAGINA: TRADE EXECUTION (NON MODIFICATA) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    # [Qui resta il tuo codice della tabella Trade che funziona bene]

# --- 7. PAGINA: SETTINGS ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    with st.form("set_balance"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("NOME CONTO")
        curr = c2.selectbox("VALUTA", ["USD", "EUR", "BTC", "USDT"])
        bal = c3.number_input("SALDO INIZIALE", min_value=0.0)
        if st.form_submit_button("INIZIALIZZA CONTO"):
            supabase.table("balances").insert({"account_name": n, "currency": curr, "initial_balance": bal}).execute()
            st.rerun()
    
    if not settings.empty:
        st.markdown("---")
        st.data_editor(settings, use_container_width=True, hide_index=True)
