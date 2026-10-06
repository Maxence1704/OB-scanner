from datetime import datetime, timezone
import streamlit as st
import common as cm

cm.setup("SMC Terminal")
cm.header("Marchés", f"Données différées · mise à jour {datetime.now(timezone.utc):%H:%M} UTC · moteur SMC en 15m")

names = list(cm.ASSETS)
for start in range(0, len(names), 4):
    cols = st.columns(4)
    for col, name in zip(cols, names[start:start + 4]):
        sym, dec = cm.ASSETS[name]
        q = cm.quote(sym)
        if not q:
            col.markdown(
                f"<div class='card'><div class='lbl'>{name}</div><div class='num' style='font-size:28px'>-</div></div>",
                unsafe_allow_html=True
            )
            continue
        c = cm.GREEN if q["chg"] >= 0 else cm.RED
        col.markdown(
            f"<div class='card'><div class='lbl'>{name}</div>"
            f"<div class='num' style='font-size:30px; margin:6px 0 10px'>{cm.fmt(q['last'], dec)}</div>"
            f"<div class='row'><div class='num' style='color:{c};font-size:15px'>{q['chg']:+.2f}%</div>"
            f"{cm.spark(q['spark'], c)}</div></div>",
            unsafe_allow_html=True
        )

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
left, right = st.columns([2, 1], gap="large")

with left:
    st.markdown("<div class='num' style='font-size:20px;margin-bottom:8px'>Flux order blocks</div>", unsafe_allow_html=True)
    with st.spinner("Analyse SMC..."):
        rows = [r for r in cm.scan_all("15m") if r["z"]]
        rows.sort(key=lambda r: (r["z"]["status"] != "EN TEST", r["z"]["dist"]))
        body = "".join(
            f"<tr><td>{r['name']}</td><td>{cm.badge(r['z'])}</td>"
            f"<td class='r'>{cm.fmt(r['price'], r['dec'])}</td><td class='r'>{r['z']['dist']:.2f}%</td></tr>"
            for r in rows[:8]
        ) or "<tr><td colspan='4' class='lbl'>Aucune zone active en 15m pour le moment.</td></tr>"
        st.markdown(
            f"<div class='card' style='padding:6px 10px'><table class='tbl'>"
            f"<tr><th>Actif</th><th>Statut</th><th class='r'>Prix</th><th class='r'>Distance</th></tr>"
            f"{body}</table></div>",
            unsafe_allow_html=True
        )

with right:
    st.markdown("<div class='num' style='font-size:20px;margin-bottom:8px'>Navigation</div>", unsafe_allow_html=True)
    st.page_link("pages/1_📊_Terminal_Live.py", label="Terminal Live · graphique et order blocks")
    st.page_link("pages/2_⚡_Scanner_Multi.py", label="Scanner Multi · surveillance 15m")
    st.caption("Source Yahoo Finance, différée. Pour du vrai temps réel, brancher OANDA, Polygon ou un broker.")
