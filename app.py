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

# --- CSS STYLE TRADE REPUBLIC ---
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

    div[data-baseweb="select"] > div {
        background-color: #09090b !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SÉLECTEURS ---
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

# --- DÉTECTION STRICTE : DERNIÈRE BOUGIE INVERSE À L'EXTRÊME DU SWING ---
def detect_luxalgo_order_blocks(data, swing_length=10):
    obs = []
    n = len(data)
    highs = data['High'].values
    lows = data['Low'].values
    closes = data['Close'].values
    opens = data['Open'].values

    for i in range(swing_length, n - swing_length):
        # 1. SOMMET MAJEUR (Bearish OB au sommet)
        is_peak = True
        pivot_high = highs[i]
        for offset in range(1, swing_length + 1):
            if highs[i - offset] >= pivot_high or highs[i + offset] > pivot_high:
                is_peak = False
                break

        if is_peak:
            target_idx = None
            for k in range(i, max(0, i - 4), -1):
                if closes[k] >= opens[k]:
                    target_idx = k
                    break
            
            if target_idx is None:
                target_idx = i

            ob_high = float(highs[target_idx])
            ob_low = float(lows[target_idx])

            swing_low_level = np.min(lows[max(0, i - swing_length):i])
            subsequent_closes = closes[i+1:]
            
            if len(subsequent_closes) > 0 and np.any(subsequent_closes < swing_low_level):
                subsequent_highs = highs[i+1:]
                if not np.any(subsequent_closes > ob_high):
                    tested = np.any(subsequent_highs >= ob_low)
                    obs.append({
                        "type": "BEARISH OB",
                        "high": ob_high,
                        "low": ob_low,
                        "start_idx": target_idx,
                        "tested": tested,
                        "border": "rgba(244, 63, 94, 0.9)",
                        "fill": "rgba(244, 63, 94, 0.18)"
                    })

        # 2. CREUX MAJEUR (Bullish OB au creux)
        is_valley = True
        pivot_low = lows[i]
        for offset in range(1, swing_length + 1):
            if lows[i - offset] <= pivot_low or lows[i + offset] < pivot_low:
                is_valley = False
                break

        if is_valley:
            target_idx = None
            for k in range(i, max(0, i - 4), -1):
                if closes[k] <= opens[k]:
                    target_idx = k
                    break

            if target_idx is None:
                target_idx = i

            ob_high = float(highs[target_idx])
            ob_low = float(lows[target_idx])

            swing_high_level = np.max(highs[max(0, i - swing_length):i])
            subsequent_closes = closes[i+1:]

            if len(subsequent_closes) > 0 and np.any(subsequent_closes > swing_high_level):
                subsequent_lows = lows[i+1:]
                if not np.any(subsequent_closes < ob_low):
                    tested = np.any(subsequent_lows <= ob_high)
                    obs.append({
                        "type": "BULLISH OB",
                        "high": ob_high,
                        "low": ob_low,
                        "start_idx": target_idx,
                        "tested": tested,
                        "border": "rgba(16, 185, 129, 0.9)",
                        "fill": "rgba(16, 185, 129, 0.18)"
                    })

    unique_obs = []
    seen_indices = set()
    for o in reversed(obs):
        if o['start_idx'] not in seen_indices:
            seen_indices.add(o['start_idx'])
            unique_obs.append(o)

    return list(reversed(unique_obs))

zones = detect_luxalgo_order_blocks(df, swing_length=10)

# --- STATISTIQUES EN TÊTE ---
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

# --- GRAPHIQUE PLEIN ÉCRAN FLUIDE ---
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

step = max(1, total_bars // 8)
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
    height=480,
    margin=dict(l=0, r=45, t=10, b=10),
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
        side="right",
        zeroline=False,
        showline=False,
        tickformat=".5f" if is_forex else ",.2f",
        tickfont=dict(color='#71717a', size=11),
        fixedrange=False
    )
)

st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# --- CARTES DE FLUX & ZONES ---
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
