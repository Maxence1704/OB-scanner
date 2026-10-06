import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="SMC Terminal | Overview",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style global Trade Republic
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
    .stApp { background-color: #000000; color: #ffffff; }
    
    .hub-title { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.04em; margin-bottom: 4px; }
    .hub-subtitle { font-size: 0.95rem; color: #71717a; margin-bottom: 28px; }
    
    .tr-metric-card {
        background: #09090b;
        border: 1px solid #18181b;
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 16px;
    }
    .tr-metric-label { font-size: 0.75rem; text-transform: uppercase; color: #71717a; font-weight: 600; letter-spacing: 0.05em; }
    .tr-metric-value { font-size: 1.8rem; font-weight: 800; color: #ffffff; margin-top: 4px; }
    .tr-metric-var { font-size: 0.85rem; font-weight: 600; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hub-title">Terminal Institutionnel</div>', unsafe_allow_html=True)
st.markdown('<div class="hub-subtitle">Surveillance de liquidité SMC & détection d\'Order Blocks haute précision.</div>', unsafe_allow_html=True)

# Cartes de marché en temps réel
watchlist = {
    "EUR/USD": "EURUSD=X",
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Or (XAU)": "GC=F",
    "NASDAQ 100": "NQ=F"
}

cols = st.columns(len(watchlist))

for i, (name, symbol) in enumerate(watchlist.items()):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="2d")
        if len(hist) >= 2:
            last = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            var = ((last - prev) / prev) * 100
            color = "#10b981" if var >= 0 else "#f43f5e"
            sign = "+" if var >= 0 else ""
            fmt = "{:.5f}" if "EUR" in symbol else "{:,.2f}"
            
            with cols[i]:
                st.markdown(f"""
                <div class="tr-metric-card">
                    <div class="tr-metric-label">{name}</div>
                    <div class="tr-metric-value">{fmt.format(last)}</div>
                    <div class="tr-metric-var" style="color: {color};">{sign}{var:.2f} %</div>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass

st.markdown("---")
st.markdown("### Navigation rapide")
c1, c2, c3 = st.columns(3)
with c1:
    st.info("**📊 Graphique Interactif** : Analyse tactile avec TradingView Lightweight Charts et projection des boîtes.")
with c2:
    st.success("**⚡ Scanner Global** : Analyse en continu de tous les actifs pour repérer les Order Blocks actifs.")
with c3:
    st.warning("**📚 Règles d'exécution** : Détail du triptyque institutionnel (Impulsion, FVG, BOS).")
