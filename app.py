import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Tailwind Trading Journal", page_icon="⚡", layout="wide")

# --- INIEZIONE TAILWIND CSS ---
# Carichiamo Tailwind tramite CDN e forziamo lo stile Dark per Streamlit
st.markdown("""
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Nascondiamo alcuni elementi standard di Streamlit per pulizia */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp { background-color: #0f172a; } /* Slate-900 di Tailwind */
    </style>
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

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("""
    <div class="p-4">
        <h1 class="text-2xl font-bold text-blue-500">TradeMenu</h1>
        <p class="text-slate-400 text-sm">v2.1 Tailwind Edition</p>
    </div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Navigazione", ["🏠 Dashboard", "📝 Inserimento", "🔥 Analisi"])

# --- PAGINA DASHBOARD ---
if page == "🏠 Dashboard":
    # Titolo con classi Tailwind
    st.markdown('<h1 class="text-3xl font-extrabold text-white mb-6">Global Analytics</h1>', unsafe_allow_html=True)

    if not df.empty:
        # Calcolo metriche
        total_pnl = df['Risultato'].sum()
        win_rate = (len(df[df['Risultato'] > 0]) / len(df)) * 100
        
        # CARD METRICHE IN STILE TAILWIND
        st.markdown(f"""
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="p-6 bg-slate-800 rounded-xl border border-slate-700 shadow-lg">
                <p class="text-slate-400 text-sm font-medium uppercase tracking-wider">P&L Totale</p>
                <p class="text-3xl font-bold text-emerald-400">€ {total_pnl:.2f}</p>
            </div>
            <div class="p-6 bg-slate-800 rounded-xl border border-slate-700 shadow-lg">
                <p class="text-slate-400 text-sm font-medium uppercase tracking-wider">Win Rate</p>
                <p class="text-3xl font-bold text-blue-400">{win_rate:.1f}%</p>
            </div>
            <div class="p-6 bg-slate-800 rounded-xl border border-slate-700 shadow-lg">
                <p class="text-slate-400 text-sm font-medium uppercase tracking-wider">Operazioni</p>
                <p class="text-3xl font-bold text-white">{len(df)}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Grafico Benchmark (normalizzato)
        st.sidebar.divider()
        bench_choice = st.sidebar.selectbox("Benchmark", ["^GSPC", "^IXIC", "BTC-USD"])
        
        df_sorted = df.sort_values('Data')
        df_sorted['Equity'] = (df_sorted['Risultato'].cumsum() / 10000) * 100
        
        fig = px.area(df_sorted, x='Data', y='Equity', template="plotly_dark", 
                      color_discrete_sequence=['#10b981']) # Emerald-500
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        st.markdown('<div class="p-4 bg-slate-800 rounded-xl border border-slate-700">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown('<div class="p-8 bg-blue-900/20 border border-blue-500/50 rounded-lg text-blue-200">Inserisci i tuoi primi trade per sbloccare la dashboard.</div>', unsafe_allow_html=True)

# --- PAGINA INSERIMENTO ---
elif page == "📝 Inserimento":
    st.markdown('<h2 class="text-2xl font-bold text-white mb-4">Aggiungi Esecuzione</h2>', unsafe_allow_html=True)
    
    with st.container():
        # Usiamo il form standard di Streamlit ma stilizzato via CSS precedentemente iniettato
        with st.form("trade_form"):
            c1, c2 = st.columns(2)
            date = c1.date_input("Data Operazione")
            asset = c2.text_input("Simbolo (es. EURUSD)")
            
            c3, c4, c5 = st.columns(3)
            side = c3.selectbox("Direzione", ["Long", "Short"])
            entry = c4.number_input("Prezzo Entrata", format="%.5f")
            exit_p = c5.number_input("Prezzo Uscita", format="%.5f")
            
            if st.form_submit_button("REGISTRA TRADE"):
                profit = (exit_p - entry) if side == "Long" else (entry - exit_p)
                new_row = pd.DataFrame([[date, asset, side, entry, 0, 0, exit_p, profit, 0, ""]], columns=df.columns[:10])
                df = pd.concat([df, new_row], ignore_index=True)
                df.to_csv(DB_FILE, index=False)
                st.balloons()
