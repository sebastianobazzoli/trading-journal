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
    st.button("[03] SYSTEM_SETTINGS", on_click=set_page, args=('SETTINGS',))

# --- 5. DASHBOARD ---
if st.session_state.page == 'DASHBOARD':
    st.markdown("### / MONITOR_DASHBOARD")
    if not balances.empty:
        st.info("Dashboard attiva. I dati di rendimento globale e liquidità sono sincronizzati con le impostazioni del Vault.")
    else:
        st.warning("Inizializza i tuoi conti nella sezione SYSTEM_SETTINGS per sbloccare la Dashboard globale.")

# --- 6. TRADE EXECUTION ---
elif st.session_state.page == 'TRADE':
    st.markdown("### / EXECUTION_LOG")
    
    # Lista conti validi per i controlli di sicurezza
    valid_accounts = balances['account_name'].unique().tolist() if not balances.empty else []

    with st.expander("NEW_TRADE_ENTRY", expanded=False):
        if valid_accounts:
            with st.form("trade_form", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns(4)
                asset = c1.text_input("TICKER")
                side = c2.selectbox("SIDE", ["LONG", "SHORT"])
                qty = c3.number_input("QTY", min_value=0.0, step=0.01)
                entry_p = c4.number_input("ENTRY", min_value=0.0)
                
                c5, c6, c7 = st.columns(3)
                exit_p = c5.number_input("EXIT (OUT)", min_value=0.0, value=0.0)
                open_d = c6.date_input("OPEN DATE")
                lev = c7.number_input("LEV", min_value=1.0, value=1.0)
                
                c8, c9 = st.columns(2)
                acc_choice = c8.selectbox("LINK TO VAULT ACCOUNT", valid_accounts)
                avail_currencies = balances[balances['account_name'] == acc_choice]['currency'].unique().tolist()
                curr_choice = c9.selectbox("CURRENCY", avail_currencies)

                if st.form_submit_button("REGISTRA"):
                    status = "CHIUSA" if exit_p > 0 else "APERTA"
                    cost = round((entry_p * qty) / lev, 2)
                    pnl = round(((exit_p - entry_p) * qty * (1 if side == "LONG" else -1)), 2) if exit_p > 0 else 0
                    supabase.table("trades").insert({
                        "asset": asset, "side": side, "shares": qty, "entry_price": entry_p,
                        "exit_price": exit_p, "status": status, "date": str(open_d),
                        "leverage": lev, "cost": cost, "profit": pnl, 
                        "pnl_perc": round(pnl/cost*100, 2) if (exit_p > 0 and cost > 0) else 0,
                        "portfolio": acc_choice, "currency": curr_choice, "instrument": "Stock"
                    }).execute()
                    st.rerun()
        else:
            st.error("ERRORE DI SISTEMA: Impossibile inserire trade. Devi prima creare e inizializzare almeno un conto con relativa valuta nella pagina SYSTEM_SETTINGS.")

    if not trades.empty:
        for c in ['shares', 'entry_price', 'exit_price', 'profit', 'pnl_perc', 'cost']:
            if c in trades.columns: trades[c] = pd.to_numeric(trades[c], errors='coerce').round(2).fillna(0.0)

        def style_ledger(df):
            s = pd.DataFrame('', index=df.index, columns=df.columns)
            if 'profit' in df.columns: s['profit'] = df['profit'].apply(lambda x: 'color: #FF00FF' if float(x) != 0 else '')
            if 'pnl_perc' in df.columns: s['pnl_perc'] = df['pnl_perc'].apply(lambda x: 'color: #00FF41' if float(x) > 0 else ('color: #FF3131' if float(x) < 0 else ''))
            if 'status' in df.columns: s['status'] = df['status'].apply(lambda x: 'color: #00FF41; font-weight: bold' if x == "APERTA" else 'color: #555')
            return s

        st.markdown("<div class='ticker-label'>LEDGER_SYSTEM</div>", unsafe_allow_html=True)
        
        # Abilitata la modifica della colonna portfolio se necessario, ma validata nel SYNC
        edited = st.data_editor(
            trades.sort_values("status", ascending=False) if 'status' in trades.columns else trades,
            use_container_width=True, hide_index=True,
            disabled=["id", "cost", "profit", "pnl_perc", "status"],
            column_config={
                "id": None, "asset": "TKR", "side": "S", "shares": "QTY", 
                "entry_price": "IN", "exit_price": "OUT", "cost": "COST", 
                "profit": "P&L", "pnl_perc": "%", "status": "STATO",
                "portfolio": st.column_config.SelectboxColumn("CONTO", options=valid_accounts, width=90)
            },
            key="ledger_v14"
        )
        
        if st.button("SYNCHRONIZE"):
            # Controllo di sicurezza preventivo: ogni riga modificata DEVE essere associata a un conto esistente
            has_error = False
            for idx, row in edited.iterrows():
                # Se la colonna conto è vuota o il conto inserito non è tra quelli validi nei settings
                if 'portfolio' not in row or pd.isna(row['portfolio']) or str(row['portfolio']).strip() == "" or row['portfolio'] not in valid_accounts:
                    has_error = True
                    st.error(f"ERRORE DI VALIDAZIONE: La riga con asset '{row.get('asset', 'Sconosciuto')}' non è associata a un conto valido nei Settings. Operazione interrotta.")
                    break
            
            if not has_error:
                try:
                    # Se passa il controllo, esegue l'allineamento sul database
                    ids_del = set(trades['id']) - set(edited['id'])
                    for d in ids_del: supabase.table("trades").delete().eq("id", d).execute()
                    
                    for _, r in edited.iterrows():
                        p_out, p_in, q, c = float(r['exit_price']), float(r['entry_price']), float(r['shares']), float(r['cost'])
                        pnl = round(((p_out - p_in) * q * (1 if r['side'] == "LONG" else -1)), 2) if p_out > 0 else 0
                        supabase.table("trades").update({
                            "exit_price": p_out, "status": "CHIUSA" if p_out > 0 else "APERTA",
                            "portfolio": r['portfolio'], # Salva la modifica del conto se cambiata
                            "profit": pnl, "pnl_perc": round(pnl/c*100, 2) if (p_out > 0 and c > 0) else 0
                        }).eq("id", r['id']).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'aggiornamento del DB: {e}")

# --- 7. SETTINGS ---
elif st.session_state.page == 'SETTINGS':
    st.markdown("### / SYSTEM_SETTINGS")
    
    with st.expander("ADD_NEW_ACCOUNT", expanded=True):
        with st.form("vault_form"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("ACCOUNT NAME")
            cr = c2.selectbox("VALUTA", ["USD", "EUR", "USDT", "BTC", "ETH"])
            bl = c3.number_input("SALDO INIZIALE", min_value=0.0)
            if st.form_submit_button("INIZIALIZZA"):
                if n:
                    try:
                        supabase.table("balances").insert({"account_name": n, "currency": cr, "initial_balance": bl}).execute()
                        st.rerun()
                    except Exception as e: st.error(f"Errore DB: {e}")

    if not balances.empty:
        st.markdown("<div class='ticker-label'>VAULT_INSIGHTS</div>", unsafe_allow_html=True)
        for acc in balances['account_name'].unique():
            acc_data = balances[balances['account_name'] == acc]
            c_info, c_chart = st.columns([1, 1.5])
            
            total_bal = 0
            margin_used = 0
            for _, r in acc_data.iterrows():
                init = float(r['initial_balance'])
                pnl = pd.to_numeric(trades[(trades['portfolio'] == acc) & (trades['status'] == 'CHIUSA')]['profit']).sum() if not trades.empty else 0
                total_bal += (init + pnl)
                margin_used += pd.to_numeric(trades[(trades['portfolio'] == acc) & (trades['status'] == 'APERTA')]['cost']).sum() if not trades.empty else 0
            
            liq = total_bal - margin_used
            
            with c_info:
                st.markdown(f"<div class='panel'><div class='card-title'>{acc}</div><div class='stat-sub'>Totale</div><div class='stat-val'>{total_bal:,.2f}</div><div class='stat-sub' style='margin-top:10px;'>Libero: <span style='color:#00FF41;'>{liq:,.2f}</span></div></div>", unsafe_allow_html=True)
            with c_chart:
                fig = px.pie(pd.DataFrame({"Cat": ["Libero", "Impegnato"], "Val": [max(0, liq), margin_used]}), values='Val', names='Cat', hole=0.6, color_discrete_map={"Libero": "#00FF41", "Impegnato": "#222"})
                fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', height=150, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("<div class='ticker-label'>EDIT_DATA</div>", unsafe_allow_html=True)
        edited_bal = st.data_editor(balances, use_container_width=True, hide_index=True, column_config={"id": None})
        if st.button("SAVE SETTINGS"):
            for _, r in edited_bal.iterrows():
                supabase.table("balances").update({"account_name": r['account_name'], "currency": r['currency'], "initial_balance": r['initial_balance']}).eq("id", r['id']).execute()
            st.rerun()
