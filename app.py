import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# --- 2. CONNESSIONE ---
@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 3. CSS TERMINALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .stButton>button { background-color: transparent !important; border: 1px solid #222 !important; color: #888 !important; border-radius: 0px !important; text-align: left !important; width: 100%; padding: 10px 15px !important; }
        header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] VAULT_RESERVES", on_click=set_page, args=('VAULT',))

# Caricamento Dati
trades = pd.DataFrame(supabase.table("trades").select("*").execute().data) if supabase else pd.DataFrame()

# --- 5. PAGINA TRADE EXECUTION (LOGICA CALCOLO CORRETTA) ---
if st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    if not trades.empty:
        # Conversione tipi per evitare errori matematici
        num_cols = ['entry_price', 'exit_price', 'shares', 'fees', 'cost', 'profit', 'pnl_perc']
        for c in num_cols: trades[c] = pd.to_numeric(trades[c], errors='coerce').fillna(0.0)

        # 1. EDITOR PER MODIFICA
        st.markdown("<div class='ticker-label'>EDIT_MODE // CAMBIA STATUS A 'CLOSED' E INSERISCI EXIT_PRICE</div>", unsafe_allow_html=True)
        edited_df = st.data_editor(
            trades, 
            use_container_width=True, 
            hide_index=True, 
            disabled=["id", "cost", "notional", "profit", "pnl_perc", "date"],
            column_config={
                "status": st.column_config.SelectboxColumn("STATUS", options=["OPEN", "CLOSED"]),
                "exit_price": st.column_config.NumberColumn("EXIT_PRICE", format="%.2f")
            },
            key="editor_final"
        )

        # 2. LOGICA DI CALCOLO E SALVATAGGIO
        if st.button("CONFIRM_EXECUTION_AND_CALCULATE"):
            try:
                for idx, row in edited_df.iterrows():
                    # Variabili locali forzate a float
                    entry = float(row['entry_price'])
                    exit_p = float(row['exit_price'])
                    qta = float(row['shares'])
                    comm = float(row['fees'])
                    costo_iniziale = float(row['cost'])
                    
                    pnl_netto = float(row['profit'])
                    pnl_p = float(row['pnl_perc'])

                    if row['status'] == "CLOSED" and exit_p > 0:
                        # CALCOLO MATEMATICO (Esempio: (5.00 - 3.76) * 300 - 0 = 372)
                        side_factor = 1 if row['side'] == "LONG" else -1
                        pnl_netto = ((exit_p - entry) * qta * side_factor) - comm
                        pnl_p = (pnl_netto / costo_iniziale * 100) if costo_iniziale > 0 else 0.0

                    # Update Supabase
                    supabase.table("trades").update({
                        "status": row['status'],
                        "exit_price": exit_p,
                        "profit": round(pnl_netto, 2),
                        "pnl_perc": round(pnl_p, 2),
                        "close_date": str(datetime.date.today()) if row['status'] == "CLOSED" else None
                    }).eq("id", row['id']).execute()
                
                st.success("CALCOLO ESEGUITO: " + str(round(pnl_netto, 2)) + "$")
                st.rerun()
            except Exception as e: st.error(f"ERROR: {e}")

        # 3. VISUALIZZAZIONE COLORATA (SOLA LETTURA)
        st.markdown("---")
        st.markdown("<div class='ticker-label'>LIVE_VIEW // FORMATTED_LEDGER</div>", unsafe_allow_html=True)
        
        def style_trades(res):
            # Magenta per P&L Netto se positivo
            color_pnl = ['color: #FF00FF' if (v > 0 and res.status.iloc[i] == 'CLOSED') else '' for i, v in enumerate(res.profit)]
            # Verde/Rosso per P&L%
            color_perc = ['color: #00FF41' if v > 0 else 'color: #FF3131' if v < 0 else '' for v in res.pnl_perc]
            
            return pd.DataFrame({'profit': color_pnl, 'pnl_perc': color_perc}, index=res.index)

        st.dataframe(trades.style.apply(style_trades, axis=None), use_container_width=True, hide_index=True)

# --- 6. DASHBOARD (Senza rimosse) ---
elif st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    if not trades.empty:
        closed = trades[trades['status'] == 'CLOSED'].copy()
        if not closed.empty:
            closed['date'] = pd.to_datetime(closed['date'])
            closed = closed.sort_values('date')
            fig = go.Figure(go.Scatter(x=closed['date'], y=closed['profit'].cumsum(), mode='lines', line=dict(color='#00FF41')))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
            st.plotly_chart(fig, use_container_width=True)
