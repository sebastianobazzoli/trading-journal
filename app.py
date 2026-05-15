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

# --- 2. CSS PROFESSIONALE ISTITUZIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        .block-container { padding-top: 4rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; max-width: 100% !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; padding-top: 2rem !important; }
        .panel { border: 1px solid #1A1A1A; padding: 12px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .stButton>button { background-color: #0A0A0A !important; border: 1px solid #1A1A1A !important; color: #777 !important; border-radius: 2px !important; width: 100% !important; text-align: left !important; padding: 10px 15px !important; font-size: 12px !important; }
        .stButton>button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
        [data-testid="stDataEditor"] div { font-size: 11px !important; }
        /* Sync Button specific style */
        div.stButton > button:first-child[kind="secondary"] { width: auto !important; padding: 6px 20px !important; margin-top: 10px !important; }
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

# --- 5. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    
    if not settings.empty and 'initial_balance' in settings.columns:
        initial_capital = pd.to_numeric(settings['initial_balance']).sum()
        
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
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=20,b=0),
                                    legend=dict(font=dict(size=10, color="#888"), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                    xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
                    st.plotly_chart(fig, use_container_width=True)
                except: pass

        # Card Conti
        st.markdown("<div class='ticker-label'>VAULT_RESERVES // REAL-TIME LIQUIDITY</div>", unsafe_allow_html=True)
        acc_cols = st.columns(len(settings))
        for i, row in settings.iterrows():
            acc_name = row['account_name']
            acc_initial = float(row['initial_balance'])
            acc_profit = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['status'] == 'CHIUSA')]['profit']).sum() if not trades.empty else 0
            acc_margin = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['status'] == 'APERTA')]['cost']).sum() if not trades.empty else 0
            
            current_val = acc_initial + acc_profit
            available = current_val - acc_margin
            
            with acc_cols[i]:
                st.markdown(f"""<div class='panel'><div class='ticker-label'>{acc_name} ({row['currency']})</div>
                <div style='font-size:20px; font-weight:700;'>{current_val:,.2f}</div>
                <div style='font-size:10px; color:#555;'>AVAILABLE LIQ: <span style='color:#00FF41;'>{available:,.2f}</span></div></div>""", unsafe_allow_html=True)
    else:
        st.info("Inizializza i conti nella sezione SETTINGS.")

# --- 6. PAGINA: TRADE EXECUTION (RIPRISTINATA INTEGRALMENTE) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=True):
        with st.form("advanced_trade", clear_on_submit=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            asset = r1c1.text_input("TICKER")
            side = r1c2.selectbox("SIDE", ["LONG", "SHORT"])
            shares = r1c3.number_input("QUANTITÀ", min_value=0.0, step=0.01)
            entry = r1c4.number_input("ENTRY PRICE", min_value=0.0)
            
            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            exit_p = r2c1.number_input("EXIT PRICE", min_value=0.0, value=0.0)
            open_d = r2c2.date_input("OPEN DATE", value=datetime.date.today())
            close_d = r2c3.date_input("CLOSE DATE", value=None)
            lev = r2c4.number_input("LEVERAGE", min_value=1.0, value=1.0)
            
            if st.form_submit_button("REGISTRA POSIZIONE"):
                status = "CHIUSA" if exit_p > 0 else "APERTA"
                final_close_date = str(close_d) if (exit_p > 0 and close_d) else (str(datetime.date.today()) if exit_p > 0 else None)
                cost = round((entry * shares) / lev, 2)
                pnl_netto = round(((exit_p - entry) * shares * (1 if side == "LONG" else -1)), 2) if exit_p > 0 else 0.0
                pnl_perc = round((pnl_netto / cost * 100), 2) if (exit_p > 0 and cost > 0) else 0.0
                
                supabase.table("trades").insert({
                    "asset": asset, "side": side, "shares": round(shares, 2), "entry_price": round(entry, 2),
                    "exit_price": round(exit_p, 2), "status": status, "date": str(open_d),
                    "close_date": final_close_date, "leverage": lev, "cost": cost,
                    "profit": pnl_netto, "pnl_perc": pnl_perc, "instrument": "Stock", "currency": "USD", "portfolio": "Main"
                }).execute()
                st.rerun()

    if not trades.empty:
        for c in ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'cost']:
            trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)

        trades = trades.sort_values(by="status", ascending=False)

        def style_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            styles['status'] = df['status'].apply(lambda x: 'color: #00FF41; font-weight: bold' if x == "APERTA" else 'color: #555')
            return styles

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM // CLEAN_VIEW</div>", unsafe_allow_html=True)
        
        edited_trades = st.data_editor(
            trades.style.apply(style_ledger, axis=None), 
            use_container_width=True, hide_index=True, num_rows="dynamic",
            disabled=["id", "cost", "profit", "pnl_perc", "status"], 
            column_config={
                "id": None, 
                "asset": st.column_config.TextColumn("TKR", width=50),
                "side": st.column_config.TextColumn("S", width=40),
                "shares": st.column_config.NumberColumn("QTY", format="%.2f", width=60),
                "entry_price": st.column_config.NumberColumn("IN", format="%.2f", width=65),
                "exit_price": st.column_config.NumberColumn("OUT", format="%.2f", width=65),
                "cost": st.column_config.NumberColumn("COSTO", format="%.2f", width=75),
                "profit": st.column_config.NumberColumn("P&L", format="%.2f", width=75),
                "pnl_perc": st.column_config.NumberColumn("%", format="%.2f%%", width=65),
                "status": st.column_config.TextColumn("STATO", width=80)
            },
            key="terminal_v_execution"
        )
        
        if st.button("SYNCHRONIZE"):
            try:
                ids_del = set(trades['id']) - set(edited_trades['id'])
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                for idx, row in edited_trades.iterrows():
                    p_in, p_out, qta = float(row['entry_price']), float(row['exit_price']), float(row['shares'])
                    nuovo_stato = "CHIUSA" if p_out > 0 else "APERTA"
                    capitale = round((p_in * qta) / float(row['leverage']), 2)
                    pnl_n = round(((p_out - p_in) * qta * (1 if row['side'] == "LONG" else -1)), 2) if p_out > 0 else 0.0
                    pnl_p = round((pnl_n / capitale * 100), 2) if (p_out > 0 and capitale > 0) else 0.0
                    supabase.table("trades").update({
                        "exit_price": round(p_out, 2), "status": nuovo_stato, "cost": capitale,
                        "profit": pnl_n, "pnl_perc": pnl_p,
                        "close_date": str(row['close_date']) if p_out > 0 else None
                    }).eq("id", row['id']).execute()
                st.rerun()
            except: pass

# --- 7. PAGINA: SETTINGS ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    with st.form("set_balance"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("NOME CONTO (es. Main, Binance)")
        curr = c2.selectbox("VALUTA", ["USD", "EUR", "BTC", "USDT"])
        bal_val = c3.number_input("SALDO INIZIALE", min_value=0.0)
        if st.form_submit_button("INIZIALIZZA CONTO"):
            supabase.table("balances").insert({"account_name": n, "currency": curr, "initial_balance": bal_val}).execute()
            st.rerun()
    
    if not settings.empty:
        st.markdown("---")
        st.markdown("<div class='ticker-label'>CONFIGURED_ACCOUNTS</div>", unsafe_allow_html=True)
        st.data_editor(settings, use_container_width=True, hide_index=True, key="settings_editor")
