import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Pro Trading Journal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STILE CSS PERSONALIZZATO (DARK MODE PRO) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #00FFA3 !important;
    }
    .stDataFrame {
        border: 1px solid #30363D;
        border-radius: 10px;
    }
    /* Arrotondamento bottoni */
    .stButton>button {
        border-radius: 8px;
        background-color: #5865F2;
        color: white;
        width: 100%;
        border: none;
        padding: 10px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #4752C4;
    }
    </style>
""", unsafe_allow_html=True)

# --- GESTIONE DATI (CSV LOCALE) ---
# Nota: Su Streamlit Cloud i dati CSV sono temporanei.
# Per renderli permanenti dovrai collegare Google Sheets (chiedimi come appena l'app è online!)
DB_FILE = "trades_database.csv"

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Data", "Asset", "Tipo", "Entrata", "SL", "TP", "Uscita", "Risultato", "R:R", "Note"])

df = load_data()

# --- SIDEBAR: INSERIMENTO ---
st.sidebar.header("📝 Registra Operazione")
with st.sidebar.form("new_trade", clear_on_submit=True):
    d_date = st.date_input("Data Trade", datetime.date.today())
    d_asset = st.text_input("Asset", placeholder="es. BTCUSDT")
    d_side = st.selectbox("Direzione", ["Long", "Short"])
    
    col_a, col_b = st.columns(2)
    d_entry = col_a.number_input("Entrata", format="%.5f", value=0.0)
    d_sl = col_b.number_input("Stop Loss", format="%.5f", value=0.0)
    
    col_c, col_d = st.columns(2)
    d_tp = col_c.number_input("Take Profit", format="%.5f", value=0.0)
    d_exit = col_d.number_input("Uscita", format="%.5f", value=0.0)
    
    d_notes = st.text_area("Note e Strategia")
    
    save = st.form_submit_button("CONFERMA TRADE")

    if save:
        # Calcolo logica semplificata P&L e R:R
        profit = d_exit - d_entry if d_side == "Long" else d_entry - d_exit
        risk = abs(d_entry - d_sl)
        rr = abs(profit / risk) if risk != 0 else 0
        
        new_row = pd.DataFrame([[str(d_date), d_asset, d_side, d_entry, d_sl, d_tp, d_exit, profit, rr, d_notes]], 
                                columns=df.columns)
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.sidebar.success("Trade salvato!")
        st.rerun()

# --- DASHBOARD PRINCIPALE ---
st.title("📈 Trading Dashboard")

if not df.empty:
    # Metriche principali
    wins = df[df['Risultato'] > 0].shape[0]
    total = df.shape[0]
    win_rate = (wins / total * 100) if total > 0 else 0
    pnl_totale = df['Risultato'].sum()
    avg_rr = df['R:R'].mean()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Win Rate", f"{win_rate:.1f}%")
    m2.metric("P&L Netto", f"€ {pnl_totale:.2f}")
    m3.metric("R:R Medio", f"{avg_rr:.2f}")
    m4.metric("N° Trade", total)

    st.divider()

    # Grafici
    g1, g2 = st.columns([2, 1])
    
    with g1:
        st.subheader("Andamento Equity")
        df['Equity'] = df['Risultato'].cumsum()
        fig_equity = px.area(df, x=df.index, y='Equity', template="plotly_dark", color_discrete_sequence=['#00FFA3'])
        fig_equity.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_equity, use_container_width=True)

    with g2:
        st.subheader("Distribuzione Esiti")
        # Conta quanti trade sono in profitto vs perdita
        df['Esito'] = df['Risultato'].apply(lambda x: 'Profit' if x > 0 else 'Loss')
        fig_pie = px.pie(df, names='Esito', hole=0.4, template="plotly_dark", color_discrete_map={'Profit':'#00FFA3', 'Loss':'#FF4B4B'})
        st.plotly_chart(fig_pie, use_container_width=True)

    # Tabella Storico
    st.subheader("📜 Storico Operazioni")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)

else:
    st.info("Benvenuto! Inserisci il tuo primo trade nella barra laterale per attivare la dashboard.")
