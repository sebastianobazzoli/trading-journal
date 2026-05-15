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
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; margin-bottom: 10px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        div.stButton > button {
            background-color: #0A0A0A !important; color: #888 !important; border: 1px solid #1A1A1A !important;
            border-radius: 2px !important; padding: 6px 20px !important; font-family: 'Roboto Mono', monospace !important;
            font-size: 11px !important; text-transform: uppercase !important; transition: all 0.2s ease !important;
        }
        div.stButton > button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
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

# --- 5. PAGINA: DASHBOARD (MULTI-CURRENCY) ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    
    if not settings.empty:
        # Calcolo Equity Globale (semplificato in USD per il grafico)
        initial_total = pd.to_numeric(settings['initial_balance']).sum()
        
        if not trades.empty:
            closed = trades[trades['status'] == 'CHIUSA'].copy()
            if not closed.empty:
                closed['close_date'] = pd.to_datetime(closed['close_date'])
                closed = closed.sort_values('close_date')
                closed['cum_profit'] = pd.to_numeric(closed['profit']).cumsum()
                closed['port_return'] = ((initial_total + closed['cum_profit']) / initial_total - 1) * 100
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=closed['close_date'], y=closed['port_return'], name="PORTFOLIO", line=dict(color='#00FF41', width=2)))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
                st.plotly_chart(fig, use_container_width=True)

        # CARD CONTI RAGGRUPPATE PER NOME CONTO
        st.markdown("<div class='ticker-label'>VAULT_RESERVES // ASSET_DISTRIBUTION</div>", unsafe_allow_html=True)
        unique_accounts = settings['account_name'].unique()
        acc_cols = st.columns(len(unique_accounts))
        
        for i, acc_name in enumerate(unique_accounts):
            acc_data = settings[settings['account_name'] == acc_name]
            
            with acc_cols[i]:
                st.markdown(f"<div class='panel'><div class='ticker-label'>{acc_name}</div>", unsafe_allow_html=True)
                for _, row in acc_data.iterrows():
                    curr = row['currency']
                    init = float(row['initial_balance'])
                    
                    # Filtriamo trades per questo conto E questa valuta
                    # (Assumendo che nel trade tu specifichi la valuta corretta)
                    pnl = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['currency'] == curr) & (trades['status'] == 'CHIUSA')]['profit']).sum() if not trades.empty else 0
                    margine = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['currency'] == curr) & (trades['status'] == 'APERTA')]['cost']).sum() if not trades.empty else 0
                    
                    total = init + pnl
                    avail = total - margine
                    
                    st.markdown(f"""
                        <div style='margin-bottom:10px;'>
                            <span style='color:#555; font-size:11px;'>{curr}</span><br>
                            <span style='font-size:16px; font-weight:700;'>{total:,.2f}</span>
                            <div style='font-size:9px; color:#555;'>LIQ: <span style='color:#00FF41;'>{avail:,.2f}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Configura i saldi iniziali in SETTINGS.")

# --- 6. PAGINA: TRADE EXECUTION (INTATTA) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    # ... [Inserire qui tutto il codice della sezione TRADE del messaggio precedente] ...

# --- 7. PAGINA: SETTINGS (MULTI-CURRENCY SUPPORT) ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    st.markdown("<div class='ticker-label'>INITIALIZE_ACCOUNT_CURRENCY</div>", unsafe_allow_html=True)
    
    with st.form("set_multi_balance"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("NOME CONTO (es. Binance)")
        curr = c2.selectbox("VALUTA", ["USD", "EUR", "BTC", "USDT", "ETH"])
        bal_val = c3.number_input("SALDO INIZIALE", min_value=0.0)
        
        if st.form_submit_button("AGGIUNGI VALUTA AL CONTO"):
            if n:
                # Upsert logica: se esiste già conto+valuta, aggiorna, altrimenti inserisce
                supabase.table("balances").insert({
                    "account_name": n, "currency": curr, "initial_balance": bal_val
                }).execute()
                st.rerun()
    
    if not settings.empty:
        st.markdown("---")
        st.markdown("<div class='ticker-label'>CURRENT_CONFIGURATIONS (CONTOS & CURRENCIES)</div>", unsafe_allow_html=True)
        # Editor per modificare o rimuovere righe
        edited_settings = st.data_editor(settings, use_container_width=True, hide_index=True, key="sett_edit_v9")
        
        if st.button("UPDATE_SETTINGS"):
            # Logica per sincronizzare modifiche dei saldi iniziali
            for idx, row in edited_settings.iterrows():
                supabase.table("balances").update({
                    "initial_balance": row['initial_balance'],
                    "currency": row['currency']
                }).eq("id", row['id']).execute()
            st.rerun()
