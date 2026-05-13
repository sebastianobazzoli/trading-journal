import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- CONNESSIONE CLOUD (SUPABASE) ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURAZIONE E TAILWIND ---
st.set_page_config(page_title="TradePro Cloud", layout="wide")
st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .stApp { background-color: #0f172a; color: #f8fafc; }
        [data-testid="stSidebar"] { background-color: #1e293b !important; border-right: 1px solid #334155; }
        .stButton>button { background-color: #3b82f6; color: white; border-radius: 0.5rem; border: none; width: 100%; transition: 0.2s; }
        .stButton>button:hover { background-color: #2563eb; transform: translateY(-1px); }
    </style>
""", unsafe_allow_html=True)

# --- FUNZIONI DI SINCRONIZZAZIONE ---
def get_data(table):
    response = supabase.table(table).select("*").execute()
    return pd.DataFrame(response.data)

def sync_trade(data):
    supabase.table("trades").insert(data).execute()

def update_balance(p_name, curr, amount):
    # Logica per aggiornare o inserire il saldo nel cloud
    res = supabase.table("balances").select("*").eq("portfolio", p_name).eq("currency", curr).execute()
    if res.data:
        new_val = res.data[0]['amount'] + amount
        supabase.table("balances").update({"amount": new_val}).eq("portfolio", p_name).eq("currency", curr).execute()
    else:
        supabase.table("balances").insert({"portfolio": p_name, "currency": curr, "amount": amount}).execute()

# --- NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'Dashboard'

with st.sidebar:
    st.markdown('<div class="p-6 mb-4"><h1 class="text-white text-2xl font-bold italic">TRADE<span class="text-blue-500">PRO</span></h1><span class="text-[10px] bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full font-bold">CLOUD SYNC</span></div>', unsafe_allow_html=True)
    if st.button("🏠 Dashboard"): st.session_state.page = 'Dashboard'
    if st.button("💼 Portafogli"): st.session_state.page = 'Portafogli'
    if st.button("📝 Nuovo Trade"): st.session_state.page = 'Trade'

# --- LOGICA PAGINE ---
if st.session_state.page == 'Dashboard':
    st.markdown('<h1 class="text-3xl font-bold mb-8">Asset Allocation Live</h1>', unsafe_allow_html=True)
    bal = get_data("balances")
    
    if not bal.empty:
        for p in bal['portfolio'].unique():
            st.markdown(f'<div class="mb-6 p-6 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl"><h3 class="text-blue-400 font-bold mb-4">{p}</h3><div class="grid grid-cols-2 md:grid-cols-4 gap-4">', unsafe_allow_html=True)
            p_bal = bal[bal['portfolio'] == p]
            for _, r in p_bal.iterrows():
                st.markdown(f'<div class="bg-slate-900/50 p-4 rounded-xl border border-slate-700/50"><p class="text-slate-500 text-[10px] font-bold uppercase">{r["currency"]}</p><p class="text-2xl font-bold text-white">{r["amount"]:,.2f}</p></div>', unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("Nessun dato sincronizzato nel cloud.")

elif st.session_state.page == 'Portafogli':
    st.markdown('<h1 class="text-3xl font-bold mb-6">Setup Portafoglio Cloud</h1>', unsafe_allow_html=True)
    with st.form("conf_p"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Nome Account")
        curr = c2.selectbox("Valuta", ["EUR", "USD", "GBP", "BTC", "USDT"])
        init_liq = c3.number_input("Versamento Iniziale")
        if st.form_submit_button("SINCRONIZZA DEPOSITO"):
            update_balance(name, curr, init_liq)
            st.success("Dati inviati al database cloud!")

elif st.session_state.page == 'Trade':
    st.markdown('<h1 class="text-3xl font-bold mb-6">Esecuzione Real-Time</h1>', unsafe_allow_html=True)
    bal = get_data("balances")
    if not bal.empty:
        with st.form("trade_form"):
            p_sel = st.selectbox("Portafoglio", bal['portfolio'].unique())
            c_sel = st.selectbox("Valuta", bal[bal['portfolio'] == p_sel]['currency'])
            asset = st.text_input("Asset")
            side = st.selectbox("Side", ["Long", "Short"])
            entry = st.number_input("Prezzo Entrata", format="%.5f")
            exit_p = st.number_input("Prezzo Uscita", format="%.5f")
            
            if st.form_submit_button("ESEGUI E AGGIORNA CLOUD"):
                profit = (exit_p - entry) if side == "Long" else (entry - exit_p)
                sync_trade({"portfolio": p_sel, "asset": asset, "profit": profit, "currency": c_sel, "date": str(datetime.date.today())})
                update_balance(p_sel, c_sel, profit)
                st.balloons()
