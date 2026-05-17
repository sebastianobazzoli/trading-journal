import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client, Client

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 2. CSS PROFESSIONALE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        .block-container { padding-top: 4rem !important; padding-left: 1.5rem !important; padding-right: 1.5rem !important; max-width: 100% !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: #050505 !important; font-family: 'Roboto Mono', monospace !important; color: #CCC; }
        [data-testid="stSidebar"] { background-color: #080808 !important; border-right: 1px solid #1A1A1A !important; padding-top: 2rem !important; }
        .panel { border: 1px solid #1A1A1A; padding: 15px; background: #0A0A0A; border-radius: 4px; margin-bottom: 15px; }
        .ticker-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        
        div.stButton > button {
            background-color: #0A0A0A !important; color: #888 !important; border: 1px solid #1A1A1A !important;
            border-radius: 2px !important; padding: 6px 20px !important; font-family: 'Roboto Mono', monospace !important;
            font-size: 11px !important; text-transform: uppercase !important; transition: all 0.2s ease !important;
        }
        div.stButton > button:hover { border-color: #00FF41 !important; color: #00FF41 !important; }
        
        .card-title { color: #00FF41; font-weight: 700; font-size: 14px; margin-bottom: 10px; border-bottom: 1px solid #1A1A1A; padding-bottom: 5px; }
        .stat-val { font-size: 18px; font-weight: 700; color: #FFF; }
        .stat-sub { font-size: 10px; color: #555; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNZIONI DATI ---
def get_data(table):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except: return pd.DataFrame()

trades = get_data("trades")
balances = get_data("balances")

# --- 4. NAVIGAZIONE ---
if 'page' not in st.session_state: st.session_state.page = 'DASHBOARD'
def set_page(name): st.session_state.page = name

with st.sidebar:
    st.markdown("<div style='color:#00FF41; font-weight:700; font-size:18px; margin-top:20px;'>TERMINAL_OS</div>", unsafe_allow_html=True)
    st.button("[01] MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("[02] TRADE_EXECUTION", on_click=set_page, args=('TRADE',))
    st.button("[03] PERFORMANCE_HEATMAP", on_click=set_page, args=('HEATMAP',))
    st.button("[04] SYSTEM_SETTINGS", on_click=set_page, args=('SETTINGS',))

# --- 5. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    if not balances.empty: st.info("Dashboard attiva e agganciata al Vault di sistema.")
    else: st.warning("Inizializza i tuoi conti nella sezione SYSTEM_SETTINGS.")

# --- 6. PAGINA: TRADE EXECUTION ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    valid_accounts = balances['account_name'].unique().tolist() if not balances.empty else []

    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        if valid_accounts:
            with st.form("trade_form", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns(4)
                asset, side, qty, entry_p = c1.text_input("TICKER"), c2.selectbox("SIDE", ["LONG", "SHORT"]), c3.number_input("QTY", min_value=0.0, step=0.01), c4.number_input("ENTRY", min_value=0.0)
                c5, c6, c7 = st.columns(3)
                exit_p, open_d, lev = c5.number_input("EXIT (OUT)", min_value=0.0, value=0.0), c6.date_input("OPEN DATE"), c7.number_input("LEV", min_value=1.0, value=1.0)
                
                c8, c9 = st.columns(2)
                acc_choice = c8.selectbox("LINK TO VAULT ACCOUNT", valid_accounts)
                avail_currencies = balances[balances['account_name'] == acc_choice]['currency'].unique().tolist()
                curr_choice = c9.selectbox("CURRENCY", avail_currencies)

                if st.form_submit_button("REGISTRA"):
                    status = "CHIUSA" if exit_p > 0 else "APERTA"
                    cost = round((entry_p * qty) / lev, 2)
                    pnl = round(((exit_p - entry_p) * qty * (1 if side == "LONG" else -1)), 2) if exit_p > 0 else 0
                    supabase.table("trades").insert({
                        "asset": asset, "side": side, "shares": qty, "entry_price": entry_p, "exit_price": exit_p,
                        "status": status, "date": str(open_d), "close_date": str(datetime.date.today()) if exit_p > 0 else None,
                        "leverage": lev, "cost": cost, "profit": pnl, 
                        "pnl_perc": round(pnl/cost*100, 2) if (exit_p > 0 and cost > 0) else 0,
                        "portfolio": acc_choice, "currency": curr_choice, "instrument": "Stock"
                    }).execute()
                    st.rerun()
        else: st.error("ERRORE DI SISTEMA: Crea prima un conto in SYSTEM_SETTINGS.")

    if not trades.empty:
        for c in ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'cost']:
            if c in trades.columns: trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)

        trades['P&L'] = trades['profit'].apply(lambda x: f"◼ {x:,.2f}" if x == 0 else (f"▲ {x:,.2f}" if x > 0 else f"▼ {x:,.2f}"))
        trades['%'] = trades['pnl_perc'].apply(lambda x: f"◼ {x:,.2f}%" if x == 0 else (f"▲ {x:,.2f}%" if x > 0 else f"▼ {x:,.2f}%"))
        trades['STATO'] = trades['status'].apply(lambda x: f"⌾ {x}" if x == "APERTA" else f"• {x}")

        column_order = ['id', 'asset', 'side', 'shares', 'entry_price', 'exit_price', 'leverage', 'cost', 'portfolio', 'currency', 'P&L', '%', 'STATO']
        display_trades = trades[[col for col in column_order if col in trades.columns]].sort_values("STATO", ascending=False)

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM</div>", unsafe_allow_html=True)
        edited = st.data_editor(display_trades, use_container_width=True, hide_index=True, disabled=["id", "cost", "P&L", "%", "STATO", "portfolio", "currency"], column_config={"id": None, "asset": "TKR", "side": "S", "shares": st.column_config.NumberColumn("QTY", format="%.2f"), "entry_price": st.column_config.NumberColumn("IN", format="%.2f"), "exit_price": st.column_config.NumberColumn("OUT", format="%.2f"), "leverage": "LEV", "cost": st.column_config.NumberColumn("COST", format="%.2f"), "portfolio": "CONTO", "currency": "VAL", "P&L": st.column_config.TextColumn("P&L (REAL)", width=100), "%": st.column_config.TextColumn("RENDIMENTO", width=95), "STATO": st.column_config.TextColumn("STATO", width=90)}, key="ledger_v20")
        
        if st.button("SYNCHRONIZE"):
            has_error = False
            for idx, row in edited.iterrows():
                if 'portfolio' not in row or row['portfolio'] not in valid_accounts:
                    has_error = True; st.error(f"ERRORE: Riga asset '{row.get('asset')}' non valida."); break
            if not has_error:
                ids_del = set(trades['id']) - set(edited['id'])
                for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                for _, r in edited.iterrows():
                    p_out, p_in, q = float(r['exit_price']), float(r['entry_price']), float(r['shares'])
                    orig = trades[trades['id'] == r['id']]; lev_val = float(orig['leverage'].values[0]) if not orig.empty else 1.0
                    c = round((p_in * q) / lev_val, 2)
                    pnl = round(((p_out - p_in) * q * (1 if r['side'] == "LONG" else -1)), 2) if p_out > 0 else 0
                    supabase.table("trades").update({
                        "exit_price": p_out, 
                        "status": "CHIUSA" if p_out > 0 else "APERTA", 
                        "close_date": str(datetime.date.today()) if p_out > 0 else None,
                        "portfolio": r['portfolio'], "cost": c, "profit": pnl, 
                        "pnl_perc": round(pnl/c*100, 2) if (p_out > 0 and c > 0) else 0
                    }).eq("id", r['id']).execute()
                st.rerun()

# --- 7. PAGINA: PERFORMANCE HEATMAP (CALENDAR VIEWS) ---
elif st.session_state.page == 'HEATMAP':
    st.markdown("### / PERFORMANCE_HEATMAP")
    
    if not trades.empty:
        # Vincolo 1: Filtriamo rigidamente tenendo SOLO le operazioni CHIUSE e con close_date compilata
        time_df = trades[(trades['status'] == 'CHIUSA') & (trades['close_date'].notna())].copy()
        
        if not time_df.empty:
            time_df['close_date'] = pd.to_datetime(time_df['close_date'], errors='coerce')
            time_df = time_df.dropna(subset=['close_date'])
            time_df['profit'] = pd.to_numeric(time_df['profit'], errors='coerce').fillna(0.0)
            
            # Parametri Temporali basati su close_date
            time_df['year'] = time_df['close_date'].dt.year
            time_df['month'] = time_df['close_date'].dt.month
            time_df['day'] = time_df['close_date'].dt.day
            time_df['month_name'] = time_df['close_date'].dt.strftime('%b')
            
            months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            all_days = list(range(1, 32)) # Griglia fissa 1-31

            # --- 1. HEATMAP MENSILE (GIORNO PER GIORNO COMPLETA) ---
            st.markdown("<div class='ticker-label'>DAILY_OPERATIONAL_MATRIX // FULL_YEAR_GRID (1-31)</div>", unsafe_allow_html=True)
            
            current_year = datetime.date.today().year
            daily_df = time_df[time_df['year'] == current_year]
            
            # Raggruppiamo i trade reali estratti per close_date
            daily_agg = daily_df.groupby(['month_name', 'day']).agg(
                pnl_totale=('profit', 'sum'),
                num_trades=('id', 'count'),
                assets_list=('asset', lambda x: ", ".join(x.dropna().unique()))
            ).reset_index()
            
            # Costruzione forzata della matrice completa (12 mesi x 31 giorni) per mostrare sempre tutti i giorni
            pivot_daily = daily_agg.pivot(index='month_name', columns='day', values='pnl_totale').reindex(index=months_order, columns=all_days).fillna(0.0)
            pivot_trades = daily_agg.pivot(index='month_name', columns='day', values='num_trades').reindex(index=months_order, columns=all_days).fillna(0)
            pivot_assets = daily_agg.pivot(index='month_name', columns='day', values='assets_list').reindex(index=months_order, columns=all_days).fillna("None")

            fig_daily = go.Figure(data=go.Heatmap(
                z=pivot_daily.values,
                x=pivot_daily.columns,
                y=pivot_daily.index,
                colorscale=[[0.0, "#FF3131"], [0.5, "#111111"], [1.0, "#00FF41"]],
                zmid=0.0,
                showscale=True,
                hovertemplate="<b>MESE:</b> %{y}<br><b>GIORNO:</b> %{x}<br><b>P&L:</b> %{z:,.2f}<br><b>OPERAZIONI:</b> %{customdata[0]}<br><b>ASSETS:</b> %{customdata[1]}<extra></extra>",
                customdata=list(zip(pivot_trades.values, pivot_assets.values))
            ))
            
            fig_daily.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Roboto Mono", color="#CCC", size=10), height=320, margin=dict(l=50,r=10,t=10,b=30))
            fig_daily.update_xaxes(title="GIORNO DEL MESE", tickmode="linear", dtick=1, gridcolor='#1A1A1A')
            fig_daily.update_yaxes(gridcolor='#1A1A1A')
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.plotly_chart(fig_daily, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # --- 2. HEATMAP ANNUALE (MESE PER MESE HISTORICAL) ---
            st.markdown("<br><div class='ticker-label'>ANNUAL_MACRO_MATRIX // MONTHLY HISTORICAL PERFORMANCE</div>", unsafe_allow_html=True)
            
            yearly_agg = time_df.groupby(['year', 'month_name']).agg(
                pnl_totale=('profit', 'sum'),
                num_trades=('id', 'count'),
                assets_list=('asset', lambda x: ", ".join(x.dropna().unique()))
            ).reset_index()
            
            unique_years = sorted(time_df['year'].unique())
            pivot_yearly = yearly_agg.pivot(index='year', columns='month_name', values='pnl_totale').reindex(index=unique_years, columns=months_order).fillna(0.0)
            pivot_y_trades = yearly_agg.pivot(index='year', columns='month_name', values='num_trades').reindex(index=unique_years, columns=months_order).fillna(0)
            pivot_y_assets = yearly_agg.pivot(index='year', columns='month_name', values='assets_list').reindex(index=unique_years, columns=months_order).fillna("None")

            fig_yearly = go.Figure(data=go.Heatmap(
                z=pivot_yearly.values,
                x=pivot_yearly.columns,
                y=pivot_yearly.index,
                colorscale=[[0.0, "#FF3131"], [0.5, "#111111"], [1.0, "#00FF41"]],
                zmid=0.0,
                showscale=True,
                hovertemplate="<b>ANNO:</b> %{y}<br><b>MESE:</b> %{x}<br><b>P&L:</b> %{z:,.2f}<br><b>OPERAZIONI:</b> %{customdata[0]}<br><b>ASSETS:</b> %{customdata[1]}<extra></extra>",
                customdata=list(zip(pivot_y_trades.values, pivot_y_assets.values))
            ))
            
            fig_yearly.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Roboto Mono", color="#CCC", size=10), height=220, margin=dict(l=50,r=10,t=10,b=30))
            fig_yearly.update_xaxes(gridcolor='#1A1A1A')
            fig_yearly.update_yaxes(title="ANNO", tickmode="linear", dtick=1, gridcolor='#1A1A1A')
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.plotly_chart(fig_yearly, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        else: st.info("Nessuna operazione risulta attualmente nello stato 'CHIUSA' con una data di chiusura valida.")
    else: st.info("Chiudi dei trade per generare le matrici temporali di performance.")

# --- 8. PAGINA: SETTINGS ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    with st.expander("ADD_NEW_ACCOUNT_ASSET", expanded=False):
        with st.form("vault_form"):
            c1, c2, c3 = st.columns(3)
            n, cr, bl = c1.text_input("ACCOUNT NAME"), c2.selectbox("CURR", ["USD", "EUR", "USDT", "BTC", "ETH"]), c3.number_input("INITIAL BALANCE", min_value=0.0)
            if st.form_submit_button("INIZIALIZZA"):
                if n: supabase.table("balances").insert({"account_name": n, "currency": cr, "initial_balance": bl}).execute(); st.rerun()

    if not balances.empty:
        st.markdown("<div class='ticker-label'>VAULT_INSIGHTS & LIVE MANAGEMENT</div>", unsafe_allow_html=True)
        for acc in balances['account_name'].unique():
            acc_data = balances[balances['account_name'] == acc]
            with st.container():
                c_info, c_chart = st.columns([1, 1.5])
                total_bal, margin_used = 0, 0
                for _, r in acc_data.iterrows():
                    init = float(r['initial_balance'])
                    pnl = pd.to_numeric(trades[(trades['portfolio'] == acc) & (trades['status'] == 'CHIUSA')]['profit']).sum() if not trades.empty else 0
                    total_bal += (init + pnl)
                    margin_used += pd.to_numeric(trades[(trades['portfolio'] == acc) & (trades['status'] == 'APERTA')]['cost']).sum() if not trades.empty else 0
                liq = total_bal - margin_used
                with c_info: st.markdown(f"<div class='panel'><div class='card-title'>{acc.upper()}</div><div class='stat-sub'>Patrimonio Totale</div><div class='stat-val'>{total_bal:,.2f}</div><div class='stat-sub' style='margin-top:10px;'>Liquidità Disponibile: <span style='color:#00FF41;'>{liq:,.2f}</span></div></div>", unsafe_allow_html=True)
                with c_chart:
                    fig = px.pie(pd.DataFrame({"Cat": ["Libero", "Impegnato"], "Val": [max(0, liq), margin_used]}), values='Val', names='Cat', hole=0.6, color_discrete_map={"Libero": "#00FF41", "Impegnato": "#222"})
                    fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=140, margin=dict(l=0,r=0,t=0,b=0)); st.plotly_chart(fig, use_container_width=True)

        st.markdown("<br><div class='ticker-label'>CONSOLE_DI_MODIFICA_CONTI</div>", unsafe_allow_html=True)
        edited_bal = st.data_editor(balances, use_container_width=True, hide_index=True, num_rows="dynamic", column_config={"id": None, "account_name": st.column_config.TextColumn("NOME CONTO", required=True), "currency": st.column_config.SelectboxColumn("VALUTA", options=["USD", "EUR", "USDT", "BTC", "ETH"], required=True), "initial_balance": st.column_config.NumberColumn("SALDO INIZIALE", format="%.2f", min_value=0.0)}, key="secure_settings_editor")
        if st.button("SYNC_SETTINGS_DATA"):
            try:
                ids_ori = set(balances['id']); ids_rim = set(edited_bal['id'].dropna())
                for d_id in (ids_ori - ids_rim): supabase.table("balances").delete().eq("id", d_id).execute()
                for _, r in edited_bal.iterrows():
                    if pd.isna(r['id']): supabase.table("balances").insert({"account_name": r['account_name'], "currency": r['currency'], "initial_balance": r['initial_balance']}).execute()
                    else: supabase.table("balances").update({"account_name": r['account_name'], "currency": r['currency'], "initial_balance": r['initial_balance']}).eq("id", r['id']).execute()
                st.rerun()
            except Exception as e: st.error(f"Errore: {e}")
