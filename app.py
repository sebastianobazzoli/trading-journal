import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configurazione Pagina
st.set_page_config(page_title="Il Mio Trading Journal", layout="wide")

# Funzione per caricare/salvare dati
DB_FILE = "trades_db.csv"
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Data", "Asset", "Tipo", "Entrata", "SL", "TP", "Uscita", "Risultato", "R:R"])

# Caricamento dati
df = load_data()

st.title("📊 My Personal Trading Journal")

# --- SIDEBAR: INSERIMENTO TRADE ---
st.sidebar.header("Inserisci Nuovo Trade")
with st.sidebar.form("trade_form", clear_on_submit=True):
    date = st.date_input("Data")
    asset = st.text_input("Asset (es. BTC, EURUSD, AAPL)")
    side = st.selectbox("Tipo", ["Long", "Short"])
    entry = st.number_input("Prezzo Entrata", format="%.5f")
    sl = st.number_input("Stop Loss", format="%.5f")
    tp = st.number_input("Take Profit", format="%.5f")
    exit_p = st.number_input("Prezzo Uscita (0 se aperto)", format="%.5f")
    
    submitted = st.form_submit_button("Salva Trade")
    
    if submitted:
        # Calcolo logica R:R e Profitto
        profit = exit_p - entry if side == "Long" else entry - exit_p
        risk = abs(entry - sl)
        rr = profit / risk if risk != 0 else 0
        
        new_data = pd.DataFrame([[date, asset, side, entry, sl, tp, exit_p, profit, rr]], 
                                columns=df.columns)
        df = pd.concat([df, new_data], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success("Trade salvato!")

# --- DASHBOARD PRINCIPALE ---
col1, col2, col3 = st.columns(3)

if not df.empty:
    win_rate = (df[df['Risultato'] > 0].shape[0] / df.shape[0]) * 100
    total_pnl = df['Risultato'].sum()
    
    col1.metric("Win Rate", f"{win_rate:.2f}%")
    col2.metric("P&L Totale", f"€ {total_pnl:.2f}")
    col3.metric("Trade Totali", len(df))

    # Grafico Equity Curve
    st.subheader("Andamento Portafoglio")
    df['Equity'] = df['Risultato'].cumsum()
    fig = px.line(df, x=df.index, y='Equity', title="Equity Curve")
    st.plotly_chart(fig, use_container_width=True)

    # Tabella Trade
    st.subheader("Storico Operazioni")
    st.dataframe(df, use_container_width=True)
else:
    st.info("Nessun trade registrato. Usa la barra laterale per iniziare!")