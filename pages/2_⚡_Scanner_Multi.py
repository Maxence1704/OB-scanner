import streamlit as st
import common as cm

cm.setup("Scanner Multi")
cm.header("Scanner Multi", "Order blocks actifs en 15m, triés par urgence puis par distance au prix")

c1, c2 = st.columns([1.4, 1])
flt = c1.selectbox("Filtre", ["Tous", "En test", "Demand", "Supply"])
c2.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)

if c2.button("Relancer le scan", use_container_width=True):
    cm.load.clear()
    cm.quote.clear()
    cm.scan_all.clear()

with st.spinner("Scan des actifs..."):
    rows = cm.scan_all("15m")

def keep(r):
    z = r["z"]
    if flt == "Tous":
        return True
    if not z:
        return False
    return z["status"] == "EN TEST" if flt == "En test" else z["side"] == flt

rows = sorted(
    (r for r in rows if keep(r)),
    key=lambda r: (
        r["z"] is None,
        r["z"]["status"] != "EN TEST" if r["z"] else True,
        r["z"]["dist"] if r["z"] else 0
    )
)

body = ""
for r in rows:
    z, c = r["z"], (cm.GREEN if r["chg"] >= 0 else cm.RED)
    zone = f"{cm.fmt(z['bottom'], r['dec'])} - {cm.fmt(z['top'], r['dec'])}" if z else "-"
    dist = f"{z['dist']:.2f}%" if z else "-"
    body += (
        f"<tr><td style='font-weight:800'>{r['name']}</td>"
        f"<td class='r num'>{cm.fmt(r['price'], r['dec'])}</td>"
        f"<td class='r' style='color:{c}'>{r['chg']:+.2f}%</td>"
        f"<td>{cm.badge(z)}</td>"
        f"<td class='r'>{zone}</td>"
        f"<td class='r'>{dist}</td>"
        f"<td class='r'>{r['n']}</td></tr>"
    )

st.markdown(
    f"<div class='card' style='padding:6px 10px; overflow-x:auto'><table class='tbl'>"
    f"<tr><th>Actif</th><th class='r'>Prix</th><th class='r'>Var. jour</th>"
    f"<th>Zone la plus proche</th><th class='r'>Boîte</th><th class='r'>Distance</th>"
    f"<th class='r'>Zones</th></tr>"
    f"{body or '<tr><td colspan=7 class=lbl>Aucun résultat pour ce filtre.</td></tr>'}</table></div>",
    unsafe_allow_html=True
)
