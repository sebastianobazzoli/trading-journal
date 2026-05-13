import streamlit as st
import pandas as pd
import os
import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="TradePro Enterprise", layout="wide")

# --- INIEZIONE TAILWIND ---
st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .stApp { background-color: #0f172a; }
        [data-testid="stSidebar"] { background-color: #1e293b !important; }
        .stSelectbox div[data-baseweb="select"] { background-color: #1e293b; color: white; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# --- GESTIONE DATABASE ---
DB_TRADES = "trades_database.csv"
DB_PORTFOLIOS = "portfolios_database.csv"

def init_dbs():
    if not os.path.exists(DB_TRADES):
        pd.DataFrame(columns=["Data", "Portfolio", "Asset", "Tipo", "Entrata", "Uscita", "Risultato", "Currency"]).to_csv(DB_TRADES, index=False)
    if not os.path.exists(DB_PORTFOLIOS):
        pd.DataFrame(columns=["Nome", "Currency", "Liquidita_Iniziale", "Liquidita_Attuale"]).to_csv(DB_PORTFOLIOS, index=False)

init_dbs()

def load_portfolios(): return pd.read_csv(DB_PORTFOLIOS)
def load_trades(): return pd.read_csv(DB_TRADES)

# --- SIDEBAR CUSTOM ---
if 'page' not in st.session_state: st.session_state.page = 'Dashboard'

with st.sidebar:
    st.markdown('<div class="p-6"><h1 class="text-white text-2xl font-bold">TRADE<span class="text-blue-500">PRO</span></h1></div>', unsafe_allow_html=True)
    if st.button("🏠 Dashboard", use_container_width=True): st.session_state.page = 'Dashboard'
    if st.button("💼 Gestione Portafogli", use_container_width=True): st.session_state.page = 'Portafogli'
    if st.button("📝 Inserisci Trade", use_container_width=True): st.session_state.page = 'Trade'

# --- PAGINA PORTAFOGLI (Configurazione) ---
if st.session_state.page == 'Portafogli':
    st.markdown('<h1 class="text-3xl font-bold text-white mb-6">Configurazione Portafogli</h1>', unsafe_allow_html=True)
    
    with st.form("new_portfolio"):
        st.markdown('<p class="text-slate-400">Crea un nuovo wallet operativo</p>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        p_name = col1.text_input("Nome Portafoglio")
        p_curr = col2.selectbox("Valuta", ["EUR", "USD", "GBP", "BTC"])
        p_liq = col3.number_input("Liquidità Iniziale", min_value=0.0)
        
        if st.form_submit_button("CREA PORTAFOGLIO"):
            portfolios = load_portfolios()
            new_p = pd.DataFrame([[p_name, p_curr, p_liq, p_liq]], columns=portfolios.columns)
            pd.concat([portfolios, new_p]).to_csv(DB_PORTFOLIOS, index=False)
            st.success(f"Portafoglio {p_name} creato!")

    st.markdown('<div class="mt-8">', unsafe_allow_html=True)
    st.dataframe(load_portfolios(), use_container_width=True)

# --- PAGINA TRADE (Omnicomprensiva) ---
elif st.session_state.page == 'Trade':
    st.markdown('<h1 class="text-3xl font-bold text-white mb-6">Nuova Operazione</h1>', unsafe_allow_html=True)
    portfolios = load_portfolios()
    
    if portfolios.empty:
        st.warning("Crea prima un portafoglio nella sezione dedicata!")
    else:
        with st.form("trade_entry"):
            target_p = st.selectbox("Seleziona Portafoglio", portfolios['Nome'].tolist())
            col1, col2 = st.columns(2)
            t_asset = col1.text_input("Asset")
            t_side = col2.selectbox("Side", ["Long", "Short"])
            
            c3, c4 = st.columns(2)
            t_entry = c3.number_input("Entrata", format="%.5f")
            t_exit = c4.number_input("Uscita", format="%.5f")
            
            if st.form_submit_button("REGISTRA E AGGIORNA LIQUIDITÀ"):
                # Calcolo Profitto
                profit = (t_exit - t_entry) if t_side == "Long" else (t_entry - t_exit)
                
                # Update Trades
                trades = load_trades()
                curr_p = portfolios[portfolios['Nome'] == target_p].iloc[0]['Currency']
                new_t = pd.DataFrame([[datetime.date.today(), target_p, t_asset, t_side, t_entry, t_exit, profit, curr_p]], columns=trades.columns)
                pd.concat([trades, new_t]).to_csv(DB_TRADES, index=False)
                
                # Update Portfolio Liquidity (AUTOMATICO)
                portfolios.loc[portfolios['Nome'] == target_p, 'Liquidita_Attuale'] += profit
                portfolios.to_csv(DB_PORTFOLIOS, index=False)
                
                st.balloons()
                st.success(f"Trade registrato. Saldo {target_p} aggiornato!")

# --- PAGINA DASHBOARD ---
elif st.session_state.page == 'Dashboard':
    st.markdown('<h1 class="text-3xl font-bold text-white mb-6">Executive Overview</h1>', unsafe_allow_html=True)
    portfolios = load_portfolios()
    
    if not portfolios.empty:
        # Visualizzazione Card Tailwind per ogni Portafoglio
        cols = st.columns(len(portfolios))
        for i, row in portfolios.iterrows():
            with cols[i]:
                st.markdown(f"""
                    <div class="p-6 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl">
                        <p class="text-blue-400 text-xs font-bold uppercase">{row['Nome']}</p>
                        <p class="text-2xl font-bold text-white mt-1">{row['Liquidita_Attuale']:.2f} <span class="text-sm text-slate-500">{row['Currency']}</span></p>
                        <p class="text-slate-500 text-[10px] mt-2">Liquidità Iniziale: {row['Liquidita_Iniziale']}</p>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Nessun portafoglio configurato.")
