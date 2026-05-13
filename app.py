import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE TERMINALE ---
st.set_page_config(
    page_title="TERMINAL_X", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. CSS ISTITUZIONALE (FIX FRECCETTE) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Reset Ambiente */
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #050505 !important; 
            font-family: 'Roboto Mono', monospace !important; 
            color: #CCC; 
        }

        /* Header Trasparente (Permette di vedere le freccette di riapertura) */
        header[data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
            color: #00FF41 !important;
        }

        /* Sidebar Stabile */
        [data-testid="stSidebar"] { 
            background-color: #080808 !important; 
            border-right: 1px solid #1A1A1A !important; 
            transition: none !important;
        }

        /* Pannelli UI Dashboard */
        .panel { 
            border: 1px solid #1A1A1A; 
            padding: 12px; 
            background: #0A0A0A; 
            border-radius: 2px; 
            height: 100%;
        }
        
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .ticker-price { font-size: 18px; font-weight: 700; margin-top: 4px; }
        
        /* Bottoni Navigazione */
        .stButton>button { 
            background-color: transparent !important; 
            border: 1px solid #222 !important; 
            color: #888 !important; 
            border-radius: 0px !important; 
            text-align: left !important; 
            width: 100%; 
            padding: 10px 15px !important; 
            font-size: 12px !important; 
        }
        .stButton>button:hover { 
            color: #00FF41 !important; 
            border-color: #00FF41 !important; 
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE SUPABASE ---
@st.cache_resource
def init_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_db()

# --- 4. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 5. LOGICA NAVIGAZIONE ---
if 'page' not in st.session_state:
    st.session_state.page = 'DASHBOARD'

def set_page(name):
    st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#444; font-size:9px; margin-bottom:40px;'>SECURE_CONNECTION_ACTIVE</div>", unsafe_allow_html=True)
    
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))
    
    st.markdown("<div style='height: 40vh;'></div>", unsafe_allow_html=True)
    if st.button("FORCE_OPEN_SIDEBAR"): # Tasto di emergenza
        st.rerun()

# CARICAMENTO DATI GLOBALI
bal = get_data("balances")
trades = get_data("trades")

# --- 6. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    # RIGA 1: TICKER WALL
    market_tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC/USD": "BTC-USD", "GOLD": "GC=F"}
    t_cols = st.columns(len(market_tickers))
    for i, (name, sym) in enumerate(market_tickers.items()):
        try:
            tk = yf.Ticker(sym).history(period="2d")
            price, change = tk['Close'].iloc[-1], ((tk['Close'].iloc[-1]/tk['Close'].iloc[-2])-1)*100
            color = "#00FF41" if change > 0 else "#FF3131"
            with t_cols[i]:
                st.markdown(f"<div class='panel'><div class='ticker-label'>{name}</div><div class='ticker-price' style='color:{color}'>{price:,.2f} <span style='font-size:10px;'>{change:+.2f}%</span></div></div>", unsafe_allow_html=True)
        except: pass

    st.markdown("<br>", unsafe_allow_html=True)

    # RIGA 2: EQUITY CURVE
    st.markdown("<div class='ticker-label'>EQUITY_CURVE // PERFORMANCE_ANALYSIS</div>", unsafe_allow_html=True)
    if not trades.empty:
        t_df = trades.copy()
        t_df['date'] = pd.to_datetime(t_df['date'])
        t_df = t_df.sort_values('date')
        t_df['cum_pnl'] = t_df['profit'].cumsum()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(showgrid=True, gridcolor='#1A1A1A'), yaxis=dict(showgrid=True, gridcolor='#1A1A1A'))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # RIGA 3: ALLOCATION & VAULT
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("<div class='ticker-label'>ASSET_ALLOCATION</div>", unsafe_allow_html=True)
        if not trades.empty and 'notional' in trades.columns:
            alloc = trades.groupby('instrument')['notional'].sum().reset_index()
            fig_pie = px.pie(alloc, values='notional', names='instrument', hole=.4, color_discrete_sequence=px.colors.sequential.Greens_r)
            fig_pie.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with c2:
        st.markdown("<div class='ticker-label'>VAULT_RESERVES</div>", unsafe_allow_html=True)
        if not bal.empty:
            for p in bal['portfolio'].unique():
                st.markdown(f"<div style='font-size:10px; color:#0070FF; margin-top:10px; font-weight:700;'>ACCOUNT: {p}</div>", unsafe_allow_html=True)
                p_bal = bal[bal['portfolio'] == p]
                v_cols = st.columns(4)
                for idx, r in enumerate(p_bal.iloc):
                    with v_cols[idx % 4]:
                        st.markdown(f"<div class='panel'><div style='font-size:14px; font-weight:700;'>{r['amount']:,.2f} <span style='color:#444; font-size:10px;'>{r['currency']}</span></div></div>", unsafe_allow_html=True)

# --- 7. PAGINA: TRADE EXECUTION ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    with st.form("trade_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        asset = c1.text_input("TICKER")
        instr = c2.selectbox("INSTRUMENT", ["Stock", "CFD", "ETF", "Crypto", "Forex"])
        shares = c3.number_input("SIZE/SHARES", min_value=0.0, format="%.4f")
        lev = c4.number_input("LEVERAGE", min_value=1.0, value=1.0)
        
        c5, c6, c7, c8 = st.columns(4)
        curr = c5.selectbox("CURRENCY", ["USD", "EUR", "BTC", "USDT"])
        acc_list = bal[bal['currency']==curr]['portfolio'].unique() if not bal.empty else []
        acc = c6.selectbox("ACCOUNT", acc_list if len(acc_list)>0 else ["SETUP_VAULT_FIRST"])
        stat = c7.selectbox("STATUS", ["OPEN", "CLOSED"])
        side = c8.selectbox("SIDE", ["LONG", "SHORT"])
        
        c9, c10, c11, c12 = st.columns(4)
        entry = c11.number_input("AVG_ENTRY", format="%.5f")
        exit_p = c12.number_input("AVG_EXIT (0 if Open)", format="%.5f")
        fees = st.number_input("FEES (Commissioni)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("COMMIT_TRADE"):
            cost = ((entry * shares) / lev) + fees
            pnl = (((exit_p - entry) * shares) if side == "LONG" else ((entry - exit_p) * shares)) - fees if stat == "CLOSED" else 0
            pnl_p = (pnl / cost) * 100 if cost > 0 else 0
            
            payload = {
                "asset": asset, "instrument": instr, "shares": shares, "leverage": lev, "currency": curr,
                "portfolio": acc, "status": stat, "side": side, "entry_price": entry, "exit_price": exit_p,
                "fees": fees, "cost": cost, "notional": entry * shares, "profit": pnl, "pnl_perc": pnl_p, "date": str(datetime.date.today())
            }
            supabase.table("trades").insert(payload).execute()
            
            if stat == "CLOSED" and acc != "SETUP_VAULT_FIRST":
                current_liq = bal[(bal['portfolio']==acc)&(bal['currency']==curr)]['amount'].iloc[0]
                supabase.table("balances").update({"amount": current_liq + pnl}).eq("portfolio", acc).eq("currency", curr).execute()
            st.rerun()

    if not trades.empty:
        st.dataframe(trades.sort_values('date', ascending=False), use_container_width=True, hide_index=True)

# --- 8. PAGINA: VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES_SETUP")
    with st.form("v_form"):
        n = st.text_input("ACCOUNT_NAME (es. Binance, IBKR)")
        c = st.selectbox("BASE_CCY", ["USD", "EUR", "BTC", "USDT"])
        a = st.number_input("INITIAL_BALANCE", min_value=0.0)
        if st.form_submit_button("SYNC_RESERVES"):
            supabase.table("balances").upsert({"portfolio": n, "currency": c, "amount": a}, on_conflict="portfolio,currency").execute()
            st.success("VAULT_SYNCHRONIZED")
            st.rerun()
    
    if not bal.empty:
        st.dataframe(bal, use_container_width=True, hide_index=True)
