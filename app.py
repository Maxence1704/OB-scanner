import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATION INTERFACE ---
st.set_page_config(
    page_title="Terminal SMC | Order Block Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS STYLE TRADE REPUBLIC ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #000000;
        color: #ffffff;
    }

    .tr-asset-name {
        font-size: 0.9rem;
        font-weight: 500;
        color: #71717a;
        margin-bottom: 2px;
    }
    .tr-price {
        font-family: 'Inter', sans-serif;
        font-size: 2.7rem;
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

    .tr-card {
        background: #09090b;
        border: 1px solid #18181b;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .tr-card-header {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #71717a;
        margin-bottom: 8px;
    }

    .badge-bull {
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-bear {
        background: rgba(244, 63, 94, 0.12);
        color: #f43f5e;
        border: 1px solid rgba(244, 63, 94, 0.3);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-tested {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 3px 6px;
        border-radius: 5px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    .badge-clean {
        background: rgba(59, 130, 246, 0.12);
        color: #60a5fa;
        border: 1px solid rgba(59, 130, 246, 0.25);
        padding: 3px 6px;
        border-radius: 5px;
        font-size: 0.7rem;
        font-weight: 600;
    }

    div[data-baseweb="select"] > div {
        background-color: #09090b !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SÉLECTEURS DE CONTRÔLE ---
col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])

with col_sel1:
    asset_label = st.selectbox(
        "Marché",
        ["EUR/USD (Forex)", "BTC/USD (Crypto)", "XAU/USD (Or)", "NASDAQ 100"],
        index=3,
        label_visibility="collapsed"
    )
with col_sel2:
    timeframe = st.selectbox(
        "Horizon",
        ["1m", "5m", "15m", "1h", "4h"],
        index=1,
        label_visibility="collapsed"
    )
with col_sel3:
    period_options = ["1d", "5d", "7d"] if timeframe == "1m" else ["5d", "1mo", "60d"]
    period = st.selectbox(
        "Historique",
        period_options,
        index=0 if timeframe == "1m" else 0,
        label_visibility="collapsed"
    )

ticker_map = {
    "EUR/USD (Forex)": "EURUSD=X",
    "BTC/USD (Crypto)": "BTC-USD",
    "XAU/USD (Or)": "GC=F",
    "NASDAQ 100": "NQ=F"
}
selected_symbol = ticker_map[asset_label]

# --- RÉCUPÉRATION DU FLUX ---
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
    st.error("Données de cotation indisponibles. Sélectionne un autre horizon.")
    st.stop()

# --- MOTEUR DE DÉTECTION SMC STRICT (AVEC HISTORIQUE 10 BOUGIES POST-TEST) ---
def detect_order_blocks_strict(data, post_touch_limit=10):
    obs = []
    n = len(data)
    highs = data['High'].values
    lows = data['Low'].values
    closes = data['Close'].values
    opens = data['Open'].values

    # Mesure de la volatilité moyenne (ATR 14)
    tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))
    atr = pd.Series(tr).rolling(14).mean().bfill().values

    for i in range(5, n - 2):
        # 1. BULLISH OB (Impulsion haussière à la base)
        body = closes[i] - opens[i]
        is_impulsive_bull = body >= (1.1 * atr[i])
        recent_high = np.max(highs[max(0, i - 10):i])
        has_bos_bull = closes[i] > recent_high
        
        # FVG haussier présent
        has_fvg_bull = lows[min(i + 1, n - 1)] > highs[i - 1]

        if is_impulsive_bull and has_bos_bull and has_fvg_bull:
            target_idx = i - 1
            ob_high = float(highs[target_idx])
            ob_low = float(lows[target_idx])

            future_lows = lows[i + 1:]
            future_closes = closes[i + 1:]

            broken = np.any(future_closes < ob_low) if len(future_closes) > 0 else False
            
            touch_idx = None
            for idx, l in enumerate(future_lows):
                if l <= ob_high:
                    touch_idx = idx
                    break

            show_zone = not broken
            tested = False
            if touch_idx is not None:
                tested = True
                if (len(future_lows) - 1 - touch_idx) > post_touch_limit:
                    show_zone = False

            if show_zone:
                obs.append({
                    "type": "BULLISH OB",
                    "high": ob_high,
                    "low": ob_low,
                    "start_idx": target_idx,
                    "tested": tested,
                    "border": "rgba(16, 185, 129, 0.9)",
                    "fill": "rgba(16, 185, 129, 0.2)"
                })

        # 2. BEARISH OB (Impulsion baissière au sommet)
        body_bear = opens[i] - closes[i]
        is_impulsive_bear = body_bear >= (1.1 * atr[i])
        recent_low = np.min(lows[max(0, i - 10):i])
        has_bos_bear = closes[i] < recent_low
        has_fvg_bear = highs[min(i + 1, n - 1)] < lows[i - 1]

        if is_impulsive_bear and has_bos_bear and has_fvg_bear:
            target_idx = i - 1
            ob_high = float(highs[target_idx])
            ob_low = float(lows[target_idx])

            future_highs = highs[i + 1:]
            future_closes = closes[i + 1:]

            broken = np.any(future_closes > ob_high) if len(future_closes) > 0 else False
            touch_idx = None
            for idx, h in enumerate(future_highs):
                if h >= ob_low:
                    touch_idx = idx
                    break

            show_zone = not broken
            tested = False
            if touch_idx is not None:
                tested = True
                if (len(future_highs) - 1 - touch_idx) > post_touch_limit:
                    show_zone = False

            if show_zone:
                obs.append({
                    "type": "BEARISH OB",
                    "high": ob_high,
                    "low": ob_low,
                    "start_idx": target_idx,
                    "tested": tested,
                    "border": "rgba(244, 63, 94, 0.9)",
                    "fill": "rgba(244, 63, 94, 0.2)"
                })

    unique = []
    seen = set()
    for o in reversed(obs):
        if o['start_idx'] not in seen:
            seen.add(o['start_idx'])
            unique.append(o)
    return list(reversed(unique))

zones = detect_order_blocks_strict(df, post_touch_limit=10)

# --- STATISTIQUES & PRIX TRADE REPUBLIC ---
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
    <div class="tr-price">{fmt.format(last_price)}</div>
    <div class="tr-variation" style="color: {var_color};">
        {sign}{fmt.format(diff)} ({sign}{diff_pct:.2f} %)
    </div>
</div>
""", unsafe_allow_html=True)

# --- GRAPHIQUE PLEIN ÉCRAN FLUIDE AVEC ÉCHELLE À GAUCHE ---
total_bars = len(df)
df_plot = df.copy()
df_plot['x_idx'] = np.arange(total_bars)

fig = go.Figure()

fig.add_trace(go.Candlestick(
    x=df_plot['x_idx'],
    open=df_plot['Open'],
    high=df_plot['High'],
    low=df_plot['Low'],
    close=df_plot['Close'],
    increasing=dict(line=dict(color='#10b981', width=1.2), fillcolor='#10b981'),
    decreasing=dict(line=dict(color='#f43f5e', width=1.2), fillcolor='#f43f5e'),
    showlegend=False
))

for z in zones:
    fig.add_shape(
        type="rect",
        x0=z['start_idx'],
        y0=z['low'],
        x1=total_bars - 1,
        y1=z['high'],
        fillcolor=z['fill'],
        line=dict(color=z['border'], width=1, dash="dot" if z['tested'] else "solid")
    )

step = max(1, total_bars // 7)
tick_indices = list(range(0, total_bars, step))
if tick_indices[-1] != total_bars - 1:
    tick_indices.append(total_bars - 1)

tick_texts = [
    df_plot.index[k].strftime('%H:%M') if timeframe in ['1m', '5m', '15m'] 
    else df_plot.index[k].strftime('%d %b') 
    for k in tick_indices
]

default_visible_bars = 90
initial_x_start = max(0, total_bars - default_visible_bars)
initial_x_end = total_bars - 1

recent_slice = df_plot.iloc[initial_x_start:]
y_min = recent_slice['Low'].min()
y_max = recent_slice['High'].max()
y_margin = (y_max - y_min) * 0.08

fig.update_layout(
    template="plotly_dark",
    plot_bgcolor="#000000",
    paper_bgcolor="#000000",
    height=520,
    margin=dict(l=60, r=20, t=10, b=10),
    dragmode="pan",
    xaxis=dict(
        range=[initial_x_start, initial_x_end],
        showgrid=False,
        zeroline=False,
        showline=False,
        tickvals=tick_indices,
        ticktext=tick_texts,
        tickfont=dict(color='#52525b', size=11),
        fixedrange=False
    ),
    yaxis=dict(
        range=[y_min - y_margin, y_max + y_margin],
        showgrid=True,
        gridcolor="#18181b",
        side="left",
        zeroline=False,
        showline=False,
        tickformat=".5f" if is_forex else ",.2f",
        tickfont=dict(color='#71717a', size=11),
        fixedrange=False
    )
)

st.plotly_chart(
    fig, 
    use_container_width=True, 
    config={
        'scrollZoom': True,
        'displayModeBar': True,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d']
    }
)

# --- CARTES DE SURVEILLANCE ---
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
            status_badge = '<span class="badge-tested">RÉACTION (EN COURS)</span>' if ob['tested'] else '<span class="badge-clean">NON TESTÉ</span>'
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                <span class="badge-bull">BULLISH OB</span>
                <span style="font-family:'JetBrains Mono', monospace; font-size:0.9rem; color:#f4f4f5;">
                    {fmt.format(ob['low'])} — {fmt.format(ob['high'])}
                </span>
                {status_badge}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#52525b; font-size:0.85rem; margin-top:6px;'>Aucun niveau vierge</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="tr-card">
        <div class="tr-card-header">Structure Vendeuse (Supply)</div>
    """, unsafe_allow_html=True)
    if bear_obs:
        for ob in reversed(bear_obs[-2:]):
            status_badge = '<span class="badge-tested">RÉACTION (EN COURS)</span>' if ob['tested'] else '<span class="badge-clean">NON TESTÉ</span>'
            st.markdown(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                <span class="badge-bear">BEARISH OB</span>
                <span style="font-family:'JetBrains Mono', monospace; font-size:0.9rem; color:#f4f4f5;">
                    {fmt.format(ob['low'])} — {fmt.format(ob['high'])}
                </span>
                {status_badge}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#52525b; font-size:0.85rem; margin-top:6px;'>Aucun niveau vierge</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
