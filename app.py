import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime
from supabase import create_client, Client

# --- SETUP & THEME ---
st.set_page_config(page_title="TERMINAL X", layout="wide", initial_sidebar_state="expanded")

# Iniezione CSS per Terminal Style
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;700&display=swap');
        
        :root {
            --term-bg: #050505;
            --term-green: #00FF41;
            --term-red: #FF3131;
            --term-blue: #0070FF;
            --border: #1A1A1A;
        }

        * { font-family: 'Roboto Mono', monospace !important; }
        .stApp { background-color: var(--term-bg); color: #CCCCCC; }
        
        /* Sidebar minimalista */
        [data-testid="stSidebar"] { background-color: #0A0A0A !important; border-right: 1px solid var(--border); }
        
        /* Pannelli stile Terminale */
        .panel {
            border: 1px solid var(--border);
            padding: 15px;
            background: #0D0D0D;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        
        .ticker-label { color: #888; font-size: 10px; text-transform: uppercase; }
        .ticker-value { font-size: 18px; font-weight: 700; }
        
        /* Custom Buttons */
        .stButton>button {
            border: 1px solid #333; background: transparent; color: #888;
            border-radius: 2px; text-transform: uppercase; font-size: 12px;
        }
        .stButton>button:hover { border-color: var(--term-blue); color: white; }
        
        header, footer { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def get_data(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

# --- NAVIGATION ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'

with st.sidebar:
    st.markdown("<h1 style='color:white; font-size:18px; margin-bottom:30px;'>SYSTEM: ONLINE</h1>", unsafe_allow_html=True)
    if st.button("01 DASHBOARD", use_container_width=True): st.session_state.page = 'DASHBOARD'
    if st.button("02 TRADE LOG", use_container_width=True): st.session_state.page = 'TRADE'
    if st.button("03 HEATMAP", use_container_width=True): st.session_state.page = 'HEATMAP'

# --- LOGIC: DASHBOARD (TERMINAL STYLE) ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("<h2 style='color:white; font-size:14px; opacity:0.6;'>TERMINAL / MARKET_OVERVIEW / PORTFOLIO</h2>", unsafe_allow_html=True)
    
    # Riga 1: Market Tickers (YFinance)
    tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC": "BTC-USD", "GOLD": "GC=F"}
    t_cols = st.columns(len(tickers))
    
    for i, (name, sym) in enumerate(tickers.items()):
        try:
            data = yf.Ticker(sym).history(period="2d")
            price = data['Close'].iloc[-1]
            change = ((price / data['Close'].iloc[-2]) - 1) * 100
            color = "#00FF41" if change > 0 else "#FF3131"
            with t_cols[i]:
                st.markdown(f"""
                    <div class="panel">
                        <div class="ticker-label">{name}</div>
                        <div class="ticker-value" style="color:{color}">{price:,.2f} <span style="font-size:10px">{change:+.2f}%</span></div>
                    </div>
                """, unsafe_allow_html=True)
        except: pass

    # Riga 2: Grafico di Rendimento Comparativo
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    trades = get_data("trades")
    if not trades.empty:
        trades['date'] = pd.to_datetime(trades['date'])
        trades = trades.sort_values('date')
        trades['User_Return'] = (trades['profit'].cumsum() / 10000) * 100  # Base 10k
        
        # Benchmark
        bench = yf.download("^GSPC", start=trades['date'].min(), end=datetime.date.today())['Close']
        bench_ret = (bench / bench.iloc[0] - 1) * 100
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trades['date'], y=trades['User_Return'], name="PORTFOLIO %", line=dict(color='#00FF41', width=2)))
        fig.add_trace(go.Scatter(x=bench_ret.index, y=bench_ret.values, name="S&P 500 %", line=dict(color='#333', dash='dot')))
        
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                          height=450, margin=dict(l=0,r=0,t=20,b=0), font=dict(family="Roboto Mono", size=10))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- LOGIC: TRADE PAGE ---
elif st.session_state.page == 'TRADE':
    st.markdown("<h2 style='color:white; font-size:14px;'>TERMINAL / EXECUTION_ENTRY</h2>", unsafe_allow_html=True)
    with st.container():
        with st.form("trade_form"):
            c1, c2, c3 = st.columns(3)
            p_name = c1.text_input("PORTFOLIO ID")
            asset = c2.text_input("TICKER (e.g. AAPL)")
            side = c3.selectbox("SIDE", ["LONG", "SHORT"])
            
            c4, c5, c6 = st.columns(3)
            entry = c4.number_input("ENTRY PRICE", format="%.5f")
            exit_p = c5.number_input("EXIT PRICE", format="%.5f")
            curr = c6.selectbox("CCY", ["EUR", "USD", "BTC"])
            
            if st.form_submit_button("EXECUTE ORDER"):
                profit = (exit_p - entry) if side == "LONG" else (entry - exit_p)
                supabase.table("trades").insert({
                    "portfolio": p_name, "asset": asset, "profit": profit, 
                    "currency": curr, "date": str(datetime.date.today())
                }).execute()
                # Update balance logic (come visto precedentemente)
                st.success("ORDER FINALIZED")

# --- LOGIC: HEATMAP ---
elif st.session_state.page == 'HEATMAP':
    st.markdown("<h2 style='color:white; font-size:14px;'>TERMINAL / RISK_HEATMAP</h2>", unsafe_allow_html=True)
    trades = get_data("trades")
    if not trades.empty:
        trades['date'] = pd.to_datetime(trades['date'])
        trades['Month'] = trades['date'].dt.month_name()
        trades['Day'] = trades['date'].dt.day_name()
        pivot = trades.groupby(['Month', 'Day'])['profit'].sum().unstack().fillna(0)
        
        fig_h = px.imshow(pivot, text_auto=True, color_continuous_scale='RdYlGn', template="plotly_dark")
        fig_h.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Roboto Mono", size=10))
        st.plotly_chart(fig_h, use_container_width=True)
