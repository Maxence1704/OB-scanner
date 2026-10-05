import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. Configuration de la page
st.set_page_config(
    page_title="OB Pro Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Thème sombre
st.markdown("""
<style>
    .stApp {
        background-color: #0b0e14;
        color: #e1e4ea;
    }
    div[data-testid="stMetric"] {
        background: #151922;
        border: 1px solid #232936;
        border-radius: 12px;
        padding: 12px 18px;
    }
    div[data-testid="stMetricLabel"] p {
        color: #8b94a5 !important;
    }
    div[data-testid="stMetricValue"] div {
        color: #f3f4f6 !important;
    }
    .badge-buy {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-sell {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .badge-status {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        padding: 4px 8px;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Contrôles
st.markdown("### ⚡ **Order Block Pro Scanner**")
st.caption("Détection SMC haute précision (Impulsion + BOS + FVG)")

c1, c2, c3 = st.columns(3)
with c1:
    ticker = st.selectbox("Actif", ["EURUSD=X", "BTC-USD", "GC=F", "NQ=F"], index=0)
with c2:
    timeframe = st.selectbox("Unité de temps", ["1m", "5m", "15m", "1h"], index=1)
with c3:
    period = st.selectbox("Historique", ["1d", "5d", "1mo"], index=1)

# 4. Chargement des données
@st.cache_data(ttl=60)
def load_data(symbol, interval, lookback):
    df = yf.download(tickers=symbol, period=lookback, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

df = load_data(ticker, timeframe, period)

if df.empty:
    st.error("Données indisponibles pour cet actif/timeframe.")
    st.stop()

# 5. Détection calibrée des Order Blocks de qualité
def detect_order_blocks(data):
    obs = []
    data['tr'] = np.maximum(
        data['High'] - data['Low'],
        np.maximum(
            abs(data['High'] - data['Close'].shift(1)),
            abs(data['Low'] - data['Close'].shift(1))
        )
    )
    atr = data['tr'].rolling(14).mean()

    for i in range(10, len(data) - 3):
        # Achat (Demand / Bullish OB)
        body_i = data['Close'].iloc[i] - data['Open'].iloc[i]
        is_strong_bull = body_i > (1.5 * atr.iloc[i])
        recent_high = data['High'].iloc[i-9:i-1].max()
        has_bos_bull = data['Close'].iloc[i] > recent_high
        has_fvg_bull = data['Low'].iloc[i+1] > data['High'].iloc[i-1]
        
        if is_strong_bull and has_bos_bull and has_fvg_bull:
            ob_high = max(data['High'].iloc[i-1], data['Open'].iloc[i])
            ob_low = data['Low'].iloc[i-1]
            subsequent = data.iloc[i+1:]
            if not (subsequent['Close'] < ob_low).any():
                tested = (subsequent['Low'] <= ob_high).any()
                obs.append({
                    "Type": "ZONE ACHAT",
                    "Borne Haute": ob_high,
                    "Borne Basse": ob_low,
                    "Statut": "⚡ En test" if tested else "⏳ En attente",
                    "Couleur": "rgba(16, 185, 129, 0.25)",
                    "BorderColor": "#10b981",
                    "Index": i-1
                })

        # Vente (Supply / Bearish OB)
        body_i_bear = data['Open'].iloc[i] - data['Close'].iloc[i]
        is_strong_bear = body_i_bear > (1.5 * atr.iloc[i])
        recent_low = data['Low'].iloc[i-9:i-1].min()
        has_bos_bear = data['Close'].iloc[i] < recent_low
        has_fvg_bear = data['High'].iloc[i+1] < data['Low'].iloc[i-1]
        
        if is_strong_bear and has_bos_bear and has_fvg_bear:
            ob_high = data['High'].iloc[i-1]
            ob_low = min(data['Low'].iloc[i-1], data['Open'].iloc[i])
            subsequent = data.iloc[i+1:]
            if not (subsequent['Close'] > ob_high).any():
                tested = (subsequent['High'] >= ob_low).any()
                obs.append({
                    "Type": "ZONE VENTE",
                    "Borne Haute": ob_high,
                    "Borne Basse": ob_low,
                    "Statut": "⚡ En test" if tested else "⏳ En attente",
                    "Couleur": "rgba(239, 68, 68, 0.25)",
                    "BorderColor": "#ef4444",
                    "Index": i-1
                })
    return obs

obs = detect_order_blocks(df)
current_price = df['Close'].iloc[-1]
price_diff = current_price - df['Open'].iloc[-1]

# 6. Métriques
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Prix Actuel", f"{current_price:,.5f}" if "EUR" in ticker else f"{current_price:,.2f} $", f"{price_diff:+,.5f}" if "EUR" in ticker else f"{price_diff:+,.2f} $")
with m2:
    st.metric("Zones Actives", f"{len(obs)}", f"{timeframe}")
with m3:
    bull_cnt = sum(1 for x in obs if x['Type'] == "ZONE ACHAT")
    bear_cnt = sum(1 for x in obs if x['Type'] == "ZONE VENTE")
    st.metric("Pression SMC", f"{bull_cnt} Achat | {bear_cnt} Vente")

# 7. Graphique
recent_df = df.tail(100)
fig = go.Figure(data=[go.Candlestick(
    x=recent_df.index,
    open=recent_df['Open'],
    high=recent_df['High'],
    low=recent_df['Low'],
    close=recent_df['Close'],
    name="Prix",
    increasing_line_color="#10b981",
    decreasing_line_color="#ef4444",
    increasing_fillcolor="#10b981",
    decreasing_fillcolor="#ef4444"
)])

for ob in obs:
    if ob["Index"] >= len(df) - 100:
        fig.add_shape(
            type="rect",
            x0=df.index[ob["Index"]],
            y0=ob["Borne Basse"],
            x1=recent_df.index[-1],
            y1=ob["Borne Haute"],
            fillcolor=ob["Couleur"],
            line=dict(width=1, color=ob["BorderColor"], dash="dot"),
        )

fig.update_layout(
    template="plotly_dark",
    plot_bgcolor="#0b0e14",
    paper_bgcolor="#0b0e14",
    xaxis_rangeslider_visible=False,
    height=480,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis=dict(gridcolor="#1b202c", showgrid=True),
    yaxis=dict(gridcolor="#1b202c", showgrid=True, side="right")
)
st.plotly_chart(fig, use_container_width=True)

# 8. Liste des zones
st.markdown("#### 📌 **Zones Institutionnelles Actives**")
if obs:
    for ob in reversed(obs[-5:]):
        badge = "badge-buy" if ob['Type'] == "ZONE ACHAT" else "badge-sell"
        st.markdown(f"""
        <div style="background:#151922; border:1px solid #232936; border-radius:10px; padding:12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="{badge}">{ob['Type']}</span>
                <span style="font-weight:600; margin-left:12px; font-size:1.05rem;">{ob['Borne Basse']:.5f} - {ob['Borne Haute']:.5f}</span>
            </div>
            <div>
                <span class="badge-status">{ob['Statut']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Aucune zone SMC active non mitigée.")
