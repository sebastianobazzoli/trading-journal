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
    try: 
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        return None

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
        [data-testid="stDataEditor"] div { font-size: 11px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNZIONI DATI ---
def get_data(table):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

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
    if not settings.empty and 'initial_balance' in settings.columns and 'account_name' in settings.columns:
        initial_total = pd.to_numeric(settings['initial_balance']).sum()
        if not trades.empty and 'status' in trades.columns:
            closed = trades[trades['status'] == 'CHIUSA'].copy()
            if not closed.empty and 'close_date' in closed.columns and closed['close_date'].notna().any():
                closed['close_date'] = pd.to_datetime(closed['close_date'])
                closed = closed.sort_values('close_date')
                closed['cum_profit'] = pd.to_numeric(closed['profit']).cumsum()
                closed['port_return'] = ((initial_total + closed['cum_profit']) / initial_total - 1) * 100
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=closed['close_date'], y=closed['port_return'], name="PORTFOLIO", line=dict(color='#00FF41', width=2)))
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=20,b=0), xaxis=dict(gridcolor='#1A1A1A'), yaxis=dict(gridcolor='#1A1A1A'))
                st.plotly_chart(fig, use_container_width=True)

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
                    pnl = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['currency'] == curr) & (trades['status'] == 'CHIUSA')]['profit']).sum() if not trades.empty else 0
                    margine = pd.to_numeric(trades[(trades['portfolio'] == acc_name) & (trades['currency'] == curr) & (trades['status'] == 'APERTA')]['cost']).sum() if not trades.empty else 0
                    total = init + pnl
                    avail = total - margine
                    st.markdown(f"<div style='margin-bottom:8px;'><span style='color:#555; font-size:11px;'>{curr}</span><br><span style='font-size:16px; font-weight:700;'>{total:,.2f}</span><div style='font-size:9px; color:#555;'>LIQ: <span style='color:#00FF41;'>{avail:,.2f}</span></div></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Configura i conti in SYSTEM_SETTINGS per sbloccare la Dashboard.")

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
            open_d = r2c2.date_input("OPEN DATE")
            close_d = r2c3.date_input("CLOSE DATE", value=None)
            lev = r2c4.number_input("LEV", min_value=1.0, value=1.0)
            
            # --- PROTEZIONE KEYERROR ---
            acc_options = ["Main"]
            if not settings.empty and 'account_name' in settings.columns:
                acc_options = settings['account_name'].unique().tolist()
            
            curr_options = ["USD", "EUR", "USDT", "BTC", "ETH"]
            
            r3c1, r3c2 = st.columns(2)
            acc_choice = r3c1.selectbox("ACCOUNT", acc_options)
            curr_choice = r3c2.selectbox("CURRENCY", curr_options)

            if st.form_submit_button("REGISTRA POSIZIONE"):
                status = "CHIUSA" if exit_p > 0 else "APERTA"
                cost = round((entry * shares) / lev, 2)
                pnl = round(((exit_p - entry) * shares * (1 if side == "LONG" else -1)), 2) if exit_p > 0 else 0.0
                
                try:
                    supabase.table("trades").insert({
                        "asset": asset, "side": side, "shares": round(shares, 2), "entry_price": round(entry, 2),
                        "exit_price": round(exit_p, 2), "status": status, "date": str(open_d),
                        "close_date": str(close_d) if (exit_p > 0 and close_d) else (str(datetime.date.today()) if exit_p > 0 else None), 
                        "leverage": lev, "cost": cost, "profit": pnl, 
                        "pnl_perc": round(pnl/cost*100, 2) if (exit_p > 0 and cost > 0) else 0,
                        "instrument": "Stock", "currency": curr_choice, "portfolio": acc_choice
                    }).execute()
                    st.rerun()
                except Exception as e: st.error(f"Errore inserimento: {e}")

    if not trades.empty:
        for c in ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'cost']:
            trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)
        
        def style_ledger(df):
            s = pd.DataFrame('', index=df.index, columns=df.columns)
            s['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            s['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            s['status'] = df['status'].apply(lambda x: 'color: #00FF41; font-weight: bold' if x == "APERTA" else 'color: #555')
            return s

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM // REGISTERED_TRADES</div>", unsafe_allow_html=True)
        edited_trades = st.data_editor(
            trades.style.apply(style_ledger, axis=None), 
            use_container_width=True, hide_index=True, num_rows="dynamic",
            disabled=["id", "cost", "profit", "pnl_perc", "status"], 
            column_config={
                "id": None, "asset": st.column_config.TextColumn("TKR", width=50),
                "side": st.column_config.TextColumn("S", width=40),
                "shares": st.column_config.NumberColumn("QTY", format="%.2f", width=60),
                "entry_price": st.column_config.NumberColumn("IN", format="%.2f", width=65),
                "exit_price": st.column_config.NumberColumn("OUT", format="%.2f", width=65),
                "cost": st.column_config.NumberColumn("COST", format="%.2f", width=75),
                "profit": st.column_config.NumberColumn("P&L", format="%.2f", width=75),
                "pnl_perc": st.column_config.NumberColumn("%", format="%.2f%%", width=65),
                "status": st.column_config.TextColumn("STATO", width=80)
            },
            key="ledger_v_final_secure"
        )
        
        if st.button("SYNCHRONIZE"):
            try:
                ids_del = set(trades['id']) - set(edited_trades['id'])
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                for idx, row in edited_trades.iterrows():
                    p_in, p_out, qta = float(row['entry_price']), float(row['exit_price']), float(row['shares'])
                    c = round((p_in * qta) / float(row['leverage']), 2)
                    pnl = round(((p_out - p_in) * qta * (1 if row['side'] == "LONG" else -1)), 2) if p_out > 0 else 0
                    supabase.table("trades").update({
                        "exit_price": round(p_out, 2), "status": "CHIUSA" if p_out > 0 else "APERTA", 
                        "cost": c, "profit": pnl, "pnl_perc": round(pnl/c*100, 2) if (p_out > 0 and c > 0) else 0
                    }).eq("id", row['id']).execute()
                st.rerun()
            except Exception as e: st.error(f"Errore sincronizzazione: {e}")

# --- 7. PAGINA: SETTINGS ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    with st.form("set_balance"):
        c1, c2, c3 = st.columns(3)
        n, curr, bal_val = c1.text_input("CONTO"), c2.selectbox("VALUTA", ["USD", "EUR", "BTC", "USDT", "ETH"]), c3.number_input("SALDO INIZIALE", min_value=0.0)
        if st.form_submit_button("AGGIUNGI VALUTA"):
            try:
                supabase.table("balances").insert({"account_name": n, "currency": curr, "initial_balance": bal_val}).execute()
                st.success(f"Conto {n} inizializzato.")
                st.rerun()
            except Exception as e: st.error(f"Errore DB: {e}")
            
    if not settings.empty:
        st.markdown("---")
        st.data_editor(settings, use_container_width=True, hide_index=True)
