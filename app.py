import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
import datetime
import os

# --- FUNZIONI DI SUPPORTO ---
def get_benchmark_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)['Close']
    # Normalizziamo a 100 per il confronto (Rendimento percentuale)
    return (data / data.iloc[0] - 1) * 100

# --- PAGINA 1: DASHBOARD ---
if page == "🏠 Dashboard":
    st.title("📈 Performance vs Global Benchmarks")
    
    if not df.empty:
        # --- FILTRI TIMEFRAME ---
        st.sidebar.subheader("Filtri Dashboard")
        timeframe = st.sidebar.selectbox("Seleziona Timeframe", ["Tutto", "Ultimi 30 giorni", "Anno Corrente"])
        benchmark_ticker = st.sidebar.selectbox("Confronta con Indice", 
                                              ["S&P 500 (^GSPC)", "NASDAQ (^IXIC)", "DAX (^GDAXI)", "Bitcoin (BTC-USD)"])

        # Filtraggio dati in base al timeframe
        today = pd.to_datetime(datetime.date.today())
        df_filtered = df.copy()
        if timeframe == "Ultimi 30 giorni":
            df_filtered = df[df['Data'] >= (today - pd.Timedelta(days=30))]
        elif timeframe == "Anno Corrente":
            df_filtered = df[df['Data'] >= pd.to_datetime(f"{datetime.date.today().year}-01-01")]

        if df_filtered.empty:
            st.warning("Nessun trade nel periodo selezionato.")
        else:
            # Calcolo Rendimento Utente (Percentuale cumulativa)
            df_sorted = df_filtered.sort_values('Data')
            # Ipotizziamo un capitale iniziale di 10.000€ se non specificato per il calcolo %
            capitale_iniziale = 10000 
            df_sorted['Rendimento_User'] = (df_sorted['Risultato'].cumsum() / capitale_iniziale) * 100
            
            # Recupero Dati Benchmark
            start_d = df_sorted['Data'].min()
            end_d = df_sorted['Data'].max() + pd.Timedelta(days=1)
            
            try:
                bench_data = get_benchmark_data(benchmark_ticker.split("(")[1].replace(")", ""), start_d, end_d)
                
                # --- GRAFICO DI CONFRONTO ---
                fig_comp = go.Figure()
                
                # Linea Utente
                fig_comp.add_trace(go.Scatter(x=df_sorted['Data'], y=df_sorted['Rendimento_User'],
                                            mode='lines+markers', name='Tuo Rendimento %',
                                            line=dict(color='#00FFA3', width=3)))
                
                # Linea Benchmark
                fig_comp.add_trace(go.Scatter(x=bench_data.index, y=bench_data.values,
                                            mode='lines', name=benchmark_ticker.split(" ")[0],
                                            line=dict(color='#FFB800', width=2, dash='dot')))
                
                fig_comp.update_layout(title=f"Tua Performance vs {benchmark_ticker}",
                                      template="plotly_dark",
                                      xaxis_title="Data",
                                      yaxis_title="Rendimento Percentuale (%)",
                                      hovermode="x unified")
                
                st.plotly_chart(fig_comp, use_container_width=True)
                
            except Exception as e:
                st.error(f"Errore nel caricamento dei dati benchmark: {e}")
                # Mostra solo il grafico utente se il benchmark fallisce
                fig_user = px.line(df_sorted, x='Data', y='Rendimento_User', title="Tuo Rendimento %", template="plotly_dark")
                st.plotly_chart(fig_user, use_container_width=True)

            # Metriche riassuntive
            c1, c2, c3 = st.columns(3)
            user_perf = df_sorted['Rendimento_User'].iloc[-1]
            c1.metric("Tuo Rendimento", f"{user_perf:.2f}%", delta=f"{user_perf:.2f}%")
            if 'bench_data' in locals():
                bench_perf = bench_data.iloc[-1]
                c2.metric(f"Rendimento {benchmark_ticker.split(' ')[0]}", f"{bench_perf:.2f}%")
                c3.metric("Alpha (Sovraperformance)", f"{(user_perf - bench_perf):.2f}%")

    else:
        st.info("Inserisci dei trade per vedere il confronto con i mercati globali.")
