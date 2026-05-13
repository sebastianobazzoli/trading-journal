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
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 3. CSS PROFESSIONALE & RESPONSIVE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Reset per massimizzare lo spazio */
        .block-container { padding: 1rem 2rem !important; }
        
        html, body, [data-testid="stAppViewContainer"] { 
            background-color: #050505 !important; 
            font-family: 'Roboto Mono', monospace !important; 
            color: #CCC; 
        }
        
        /* Tabella Responsive: scrollbar sottile */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-thumb { background: #1A1A1A; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #00FF41; }

        .panel { border: 1px solid #1A1A1A; padding: 10px; background: #0A0A0A; border-radius: 2px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        
        /* Pulsanti Sidebar */
        .stButton>button { 
            background-color: transparent !important; 
            border: 1px solid #222 !important; 
            color: #888 !important; 
            border-radius: 0px !important; 
            width: 100%; 
            font-size: 12px !important; 
            transition: 0.3s;
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
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

trades = get_data("trades")
bal = get_data("balances")

# --- 6. PAGINA: DASHBOARD (Invariata) ---
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

# --- 7. PAGINA: TRADE EXECUTION (LOGICA RESPONSIVE) ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    # ... [Form Inserimento Invariato] ...
    
    if not trades.empty:
        def color_ledger(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            styles['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) > 0 else '')
            styles['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            return styles

        st.markdown("<div class='ticker-label'>DYNAMIC_LEDGER_SYSTEM</div>", unsafe_allow_html=True)
        
        # TABELLA CON CONFIGURAZIONE COLONNE OTTIMIZZATA
        edited_trades = st.data_editor(
            trades.style.apply(color_ledger, axis=None), 
            use_container_width=True, 
            hide_index=True, 
            num_rows="dynamic",
            disabled=["id", "cost", "notional", "date", "profit", "pnl_perc"], 
            column_config={
                "asset": st.column_config.TextColumn("TICKER", width="small"),
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"], width="small"),
                "side": st.column_config.TextColumn("SIDE", width="small"),
                "shares": st.column_config.NumberColumn("QTY", format="%.2f", width="small"),
                "exit_price": st.column_config.NumberColumn("EXIT (PMC)", format="%.4f", width="medium"),
                "profit": st.column_config.NumberColumn("P&L NET", format="%.2f", width="medium"),
                "pnl_perc": st.column_config.NumberColumn("P&L %", format="%.2f%%", width="medium"),
                "portfolio": st.column_config.TextColumn("ACCOUNT", width="small")
            },
            key="responsive_editor"
        )
        
        if st.button("SYNC_AND_RECALCULATE"):
            try:
                ids_orig = set(trades['id']); ids_new = set(edited_trades['id']); ids_del = ids_orig - ids_new
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()

                for idx, row in edited_trades.iterrows():
                    p_in, p_out = float(row['entry_price']), float(row['exit_price'])
                    qta, comm, capitale = float(row['shares']), float(row['fees']), float(row['cost'])
                    pnl_netto, pnl_perc = 0.0, 0.0
                    if p_out > 0:
                        side_m = 1 if row['side'] == "LONG" else -1
                        pnl_netto = ((p_out - p_in) * qta * side_m) - comm
                        if capitale > 0: pnl_perc = (pnl_netto / capitale) * 100
                    
                    supabase.table("trades").update({
                        "status": row['status'], "exit_price": round(p_out, 4), 
                        "profit": round(pnl_netto, 2), "pnl_perc": round(pnl_perc, 2),
                        "close_date": str(datetime.date.today()) if row['status'] == "CLOSED" else None
                    }).eq("id", row['id']).execute()
                
                st.success("SYNC COMPLETE"); st.rerun()
            except Exception as e: st.error(f"SYNC_ERROR: {e}")

# --- 8. VAULT ---
elif st.session_state.page == 'VAULT':
    st.markdown("### / VAULT_RESERVES")
    # ... (Codice Vault precedente)
