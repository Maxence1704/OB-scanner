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

# 2. CSS personnalisé pour un look sombre pro et tactile
st.markdown("""
<style>
    /* Fond général sombre */
    .stApp {
        background-color: #0b0e14;
        color: #e1e4ea;
    }
    
    /* Cartes de métriques */
    div[data-testid="stMetric"] {
        background: #151922;
        border: 1px solid #232936;
        border-radius: 12px;
        padding: 12px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    div[data-testid="stMetricLabel"] p {
        color: #8b94a5 !important;
        font-weight: 500;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] div {
        color: #f3f4f6 !important;
        font-weight: 700;
    }
    
    /* Badges stylisés */
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
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. En-tête et contrôles
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.markdown("### ⚡ **Order Block Pro Scanner**")
    st.caption("Détection algorithmique institutionnelle • SMC & Price Action")

# Barre de contrôle
c1, c2, c3 = st.columns(3)
with c1:
    ticker = st.selectbox("Actif", ["BTC-USD", "GC=F", "EURUSD=X", "NQ=F"], index=0)
with c2:
    timeframe = st.selectbox("Unité de temps", ["5m", "15m", "1h"], index=1)
with c3:
    period = st.selectbox("Historique", ["5d", "1mo", "60d"], index=0)

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

# 5. Détection des Order Blocks
def detect_order_blocks(data):
    obs = []
    for i in range(2, len(data) - 2):
        # Bullish OB
        if data['Close'].iloc[i-1] < data['Open'].iloc[i-1]:
            if data['Low'].iloc[i+1] > data['High'].iloc[i-1]:
                ob_high = data['High'].iloc[i-1]
                ob_low = data['Low'].iloc[i-1]
                subsequent = data.iloc[i:]
                if not (subsequent['Close'] < ob_low).any():
                    tested = (subsequent['Low'] <= ob_high).any()
                    obs.append({
                        "Type": "ACHAT",
                        "Borne Haute": ob_high,
                        "Borne Basse": ob_low,
                        "Statut": "⚡ En test" if tested else "⏳ Non testé",
                        "Couleur": "rgba(16, 185, 129, 0.25)",
                        "BorderColor": "#10b981",
                        "Index": i-1
                    })
        # Bearish OB
        elif data['Close'].iloc[i-1] > data['Open'].iloc[i-1]:
            if data['High'].iloc[i+1] < data['Low'].iloc[i-1]:
                ob_high = data['High'].iloc[i-1]
                ob_low = data['Low'].iloc[i-1]
                subsequent = data.iloc[i:]
                if not (subsequent['Close'] > ob_high).any():
                    tested = (subsequent['High'] >= ob_low).any()
                    obs.append({
                        "Type": "VENTE",
                        "Borne Haute": ob_high,
                        "Borne Basse": ob_low,
                        "Statut": "⚡ En test" if tested else "⏳ Non testé",
                        "Couleur": "rgba(239, 68, 68, 0.25)",
                        "BorderColor": "#ef4444",
                        "Index": i-1
                    })
    return obs

obs = detect_order_blocks(df)
current_price = df['Close'].iloc[-1]
price_diff = current_price - df['Open'].iloc[-1]

# 6. Affichage des métriques visuelles
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Prix Actuel", f"{current_price:,.2f} $", f"{price_diff:+,.2f} $")
with m2:
    st.metric("OB Actifs", f"{len(obs)}", f"{timeframe}")
with m3:
    bullish_cnt = sum(1 for x in obs if x['Type'] == "ACHAT")
    bearish_cnt = sum(1 for x in obs if x['Type'] == "VENTE")
    st.metric("Pression OB", f"{bullish_cnt} Achat | {bearish_cnt} Vente")

# 7. Graphique Candlestick moderne (Plotly Dark)
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

# Ajout des zones d'Order Blocks avec design soigné
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

# 8. Tableau des zones actives en format cartes
st.markdown("#### 📌 **Zones Institutionnelles Récentes**")
if obs:
    for ob in reversed(obs[-4:]):
        badge = "badge-buy" if ob['Type'] == "ACHAT" else "badge-sell"
        st.markdown(f"""
        <div style="background:#151922; border:1px solid #232936; border-radius:10px; padding:12px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span class="{badge}">{ob['Type']}</span>
                <span style="font-weight:600; margin-left:12px; font-size:1.05rem;">{ob['Borne Basse']:,.2f} - {ob['Borne Haute']:,.2f}</span>
            </div>
            <div>
                <span class="badge-status">{ob['Statut']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Aucune zone active non mitigée.")
