import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
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
        .panel { border: 1px solid #1A1A1A; padding: 15px; background: #0A0A0A; border-radius: 4px; margin-bottom: 15px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        div.stButton > button {
            background-color: #0A0A0A !important; color: #888 !important; border: 1px solid #1A1A1A !important;
            border-radius: 2px !important; padding: 6px 20px !important; font-family: 'Roboto Mono', monospace !important;
            font-size: 11px !important; text-transform: uppercase !important; transition: all 0.2s ease !important;
        }
        div.stButton > button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
        .card-title { color: #00FF41; font-weight: 700; font-size: 14px; margin-bottom: 10px; border-bottom: 1px solid #1A1A1A; padding-bottom: 5px; }
        .stat-val { font-size: 18px; font-weight: 700; color: #FFF; }
        .stat-sub { font-size: 10px; color: #555; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNZIONI DATI ---
def get_data(table):
    if not supabase: return pd.DataFrame()
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
        initial_total = pd.to_numeric(settings['initial_balance']).sum()
        if not trades.empty and 'status' in trades.columns:
            closed = trades[trades['status'] == 'CHIUSA'].copy()
            if not closed.empty and 'close_date' in closed.columns and 'profit' in closed.columns:
                closed['close_date'] = pd.to_datetime(closed['close_date'])
                closed = closed.sort_values('close_date')
                closed['cum_profit'] = pd.to_numeric(closed['profit']).cumsum()
                closed['port_return'] = ((initial_total + closed['cum_profit']) / initial_total - 1) * 100
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=closed['close_date'], y=closed['port_return'], name="PORTFOLIO", line=dict(color='#00FF41', width=2)))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
                st.plotly_chart(fig, use_container_width=True)
    else: st.info("Configura i saldi iniziali in SETTINGS.")

# --- 6. PAGINA: TRADE EXECUTION ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        with st.form("advanced_trade", clear_on_submit=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            asset = r1c1.text_input("TICKER")
            side = r1c2.selectbox("SIDE", ["LONG", "SHORT"])
            shares = r1c3.number_input("QTY", min_value=0.0, step=0.01)
            entry = r1c4.number_input("IN PRICE", min_value=0.0)
            
            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            exit_p = r2c1.number_input("OUT PRICE", min_value=0.0, value=0.0)
            open_d = r2c2.date_input("OPEN")
            close_d = r2c3.date_input("CLOSE", value=None)
            lev = r2c4.number_input("LEV", min_value=1.0, value=1.0)
            
            # Protezione opzioni account
            acc_list = ["Main"]
            if not settings.empty and 'account_name' in settings.columns:
                acc_list = settings['account_name'].unique().tolist()
            
            r3c1, r3c2 = st.columns(2)
            acc_choice = r3c1.selectbox("ACCOUNT", acc_list)
            curr_choice = r3c2.selectbox("CURR", ["USD", "EUR", "USDT", "BTC", "ETH"])
            
            if st.form_submit_button("REGISTRA"):
                status = "CHIUSA" if exit_p > 0 else "APERTA"
                cost = round((entry * shares) / lev, 2)
                pnl = round(((exit_p - entry) * shares * (1 if side == "LONG" else -1)), 2) if exit_p > 0 else 0
                supabase.table("trades").insert({
                    "asset": asset, "side": side, "shares": shares, "entry_price": entry,
                    "exit_price": exit_p, "status": status, "date": str(open_d),
                    "close_date": str(close_d) if exit_p > 0 else None, "leverage": lev,
                    "cost": cost, "profit": pnl, "pnl_perc": round(pnl/cost*100, 2) if (cost>0 and exit_p>0) else 0,
                    "portfolio": acc_choice, "currency": curr_choice, "instrument": "Stock"
                }).execute()
                st.rerun()

    if not trades.empty:
        for c in ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'cost']:
            if c in trades.columns: trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)
        
        def style_ledger(df):
            s = pd.DataFrame('', index=df.index, columns=df.columns)
            if 'profit' in df.columns: s['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            if 'pnl_perc' in df.columns: s['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            if 'status' in df.columns: s['status'] = df['status'].apply(lambda x: 'color: #00FF41; font-weight: bold' if x == "APERTA" else 'color: #555')
            return s

        edited_trades = st.data_editor(trades.sort_values("status", ascending=False) if 'status' in trades.columns else trades, 
                                      use_container_width=True, hide_index=True, disabled=["id", "cost", "profit", "pnl_perc", "status"], 
                                      column_config={"id": None, "asset": "TKR", "side": "S", "shares": "QTY", "entry_price": "IN", "exit_price": "OUT", "cost": "COSTO", "profit": "P&L", "pnl_perc": "%", "status": "STATO"}, key="ledger_v11")
        if st.button("SYNCHRONIZE"):
            for d in (set(trades['id']) - set(edited_trades['id'])): supabase.table("trades").delete().eq("id", d).execute()
            for _, r in edited_trades.iterrows():
                pnl = round(((float(r['exit_price']) - float(r['entry_price'])) * float(r['shares']) * (1 if r['side'] == "LONG" else -1)), 2) if float(r['exit_price']) > 0 else 0
                supabase.table("trades").update({"exit_price": r['exit_price'], "status": "CHIUSA" if float(r['exit_price']) > 0 else "APERTA", "profit": pnl, "pnl_perc": round(pnl/float(r['cost'])*100, 2) if (float(r['exit_price']) > 0 and float(r['cost']) > 0) else 0}).eq("id", r['id']).execute()
            st.rerun()

# --- 7. PAGINA: SETTINGS ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    
    with st.expander("ADD_NEW_VAULT_ASSET", expanded=False):
        with st.form("new_acc"):
            c1, c2, c3 = st.columns(3)
            n, cr, bl = c1.text_input("ACCOUNT NAME"), c2.selectbox("CURR", ["USD", "EUR", "USDT", "BTC", "ETH"]), c3.number_input("INITIAL BALANCE", min_value=0.0)
            if st.form_submit_button("INITIALIZE"):
                supabase.table("balances").insert({"account_name": n, "currency": cr, "initial_balance": bl}).execute()
                st.rerun()

    if not settings.empty and 'account_name' in settings.columns:
        st.markdown("<div class='ticker-label'>VAULT_INSIGHTS</div>", unsafe_allow_html=True)
        unique_accounts = settings['account_name'].unique()
        
        for acc in unique_accounts:
            acc_rows = settings[settings['account_name'] == acc]
            c_info, c_chart = st.columns([1, 1.5])
            
            total_balance = 0
            total_margin_used = 0
            for _, r in acc_rows.iterrows():
                init = float(r['initial_balance'])
                pnl = pd.to_numeric(trades[(trades['portfolio'] == acc) & (trades['currency'] == r['currency']) & (trades['status'] == 'CHIUSA')]['profit']).sum() if not trades.empty else 0
                total_balance += (init + pnl)
                total_margin_used += pd.to_numeric(trades[(trades['portfolio'] == acc) & (trades['currency'] == r['currency']) & (trades['status'] == 'APERTA')]['cost']).sum() if not trades.empty else 0
            
            liq = total_balance - total_margin_used
            
            with c_info:
                st.markdown(f"<div class='panel'><div class='card-title'>VAULT: {acc}</div><div class='stat-sub'>Patrimonio Totale</div><div class='stat-val'>{total_balance:,.2f}</div><div style='margin-top:10px;'><span class='stat-sub'>Liquidità: </span><span style='color:#00FF41; font-weight:700;'>{liq:,.2f}</span></div></div>", unsafe_allow_html=True)
            with c_chart:
                fig = px.pie(pd.DataFrame({"Cat": ["Liquidità", "Asset"], "Val": [liq, total_margin_used]}), values='Val', names='Cat', hole=0.6, color_discrete_map={"Liquidità": "#00FF41", "Asset": "#222"})
                fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=160, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("<br><div class='ticker-label'>EDIT_VAULT_DATA</div>", unsafe_allow_html=True)
        edited_settings = st.data_editor(settings, use_container_width=True, hide_index=True, column_config={"id": None}, key="sett_edit_v11")
        if st.button("SYNC_SETTINGS"):
            for d_id in (set(settings['id']) - set(edited_settings['id'])): supabase.table("balances").delete().eq("id", d_id).execute()
            for _, r in edited_settings.iterrows(): supabase.table("balances").update({"account_name": r['account_name'], "initial_balance": r['initial_balance'], "currency": r['currency']}).eq("id", r['id']).execute()
            st.rerun()
    else: st.info("Nessun conto configurato.")
