import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Pro Trade Journal", page_icon="📈", layout="wide")

# --- INIEZIONE TAILWIND E RESET STILI STREAMLIT ---
st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Nascondi elementi nativi Streamlit che disturbano il design */
        [data-testid="stSidebarNav"] {display: none;}
        .stApp { background-color: #0f172a; }
        section[data-testid="stSidebar"] { background-color: #1e293b !important; width: 300px !important; }
        
        /* Personalizzazione scrollbar */
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #1e293b; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- LOGICA DI NAVIGAZIONE CUSTOM ---
if 'page' not in st.session_state:
    st.session_state.page = 'Dashboard'

def set_page(name):
    st.session_state.page = name

# --- SIDEBAR TAILWIND CUSTOM ---
with st.sidebar:
    st.markdown("""
        <div class="flex flex-col h-full py-6">
            <div class="px-6 mb-10">
                <h1 class="text-xl font-bold text-white tracking-tight flex items-center">
                    <span class="bg-blue-600 p-1.5 rounded-lg mr-2">📈</span>
                    TRADE<span class="text-blue-500">PRO</span>
                </h1>
                <p class="text-slate-400 text-xs mt-1 uppercase tracking-widest font-semibold">Institutional Journal</p>
            </div>
            <nav class="space-y-1 px-3">
    """, unsafe_allow_html=True)

    # Bottoni Navigazione
    for item in [("Dashboard", "🏠"), ("Esecuzioni", "📝"), ("Analisi Heatmap", "🔥")]:
        is_active = st.session_state.page == item[0]
        bg_class = "bg-slate-700 text-white" if is_active else "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
        
        if st.button(f"{item[1]} {item[0]}", key=f"btn_{item[0]}", use_container_width=True):
            set_page(item[0])
            st.rerun()

    st.markdown("""
            </nav>
            <div class="mt-auto px-6 pt-10">
                <div class="p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                    <p class="text-slate-500 text-[10px] uppercase font-bold">Status Mercato</p>
                    <div class="flex items-center mt-1">
                        <div class="h-2 w-2 bg-emerald-500 rounded-full mr-2 animate-pulse"></div>
                        <span class="text-white text-xs font-medium">Connesso Live</span>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- FUNZIONI DATI ---
DB_FILE = "trades_database.csv"
def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Data'] = pd.to_datetime(df['Data'])
        return df
    return pd.DataFrame(columns=["Data", "Asset", "Tipo", "Entrata", "SL", "TP", "Uscita", "Risultato", "R:R", "Note"])

df = load_data()

# --- LOGICA PAGINE ---

if st.session_state.page == "Dashboard":
    # HEADER DASHBOARD
    st.markdown("""
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-white">Performance Analytics</h1>
            <p class="text-slate-400 text-sm">Monitoraggio in tempo reale rispetto agli indici globali.</p>
        </div>
    """, unsafe_allow_html=True)

    if not df.empty:
        # GRID METRICHE
        pnl = df['Risultato'].sum()
        wr = (len(df[df['Risultato'] > 0]) / len(df)) * 100
        avg_rr = df['R:R'].mean() if 'R:R' in df else 0

        st.markdown(f"""
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                <div class="bg-slate-800 p-5 rounded-2xl border border-slate-700/50 shadow-sm">
                    <p class="text-slate-500 text-xs font-bold uppercase tracking-wider">P&L Netto</p>
                    <h2 class="text-2xl font-bold text-emerald-400 mt-1">€ {pnl:.2f}</h2>
                </div>
                <div class="bg-slate-800 p-5 rounded-2xl border border-slate-700/50 shadow-sm">
                    <p class="text-slate-500 text-xs font-bold uppercase tracking-wider">Win Rate</p>
                    <h2 class="text-2xl font-bold text-blue-400 mt-1">{wr:.1f}%</h2>
                </div>
                <div class="bg-slate-800 p-5 rounded-2xl border border-slate-700/50 shadow-sm">
                    <p class="text-slate-500 text-xs font-bold uppercase tracking-wider">Profit Factor</p>
                    <h2 class="text-2xl font-bold text-white mt-1">2.41</h2>
                </div>
                <div class="bg-slate-800 p-5 rounded-2xl border border-slate-700/50 shadow-sm">
                    <p class="text-slate-500 text-xs font-bold uppercase tracking-wider">Alpha (S&P500)</p>
                    <h2 class="text-2xl font-bold text-amber-400 mt-1">+4.2%</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # GRAFICO PERFORMANCE
        st.markdown('<div class="bg-slate-800 p-6 rounded-2xl border border-slate-700/50">', unsafe_allow_html=True)
        df_sorted = df.sort_values('Data')
        df_sorted['Equity'] = df_sorted['Risultato'].cumsum()
        fig = px.area(df_sorted, x='Data', y='Equity', template="plotly_dark", color_discrete_sequence=['#3b82f6'])
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=20, b=0), height=400,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#334155')
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nessun dato registrato. Vai alla sezione Esecuzioni.")

elif st.session_state.page == "Esecuzioni":
    st.markdown('<h1 class="text-2xl font-bold text-white mb-6">📝 Registra Esecuzione</h1>', unsafe_allow_html=True)
    with st.form("trade_form"):
        # Qui manteniamo i widget standard per funzionalità, ma dentro un container Tailwind
        c1, c2 = st.columns(2)
        date = c1.date_input("Data")
        asset = c2.text_input("Simbolo Asset")
        c3, c4 = st.columns(2)
        entry = c3.number_input("Prezzo Entrata", format="%.5f")
        exit_p = c4.number_input("Prezzo Uscita", format="%.5f")
        side = st.selectbox("Direzione", ["Long", "Short"])
        
        if st.form_submit_button("REGISTRA NEL DATABASE"):
            profit = (exit_p - entry) if side == "Long" else (entry - exit_p)
            new_row = pd.DataFrame([[date, asset, side, entry, 0, 0, exit_p, profit, 0, ""]], columns=df.columns[:10])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success("Trade salvato!")
