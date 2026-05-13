import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE (WIDE MODE) ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONNESSIONE ---
@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 3. CSS "FULL-WIDTH" (SIDEBAR FISSA + TABELLA COMPATTA) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Forza l'uso di tutto lo schermo */
        .block-container { 
            padding: 1rem 1rem !important; 
            max-width: 100% !important;
        }

        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #050505 !important; 
            font-family: 'Roboto Mono', monospace !important; 
            color: #CCC; 
        }

        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .panel { border: 1px solid #1A1A1A; padding: 10px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }

        /* Riduzione drastica font tabella per fit orizzontale */
        [data-testid="stDataEditor"] div { font-size: 11px !important; }
        
        /* Bottoni Sidebar */
        .stButton>button { 
            background-color: transparent !important; 
            border: 1px solid #222 !important; 
            color: #888 !important; 
            border-radius: 0px !important; 
            width: 100% !important;
            text-align: left !important;
            padding: 8px 12px !important;
        }
        .stButton>button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
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
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-bottom:15px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

trades = get_data("trades")
bal = get_data("balances")

# --- 6. DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    market_tickers = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "BTC/USD": "BTC-USD", "GOLD": "GC=F"}
    t_cols = st.columns(len(market_tickers))
    for i, (name, sym) in enumerate(market_tickers.items()):
        try:
            tk = yf.Ticker(sym).history(period="2d")
            price, change = tk['Close'].iloc[-1], ((tk['Close'].iloc[-1]/tk['Close'].iloc[-2])-1)*100
            color = "#00FF41" if change > 0 else "#FF3131"
            with t_cols[i]:
                st.markdown(f"<div class='panel'><div class='ticker-label'>{name}</div><div style='font-size:16px; font-weight:700; color:{color}'>{price:,.2f} <span style='font-size:9px;'>{change:+.2f}%</span></div></div>", unsafe_allow_html=True)
        except: pass
    
    st.markdown("<br>", unsafe_allow_html=True)
    if not trades.empty:
        t_df = trades[trades['status'] == 'CLOSED'].copy()
        if not t_df.empty:
            t_df['date'] = pd.to_datetime(t_df['date'])
            t_df = t_df.sort_values('date')
            t_df['cum_pnl'] = pd.to_numeric(t_df['profit']).cumsum()
            fig = go.Figure(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines+markers', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
            st.plotly_chart(fig, use_container_width=True)

# --- 7. TRADE EXECUTION (FULL-WIDTH & ROUNDED) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    if not trades.empty:
        # Arrotondamento forzato alla seconda cifra decimale per la tabella
        cols_round = ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'fees', 'cost', 'leverage']
        for c in cols_round:
            if c in trades.columns:
                trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)

        def color_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            return styles

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM // ALL_VISIBLE</div>", unsafe_allow_html=True)
        
        # EDITOR OTTIMIZZATO PER EVITARE SCROLL ORIZZONTALE
        edited_trades = st.data_editor(
            trades.style.apply(color_ledger, axis=None), 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            disabled=["id", "cost", "notional", "date", "profit", "pnl_perc"], 
            column_config={
                "asset": st.column_config.TextColumn("TKR", width=50),
                "status": st.column_config.SelectboxColumn("ST", options=["OPEN", "CLOSED"], width=65),
                "side": st.column_config.TextColumn("S", width=40),
                "shares": st.column_config.NumberColumn("QTY", format="%.2f", width=60),
                "entry_price": st.column_config.NumberColumn("IN", format="%.2f", width=65),
                "exit_price": st.column_config.NumberColumn("OUT", format="%.2f", width=65),
                "profit": st.column_config.NumberColumn("P&L", format="%.2f", width=75),
                "pnl_perc": st.column_config.NumberColumn("%", format="%.2f%%", width=65),
                "portfolio": st.column_config.TextColumn("ACC", width=65),
                "fees": st.column_config.NumberColumn("FEE", format="%.2f", width=55),
                "leverage": st.column_config.NumberColumn("LV", format="x%d", width=45)
            },
            key="fit_editor_final"
        )
        
        if st.button("SYNC_AND_CALC"):
            try:
                ids_orig = set(trades['id']); ids_new = set(edited_trades['id']); ids_del = ids_orig - ids_new
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                
                for idx, row in edited_trades.iterrows():
                    p_in, p_out, qta = float(row['entry_price']), float(row['exit_price']), float(row['shares'])
                    comm, margine = float(row['fees']), float(row['cost'])
                    pnl_netto, pnl_perc = 0.0, 0.0
                    
                    if p_out > 0:
                        side_m = 1 if row['side'] == "LONG" else -1
                        pnl_netto = ((p_out - p_in) * qta * side_m) - comm
                        if margine > 0: pnl_perc = (pnl_netto / margine) * 100
                    
                    supabase.table("trades").update({
                        "status": row['status'], 
                        "exit_price": round(p_out, 2), 
                        "profit": round(pnl_netto, 2), 
                        "pnl_perc": round(pnl_perc, 2)
                    }).eq("id", row['id']).execute()
                st.rerun()
            except: pass
