import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# --- SETUP SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="TradePro Elite", layout="wide")

# --- CSS CUSTOM: ELEGANT MINIMALISM ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
        
        :root {
            --bg-primary: #05070A;
            --card-bg: rgba(23, 27, 34, 0.7);
            --accent-blue: #3E63DD;
            --text-main: #F8FAFC;
            --border-color: rgba(255, 255, 255, 0.08);
        }

        * { font-family: 'Plus Jakarta Sans', sans-serif; }
        
        .stApp { background: var(--bg-primary); }
        
        /* Sidebar Design */
        [data-testid="stSidebar"] {
            background-color: #080A0F !important;
            border-right: 1px solid var(--border-color);
        }

        /* Glassmorphism Card */
        .glass-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(5px);
            margin-bottom: 20px;
        }

        /* Metric Styling */
        .metric-label { color: #64748B; font-size: 11px; font-weight: 700; uppercase; letter-spacing: 1px; }
        .metric-value { color: #FFFFFF; font-size: 24px; font-weight: 700; margin-top: 4px; }
        
        /* Custom Buttons */
        .stButton>button {
            background: linear-gradient(135deg, #3E63DD 0%, #2D4699 100%);
            color: white; border: none; border-radius: 8px;
            padding: 10px 24px; font-weight: 600; width: 100%; transition: 0.3s;
        }
        .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(62, 99, 221, 0.4); }

        /* Remove Streamlit Clutter */
        #MainMenu, footer, header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- NAVIGATION LOGIC ---
if 'page' not in st.session_state: st.session_state.page = 'Overview'

def nav_to(page_name):
    st.session_state.page = page_name

# --- SIDEBAR NAV ---
with st.sidebar:
    st.markdown("""
        <div style="padding: 20px 0 40px 0; text-align: left;">
            <h2 style="color: white; font-weight: 700; font-size: 22px; letter-spacing: -0.5px;">
                <span style="color: #3E63DD;">●</span> TradePro <span style="font-weight: 300; opacity: 0.6;">Elite</span>
            </h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.button("Dashboard Overview", on_click=nav_to, args=("Overview",))
    st.button("Multi-Currency Vault", on_click=nav_to, args=("Vault",))
    st.button("New Execution", on_click=nav_to, args=("Execution",))

# --- HELPERS ---
def get_data(table):
    try:
        response = supabase.table(table).select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except: return pd.DataFrame()

# --- PAGE: OVERVIEW ---
if st.session_state.page == 'Overview':
    st.markdown('<h1 style="color: white; font-weight: 700; font-size: 32px; margin-bottom: 8px;">Institutional Overview</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color: #64748B; margin-bottom: 40px;">Real-time performance metrics and asset allocation.</p>', unsafe_allow_html=True)
    
    bal = get_data("balances")
    if not bal.empty:
        for p in bal['portfolio'].unique():
            st.markdown(f'<div style="margin-top: 30px; border-left: 2px solid #3E63DD; padding-left: 15px; margin-bottom: 15px; color: #94A3B8; font-size: 12px; font-weight: 700; text-transform: uppercase;">Account: {p}</div>', unsafe_allow_html=True)
            cols = st.columns(4)
            p_bal = bal[bal['portfolio'] == p]
            for idx, r in enumerate(p_bal.iloc):
                with cols[idx % 4]:
                    st.markdown(f"""
                        <div class="glass-card">
                            <div class="metric-label">{r["currency"]} BALANCE</div>
                            <div class="metric-value">{r["amount"]:,.2f}</div>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No active accounts. Configure your vault first.")

# --- PAGE: EXECUTION ---
elif st.session_state.page == 'Execution':
    st.markdown('<h1 style="color: white; font-weight: 700; font-size: 32px; margin-bottom: 40px;">New Execution</h1>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        with st.form("exec_form", clear_on_submit=True):
            bal = get_data("balances")
            p_list = bal['portfolio'].unique().tolist() if not bal.empty else ["Standard"]
            
            p_sel = st.selectbox("Portfolio Target", p_list)
            c_sel = st.selectbox("Settlement Currency", ["EUR", "USD", "GBP", "BTC", "USDT"])
            
            c1, c2 = st.columns(2)
            asset = c1.text_input("Instrument Symbol")
            side = c2.selectbox("Order Side", ["Long", "Short"])
            
            c3, c4 = st.columns(2)
            entry = c3.number_input("Average Entry", format="%.5f")
            exit_p = c4.number_input("Average Exit", format="%.5f")
            
            if st.form_submit_button("Confirm & Sync"):
                profit = (exit_p - entry) if side == "Long" else (entry - exit_p)
                supabase.table("trades").insert({
                    "portfolio": p_sel, "asset": asset, "profit": profit, 
                    "currency": c_sel, "date": str(datetime.date.today())
                }).execute()
                
                res = supabase.table("balances").select("*").eq("portfolio", p_sel).eq("currency", c_sel).execute()
                if res.data:
                    new_val = float(res.data[0]['amount']) + profit
                    supabase.table("balances").update({"amount": new_val}).eq("portfolio", p_sel).eq("currency", c_sel).execute()
                else:
                    supabase.table("balances").insert({"portfolio": p_sel, "currency": c_sel, "amount": profit}).execute()
                st.success("Execution Synced with Cloud")
        st.markdown('</div>', unsafe_allow_html=True)
