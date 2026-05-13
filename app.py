import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- SETUP SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURAZIONE E TAILWIND ---
st.set_page_config(page_title="TradePro Enterprise", layout="wide")

# Iniezione Tailwind e Lucide Icons (per icone minimal)
st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        
        * { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #0B0E14; color: #F8FAF7; }
        [data-testid="stSidebar"] { background-color: #0F1219 !important; border-right: 1px solid #1E232D; }
        
        /* Bottoni Menu Laterale */
        .nav-btn {
            display: flex; align-items: center; padding: 10px 16px; border-radius: 6px;
            color: #94A3B8; text-decoration: none; font-size: 14px; transition: 0.2s; cursor: pointer;
        }
        .nav-btn:hover { background-color: #1E232D; color: #3B82F6; }
        .active-btn { background-color: #1E232D; color: #3B82F6; font-weight: 600; }
        
        /* Nascondi elementi Streamlit */
        [data-testid="stSidebarNav"], footer, #MainMenu { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- LOGICA NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'Dashboard'

# --- SIDEBAR MINIMAL ---
with st.sidebar:
    st.markdown("""
        <div class="px-4 py-8">
            <div class="flex items-center space-x-2 mb-10">
                <div class="h-8 w-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold">T</div>
                <span class="text-xl font-semibold tracking-tight text-white">TradePro</span>
            </div>
            <div class="space-y-1">
    """, unsafe_allow_html=True)

    # Navigazione manuale tramite bottoni stilizzati
    if st.button("Analytics Dashboard", use_container_width=True, key="nav_dash"): st.session_state.page = 'Dashboard'
    if st.button("Portfolios Assets", use_container_width=True, key="nav_port"): st.session_state.page = 'Portafogli'
    if st.button("New Execution", use_container_width=True, key="nav_trade"): st.session_state.page = 'Trade'

    st.markdown("""
            </div>
            <div class="absolute bottom-8 left-8">
                <div class="flex items-center space-x-2 opacity-50">
                    <div class="h-2 w-2 bg-green-500 rounded-full"></div>
                    <span class="text-xs text-slate-400 uppercase tracking-widest">Network Live</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- HELPER DATABASE ---
def get_data(table):
    try:
        response = supabase.table(table).select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except: return pd.DataFrame()

# --- PAGINA: DASHBOARD ---
if st.session_state.page == 'Dashboard':
    st.markdown('<div class="px-8 py-10">', unsafe_allow_html=True)
    st.markdown('<h1 class="text-2xl font-semibold text-white mb-2">Performance Analytics</h1>', unsafe_allow_html=True)
    st.markdown('<p class="text-slate-500 text-sm mb-8">Asset overview and real-time equity tracking</p>', unsafe_allow_html=True)
    
    bal = get_data("balances")
    if not bal.empty:
        for p in bal['portfolio'].unique():
            st.markdown(f'<div class="mb-8"><h2 class="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-800 pb-2">{p}</h2><div class="grid grid-cols-1 md:grid-cols-4 gap-4">', unsafe_allow_html=True)
            p_bal = bal[bal['portfolio'] == p]
            for _, r in p_bal.iterrows():
                st.markdown(f"""
                    <div class="bg-[#161B22] p-5 rounded-lg border border-[#1E232D]">
                        <p class="text-slate-500 text-[10px] font-bold uppercase tracking-wider mb-1">{r["currency"]}</p>
                        <p class="text-xl font-medium text-white">{r["amount"]:,.2f}</p>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div></div>', unsafe_allow_html=True)
    else:
        st.info("No active portfolios detected.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- PAGINA: TRADE ---
elif st.session_state.page == 'Trade':
    st.markdown('<div class="px-8 py-10 max-w-2xl">', unsafe_allow_html=True)
    st.markdown('<h1 class="text-2xl font-semibold text-white mb-6">Execution Log</h1>', unsafe_allow_html=True)
    
    with st.container():
        # Useremo i widget standard ma racchiusi in container Tailwind
        with st.form("trade_form", clear_on_submit=True):
            bal = get_data("balances")
            p_list = bal['portfolio'].unique().tolist() if not bal.empty else ["No Portfolio"]
            
            p_sel = st.selectbox("Portfolio Account", p_list)
            c_sel = st.selectbox("Execution Currency", ["EUR", "USD", "BTC", "USDT"])
            
            col1, col2 = st.columns(2)
            asset = col1.text_input("Asset Symbol")
            side = col2.selectbox("Side", ["Long", "Short"])
            
            col3, col4 = st.columns(2)
            entry = col3.number_input("Entry Price", format="%.5f")
            exit_p = col4.number_input("Exit Price", format="%.5f")
            
            if st.form_submit_button("Confirm Execution"):
                profit = (exit_p - entry) if side == "Long" else (entry - exit_p)
                supabase.table("trades").insert({
                    "portfolio": p_sel, "asset": asset, "profit": profit, 
                    "currency": c_sel, "date": str(datetime.date.today())
                }).execute()
                
                # Aggiornamento saldo nel cloud
                res = supabase.table("balances").select("*").eq("portfolio", p_sel).eq("currency", c_sel).execute()
                if res.data:
                    new_val = float(res.data[0]['amount']) + profit
                    supabase.table("balances").update({"amount": new_val}).eq("portfolio", p_sel).eq("currency", c_sel).execute()
                else:
                    supabase.table("balances").insert({"portfolio": p_sel, "currency": c_sel, "amount": profit}).execute()
                st.toast("Trade recorded successfully")

    st.markdown('</div>', unsafe_allow_html=True)
