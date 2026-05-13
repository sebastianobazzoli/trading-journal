import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE TERMINALE ---
st.set_page_config(
    page_title="TERMINAL_X", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. CSS ISTITUZIONALE BLOOMBERG STYLE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Reset Ambiente */
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #050505 !important; 
            font-family: 'Roboto Mono', monospace !important; 
            color: #CCC; 
        }

        /* Sidebar Integrated */
        [data-testid="stSidebar"] { 
            background-color: #080808 !important; 
            border-right: 1px solid #1A1A1A !important; 
            transition: none !important;
        }

        /* Fix Posizione Tasto Sidebar */
        [data-testid="stSidebarCollapseByFrame"] { 
            color: #00FF41 !important; 
            top: 10px !important; 
            left: 10px !important; 
        }

        /* Pannelli UI */
        .panel { 
            border: 1px solid #1A1A1A; 
            padding: 12px; 
            background: #0A0A0A; 
            border-radius: 2px; 
            height: 100%;
        }
        
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .ticker-price { font-size: 18px; font-weight: 700; margin-top: 4px; }
        
        /* Bottoni Navigazione Alfanumerici */
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
        
        /* Hide Header Standard */
        header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE SUPABASE ---
@st.cache_resource
def init_db():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"DATABASE_CONNECTION_ERROR: {e}")
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
    st.markdown("<div style='color:#444; font-size:9px; margin-bottom:40px;'>v.4.5 // STABLE_RELEASE</div>", unsafe_allow_html=True)
    
    st.button("[01] MONITOR_DASH", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_SETUP", on_click=set_page, args=('VAULT',))
    
    st.markdown("<div style='height: 40vh;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#222; font-size:9px;'>SYS_ID: 99x-FLS-2026<br>STATUS: ENCRYPTED</div>", unsafe_allow_html=True)

# --- 6. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    # --- RIGA 1: TICKER WALL ---
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

    # --- RIGA 2: EQUITY CURVE ---
    st.markdown("<div style='color:#555; font-size:10px; margin-bottom:10px;'>PERFORMANCE_GRAPH // CUMULATIVE_PNL:</div>", unsafe_allow_html=True)
    trades_df = get_data("trades")

    if not trades_df.empty:
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        trades_df = trades_df.sort_values('date')
        trades_df['cumulative_profit'] = trades_df['profit'].cumsum()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trades_df['date'], y=trades_df['cumulative_profit'],
            mode='lines', line=dict(color='#00FF41', width=2),
            fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)',
            hoverinfo='x+y'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0), height=300,
            xaxis=dict(showgrid=True, gridcolor='#1A1A1A', showline=False, tickfont=dict(color='#444', size=10)),
            yaxis=dict(showgrid=True, gridcolor='#1A1A1A', showline=False, tickfont=dict(color='#444', size=10)),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown("<div class='panel' style='color:#333; height:150px; display:flex; align-items:center; justify-content:center;'>AWAITING_DATA_FOR_GRAPH_RENDERING</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- RIGA 3: VAULT MONITOR ---
    st.markdown("<div style='color:#555; font-size:10px; margin-bottom:10px;'>CONSOLIDATED_RESERVES:</div>", unsafe_allow_html=True)
    bal = get_data("balances")
    
    if not bal.empty:
        for p_name in bal['portfolio'].unique():
            st.markdown(f"<div style='border-left: 2px solid #0070FF; padding-left: 15px; margin-bottom:10px; color:white; font-size:11px; font-weight:700;'>{p_name}</div>", unsafe_allow_html=True)
            p_subset = bal[bal['portfolio'] == p_name]
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
        st.info("NO_VAULT_DATA. ACCESS [03] VAULT_SETUP.")

# --- PAGINA: TRADE ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    bal = get_data("balances")
    
    if bal.empty:
        st.warning("CONFIG_VAULT_REQUIRED_BEFORE_EXECUTION")
    else:
        with st.form("trade_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            p_sel = c1.selectbox("PORTFOLIO", bal['portfolio'].unique())
            asset = c2.text_input("TICKER (e.g. AAPL)")
            side = c3.selectbox("SIDE", ["LONG", "SHORT"])
            
            c4, c5, c6 = st.columns(3)
            entry = c4.number_input("ENTRY_PRICE", format="%.5f")
            exit_p = c5.number_input("EXIT_PRICE", format="%.5f")
            status = c6.selectbox("STATUS", ["OPEN", "CLOSED"])
            
            if st.form_submit_button("EXECUTE_ORDER"):
                profit = (exit_p - entry) if (status == "CLOSED" and side == "LONG") else (entry - exit_p if status == "CLOSED" else 0)
                
                # Insert Trade
                supabase.table("trades").insert({
                    "portfolio": p_sel, "asset": asset, "profit": profit, 
                    "currency": "USD", "status": status, "date": str(datetime.date.today())
                }).execute()
                
                # Auto-Update Vault Balance
                if status == "CLOSED" and profit != 0:
                    current = bal[(bal['portfolio'] == p_sel)]['amount'].sum()
                    supabase.table("balances").update({"amount": current + profit}).eq("portfolio", p_sel).execute()
                
                st.success("ORDER_SYNCED_TO_CLOUD")
                st.rerun()

# --- PAGINA: VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_CONFIGURATION")
    with st.form("vault_config"):
        c1, c2, c3 = st.columns(3)
        v_name = c1.text_input("ACCOUNT_ID")
        v_curr = c2.selectbox("BASE_CURRENCY", ["USD", "EUR", "GBP", "BTC", "USDT"])
        v_amount = c3.number_input("INITIAL_CAPITAL", min_value=0.0)
        
        if st.form_submit_button("COMMIT_SYNC"):
            supabase.table("balances").upsert(
                {"portfolio": v_name, "currency": v_curr, "amount": v_amount}, 
                on_conflict="portfolio,currency"
            ).execute()
            st.success("VAULT_DATABASE_UPDATED")
            st.rerun()
