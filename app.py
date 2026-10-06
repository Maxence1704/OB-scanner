import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Trade Republic | Web Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PIXEL-PERFECT TRADE REPUBLIC WEB TERMINAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    /* Reset global */
    html, body, [class*="css"], .stApp {
        background-color: #000000 !important;
        color: #ffffff !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }

    /* Suppression des marges parasites Streamlit */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 100% !important;
    }

    /* Barre latérale Trade Republic */
    section[data-testid="stSidebar"] {
        background-color: #000000 !important;
        border-right: 1px solid #1c1c1e !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        padding-top: 1rem;
    }
    section[data-testid="stSidebar"] span {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        color: #8e8e93 !important;
    }

    /* Grand titre Trade Republic style */
    .tr-sub-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #636366;
        margin-bottom: 4px;
    }
    .tr-hero-title {
        font-size: 3.8rem;
        font-weight: 900;
        letter-spacing: -0.06em;
        color: #ffffff;
        line-height: 1.0;
        margin-bottom: 8px;
    }
    .tr-status {
        font-size: 0.95rem;
        font-weight: 600;
        color: #00d632;
        letter-spacing: -0.02em;
        margin-bottom: 35px;
    }

    /* Cartes d'actifs (Widgets) */
    .tr-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 30px;
    }
    .tr-card {
        background: #09090b;
        border: 1px solid #18181b;
        border-radius: 14px;
        padding: 20px;
        transition: border-color 0.2s ease;
    }
    .tr-card:hover {
        border-color: #27272a;
    }
    .tr-card-title {
        font-size: 0.75rem;
        font-weight: 700;
        color: #71717a;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .tr-card-price {
        font-size: 1.85rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: #ffffff;
        line-height: 1.1;
    }
    .tr-card-var {
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 6px;
    }

    /* Modules de navigation */
    .tr-panel {
        background: #09090b;
        border: 1px solid #18181b;
        border-radius: 14px;
        padding: 24px;
        height: 100%;
    }
    .tr-panel-tag {
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #52525b;
        margin-bottom: 8px;
    }
    .tr-panel-h {
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #ffffff;
        margin-bottom: 6px;
    }
    .tr-panel-p {
        font-size: 0.88rem;
        color: #8e8e93;
        line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)

# En-tête
st.markdown("""
<div>
    <div class="tr-sub-label">Flux Institutionnel · Smart Money Concepts</div>
    <div class="tr-hero-title">SMC Terminal</div>
    <div class="tr-status">● Marchés connectés en temps réel</div>
</div>
""", unsafe_allow_html=True)

# Données des marchés
markets = [
    {"label": "EUR / USD", "ticker": "EURUSD=X", "is_fx": True},
    {"label": "Bitcoin", "ticker": "BTC-USD", "is_fx": False},
    {"label": "Or (XAU)", "ticker": "GC=F", "is_fx": False},
    {"label": "NASDAQ 100", "ticker": "NQ=F", "is_fx": False}
]

cols = st.columns(4)

for i, m in enumerate(markets):
    try:
        t = yf.Ticker(m["ticker"])
        h = t.history(period="2d")
        if len(h) >= 2:
            last = float(h['Close'].iloc[-1])
            prev = float(h['Close'].iloc[-2])
            pct = ((last - prev) / prev) * 100
            color = "#00d632" if pct >= 0 else "#ff3b30"
            sign = "+" if pct >= 0 else ""
            fmt = f"{last:.5f} €" if m["is_fx"] else f"{last:,.2f} €"

            with cols[i]:
                st.markdown(f"""
                <div class="tr-card">
                    <div class="tr-card-title">{m['label']}</div>
                    <div class="tr-card-price">{fmt}</div>
                    <div class="tr-card-var" style="color: {color};">{sign}{pct:.2f} %</div>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass

st.markdown("<br>", unsafe_allow_html=True)

# Panneaux de redirection
c1, c2 = st.columns(2)
with c1:
    st.markdown("""
    <div class="tr-panel">
        <div class="tr-panel-tag">Terminal Graphique</div>
        <div class="tr-panel-h">Pro Charting & Order Blocks</div>
        <div class="tr-panel-p">
            Accède au graphique interactif officiel TradingView avec détection automatique des FVG, BOS et Order Blocks institutionnels.
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="tr-panel">
        <div class="tr-panel-tag">Multi-Marchés</div>
        <div class="tr-panel-h">Scanner de Liquidité</div>
        <div class="tr-panel-p">
            Surveille l'ensemble des paires de devises, indices et cryptomonnaies pour identifier les zones en cours de test.
        </div>
    </div>
    """, unsafe_allow_html=True)
