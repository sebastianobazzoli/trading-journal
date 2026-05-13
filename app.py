import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Ultimate Trading Journal", page_icon="📊", layout="wide")

# --- STILE CSS (DARK UI) ---
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    [data-testid="stMetricValue"] { color: #00FFA3 !important; font-size: 1.8rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #161B22; border-radius: 5px; color: white; }
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

# --- NAVIGAZIONE SIDEBAR ---
st.sidebar.title("🚀 TradeMenu")
page = st.sidebar.radio("Vai a:", ["🏠 Dashboard", "📝 Inserimento Trade", "🔥 Heatmap Operativa"])

# --- PAGINA 1: DASHBOARD ---
if page == "🏠 Dashboard":
    st.title("📈 Global Analytics")
    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Win Rate", f"{(df[df['Risultato']>0].shape[0]/len(df)*100):.1f}%")
        m2.metric("P&L Totale", f"€ {df['Risultato'].sum():.2f}")
        m3.metric("Profit Factor", f"{(df[df['Risultato']>0]['Risultato'].sum() / abs(df[df['Risultato']<0]['Risultato'].sum())):.2f}" if any(df['Risultato']<0) else "INF")
        m4.metric("Trade Totali", len(df))

        st.divider()
        c1, c2 = st.columns([2, 1])
        with c1:
            df_sorted = df.sort_values('Data')
            df_sorted['Equity'] = df_sorted['Risultato'].cumsum()
            fig = px.area(df_sorted, x='Data', y='Equity', title="Equity Curve", template="plotly_dark", color_discrete_sequence=['#00FFA3'])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig_pie = px.pie(df, names='Asset', title="Asset Distribution", hole=0.4, template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Nessun dato disponibile. Inizia a inserire trade!")

# --- PAGINA 2: INSERIMENTO ---
elif page == "📝 Inserimento Trade":
    st.title("📝 New Execution")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        d_date = col1.date_input("Data", datetime.date.today())
        d_asset = col2.text_input("Asset (es. NASDAQ, BTC)")
        
        col3, col4, col5 = st.columns(3)
        d_entry = col3.number_input("Entrata", format="%.5f")
        d_exit = col4.number_input("Uscita", format="%.5f")
        d_side = col5.selectbox("Side", ["Long", "Short"])
        
        d_notes = st.text_area("Note del Trade")
        submit = st.form_submit_button("SALVA OPERAZIONE")

        if submit:
            profit = (d_exit - d_entry) if d_side == "Long" else (d_entry - d_exit)
            new_data = pd.DataFrame([[d_date, d_asset, d_side, d_entry, 0, 0, d_exit, profit, 0, d_notes]], columns=df.columns[:10])
            df = pd.concat([df, new_data], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            st.success("Trade registrato con successo!")

# --- PAGINA 3: HEATMAP ---
elif page == "🔥 Heatmap Operativa":
    st.title("🔥 Market Presence Heatmap")
    if not df.empty:
        # Preparazione dati per Heatmap Giornaliera
        df['Giorno'] = df['Data'].dt.day
        df['Mese'] = df['Data'].dt.month_name()
        
        heatmap_data = df.groupby(['Mese', 'Giorno'])['Risultato'].sum().unstack().fillna(0)
        
        st.subheader("Performance Giornaliera (Mese corrente)")
        fig_heat = px.imshow(heatmap_data, 
                            labels=dict(x="Giorno del Mese", y="Mese", color="Profitto (€)"),
                            color_continuous_scale='RdYlGn', 
                            template="plotly_dark")
        st.plotly_chart(fig_heat, use_container_width=True)
        
        st.divider()
        st.subheader("Performance Mensile (Anno)")
        df['Anno'] = df['Data'].dt.year
        monthly_perf = df.groupby(['Anno', 'Mese'])['Risultato'].sum().unstack().fillna(0)
        fig_month = px.bar(df.groupby('Mese')['Risultato'].sum(), title="Profitto per Mese", template="plotly_dark", color_value="Risultato", color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_month, use_container_width=True)
    else:
        st.warning("Inserisci dei trade per visualizzare la Heatmap.")
