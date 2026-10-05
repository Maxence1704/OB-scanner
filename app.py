import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuration de la page pour smartphone et tablette
st.set_page_config(page_title="OB Scanner", layout="wide", initial_sidebar_state="collapsed")

st.title("🎯 Order Block Scanner")

# Sélecteurs tactiles
col1, col2, col3 = st.columns(3)
with col1:
    ticker = st.selectbox("Actif", ["BTC-USD", "GC=F", "EURUSD=X", "NQ=F"])
with col2:
    timeframe = st.selectbox("Timeframe", ["5m", "15m", "1h"], index=1)
with col3:
    period = st.selectbox("Période", ["5d", "1mo", "60d"], index=0)

# Téléchargement des données
@st.cache_data(ttl=60)
def load_data(symbol, interval, lookback):
    df = yf.download(tickers=symbol, period=lookback, interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

df = load_data(ticker, timeframe, period)

if df.empty:
    st.error("Aucune donnée disponible pour cet actif/timeframe.")
    st.stop()

# Logique de détection des OB valides (FVG + Impulsion)
def detect_order_blocks(data):
    obs = []
    for i in range(2, len(data) - 2):
        # Bullish OB : bougie baissière suivie d'une impulsion avec FVG
        if data['Close'].iloc[i-1] < data['Open'].iloc[i-1]:
            # Présence d'un FVG haussier
            if data['Low'].iloc[i+1] > data['High'].iloc[i-1]:
                ob_high = data['High'].iloc[i-1]
                ob_low = data['Low'].iloc[i-1]
                # Vérifier si l'OB est encore actif (non invalidé par la clôture)
                subsequent_data = data.iloc[i:]
                if not (subsequent_data['Close'] < ob_low).any():
                    # Statut : en test ou non touché
                    tested = (subsequent_data['Low'] <= ob_high).any()
                    obs.append({
                        "Type": "ACHAT (Bullish)",
                        "Borne Haute": ob_high,
                        "Borne Basse": ob_low,
                        "Statut": "En test" if tested else "Non touché",
                        "Couleur": "rgba(0, 200, 100, 0.35)",
                        "Index": i-1
                    })

        # Bearish OB : bougie haussière suivie d'une impulsion avec FVG
        elif data['Close'].iloc[i-1] > data['Open'].iloc[i-1]:
            # Présence d'un FVG baissier
            if data['High'].iloc[i+1] < data['Low'].iloc[i-1]:
                ob_high = data['High'].iloc[i-1]
                ob_low = data['Low'].iloc[i-1]
                subsequent_data = data.iloc[i:]
                if not (subsequent_data['Close'] > ob_high).any():
                    tested = (subsequent_data['High'] >= ob_low).any()
                    obs.append({
                        "Type": "VENTE (Bearish)",
                        "Borne Haute": ob_high,
                        "Borne Basse": ob_low,
                        "Statut": "En test" if tested else "Non touché",
                        "Couleur": "rgba(255, 60, 60, 0.35)",
                        "Index": i-1
                    })
    return obs

obs = detect_order_blocks(df)
current_price = df['Close'].iloc[-1]

# Affichage des métriques clés
st.metric("Prix Actuel", f"{current_price:.2f}", delta=f"{len(obs)} OB actifs")

# Tableau synthétique des OB actifs
if obs:
    table_data = []
    for ob in obs[-6:]:  # Garder les plus récents
        table_data.append({
            "Type": ob["Type"],
            "Borne Haute": round(ob["Borne Haute"], 2),
            "Borne Basse": round(ob["Borne Basse"], 2),
            "Statut": ob["Statut"]
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)
else:
    st.info("Aucun Order Block valide non mitigé pour le moment.")

# Graphique interactif Plotly
recent_df = df.tail(120)
fig = go.Figure(data=[go.Candlestick(
    x=recent_df.index,
    open=recent_df['Open'],
    high=recent_df['High'],
    low=recent_df['Low'],
    close=recent_df['Close'],
    name="Prix"
)])

# Tracer les rectangles des OB actifs
for ob in obs:
    if ob["Index"] >= len(df) - 120:
        fig.add_shape(
            type="rect",
            x0=df.index[ob["Index"]],
            y0=ob["Borne Basse"],
            x1=recent_df.index[-1],
            y1=ob["Borne Haute"],
            fillcolor=ob["Couleur"],
            line=dict(width=1, color="black" if "ACHAT" in ob["Type"] else "red"),
        )

fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=450,
    margin=dict(l=10, r=10, t=10, b=10)
)
st.plotly_chart(fig, use_container_width=True)
