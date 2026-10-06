import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Radar | Trade Republic Style", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
    html, body, [class*="css"], .stApp {
        background-color: #000000 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }
    .tr-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-bottom: 2px;
    }
    .tr-desc {
        color: #8e8e93;
        font-size: 0.9rem;
        margin-bottom: 24px;
    }
    .tr-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 18px;
        background: #0c0c0e;
        border: 1px solid #1c1c1e;
        border-radius: 12px;
        margin-bottom: 8px;
    }
    .tr-name { font-weight: 600; font-size: 0.95rem; }
    .tr-price { font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; }
    .badge-bull { background: rgba(48, 209, 88, 0.15); color: #30d158; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; }
    .badge-bear { background: rgba(255, 69, 58, 0.15); color: #ff453a; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; }
    .badge-neutre { background: rgba(142, 142, 147, 0.15); color: #8e8e93; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="tr-title">Scanner de Liquidité</div>', unsafe_allow_html=True)
st.markdown('<div class="tr-desc">Surveillance des zones institutionnelles non testées (Horizon 15m).</div>', unsafe_allow_html=True)

assets = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "EUR / USD": "EURUSD=X",
    "Or": "GC=F",
    "Argent": "SI=F",
    "NASDAQ 100": "NQ=F"
}

for name, ticker in assets.items():
    try:
        df = yf.download(ticker, period="5d", interval="15m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        if len(df) > 25:
            last_p = df['Close'].iloc[-1]
            highs, lows, closes = df['High'].values, df['Low'].values, df['Close'].values

            has_supply = np.any(closes[-8:] < np.min(lows[-25:-8]))
            has_demand = np.any(closes[-8:] > np.max(highs[-25:-8]))

            if has_demand:
                badge = '<span class="badge-bull">ZONE ACHAT ACTIVE</span>'
            elif has_supply:
                badge = '<span class="badge-bear">ZONE VENTE ACTIVE</span>'
            else:
                badge = '<span class="badge-neutre">NEUTRE</span>'

            fmt = f"{last_p:.5f}" if "EUR" in ticker else f"{last_p:,.2f}"

            st.markdown(f"""
            <div class="tr-row">
                <span class="tr-name">{name}</span>
                <span class="tr-price">{fmt}</span>
                {badge}
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass
