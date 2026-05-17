import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client

# --- 1. CONFIGURAZIONE & COSTANTI GLOBALI ---
st.set_page_config(page_title="TERMINAL_X", layout="wide", initial_sidebar_state="expanded")

# Costante globale valute
valid_currencies = ["USD", "EUR", "USDT", "BTC", "ETH"]

@st.cache_resource
def init_db():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_db()

# --- 2. CSS BLOOMBERG TERMINAL CORE (AMBER HOVER PATCH) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap');
        
        /* Layout & Sfondi Nativi Terminale */
        .block-container { padding-top: 2rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; }
        html, body, [data-testid="stAppViewContainer"] { background-color: #000000 !important; font-family: 'Roboto Mono', monospace !important; color: #D5D5D5; }
        [data-testid="stSidebar"] { background-color: #0A0A0A !important; border-right: 2px solid #222222 !important; padding-top: 1rem !important; }
        
        /* Pannelli Stile Bloomberg */
        .panel { border: 1px solid #222222; padding: 12px; background: #050505; border-radius: 2px; margin-bottom: 10px; }
        .ticker-label { color: #FFD700; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; border-left: 3px solid #FFD700; padding-left: 6px; }
        
        /* Pulsanti Professionali - FIX HOVER GIALLO BLOOMBERG */
        div.stButton > button {
            background-color: #111111 !important; color: #FFD700 !important; border: 1px solid #333333 !important;
            border-radius: 0px !important; padding: 4px 14px !important; font-family: 'Roboto Mono', monospace !important;
            font-size: 11px !important; text-transform: uppercase !important; font-weight: bold; width: 100%; text-align: left;
            transition: all 0.15s ease-in-out !important;
        }
        div.stButton > button:hover { 
            border-color: #FFFF00 !important; 
            color: #FFFF00 !important; 
            background-color: #1A1A1A !important; 
            box-shadow: inset 0 0 4px rgba(255, 215, 0, 0.2) !important;
        }
        
        /* Monitor Panel Card */
        .card-title { color: #FFD700; font-weight: 700; font-size: 13px; margin-bottom: 8px; border-bottom: 1px solid #222222; padding-bottom: 4px; text-transform: uppercase; }
        .stat-val { font-size: 20px; font-weight: 700; color: #FFFFFF; font-family: 'Roboto Mono', monospace; }
        .stat-sub { font-size: 9px; color: #666666; text-transform: uppercase; font-weight: bold; }
        
        div[data-testid="stDataEditor"] { background-color: #050505 !important; border: 1px solid #222222 !important; }
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
    st.markdown("<div style='color:#FFD700; font-weight:700; font-size:16px; margin-bottom:20px; padding-left:10px;'>BLOOMBERG_X // OS</div>", unsafe_allow_html=True)
    st.button("<GO> 1 . MONITOR_DASHBOARD", on_click=set_page, args=('DASHBOARD',))
    st.button("<GO> 2 . TRADE_EXECUTION_LOG", on_click=set_page, args=('TRADE',))
    st.button("<GO> 3 . PERFORMANCE_HEATMAP", on_click=set_page, args=('HEATMAP',))
    st.button("<GO> 4 . SYSTEM_SETTINGS_VAULT", on_click=set_page, args=('SETTINGS',))

# --- 5. PAGINA: DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("<h2 style='color:#FFF; font-size:20px; margin-bottom:15px;'>/ BBG_MONITOR_DASHBOARD</h2>", unsafe_allow_html=True)
    if not balances.empty:
        st.markdown("<div class='ticker-label'>GLOBAL_LIQUIDITY_RESERVES (AGGREGATED BY CURRENCY)</div>", unsafe_allow_html=True)
        global_curr = balances['currency'].unique()
        g_cols = st.columns(max(len(global_curr), 1))
        
        for idx, curr in enumerate(global_curr):
            curr_str = str(curr).strip()
            total_init = pd.to_numeric(balances[balances['currency'] == curr_str]['initial_balance']).sum()
            
            total_pnl, total_margin = 0, 0
            if not trades.empty:
                trades['currency_clean'] = trades['currency'].astype(str).str.strip()
                total_pnl = pd.to_numeric(trades[(trades['currency_clean'] == curr_str) & (trades['status'] == 'CHIUSA')]['profit']).sum()
                total_margin = pd.to_numeric(trades[(trades['currency_clean'] == curr_str) & (trades['status'] == 'APERTA')]['cost']).sum()
            
            total_vault = total_init + total_pnl
            total_liq = total_vault - total_margin
            
            with g_cols[idx]:
                st.markdown(f"""
                    <div class='panel'>
                        <div class='card-title'>TOTAL {curr_str}</div>
                        <div class='stat-sub'>Aggregated Equity Portfolio</div>
                        <div class='stat-val'>{total_vault:,.2f}</div>
                        <div class='stat-sub' style='margin-top:6px;'>Available Liquidity: <span style='color:#FFFF00;'>{total_liq:,.2f}</span></div>
                    </div>
                """, unsafe_allow_html=True)
    else: st.warning("Inizializza i tuoi conti nella sezione SYSTEM_SETTINGS.")

# --- 6. PAGINA: TRADE EXECUTION ---
elif st.session_state.page == 'TRADE':
    st.markdown("<h2 style='color:#FFF; font-size:20px; margin-bottom:15px;'>/ BBG_EXECUTION_BLOTTER</h2>", unsafe_allow_html=True)
    valid_accounts = balances['account_name'].unique().tolist() if not balances.empty else []

    with st.expander("📝 EXECUTE_NEW_ORDER_TICKET", expanded=False):
        if valid_accounts:
            with st.form("trade_form", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns(4)
                asset, side, qty, entry_p = c1.text_input("TICKER (eg. AAPL)"), c2.selectbox("SIDE", ["LONG", "SHORT"]), c3.number_input("QTY", min_value=0.0, step=0.01), c4.number_input("ENTRY PRICE", min_value=0.0)
                c5, c6, c7 = st.columns(3)
                exit_p, open_d, lev = c5.number_input("EXIT PRICE (Optional)", min_value=0.0, value=0.0), c6.date_input("TRADE DATE"), c7.number_input("LEVERAGE", min_value=1.0, value=1.0)
                
                c8, c9 = st.columns(2)
                acc_choice = c8.selectbox("ASSIGN TO VAULT", valid_accounts)
                curr_choice = c9.selectbox("SET TRADING CURRENCY", valid_currencies)

                if st.form_submit_button("TRANSMIT ORDER <GO>"):
                    status = "CHIUSA" if exit_p > 0 else "APERTA"
                    cost = round((entry_p * qty) / lev, 2)
                    pnl = round(((exit_p - entry_p) * qty * (1 if side == "LONG" else -1)), 2) if exit_p > 0 else 0
                    supabase.table("trades").insert({
                        "asset": asset.upper(), "side": side, "shares": qty, "entry_price": entry_p, "exit_price": exit_p,
                        "status": status, "date": str(open_d), "close_date": str(datetime.date.today()) if exit_p > 0 else None,
                        "leverage": lev, "cost": cost, "profit": pnl, 
                        "pnl_perc": round(pnl/cost*100, 2) if (exit_p > 0 and cost > 0) else 0,
                        "portfolio": acc_choice, "currency": curr_choice, "instrument": "Stock"
                    }).execute()
                    st.rerun()
        else: st.error("SISTEMA BLOCCATO: Inizializza almeno un conto Vault nei Settings.")

    if not trades.empty:
        for c in ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'cost', 'leverage']:
            if c in trades.columns: trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)

        trades['P&L_MARK'] = trades['profit'].apply(lambda x: f"◼ {x:,.2f}" if x == 0 else (f"▲ {x:,.2f}" if x > 0 else f"▼ {x:,.2f}"))
        trades['%_MARK'] = trades['pnl_perc'].apply(lambda x: f"◼ {x:,.2f}%" if x == 0 else (f"▲ {x:,.2f}%" if x > 0 else f"▼ {x:,.2f}%"))
        trades['STATO_MARK'] = trades['status'].apply(lambda x: f"⌾ {x}" if x == "APERTA" else f"• {x}")

        column_order = ['id', 'asset', 'side', 'shares', 'entry_price', 'exit_price', 'date', 'close_date', 'leverage', 'portfolio', 'currency', 'cost', 'P&L_MARK', '%_MARK', 'STATO_MARK']
        display_trades = trades[[col for col in column_order if col in trades.columns]].sort_values("id", ascending=False)

        st.markdown("<div class='ticker-label'>ACTIVE_LEDGER_BLOTTER (DOUBLE CLICK TO EDIT ANY CELL // SELECT & PRESS DEL TO REMOVE)</div>", unsafe_allow_html=True)
        
        edited = st.data_editor(
            display_trades, use_container_width=True, hide_index=True, num_rows="dynamic", 
            disabled=["id", "cost", "P&L_MARK", "%_MARK", "STATO_MARK"], 
            column_config={
                "id": None, "asset": st.column_config.TextColumn("TICKER", required=True), 
                "side": st.column_config.SelectboxColumn("S", options=["LONG", "SHORT"], required=True, width=70), 
                "shares": st.column_config.NumberColumn("QTY", format="%.2f", min_value=0.0), 
                "entry_price": st.column_config.NumberColumn("IN", format="%.2f", min_value=0.0), 
                "exit_price": st.column_config.NumberColumn("OUT", format="%.2f", min_value=0.0), 
                "date": st.column_config.TextColumn("OPEN DATE"), "close_date": st.column_config.TextColumn("CLOSE DATE"), 
                "leverage": st.column_config.NumberColumn("LEV", format="%d", min_value=1), 
                "portfolio": st.column_config.SelectboxColumn("CONTO", options=valid_accounts, required=True, width=110), 
                "currency": st.column_config.SelectboxColumn("VALUTA", options=valid_currencies, required=True, width=80), 
                "cost": st.column_config.NumberColumn("COST", format="%.2f"), 
                "P&L_MARK": st.column_config.TextColumn("P&L (REAL)", width=110), "%_MARK": st.column_config.TextColumn("RENDIMENTO", width=100), "STATO_MARK": st.column_config.TextColumn("STATO", width=95)
            }, 
            key="bloomberg_ledger_v27"
        )
        
        if st.button("COMMIT_CHANGES <GO>"):
            ids_originali = set(trades['id'].astype(int))
            edited_clean = edited.dropna(subset=['id'])
            ids_rimasti = set(edited_clean['id'].astype(int))
            
            ids_da_cancellare = ids_originali - ids_rimasti
            for d_id in ids_da_cancellare: supabase.table("trades").delete().eq("id", d_id).execute()
            
            for _, r in edited_clean.iterrows():
                p_out = float(r['exit_price']) if pd.notna(r['exit_price']) else 0.0
                p_in = float(r['entry_price']) if pd.notna(r['entry_price']) else 0.0
                q = float(r['shares']) if pd.notna(r['shares']) else 0.0
                lev_val = float(r['leverage']) if pd.notna(r['leverage']) else 1.0
                
                c = round((p_in * q) / lev_val, 2)
                pnl = round(((p_out - p_in) * q * (1 if r['side'] == "LONG" else -1)), 2) if p_out > 0 else 0
                c_date = r['close_date']
                if p_out > 0 and (pd.isna(c_date) or str(c_date).strip() == "" or c_date == "None"): c_date = str(datetime.date.today())
                elif p_out == 0: c_date = None
                
                supabase.table("trades").update({
                    "asset": str(r['asset']).upper(), "side": r['side'], "shares": q, "entry_price": p_in, "exit_price": p_out,
                    "status": "CHIUSA" if p_out > 0 else "APERTA", "date": str(r['date']), "close_date": str(c_date) if c_date else None, 
                    "portfolio": r['portfolio'], "currency": r['currency'], "leverage": lev_val, "cost": c, "profit": pnl, 
                    "pnl_perc": round(pnl/c*100, 2) if (p_out > 0 and c > 0) else 0
                }).eq("id", int(r['id'])).execute()
            st.rerun()

# --- 7. PAGINA: PERFORMANCE HEATMAP ---
elif st.session_state.page == 'HEATMAP':
    st.markdown("<h2 style='color:#FFF; font-size:20px; margin-bottom:15px;'>/ PERFORMANCE_HEATMAP_ENGINE</h2>", unsafe_allow_html=True)
    if not trades.empty:
        time_df = trades[(trades['status'] == 'CHIUSA') & (trades['close_date'].notna())].copy()
        if not time_df.empty:
            time_df['close_date'] = pd.to_datetime(time_df['close_date'], errors='coerce')
            time_df = time_df.dropna(subset=['close_date'])
            time_df['profit'] = pd.to_numeric(time_df['profit'], errors='coerce').fillna(0.0)
            time_df['year'] = time_df['close_date'].dt.year
            time_df['month'] = time_df['close_date'].dt.month
            time_df['day'] = time_df['close_date'].dt.day
            time_df['month_name'] = time_df['close_date'].dt.strftime('%b')
            
            months_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            all_days = list(range(1, 32))

            st.markdown("<div class='ticker-label'>DAILY_OPERATIONAL_MATRIX // GRID_SYSTEM</div>", unsafe_allow_html=True)
            current_year = datetime.date.today().year
            daily_df = time_df[time_df['year'] == current_year]
            daily_agg = daily_df.groupby(['month_name', 'day']).agg(pnl_totale=('profit', 'sum'), num_trades=('id', 'count'), assets_list=('asset', lambda x: ", ".join(x.dropna().unique()))).reset_index()
            pivot_daily = daily_agg.pivot(index='month_name', columns='day', values='pnl_totale').reindex(index=months_order, columns=all_days).fillna(0.0)
            pivot_trades = daily_agg.pivot(index='month_name', columns='day', values='num_trades').reindex(index=months_order, columns=all_days).fillna(0)
            pivot_assets = daily_agg.pivot(index='month_name', columns='day', values='assets_list').reindex(index=months_order, columns=all_days).fillna("None")

            fig_daily = go.Figure(data=go.Heatmap(z=pivot_daily.values, x=pivot_daily.columns, y=pivot_daily.index, colorscale=[[0.0, "#FF3131"], [0.5, "#0A0A0A"], [1.0, "#00FF41"]], zmid=0.0, showscale=True, hovertemplate="<b>MESE:</b> %{y}<br><b>GIORNO:</b> %{x}<br><b>P&L:</b> %{z:,.2f}<br><b>TRADE:</b> %{customdata[0]}<br><b>ASSET:</b> %{customdata[1]}<extra></extra>", customdata=list(zip(pivot_trades.values, pivot_assets.values))))
            fig_daily.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Roboto Mono", color="#D5D5D5", size=10), height=280, margin=dict(l=50, r=10, t=10, b=30))
            fig_daily.update_xaxes(tickmode="linear", dtick=1, gridcolor='#222222')
            fig_daily.update_yaxes(gridcolor='#222222')
            st.plotly_chart(fig_daily, use_container_width=True)

            st.markdown("<br><div class='ticker-label'>ANNUAL_MACRO_MATRIX // MONTHLY HISTORICAL SUMMARY</div>", unsafe_allow_html=True)
            yearly_agg = time_df.groupby(['year', 'month_name']).agg(pnl_totale=('profit', 'sum'), num_trades=('id', 'count'), assets_list=('asset', lambda x: ", ".join(x.dropna().unique()))).reset_index()
            unique_years = sorted(time_df['year'].unique())
            pivot_yearly = yearly_agg.pivot(index='year', columns='month_name', values='pnl_totale').reindex(index=unique_years, columns=months_order).fillna(0.0)
            pivot_y_trades = yearly_agg.pivot(index='year', columns='month_name', values='num_trades').reindex(index=unique_years, columns=months_order).fillna(0)
            pivot_y_assets = yearly_agg.pivot(index='year', columns='month_name', values='assets_list').reindex(index=unique_years, columns=months_order).fillna("None")

            fig_yearly = go.Figure(data=go.Heatmap(z=pivot_yearly.values, x=pivot_yearly.columns, y=pivot_yearly.index, colorscale=[[0.0, "#FF3131"], [0.5, "#0A0A0A"], [1.0, "#00FF41"]], zmid=0.0, showscale=True, hovertemplate="<b>ANNO:</b> %{y}<br><b>MESE:</b> %{x}<br><b>P&L:</b> %{z:,.2f}<br><b>TRADE:</b> %{customdata[0]}<br><b>ASSET:</b> %{customdata[1]}<extra></extra>", customdata=list(zip(pivot_y_trades.values, pivot_y_assets.values))))
            fig_yearly.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Roboto Mono", color="#D5D5D5", size=10), height=180, margin=dict(l=50, r=10, t=10, b=30))
            fig_yearly.update_xaxes(gridcolor='#222222')
            fig_yearly.update_yaxes(tickmode="linear", dtick=1, gridcolor='#222222')
            st.plotly_chart(fig_yearly, use_container_width=True)
        else: st.info("Nessuna operazione consolidata disponibile.")

# --- 8. PAGINA: SYSTEM SETTINGS ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("<h2 style='color:#FFF; font-size:20px; margin-bottom:15px;'>/ SYSTEM_SETTINGS_VAULT</h2>", unsafe_allow_html=True)
    with st.expander("ADD_NEW_ACCOUNT_ASSET", expanded=False):
        with st.form("vault_form"):
            c1, c2, c3 = st.columns(3)
            n, cr, bl = c1.text_input("ACCOUNT NAME"), c2.selectbox("CURR", ["USD", "EUR", "USDT", "BTC", "ETH"]), c3.number_input("INITIAL BALANCE", min_value=0.0)
            if st.form_submit_button("INIZIALIZZA"):
                if n: supabase.table("balances").insert({"account_name": n.strip(), "currency": cr, "initial_balance": bl}).execute(); st.rerun()

    if not balances.empty:
        st.markdown("<div class='ticker-label'>VAULT_INSIGHTS & LIVE CONSOLE</div>", unsafe_allow_html=True)
        for idx, row_balance in balances.iterrows():
            acc = str(row_balance['account_name']).strip()
            curr = str(row_balance['currency']).strip()
            init_val = float(row_balance['initial_balance'])
            row_id = row_balance['id']
            
            pnl, margin_used = 0, 0
            if not trades.empty:
                trades['portfolio_clean'] = trades['portfolio'].astype(str).str.strip()
                trades['currency_clean'] = trades['currency'].astype(str).str.strip()
                pnl = pd.to_numeric(trades[(trades['portfolio_clean'] == acc) & (trades['currency_clean'] == curr) & (trades['status'] == 'CHIUSA')]['profit']).sum()
                margin_used = pd.to_numeric(trades[(trades['portfolio_clean'] == acc) & (trades['currency_clean'] == curr) & (trades['status'] == 'APERTA')]['cost']).sum()
            
            total_bal = init_val + pnl
            liq = total_bal - margin_used
            
            with st.container():
                c_info, c_chart, c_actions = st.columns([1.5, 1.5, 1])
                with c_info:
                    st.markdown(f"""
                        <div class='panel'>
                            <div class='card-title'>{acc.upper()} // <span style='color:#666;'>{curr}</span></div>
                            <div class='total-label' style='font-size:9px; color:#666; text-transform:uppercase; font-weight:bold;'>Total Equity Balance</div>
                            <div class='stat-val'>{total_bal:,.2f}</div>
                            <div class='stat-sub' style='margin-top:10px;'>Free Cash Liquidity: <span style='color:#FFFF00;'>{liq:,.2f}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with c_chart:
                    fig = px.pie(pd.DataFrame({"Cat": ["Cash", "Margin Locked"], "Val": [max(0, liq), margin_used]}), values='Val', names='Cat', hole=0.6, color_discrete_map={"Cash": "#FFFF00", "Margin Locked": "#222"})
                    fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=110, margin=dict(l=0, r=0, t=0, b=0))
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{row_id}")
                
                with c_actions:
                    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
                    with st.popover("⚙ EDIT VALUE"):
                        new_name = st.text_input("Modifica Nome Conto", value=acc, key=f"edit_n_{row_id}")
                        new_curr = st.selectbox("Modifica Valuta", valid_currencies, index=valid_currencies.index(curr), key=f"edit_c_{row_id}")
                        new_bal = st.number_input("Ricalibra Saldo Iniziale", min_value=0.0, value=init_val, key=f"edit_b_{row_id}")
                        if st.button("SAVE CHANGES", key=f"save_{row_id}"):
                            supabase.table("balances").update({"account_name": new_name.strip(), "currency": new_curr, "initial_balance": new_bal}).eq("id", row_id).execute(); st.rerun()
                    
                    if st.button("❌ REMOVE VAULT", key=f"del_{row_id}"):
                        supabase.table("balances").delete().eq("id", row_id).execute(); st.rerun()
                st.markdown("---")
