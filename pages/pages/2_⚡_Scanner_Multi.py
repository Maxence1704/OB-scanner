import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Radar Multi-Actifs | SMC", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Scanner Multi-Actifs")
st.caption("Détection rapide des niveaux sur l'ensemble de la sélection.")

assets = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "EUR/USD": "EURUSD=X",
    "Or": "GC=F",
    "Argent": "SI=F",
    "NASDAQ 100": "NQ=F"
}

results = []

for name, ticker in assets.items():
    try:
        df = yf.download(ticker, period="5d", interval="15m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        if len(df) > 30:
            last_p = df['Close'].iloc[-1]
            highs, lows, closes = df['High'].values, df['Low'].values, df['Close'].values
            
            has_supply = np.any(closes[-8:] < np.min(lows[-25:-8]))
            has_demand = np.any(closes[-8:] > np.max(highs[-25:-8]))
            
            statut = "Neutre"
            if has_supply: statut = "Pression Vendeuse"
            if has_demand: statut = "Pression Acheteuse"
            
            fmt = "{:.5f}" if "EUR" in ticker else "{:,.2f}"
            results.append({
                "Actif": name,
                "Prix Actuel": fmt.format(last_p),
                "Tendance Récente (15m)": statut
            })
    except Exception:
        pass

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
