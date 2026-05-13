import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Pro Trading Journal v2.0",
    page_icon="📊",
    layout="wide"
)

# --- STILE CSS PERSONALIZZATO (DARK UI) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    [data-testid="stMetricValue"] { color: #00FFA3 !important; font-size: 1.8rem !important; }
    .stSidebar { background-color: #161B22; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #5865F2; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- FUNZIONI DI SUPPORTO DATI ---
DB_FILE = "trades_database.csv"

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Data'] = pd.to_datetime(df['Data'])
        return df
    return pd.DataFrame(columns=["Data", "Asset", "Tipo", "Entrata", "SL", "TP", "Uscita", "Risultato", "R:R", "Note"])

def get_benchmark_data(ticker, start_date, end_date):
    try:
        data = yf.download(ticker, start=start_date, end=end_date)['Close']
        if isinstance(data, pd.DataFrame):
            data = data.iloc[:, 0]
        return (data / data.iloc[0] - 1) * 100
    except:
        return None

# Caricamento database
df = load_data()

# --- 1. DEFINIZIONE SIDEBAR (Risolve il NameError) ---
st.sidebar.title("🚀 TradeMenu")
page = st.sidebar.radio("Navigazione:", ["🏠 Dashboard", "📝 Inserimento Trade", "🔥 Heatmap Operativa"])

# --- 2. LOGICA DELLE PAGINE ---

# --- PAGINA: DASHBOARD ---
if page == "🏠 Dashboard":
    st.title("📈 Performance vs Benchmarks")
    
    if not df.empty:
        # Selettori in Sidebar per Dashboard
        st.sidebar.divider()
        st.sidebar.subheader("Impostazioni Grafico")
        timeframe = st.sidebar.selectbox("Timeframe", ["Tutto", "Ultimi 30 giorni", "Anno Corrente"])
        bench_choice = st.sidebar.selectbox("Benchmark", ["S&P 500 (^GSPC)", "NASDAQ (^IXIC)", "DAX (^GDAXI)", "Bitcoin (BTC-USD)"])
        
        # Filtro dati
        df_filtered = df.copy().sort_values('Data')
        today = pd.to_datetime(datetime.date.today())
        
        if timeframe == "Ultimi 30 giorni":
            df_filtered = df_filtered[df_filtered['Data'] >= (today - pd.Timedelta(days=30))]
        elif timeframe == "Anno Corrente":
            df_filtered = df_filtered[df_filtered['Data'].dt.year == today.year]

        if not df_filtered.empty:
            # Calcolo Rendimento Utente (Capitale base ipotetico 10k)
            capitale_iniziale = 10000
            df_filtered['Rendimento_User'] = (df_filtered['Risultato'].cumsum() / capitale_iniziale) * 100
            
            # Recupero Benchmark
            start_d = df_filtered['Data'].min()
            end_d = df_filtered['Data'].max() + pd.Timedelta(days=1)
            bench_ticker = bench_choice.split("(")[1].replace(")", "")
            bench_series = get_benchmark_data(bench_ticker, start_d, end_d)

            # --- Grafico Comparativo ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_filtered['Data'], y=df_filtered['Rendimento_User'], name="Tu (Relativo %)", line=dict(color='#00FFA3', width=3)))
            
            if bench_series is not None:
                fig.add_trace(go.Scatter(x=bench_series.index, y=bench_series.values, name=bench_choice.split(" ")[0], line=dict(color='#FFB800', dash='dot')))
            
            fig.update_layout(template="plotly_dark", title="Confronto Rendimento Percentuale", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # Metriche
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("P&L Totale", f"€ {df_filtered['Risultato'].sum():.2f}")
            c2.metric("Win Rate", f"{(len(df_filtered[df_filtered['Risultato']>0])/len(df_filtered)*100):.1f}%")
            c3.metric("Rendimento %", f"{df_filtered['Rendimento_User'].iloc[-1]:.2f}%")
            c4.metric("Alpha", f"{(df_filtered['Rendimento_User'].iloc[-1] - (bench_series.iloc[-1] if bench_series is not None else 0)):.2f}%")
        else:
            st.warning("Nessun dato per il timeframe selezionato.")
    else:
        st.info("Benvenuto! Registra il tuo primo trade per attivare la dashboard.")

# --- PAGINA: INSERIMENTO ---
elif page == "📝 Inserimento Trade":
    st.title("📝 Registra Nuova Operazione")
    with st.form("trade_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        date = c1.date_input("Data", datetime.date.today())
        asset = c2.text_input("Asset (es. AAPL, BTC)")
        side = c3.selectbox("Tipo", ["Long", "Short"])
        
        c4, c5, c6 = st.columns(3)
        entry = c4.number_input("Entrata", format="%.5f")
        exit_p = c5.number_input("Uscita", format="%.5f")
        notes = c6.text_input("Note veloci")
        
        submitted = st.form_submit_button("SALVA TRADE")
        if submitted:
            profit = (exit_p - entry) if side == "Long" else (entry - exit_p)
            new_trade = pd.DataFrame([[date, asset, side, entry, 0, 0, exit_p, profit, 0, notes]], columns=df.columns[:10])
            df = pd.concat([df, new_trade], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success("Trade salvato correttamente!")

# --- PAGINA: HEATMAP ---
elif page == "🔥 Heatmap Operativa":
    st.title("🔥 Analisi Frequenza e Profittabilità")
    if not df.empty:
        df['Mese'] = df['Data'].dt.month_name()
        df['Giorno_Settimana'] = df['Data'].dt.day_name()
        
        # Heatmap profitti per Giorno e Mese
        pivot = df.groupby(['Mese', 'Giorno_Settimana'])['Risultato'].sum().unstack().fillna(0)
        fig_heat = px.imshow(pivot, text_auto=True, color_continuous_scale='RdYlGn', template="plotly_dark", title="Heatmap Profitti (€)")
        st.plotly_chart(fig_heat, use_container_width=True)
        
        # Bar chart mensile
        st.divider()
        monthly_bar = df.groupby('Mese')['Risultato'].sum().reset_index()
        fig_bar = px.bar(monthly_bar, x='Mese', y='Risultato', color='Risultato', color_continuous_scale='RdYlGn', template="plotly_dark", title="Performance per Mese")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("Dati insufficienti per generare la Heatmap.")
