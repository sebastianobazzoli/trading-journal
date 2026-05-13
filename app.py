import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE (WIDE MODE OBBLIGATORIA) ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONNESSIONE ---
@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 3. CSS TOTALE (RIPRISTINO SIDEBAR + TABELLA FIT) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Font e Sfondo globale */
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #050505 !important; 
            font-family: 'Roboto Mono', monospace !important; 
            color: #CCC; 
        }

        /* Sidebar Responsive */
        [data-testid="stSidebar"] { 
            background-color: #080808 !important; 
            border-right: 1px solid #1A1A1A !important;
            width: 260px !important;
        }

        /* Padding Main Content per evitare scroll orizzontale */
        .block-container { 
            padding: 2rem 1rem !important; 
            max-width: 100% !important;
        }

        /* Pannelli Dashboard */
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }

        /* Bottoni Sidebar */
        .stButton>button { 
            background-color: transparent !important; 
            border: 1px solid #222 !important; 
            color: #888 !important; 
            border-radius: 0px !important; 
            width: 100% !important;
            text-align: left !important;
            padding: 10px 15px !important;
        }
        .stButton>button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }

        /* Riduzione font tabella per stare in una riga */
        [data-testid="stTable"] td, [data-testid="stTable"] th { font-size: 11px !important; }
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
                st.markdown(f"<div class='panel'><div class='ticker-label'>{name}</div><div style='font-size:18px; font-weight:700; color:{color}'>{price:,.2f} <span style='font-size:10px;'>{change:+.2f}%</span></div></div>", unsafe_allow_html=True)
        except: pass
    
    st.markdown("<br>", unsafe_allow_html=True)
    if not trades.empty:
        t_df = trades[trades['status'] == 'CLOSED'].copy()
        if not t_df.empty:
            t_df['date'] = pd.to_datetime(t_df['date'])
            t_df = t_df.sort_values('date')
            t_df['cum_pnl'] = pd.to_numeric(t_df['profit']).cumsum()
            fig = go.Figure(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines+markers', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=0,b=0), xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
            st.plotly_chart(fig, use_container_width=True)

# --- 7. TRADE EXECUTION (FIT-TO-SCREEN TABLE) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        # Form compatto
        with st.form("t_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            asset = c1.text_input("TICKER")
            shares = c2.number_input("QTY", min_value=0.0)
            entry = c3.number_input("ENTRY")
            side = c4.selectbox("SIDE", ["LONG", "SHORT"])
            if st.form_submit_button("OPEN"):
                cost = (entry * shares)
                supabase.table("trades").insert({"asset": asset, "shares": shares, "entry_price": entry, "side": side, "cost": cost, "status": "OPEN", "date": str(datetime.date.today()), "profit": 0, "pnl_perc": 0, "leverage": 1, "fees": 0, "instrument": "Stock", "currency": "USD"}).execute()
                st.rerun()

    if not trades.empty:
        def color_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            return styles

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM</div>", unsafe_allow_html=True)
        
        # Configurazione per far stare tutto in una schermata senza scroll
        edited_trades = st.data_editor(
            trades.style.apply(color_ledger, axis=None), 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            disabled=["id", "cost", "notional", "date", "profit", "pnl_perc", "leverage", "fees", "instrument", "currency"], 
            column_config={
                "asset": st.column_config.TextColumn("TKR", width=60),
                "status": st.column_config.SelectboxColumn("ST", options=["OPEN", "CLOSED"], width=70),
                "side": st.column_config.TextColumn("S", width=40),
                "shares": st.column_config.NumberColumn("QTY", width=60),
                "entry_price": st.column_config.NumberColumn("IN", width=70),
                "exit_price": st.column_config.NumberColumn("OUT", width=70),
                "profit": st.column_config.NumberColumn("P&L", format="%.2f", width=80),
                "pnl_perc": st.column_config.NumberColumn("%", format="%.1f%%", width=60),
                "portfolio": st.column_config.TextColumn("ACC", width=70),
                "close_date": st.column_config.TextColumn("END", width=80)
            },
            key="fit_editor"
        )
        
        if st.button("SYNC"):
            try:
                ids_orig = set(trades['id']); ids_new = set(edited_trades['id']); ids_del = ids_orig - ids_new
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                for idx, row in edited_trades.iterrows():
                    p_in, p_out, qta = float(row['entry_price']), float(row['exit_price']), float(row['shares'])
                    pnl_netto = ((p_out - p_in) * qta * (1 if row['side'] == "LONG" else -1)) if p_out > 0 else 0
                    pnl_perc = (pnl_netto / (p_in * qta) * 100) if (p_in * qta) > 0 else 0
                    supabase.table("trades").update({"status": row['status'], "exit_price": p_out, "profit": round(pnl_netto, 2), "pnl_perc": round(pnl_perc, 2)}).eq("id", row['id']).execute()
                st.rerun()
            except: pass

# --- 8. VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES")
    if not bal.empty: st.dataframe(bal, use_container_width=True, hide_index=True)
