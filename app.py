import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONNESSIONE ---
@st.cache_resource
def init_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_db()

# --- 3. CSS ISTITUZIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        header[data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; color: #00FF41 !important; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; height: 100%; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .ticker-price { font-size: 18px; font-weight: 700; margin-top: 4px; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; padding: 10px 15px !important; font-size: 12px !important; }
        .stButton>button:hover { color: #00FF41 !important; border-color: #00FF41 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNZIONI DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 5. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

# --- 6. CARICAMENTO E PULIZIA DATI ---
bal = get_data("balances")
trades = get_data("trades")

if not trades.empty:
    # Conversione Date
    trades['date'] = pd.to_datetime(trades['date']).dt.date
    if 'close_date' in trades.columns:
        trades['close_date'] = pd.to_datetime(trades['close_date']).dt.date
    
    # Conversione Numerica Forzata (Risolve il problema degli "0" e KeyError)
    num_cols = ['entry_price', 'exit_price', 'shares', 'fees', 'cost', 'profit', 'pnl_perc', 'notional']
    for col in num_cols:
        if col in trades.columns:
            trades[col] = pd.to_numeric(trades[col], errors='coerce').fillna(0.0)

# --- 7. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    # Market Tickers
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

    # Equity Curve
    if not trades.empty:
        st.markdown("<div class='ticker-label'>EQUITY_CURVE // CLOSED_ONLY</div>", unsafe_allow_html=True)
        t_df = trades[trades['status'] == 'CLOSED'].copy()
        if not t_df.empty:
            t_df = t_df.sort_values('date')
            t_df['cum_pnl'] = t_df['profit'].cumsum()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=t_df['date'], y=t_df['cum_pnl'], mode='lines', line=dict(color='#00FF41', width=2), fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.05)'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=250, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(showgrid=True, gridcolor='#1A1A1A'), yaxis=dict(showgrid=True, gridcolor='#1A1A1A'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("AWAITING_CLOSED_TRADES")

# --- 8. PAGINA: TRADE EXECUTION (LOGICA CALCOLO FIXATA) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        with st.form("t_form", clear_on_submit=True):
            f1, f2, f3 = st.columns(3); asset = f1.text_input("TICKER"); instr = f2.selectbox("INSTRUMENT", ["Stock", "CFD", "ETF", "Crypto"]); shares = f3.number_input("SHARES", min_value=0.0, format="%.4f")
            f4, f5, f6 = st.columns(3); curr = f4.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); acc = f5.selectbox("ACCOUNT", bal['portfolio'].unique() if not bal.empty else ["-"]); side = f6.selectbox("SIDE", ["LONG", "SHORT"])
            f7, f8, f9 = st.columns(3); entry = f7.number_input("ENTRY", format="%.5f"); lev = f8.number_input("LEVERAGE", min_value=1.0, value=1.0); fees = f9.number_input("FEES", min_value=0.0)
            if st.form_submit_button("OPEN_POSITION"):
                cost = ((entry * shares) / lev) + fees
                supabase.table("trades").insert({"asset": asset, "instrument": instr, "shares": shares, "leverage": lev, "currency": curr, "portfolio": acc, "side": side, "entry_price": entry, "fees": fees, "cost": cost, "notional": entry * shares, "status": "OPEN", "date": str(datetime.date.today()), "profit": 0, "pnl_perc": 0}).execute()
                st.rerun()

    if not trades.empty:
        st.markdown("<div class='ticker-label'>INTERACTIVE_LEDGER (Edit Exit Price & Status)</div>", unsafe_allow_html=True)
        
        edited_trades = st.data_editor(
            trades, 
            use_container_width=True, 
            hide_index=True, 
            disabled=["id", "cost", "notional", "date"], 
            column_config={
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"]),
                "exit_price": st.column_config.NumberColumn("EXIT_PRICE", format="%.5f"),
                "profit": st.column_config.NumberColumn("P&L NETTO", format="%.2f"),
                "pnl_perc": st.column_config.NumberColumn("P&L %", format="%.2f%%")
            },
            key="trades_ledger_v3"
        )
        
        if st.button("SAVE_AND_CALCULATE_RENDIMENT"):
            try:
                for idx, row in edited_trades.iterrows():
                    # Valori originali per calcolo
                    curr_pnl = float(row['profit'])
                    curr_perc = float(row['pnl_perc'])
                    
                    if row['status'] == "CLOSED" and float(row['exit_price']) > 0:
                        # Ricalcolo matematico pulito
                        side_mult = 1 if row['side'] == "LONG" else -1
                        raw_pnl = (float(row['exit_price']) - float(row['entry_price'])) * float(row['shares']) * side_mult
                        curr_pnl = raw_pnl - float(row['fees'])
                        curr_perc = (curr_pnl / float(row['cost'])) * 100 if float(row['cost']) > 0 else 0.0
                        
                        # Aggiornamento Vault se prima era OPEN
                        old_status = trades.loc[trades['id'] == row['id'], 'status'].values[0]
                        if old_status == "OPEN":
                            acc_res = supabase.table("balances").select("amount").eq("portfolio", row['portfolio']).eq("currency", row['currency']).execute()
                            if acc_res.data:
                                new_bal = float(acc_res.data[0]['amount']) + curr_pnl
                                supabase.table("balances").update({"amount": new_bal}).eq("portfolio", row['portfolio']).eq("currency", row['currency']).execute()

                    # Update Database
                    supabase.table("trades").update({
                        "status": row['status'],
                        "exit_price": float(row['exit_price']),
                        "profit": round(curr_pnl, 2),
                        "pnl_perc": round(curr_perc, 2),
                        "close_date": str(row['close_date']) if row['close_date'] else str(datetime.date.today())
                    }).eq("id", row['id']).execute()
                
                st.success("SYNC_COMPLETE: Rendimento Calcolato."); st.rerun()
            except Exception as e: st.error(f"SYNC_ERROR: {e}")

# --- 9. PAGINA: VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES")
    with st.form("v_form"):
        v1, v2, v3 = st.columns(3); n = v1.text_input("ACCOUNT"); c = v2.selectbox("CCY", ["USD", "EUR", "BTC", "USDT"]); a = v3.number_input("BALANCE")
        if st.form_submit_button("SYNC_VAULT"):
            supabase.table("balances").upsert({"portfolio": n, "currency": c, "amount": a}, on_conflict="portfolio,currency").execute()
            st.rerun()
    if not bal.empty: st.dataframe(bal, use_container_width=True, hide_index=True)
