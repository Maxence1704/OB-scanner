import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Terminal SMC | Order Block Scanner",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS HAUT DE GAMME (DARK INSTITUTIONNEL) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    .stApp {
        background-color: #08090c;
        color: #d1d5db;
    }
    
    /* Cartes de données */
    .metric-card {
        background: #111318;
        border: 1px solid #1f242d;
        border-radius: 8px;
        padding: 14px 18px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.4rem;
        font-weight: 700;
        color: #f9fafb;
    }
    .metric-sub {
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Badges */
    .badge {
        font-family: 'JetBrains Mono', monospace;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-buy { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-sell { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-waiting { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-tested { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    
    /* Sélecteurs épurés */
    div[data-baseweb="select"] > div {
        background-color: #111318 !important;
        border: 1px solid #1f242d !important;
        border-radius: 6px !important;
        color: white !important;
    }
    
    /* Bouton d'actualisation */
    .stButton>button {
        width: 100%;
        background-color: #1f242d;
        color: #f3f4f6;
        border: 1px solid #374151;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #2d3748;
        border-color: #4b5563;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# --- BARRE SUPÉRIEURE : EN-TÊTE & CONTRÔLES ---
top_left, top_right = st.columns([3, 1])
with top_left:
    st.markdown("### 🟢 **TERMINAL SMC** `v2.0`")
    st.caption("Détection algorithmique institutionnelle : Order Blocks • Fair Value Gaps • Break of Structure")

# Filtres actifs et timeframes
c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
with c1:
    ticker_choice = st.selectbox(
        "Marché",
        ["EUR/USD (Forex)", "BTC/USD (Crypto)", "XAU/USD (Or)", "NASDAQ 100"],
        index=0
    )
with c2:
    timeframe = st.selectbox("Unité de temps", ["1m", "5m", "15m", "1h", "4h"], index=2)
with c3:
    # Ajustement automatique de la période maximale supportée par Yahoo Finance
    period_options = ["1d", "5d", "7d"] if timeframe == "1m" else ["5d", "1mo", "60d"]
    period = st.selectbox("Historique", period_options, index=0 if timeframe == "1m" else 1)
with c4:
    st.write("")
    st.write("")
    refresh = st.button("↻ Actualiser")

ticker_map = {
    "EUR/USD (Forex)": "EURUSD=X",
    "BTC/USD (Crypto)": "BTC-USD",
    "XAU/USD (Or)": "GC=F",
    "NASDAQ 100": "NQ=F"
}
selected_symbol = ticker_map[ticker_choice]

# --- RÉCUPÉRATION ROBUSTE DES DONNÉES ---
@st.cache_data(ttl=30, show_spinner=False)
def fetch_clean_data(symbol, interval, lookback):
    try:
        df = yf.download(symbol, period=lookback, interval=interval, progress=False)
        if df.empty:
            return None
        # Nettoyage MultiIndex fréquent sur les dernières versions de yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
        return df
    except Exception:
        return None

with st.spinner("Synchronisation des flux de marché..."):
    df = fetch_clean_data(selected_symbol, timeframe, period)

if df is None or len(df) < 20:
    st.error("Flux indisponible pour cet horizon. Choisis une autre unité de temps.")
    st.stop()

# --- ALGORITHME DE DÉTECTION PRÉCIS SMC ---
def scan_order_blocks(data):
    obs = []
    # Calcul ATR pour mesurer la violence des impulsions
    high_low = data['High'] - data['Low']
    high_close = abs(data['High'] - data['Close'].shift(1))
    low_close = abs(data['Low'] - data['Close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().bfill()

    n = len(data)
    for i in range(10, n - 3):
        # 1. OB ACHETEUR (Demand Zone)
        # Bougie i d'impulsion verte puissante
        impulse_bull = (data['Close'].iloc[i] - data['Open'].iloc[i]) > (1.2 * atr.iloc[i])
        # Cassure du plus haut récent (BOS)
        bos_bull = data['Close'].iloc[i] > data['High'].iloc[i-8:i].max()
        # Déséquilibre net (FVG)
        fvg_bull = data['Low'].iloc[i+1] > data['High'].iloc[i-1]

        if impulse_bull and bos_bull and fvg_bull:
            ob_high = max(data['High'].iloc[i-1], data['Open'].iloc[i])
            ob_low = data['Low'].iloc[i-1]
            future = data.iloc[i+1:]
            
            # Non invalidé (aucune clôture sous le bas de l'OB)
            if not (future['Close'] < ob_low).any():
                tested = (future['Low'] <= ob_high).any()
                obs.append({
                    "type": "DEMAND (ACHAT)",
                    "high": float(ob_high),
                    "low": float(ob_low),
                    "time": data.index[i-1],
                    "idx": i-1,
                    "status": "EN TEST" if tested else "NON TESTÉ",
                    "color": "rgba(16, 185, 129, 0.22)",
                    "border": "#10b981"
                })

        # 2. OB VENDEUR (Supply Zone)
        impulse_bear = (data['Open'].iloc[i] - data['Close'].iloc[i]) > (1.2 * atr.iloc[i])
        bos_bear = data['Close'].iloc[i] < data['Low'].iloc[i-8:i].min()
        fvg_bear = data['High'].iloc[i+1] < data['Low'].iloc[i-1]

        if impulse_bear and bos_bear and fvg_bear:
            ob_high = data['High'].iloc[i-1]
            ob_low = min(data['Low'].iloc[i-1], data['Open'].iloc[i])
            future = data.iloc[i+1:]
            
            # Non invalidé (aucune clôture au-dessus du haut de l'OB)
            if not (future['Close'] > ob_high).any():
                tested = (future['High'] >= ob_low).any()
                obs.append({
                    "type": "SUPPLY (VENTE)",
                    "high": float(ob_high),
                    "low": float(ob_low),
                    "time": data.index[i-1],
                    "idx": i-1,
                    "status": "EN TEST" if tested else "NON TESTÉ",
                    "color": "rgba(239, 68, 68, 0.22)",
                    "border": "#ef4444"
                })

    return obs

zones = scan_order_blocks(df)
last_close = float(df['Close'].iloc[-1])
prev_close = float(df['Close'].iloc[-2])
change_pct = ((last_close - prev_close) / prev_close) * 100
is_forex = "EUR" in selected_symbol
fmt = "{:.5f}" if is_forex else "{:,.2f}"

# --- MÉTRIQUES SUPÉRIEURES EN CARTES MODERNES ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Dernier Prix</div>
        <div class="metric-value">{fmt.format(last_close)}</div>
        <div class="metric-sub" style="color: {'#10b981' if change_pct >= 0 else '#ef4444'};">
            {'+' if change_pct >= 0 else ''}{change_pct:.2f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    demand_count = sum(1 for z in zones if "ACHAT" in z['type'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Zones Demand (Achat)</div>
        <div class="metric-value" style="color:#10b981;">{demand_count}</div>
        <div class="metric-sub" style="color:#6b7280;">Structure institutionnelle</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    supply_count = sum(1 for z in zones if "VENTE" in z['type'])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Zones Supply (Vente)</div>
        <div class="metric-value" style="color:#ef4444;">{supply_count}</div>
        <div class="metric-sub" style="color:#6b7280;">Structure institutionnelle</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    active_now = sum(1 for z in zones if z['status'] == "EN TEST")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Zones en cours de test</div>
        <div class="metric-value" style="color:#f59e0b;">{active_now}</div>
        <div class="metric-sub" style="color:#6b7280;">Action de prix immédiate</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# --- GRAPHIQUE PROFESSIONNEL PLOTLY ---
display_bars = 140
plot_data = df.tail(display_bars)

fig = go.Figure()

# Chandelier japonais style terminal
fig.add_trace(go.Candlestick(
    x=plot_data.index,
    open=plot_data['Open'],
    high=plot_data['High'],
    low=plot_data['Low'],
    close=plot_data['Close'],
    name="Prix",
    increasing=dict(line=dict(color='#10b981', width=1), fillcolor='#10b981'),
    decreasing=dict(line=dict(color='#ef4444', width=1), fillcolor='#ef4444')
))

# Dessin des Order Blocks
cutoff_idx = len(df) - display_bars
for z in zones:
    if z['idx'] >= cutoff_idx:
        fig.add_shape(
            type="rect",
            x0=z['time'],
            y0=z['low'],
            x1=plot_data.index[-1],
            y1=z['high'],
            fillcolor=z['color'],
            line=dict(color=z['border'], width=1, dash="dot" if z['status'] == "EN TEST" else "solid")
        )

fig.update_layout(
    template="plotly_dark",
    plot_bgcolor="#0b0d13",
    paper_bgcolor="#0b0d13",
    height=540,
    margin=dict(l=10, r=60, t=10, b=10),
    xaxis=dict(
        showgrid=True,
        gridcolor="#161a23",
        rangeslider_visible=False,
        type="date"
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#161a23",
        side="right",
        tickformat=".5f" if is_forex else ",.2f"
    ),
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- LISTE DES NIVEAUX INSTITUTIONNELS ACTIFS ---
st.markdown("##### 🎯 **Cartographie des zones actives (Price Action)**")

if zones:
    cols = st.columns(len(zones[-4:]))
    for i, z in enumerate(reversed(zones[-4:])):
        is_buy = "ACHAT" in z['type']
        badge_type = "badge-buy" if is_buy else "badge-sell"
        badge_status = "badge-tested" if z['status'] == "EN TEST" else "badge-waiting"
        
        with cols[i]:
            st.markdown(f"""
            <div style="background:#111318; border:1px solid #1f242d; border-radius:8px; padding:12px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <span class="badge {badge_type}">{z['type']}</span>
                    <span class="badge {badge_status}">{z['status']}</span>
                </div>
                <div style="font-family:'JetBrains Mono', monospace; font-size:0.95rem; font-weight:600; color:#f3f4f6;">
                    {fmt.format(z['low'])} — {fmt.format(z['high'])}
                </div>
                <div style="font-size:0.75rem; color:#6b7280; margin-top:4px;">
                    Détecté le {z['time'].strftime('%d/%m à %H:%M')}
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Aucune zone SMC propre active sur cette période.")
