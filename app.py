import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Trade Republic | SMC Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS OFFICIEL STYLE TRADE REPUBLIC ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');

    /* Reset global */
    html, body, [class*="css"], .stApp {
        background-color: #000000 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }

    /* En-tête portefeuille néo-banque */
    .tr-header-label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #8e8e93;
        letter-spacing: -0.01em;
        margin-bottom: 2px;
    }
    .tr-big-price {
        font-size: 3.2rem;
        font-weight: 800;
        letter-spacing: -0.05em;
        color: #ffffff;
        line-height: 1.05;
        margin-bottom: 4px;
    }
    .tr-sub-var {
        font-size: 0.95rem;
        font-weight: 600;
        letter-spacing: -0.02em;
        margin-bottom: 24px;
    }

    /* Cartes Trade Republic */
    .tr-card {
        background: #0c0c0e;
        border: 1px solid #1c1c1e;
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 12px;
        transition: border 0.15s ease;
    }
    .tr-card:hover {
        border-color: #2c2c2e;
    }
    .tr-card-title {
        font-size: 0.72rem;
        font-weight: 700;
        color: #636366;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }
    .tr-card-value {
        font-size: 1.45rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #ffffff;
    }
    .tr-card-change {
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 4px;
    }

    /* Badges épurés */
    .pill-green {
        color: #30d158;
        background: rgba(48, 209, 88, 0.12);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .pill-red {
        color: #ff453a;
        background: rgba(255, 69, 58, 0.12);
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Nettoyage barre latérale */
    section[data-testid="stSidebar"] {
        background-color: #000000 !important;
        border-right: 1px solid #1c1c1e !important;
    }
    section[data-testid="stSidebar"] * {
        color: #8e8e93 !important;
    }
</style>
""", unsafe_allow_html=True)

# En-tête principal
st.markdown("""
<div>
    <div class="tr-header-label">Marchés en direct · Flux institutionnel</div>
    <div class="tr-big-price">SMC Radar</div>
    <div class="tr-sub-var" style="color: #30d158;">Système actif · Algorithme temps réel</div>
</div>
""", unsafe_allow_html=True)

# Liste des actifs surveillés
watchlist = [
    {"label": "Bitcoin", "symbol": "BTC-USD", "fx": False},
    {"label": "Ethereum", "symbol": "ETH-USD", "fx": False},
    {"label": "EUR / USD", "symbol": "EURUSD=X", "fx": True},
    {"label": "Or (XAU)", "symbol": "GC=F", "fx": False},
    {"label": "NASDAQ 100", "symbol": "NQ=F", "fx": False}
]

cols = st.columns(len(watchlist))

for i, item in enumerate(watchlist):
    try:
        t = yf.Ticker(item["symbol"])
        hist = t.history(period="2d")
        if len(hist) >= 2:
            last = float(hist['Close'].iloc[-1])
            prev = float(hist['Close'].iloc[-2])
            chg = ((last - prev) / prev) * 100
            color = "#30d158" if chg >= 0 else "#ff453a"
            sign = "+" if chg >= 0 else ""
            fmt = f"{last:.5f} €" if item["fx"] else f"{last:,.2f} €"
            
            with cols[i]:
                st.markdown(f"""
                <div class="tr-card">
                    <div class="tr-card-title">{item['label']}</div>
                    <div class="tr-card-value">{fmt}</div>
                    <div class="tr-card-change" style="color: {color};">{sign}{chg:.2f} %</div>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass

st.markdown("<br>", unsafe_allow_html=True)

# Section d'accès direct
c1, c2 = st.columns(2)
with c1:
    st.markdown("""
    <div class="tr-card">
        <div class="tr-card-title">Terminal Graphique</div>
        <div style="font-size: 1.05rem; font-weight: 600; margin-top: 6px;">Lightweight Charts interactif</div>
        <p style="color: #8e8e93; font-size: 0.85rem; margin-top: 6px;">Navigue dans la barre latérale vers <strong>1_📊_Terminal_Live</strong> pour analyser les Order Blocks sur le graphique officiel TradingView.</p>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="tr-card">
        <div class="tr-card-title">Radar Multi-Marchés</div>
        <div style="font-size: 1.05rem; font-weight: 600; margin-top: 6px;">Détection continue</div>
        <p style="color: #8e8e93; font-size: 0.85rem; margin-top: 6px;">Consulte <strong>2_⚡_Scanner_Multi</strong> pour voir en un coup d'œil quelles zones sont actuellement testées.</p>
    </div>
    """, unsafe_allow_html=True)
