import json
import streamlit as st
import streamlit.components.v1 as components
import common as cm

cm.setup("Terminal Live")
cm.header("Terminal Live", "Échelles étirables au glisser · pan libre · boîtes SMC synchronisées")

c1, c2, c3, c4 = st.columns([2, 1.2, 1.2, 1])
name = c1.selectbox("Actif", list(cm.ASSETS), index=0)
tf = c2.selectbox("Timeframe", list(cm.TFS), index=1)
show = c3.selectbox("Order blocks", ["Afficher", "Masquer"])
c4.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)

if c4.button("Actualiser", use_container_width=True):
    cm.load.clear()
    cm.quote.clear()
    cm.scan_all.clear()

sym, dec = cm.ASSETS[name]
df = cm.load(sym, tf)

if df.empty:
    st.error("Aucune donnée reçue de Yahoo Finance pour cet actif et ce timeframe. Réessayez dans un instant.")
    st.stop()

df = df.tail(1500)
last, first = float(df["Close"].iloc[-1]), float(df["Open"].iloc[0])
q = cm.quote(sym)
chg = q["chg"] if q else (last / first - 1) * 100
col = cm.GREEN if chg >= 0 else cm.RED
zones = cm.detect(df) if show == "Afficher" else []

st.markdown(
    f"<div style='display:flex; align-items:baseline; gap:18px'>"
    f"<span class='num' style='font-size:48px'>{cm.fmt(last, dec)}</span>"
    f"<span class='num' style='font-size:20px; color:{col}'>{chg:+.2f}%</span>"
    f"<span class='lbl'>{name} · {tf} · {len(zones)} zone(s)</span></div>",
    unsafe_allow_html=True
)

candles = [
    dict(time=int(t.timestamp()), open=float(r.Open), high=float(r.High), low=float(r.Low), close=float(r.Close))
    for t, r in df.iterrows()
]

HTML = """<!doctype html><html><head><meta charset="utf-8">
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
html, body { margin: 0; height: 100%; background: #000; overflow: hidden; }
#w { position: relative; height: 100%; border: 1px solid #18181b; border-radius: 16px; overflow: hidden; box-sizing: border-box; }
#c { position: absolute; inset: 0; }
#o { position: absolute; left: 0; top: 0; pointer-events: none; }
</style></head>
<body><div id="w"><div id="c"></div><canvas id="o"></canvas></div><script>
const D = _DATA_, Z = _ZONES_, DEC = _DEC_;
const el = document.getElementById('c'), cv = document.getElementById('o'), cx = cv.getContext('2d');
const chart = LightweightCharts.createChart(el, {
    width: el.clientWidth,
    height: el.clientHeight,
    layout: { background: { type: 'solid', color: '#000000' }, textColor: '#71717a', fontFamily: 'Inter, sans-serif' },
    grid: { vertLines: { color: '#0c0c0e' }, horzLines: { color: '#0c0c0e' } },
    crosshair: { mode: 0 },
    rightPriceScale: { borderColor: '#18181b', scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: { borderColor: '#18181b', timeVisible: true, secondsVisible: false, rightOffset: 8 },
    handleScale: { axisPressedMouseMove: { time: true, price: true }, mouseWheel: true, pinch: true },
    handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true }
});

const s = chart.addCandlestickSeries({
    upColor: '#00d632', downColor: '#ff3b30', borderUpColor: '#00d632', borderDownColor: '#ff3b30',
    wickUpColor: '#00d632', wickDownColor: '#ff3b30',
    priceFormat: { type: 'price', precision: DEC, minMove: 1 / Math.pow(10, DEC) }
});
s.setData(D);
chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, D.length - 140), to: D.length - 1 + 8 });

const ts = chart.timeScale();
let last = '';

function dims() {
    let pw = 60, th = 28;
    try { pw = chart.priceScale('right').width(); } catch(e) {}
    try { th = ts.height(); } catch(e) {}
    return [Math.max(1, el.clientWidth - pw), Math.max(1, el.clientHeight - th)];
}

function draw() {
    const [w, h] = dims(), tEnd = D[D.length - 1].time, R = [];
    let sig = w + ' | ' + h;
    for (const z of Z) {
        const x0 = ts.timeToCoordinate(z.t0), x1 = ts.timeToCoordinate(tEnd);
        const y0 = s.priceToCoordinate(z.top), y1 = s.priceToCoordinate(z.bottom);
        if (y0 === null || y1 === null) continue;
        R.push([z, x0 === null ? 0 : x0, x1 === null ? w : x1, y0, y1]);
        sig += '|' + x0 + ',' + x1 + ',' + y0 + ',' + y1;
    }
    if (sig === last) return;
    last = sig;
    const d = window.devicePixelRatio || 1;
    cv.width = w * d; cv.height = h * d;
    cv.style.width = w + 'px'; cv.style.height = h + 'px';
    cx.setTransform(d, 0, 0, d, 0, 0);
    cx.clearRect(0, 0, w, h);
    for (const [z, x0, x1, y0, y1] of R) {
        if (x1 < 0 || x0 > w) continue;
        const up = z.side === 'Demand', c = up ? '0,214,50' : '255,59,48';
        const test = z.status === 'EN TEST', L = Math.max(x0, 0);
        cx.fillStyle = 'rgba(' + c + ',' + (test ? 0.24 : 0.12) + ')';
        cx.fillRect(L, y0, x1 - L, y1 - y0);
        cx.strokeStyle = 'rgba(' + c + ',.9)';
        cx.setLineDash(test ? [5, 3] : []);
        cx.lineWidth = 1;
        cx.strokeRect(L + 0.5, y0 + 0.5, x1 - L, y1 - y0);
        cx.fillStyle = 'rgb(' + c + ')';
        cx.font = '600 11px Inter, sans-serif';
        cx.fillText((up ? 'DEMAND' : 'SUPPLY') + ' ' + z.status, L + 6, Math.min(y0, y1) + 14);
    }
}

(function loop() { draw(); requestAnimationFrame(loop); })();
new ResizeObserver(() => { chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }); last = ''; }).observe(el);
</script></body></html>"""

html = (HTML.replace("_DATA_", json.dumps(candles))
            .replace("_ZONES_", json.dumps(zones))
            .replace("_DEC_", str(dec)))

components.html(html, height=660, scrolling=False)

st.caption("Contact mèche : EN TEST pendant 10 bougies. Clôture au-delà de la boîte : zone supprimée. "
           "Un pivot n'est confirmé qu'après 5 bougies, donc le dernier swing n'apparaît qu'avec ce délai.")
