import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION INTERFACE ---
st.set_page_config(
    page_title="Terminal | Trade Republic Style",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS STYLE TRADE REPUBLIC (MINIMALISTE & NOIR PUR) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #000000;
        color: #ffffff;
    }

    /* En-tête de solde / Prix Trade Republic */
    .tr-asset-name {
        font-size: 0.95rem;
        font-weight: 500;
        color: #71717a;
        margin-bottom: 2px;
    }
    .tr-price {
        font-family: 'Inter', sans-serif;
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: #ffffff;
        line-height: 1.1;
    }
    .tr-variation {
        font-size: 0.95rem;
        font-weight: 600;
        margin-top: 6px;
        margin-bottom: 20px;
    }

    /* Cartes minimalistes Trade Republic */
    .tr-card {
        background: #09090b;
        border: 1px solid #18181b;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .tr-card-header {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #71717a;
    }
    .tr-card-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.35rem;
        font-weight: 700;
        color: #fafafa;
        margin-top: 4px;
    }

    /* Badges épurés */
    .badge-bull {
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.25);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-bear {
        background: rgba(244, 63, 94, 0.12);
        color: #f43f5e;
        border: 1px solid rgba(244, 63, 94, 0.25);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Sélecteurs épurés intégrés */
    div[data-baseweb="select"] > div {
        background-color: #09090b !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SÉLECTEURS DE MARCHÉ ET TIMEFRAME ---
col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])

with col_sel1:
    asset_label = st.selectbox(
        "Marché",
        ["EUR/USD (Forex)", "BTC/USD (Crypto)", "XAU/USD (Or)", "NASDAQ 100"],
        index=0,
        label_visibility="collapsed"
    )
with col_sel2:
    timeframe = st.selectbox(
        "Horizon",
        ["5m", "15m", "1h", "4h"],
        index=1,
        label_visibility="collapsed"
    )
with col_sel3:
    period = st.selectbox(
        "Historique",
        ["5d", "1mo", "60d"],
        index=0,
        label_visibility="collapsed"
    )

ticker_map = {
    "EUR/USD (Forex)": "EURUSD=X",
    "BTC/USD (Crypto)": "BTC-USD",
    "XAU/USD (Or)": "GC=F",
    "NASDAQ 100": "NQ=F"
}
selected_symbol = ticker_map[asset_label]

# --- CHARGEMENT DU FLUX MARCHÉ ---
@st.cache_data(ttl=30, show_spinner=False)
def get_market_data(symbol, interval, lookback):
    try:
        df = yf.download(symbol, period=lookback, interval=interval, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close']].dropna()
        return df
    except Exception:
        return None

df = get_market_data(selected_symbol, timeframe, period)

if df is None or len(df) < 30:
    st.error("Données de cotation indisponibles. Réessaye avec un autre horizon.")
    st.stop()

# --- ALGORITHME LUXALGO : ORDER BLOCK DETECTOR ---
def detect_luxalgo_order_blocks(data, swing_length=5):
    """
    Reproduction fidèle du détecteur LuxAlgo :
    1. Identification des points pivots (Swing High / Swing Low).
    2. Suivi de la cassure de structure (BOS).
    3. Traçage de l'Order Block d'origine avec maintien tant que non invalidé par clôture.
    """
    obs = []
    n = len(data)
    highs = data['High'].values
    lows = data['Low'].values
    closes = data['Close'].values
    opens = data['Open'].values

    # Balayage des bougies
    for i in range(swing_length * 2, n - 2):
        # Vérification Swing High (BOS Vente)
        is_swing_high = True
        for offset in range(1, swing_length + 1):
            if highs[i - swing_length] <= highs[i - swing_length - offset] or highs[i - swing_length] <= highs[i - swing_length + offset]:
                is_swing_high = False
                break

        # Rupture baissière de structure (Bearish OB)
        if closes[i] < lows[i - swing_length]:
            # Chercher la dernière bougie haussière dans la structure précédente
            for j in range(i, max(0, i - 10), -1):
                if closes[j] > opens[j]:
                    ob_high = highs[j]
                    ob_low = lows[j]
                    
                    # Vérifier si mitigé (clôture au-dessus)
                    subsequent_closes = closes[i+1:]
                    if len(subsequent_closes) == 0 or not np.any(subsequent_closes > ob_high):
                        tested = np.any(highs[i+1:] >= ob_low) if len(highs[i+1:]) > 0 else False
                        obs.append({
                            "type": "BEARISH OB",
                            "high": float(ob_high),
                            "low": float(ob_low),
                            "start_idx": j,
                            "tested": tested,
                            "border": "rgba(244, 63, 94, 0.9)",
                            "fill": "rgba(244, 63, 94, 0.16)"
                        })
                    break

        # Rupture haussière de structure (Bullish OB)
        if closes[i] > highs[i - swing_length]:
            # Chercher la dernière bougie baissière dans la structure précédente
            for j in range(i, max(0, i - 10), -1):
                if closes[j] < opens[j]:
                    ob_high = highs[j]
                    ob_low = lows[j]
                    
                    subsequent_closes = closes[i+1:]
                    if len(subsequent_closes) == 0 or not np.any(subsequent_closes < ob_low):
                        tested = np.any(lows[i+1:] <= ob_high) if len(lows[i+1:]) > 0 else False
                        obs.append({
                            "type": "BULLISH OB",
                            "high": float(ob_high),
                            "low": float(ob_low),
                            "start_idx": j,
                            "tested": tested,
                            "border": "rgba(16, 185, 129, 0.9)",
                            "fill": "rgba(16, 185, 129, 0.16)"
                        })
                    break

    # Dédoublonnage pour conserver les zones les plus fraîches
    unique_obs = []
    seen = set()
    for o in reversed(obs):
        key = (round(o['high'], 4), round(o['low'], 4), o['type'])
        if key not in seen:
            seen.add(key)
            unique_obs.append(o)
    return list(reversed(unique_obs))

# Exécution
zones = detect_luxalgo_order_blocks(df, swing_length=5)

# --- VALEURS CLÉS FORMAT TRADE REPUBLIC ---
last_price = float(df['Close'].iloc[-1])
first_price = float(df['Open'].iloc[0])
diff = last_price - first_price
diff_pct = (diff / first_price) * 100
is_forex = "EUR" in selected_symbol
fmt = "{:.5f}" if is_forex else "{:,.2f}"

var_color = "#10b981" if diff >= 0 else "#f43f5e"
sign = "+" if diff >= 0 else ""

st.markdown(f"""
<div>
    <div class="tr-asset-name">{asset_label} · {timeframe}</div>
    <div class="tr-price">{fmt.format(last_price)} €</div>
    <div class="tr-variation" style="color: {var_color};">
        {sign}{fmt.format(diff)} ({sign}{diff_pct:.2f} %)
    </div>
</div>
""", unsafe_allow_html=True)

# --- GRAPHIQUE ÉPURÉ STYLE TERMINAL SANS TROUS ---
plot_bars = 120
recent_df = df.tail(plot_bars).copy()
recent_df['x_idx'] = np.arange(len(recent_df))

fig = go.Figure()

# Chandeliers minimalistes
fig.add_trace(go.Candlestick(
    x=recent_df['x_idx'],
    open=recent_df['Open'],
    high=recent_df['High'],
    low=recent_df['Low'],
    close=recent_df['Close'],
    increasing=dict(line=dict(color='#10b981', width=1.2), fillcolor='#10b981'),
    decreasing=dict(line=dict(color='#f43f5e', width=1.2), fillcolor='#f43f5e'),
    showlegend=False
))

# Zones LuxAlgo
min_global_idx = len(df) - plot_bars
for z in zones:
    if z['start_idx'] >= min_global_idx:
        x0_local = z['start_idx'] - min_global_idx
        fig.add_shape(
            type="rect",
            x0=x0_local,
            y0=z['low'],
            x1=plot_bars - 1,
            y1=z['high'],
            fillcolor=z['fill'],
            line=dict(color=z['border'], width=1, dash="dot" if z['tested'] else "solid")
        )

# Graduations dates discrètes en bas
step = max(1, len(recent_df) // 5)
tick_indices = list(range(0, len(recent_df), step))
tick_texts = [recent_df.index[k].strftime('%H:%M') if timeframe in ['1m', '5m', '15m'] else recent_df.index[k].strftime('%d %b') for k in tick_indices]

fig.update_layout(
    template="plotly_dark",
    plot_bgcolor="#000000",
    paper_bgcolor="#000000",
    height=420,
    margin=dict(l=0, r=45, t=10, b=10),
    dragmode="pan",
    xaxis=dict(
        showgrid=False,
        zeroline=False,
        showline=False,
        tickvals=tick_indices,
        ticktext=tick_texts,
        tickfont=dict(color='#52525b', size=11)
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="#18181b",
        side="right",
        zeroline=False,
        showline=False,
        tickformat=".5f" if is_forex else ",.2f",
        tickfont=dict(color='#71717a', size=11)
    )
)

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# --- CARTES DE FLUX & ZONES (LOOK NÉO-BANQUE) ---
c1, c2 = st.columns(2)
bull_obs = [z for z in zones if z['type'] == "BULLISH OB"]
bear_obs = [z for z in zones if z['type'] == "BEARISH OB"]

with c1:
    st.markdown("""
    <div class="tr-card">
        <div class="tr-card-header">Structure Acheteuse (Demand)</div>
    """, unsafe_allow_html=True)
    if bull_obs:
        for ob in reversed(bull_obs[-2:]):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                <span class="badge-bull">BULLISH OB</span>
                <span style="font-family:'JetBrains Mono', monospace; font-size:0.9rem; color:#f4f4f5;">
                    {fmt.format(ob['low'])} — {fmt.format(ob['high'])}
                </span>
                <span style="font-size:0.75rem; color:#71717a;">{'En test' if ob['tested'] else 'Vierge'}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#52525b; font-size:0.85rem; margin-top:8px;'>Aucune zone active</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="tr-card">
        <div class="tr-card-header">Structure Vendeuse (Supply)</div>
    """, unsafe_allow_html=True)
    if bear_obs:
        for ob in reversed(bear_obs[-2:]):
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                <span class="badge-bear">BEARISH OB</span>
                <span style="font-family:'JetBrains Mono', monospace; font-size:0.9rem; color:#f4f4f5;">
                    {fmt.format(ob['low'])} — {fmt.format(ob['high'])}
                </span>
                <span style="font-size:0.75rem; color:#71717a;">{'En test' if ob['tested'] else 'Vierge'}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#52525b; font-size:0.85rem; margin-top:8px;'>Aucune zone active</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
