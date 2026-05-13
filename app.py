import streamlit as st
import pandas as pd
import os
import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="TradePro Multicurrency", layout="wide")

# --- INIEZIONE TAILWIND ---
st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .stApp { background-color: #0f172a; color: #f8fafc; }
        [data-testid="stSidebar"] { background-color: #1e293b !important; }
        /* Reset stili Streamlit per Tailwind */
        .stButton>button { background-color: #3b82f6; color: white; border: none; border-radius: 0.5rem; }
        .stDataFrame { background-color: #1e293b; border-radius: 0.75rem; }
    </style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE DATABASE ---
DB_TRADES = "trades_multicurrency.csv"
DB_SALDI = "portfolio_balances.csv"

def init_dbs():
    if not os.path.exists(DB_TRADES):
        pd.DataFrame(columns=["Data", "Portafoglio", "Asset", "Tipo", "Entrata", "Uscita", "Risultato", "Valuta"]).to_csv(DB_TRADES, index=False)
    if not os.path.exists(DB_SALDI):
        # Ogni riga è una combinazione Portafoglio-Valuta
        pd.DataFrame(columns=["Nome_Portafoglio", "Valuta", "Saldo"]).to_csv(DB_SALDI, index=False)

init_dbs()

# --- SIDEBAR CUSTOM ---
if 'page' not in st.session_state: st.session_state.page = 'Dashboard'

with st.sidebar:
    st.markdown('<div class="p-6"><h1 class="text-white text-2xl font-bold">TRADE<span class="text-blue-500">PRO</span></h1><p class="text-slate-500 text-[10px] uppercase tracking-widest">Multicurrency Engine</p></div>', unsafe_allow_html=True)
    if st.button("🏠 Dashboard", use_container_width=True): st.session_state.page = 'Dashboard'
    if st.button("💼 Gestione Portafogli", use_container_width=True): st.session_state.page = 'Portafogli'
    if st.button("📝 Inserisci Trade", use_container_width=True): st.session_state.page = 'Trade'

# --- LOGICA PAGINA: PORTAFOGLI ---
if st.session_state.page == 'Portafogli':
    st.markdown('<h1 class="text-3xl font-bold mb-6">Gestione Portafogli Multicurrency</h1>', unsafe_allow_html=True)
    
    with st.expander("➕ Crea o Aggiungi Valuta a un Portafoglio", expanded=True):
        with st.form("add_balance"):
            col1, col2, col3 = st.columns(3)
            p_name = col1.text_input("Nome Portafoglio (es. IBKR Main)")
            p_curr = col2.selectbox("Valuta da aggiungere", ["EUR", "USD", "GBP", "CHF", "BTC"])
            p_amount = col3.number_input("Liquidità Iniziale", min_value=0.0)
            
            if st.form_submit_button("AGGIORNA ASSETTO"):
                saldi = pd.read_csv(DB_SALDI)
                # Se esiste già la coppia Portafoglio-Valuta, aggiorna, altrimenti aggiungi
                mask = (saldi['Nome_Portafoglio'] == p_name) & (saldi['Valuta'] == p_curr)
                if mask.any():
                    saldi.loc[mask, 'Saldo'] += p_amount
                else:
                    new_line = pd.DataFrame([[p_name, p_curr, p_amount]], columns=saldi.columns)
                    saldi = pd.concat([saldi, new_line])
                saldi.to_csv(DB_SALDI, index=False)
                st.success(f"Portafoglio {p_name} aggiornato con {p_amount} {p_curr}")

    st.markdown('<h2 class="text-xl font-semibold mt-8 mb-4 text-slate-400">Riepilogo Asset</h2>', unsafe_allow_html=True)
    st.dataframe(pd.read_csv(DB_SALDI), use_container_width=True)

# --- LOGICA PAGINA: TRADE ---
elif st.session_state.page == 'Trade':
    st.markdown('<h1 class="text-3xl font-bold mb-6">Nuova Esecuzione</h1>', unsafe_allow_html=True)
    saldi = pd.read_csv(DB_SALDI)
    
    if saldi.empty:
        st.warning("Configura almeno un portafoglio e una valuta prima di tradare!")
    else:
        with st.form("trade_entry"):
            # L'utente sceglie il portafoglio e la valuta specifica del trade
            p_options = saldi['Nome_Portafoglio'].unique().tolist()
            target_p = st.selectbox("Portafoglio", p_options)
            
            # Filtra valute disponibili per quel portafoglio
            v_options = saldi[saldi['Nome_Portafoglio'] == target_p]['Valuta'].tolist()
            target_v = st.selectbox("Valuta del Trade", v_options)
            
            col1, col2, col3 = st.columns(3)
            t_asset = col1.text_input("Asset (es. AAPL)")
            t_entry = col2.number_input("Entrata", format="%.5f")
            t_exit = col3.number_input("Uscita", format="%.5f")
            t_side = st.selectbox("Direzione", ["Long", "Short"])
            
            if st.form_submit_button("REGISTRA OPERAZIONE"):
                profit = (t_exit - t_entry) if t_side == "Long" else (t_entry - t_exit)
                
                # Salva Trade
                trades = pd.read_csv(DB_TRADES)
                new_t = pd.DataFrame([[datetime.date.today(), target_p, t_asset, t_side, t_entry, t_exit, profit, target_v]], columns=trades.columns)
                pd.concat([trades, new_t]).to_csv(DB_TRADES, index=False)
                
                # Aggiorna Saldo specifico per quella valuta
                saldi.loc[(saldi['Nome_Portafoglio'] == target_p) & (saldi['Valuta'] == target_v), 'Saldo'] += profit
                saldi.to_csv(DB_SALDI, index=False)
                
                st.balloons()
                st.success(f"Saldo aggiornato: {profit:.2f} {target_v} su {target_p}")

# --- LOGICA PAGINA: DASHBOARD ---
elif st.session_state.page == 'Dashboard':
    st.markdown('<h1 class="text-3xl font-bold mb-8 text-white">Aggregato Portafogli</h1>', unsafe_allow_html=True)
    saldi = pd.read_csv(DB_SALDI)
    
    if not saldi.empty:
        # Raggruppa per portafoglio per mostrare tutte le valute contenute
        for p_name in saldi['Nome_Portafoglio'].unique():
            st.markdown(f"""
                <div class="mb-6 p-6 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl">
                    <h3 class="text-blue-500 font-bold uppercase tracking-widest text-sm">{p_name}</h3>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            """, unsafe_allow_html=True)
            
            subset = saldi[saldi['Nome_Portafoglio'] == p_name]
            for _, row in subset.iterrows():
                st.markdown(f"""
                    <div class="bg-slate-900/50 p-4 rounded-xl border border-slate-700/50">
                        <p class="text-slate-500 text-[10px] font-bold">{row['Valuta']}</p>
                        <p class="text-xl font-bold text-white">{row['Saldo']:.2f}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True)
    else:
        st.info("Nessun dato disponibile.")
