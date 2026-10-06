"""Données, moteur SMC et thème partagés par toutes les pages."""
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

ASSETS = {  # nom: (ticker Yahoo, décimales)
    "EUR/USD": ("EURUSD=X", 5), "GBP/USD": ("GBPUSD=X", 5), "USD/JPY": ("JPY=X", 3),
    "XAU/USD": ("GC=F", 2), "BTC/USD": ("BTC-USD", 2), "NAS100": ("NQ=F", 2), "S&P 500": ("ES=F", 2),
}
TFS = {  # tf: (interval, period, resample)
    "5m": ("5m", "5d", None), "15m": ("15m", "30d", None), "1h": ("1h", "180d", None),
    "4h": ("1h", "360d", "4h"), "1D": ("1d", "2y", None),
}
GREEN, RED, AMBER = "#00d632", "#ff3b30", "#f5a524"


@st.cache_data(ttl=60, show_spinner=False)
def load(sym: str, tf: str) -> pd.DataFrame:
    iv, per, rs = TFS[tf]
    try:
        df = yf.download(sym, interval=iv, period=per, progress=False, auto_adjust=False)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].dropna()
    df.index = pd.to_datetime(df.index)
    df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    if rs:
        df = df.resample(rs).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    return df


# ───────────── Moteur SMC ─────────────
def _scan(o, h, l, c, atr, n=5, mult=1.2, hold=10):
    """Order blocks HAUSSIERS (Demand) sur des tableaux numpy.

    Le Supply est obtenu en passant (-o, -l, -h, -c) : une bougie baissière devient
    haussière, un sommet devient un creux, donc les deux côtés partagent exactement
    la même logique. Retourne [(k, bottom, top, statut)] ; k = index de la bougie d'ancrage.
    """
    N = len(c)
    # Pivots swing high (confirmés par n bougies de chaque côté, aucun repainting)
    piv_h = [q for q in range(n, N - n)
             if h[q] > h[q - n:q].max() and h[q] >= h[q + 1:q + n + 1].max()]
    found = {}
    for j in range(15, N - 1):                       # j+1 doit exister pour le FVG
        # 1. Impulsion : bougie haussière, corps >= 1.2 x ATR(14)
        if not (c[j] > o[j] and (c[j] - o[j]) >= mult * atr[j]):
            continue
        # 2. FVG haussier : Low[j+1] > High[j-1]
        if not l[j + 1] > h[j - 1]:
            continue
        # 3. BOS réel : clôture de j ou j+1 au-dessus du dernier swing high NON encore cassé
        lvl = None
        for q in reversed(piv_h):
            if q + n >= j:
                continue                              # pivot pas encore confirmé à j
            if q + 1 < j and c[q + 1:j].max() > h[q]:
                continue                              # déjà cassé avant : pas une rupture
            lvl = h[q]
            break
        if lvl is None or not (c[j] > lvl or c[j + 1] > lvl):
            continue
        # 4. Début de l'impulsion s : on remonte la série de bougies vertes collées à j
        s = j
        while s - 1 >= 0 and c[s - 1] > o[s - 1]:
            s -= 1
        # 5. Bougie d'ancrage k : dernière bougie ROUGE avant s (on saute seulement les dojis)
        k = s - 1
        while k >= 0 and c[k] == o[k]:
            k -= 1
        if k < 0 or not c[k] < o[k]:
            continue                                  # pas de bougie rouge : AUCUNE zone
        # 6. Phase de creux : suite de bougies baissières/dojis qui se termine en k
        ps = k
        while ps - 1 >= 0 and c[ps - 1] <= o[ps - 1]:
            ps -= 1
        bottom = float(l[ps:k + 1].min())
        top = float(max(o[k], c[k]))
        # Le creux doit être un vrai swing low : aucun plus bas juste avant ni pendant l'impulsion
        if ps > 0 and bottom > l[max(0, ps - n):ps].min():
            continue
        if bottom > l[k + 1:j + 2].min():
            continue
        if k not in found:                            # une seule zone par bougie d'ancrage
            found[k] = (j, bottom, top)
    out = []
    for k, (j, bottom, top) in sorted(found.items()):
        touched, alive = None, True
        for t in range(j + 2, N):                     # cycle de vie après formation (j, j+1)
            if touched is not None and t - touched >= hold:
                alive = False                         # EN TEST : exactement 10 bougies
                break
            if c[t] < bottom:                         # clôture sous la boîte : suppression
                alive = False
                break
            if touched is None and l[t] <= top:       # mèche dans la boîte
                touched = t
        if alive:
            out.append((k, bottom, top, "EN TEST" if touched is not None else "ACTIVE"))
    return out


def detect(df: pd.DataFrame, n: int = 5) -> list:
    """Retourne les OB vivants : dict(side, t0, bottom, top, status)."""
    if df is None or len(df) < 40:
        return []
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()   # ATR(14) de Wilder
    ts = [int(t.timestamp()) for t in df.index]
    zones = []
    for side, res in (("Demand", _scan(o, h, l, c, atr, n)),
                      ("Supply", _scan(-o, -l, -h, -c, atr, n))):
        for k, bot, top, status in res:
            if side == "Supply":                      # retour dans l'espace des prix réels
                bot, top = -top, -bot
            # Garde-fou : couleur de l'ancre cohérente avec le côté (rouge=Demand, verte=Supply)
            if (side == "Demand" and not c[k] < o[k]) or (side == "Supply" and not c[k] > o[k]):
                continue
            if not top > bot:
                continue
            zones.append(dict(side=side, t0=ts[k], bottom=float(bot), top=float(top), status=status))
    return sorted(zones, key=lambda z: z["t0"])


# ───────────── Quotes & scanner ─────────────
def fmt(v, dec):
    return f"{v:,.{dec}f}" if dec <= 2 else f"{v:.{dec}f}"


@st.cache_data(ttl=45, show_spinner=False)
def quote(sym: str):
    i, d = load(sym, "5m"), load(sym, "1D")
    if i.empty or len(d) < 2:
        return None
    last = float(i["Close"].iloc[-1])
    prev = float(d["Close"].iloc[-1] if d.index[-1].date() < i.index[-1].date() else d["Close"].iloc[-2])
    return dict(last=last, chg=(last / prev - 1) * 100, spark=[float(x) for x in i["Close"].tail(70)])


@st.cache_data(ttl=120, show_spinner=False)
def scan_all(tf: str = "15m") -> list:
    rows = []
    for name, (sym, dec) in ASSETS.items():
        df = load(sym, tf)
        if df.empty:
            continue
        px, zs = float(df["Close"].iloc[-1]), detect(df)
        best = None
        for z in zs:
            d = 0.0 if z["bottom"] <= px <= z["top"] else min(abs(px - z["top"]), abs(px - z["bottom"])) / px * 100
            if best is None or d < best["dist"]:
                best = dict(z, dist=d)
        q = quote(sym)
        rows.append(dict(name=name, dec=dec, price=px, chg=q["chg"] if q else 0.0, n=len(zs), z=best))
    return rows


# ───────────── UI ─────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html,body,.stApp,[class*="css"]{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif!important}
.stApp{background:#000!important;color:#fff}
header[data-testid="stHeader"],footer,#MainMenu,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none!important}
.block-container{padding:1.8rem 2.2rem 2rem!important;max-width:1560px}
[data-testid="stVerticalBlock"]{gap:.9rem}
section[data-testid="stSidebar"]{background:#050506!important;border-right:1px solid #18181b}
[data-testid="stSidebarNav"] a{border-radius:10px;padding:.45rem .7rem;color:#8e8e93!important;font-weight:600}
[data-testid="stSidebarNav"] a:hover{background:#0c0c0e}
[data-testid="stSidebarNav"] a[aria-current="page"]{background:#0c0c0e;color:#fff!important;border:1px solid #1c1c1e}
[data-testid="stWidgetLabel"] p,label{color:#71717a!important;font-size:12px!important;font-weight:600!important;letter-spacing:-.01em}
div[data-baseweb="select"]>div{background:#09090b!important;border:1px solid #1c1c1e!important;border-radius:12px!important;min-height:46px;color:#fff;font-weight:600}
div[data-baseweb="select"]>div:hover{border-color:#2c2c2e!important}
div[data-baseweb="popover"] ul,div[data-baseweb="menu"]{background:#09090b!important;border:1px solid #1c1c1e;border-radius:12px}
li[role="option"]:hover{background:#18181b!important}
a[data-testid="stPageLink-NavLink"]{background:#09090b;border:1px solid #18181b;border-radius:14px;padding:.8rem 1rem;color:#fff!important;font-weight:700}
a[data-testid="stPageLink-NavLink"]:hover{border-color:#00d632}
.stButton>button{background:#09090b;border:1px solid #1c1c1e;border-radius:12px;color:#fff;font-weight:700;min-height:46px}
.stButton>button:hover{border-color:#00d632;color:#00d632}
.num{font-weight:800;letter-spacing:-.05em;font-variant-numeric:tabular-nums}
.ttl{font-weight:800;letter-spacing:-.05em;font-size:34px;line-height:1.05;margin:0}
.sub{color:#71717a;font-size:13px;font-weight:500;margin-top:6px;letter-spacing:-.01em}
.card{background:linear-gradient(180deg,#0c0c0e,#09090b);border:1px solid #18181b;border-radius:18px;padding:18px 20px;height:100%}
.card:hover{border-color:#27272a}
.lbl{color:#8e8e93;font-size:12px;font-weight:600;letter-spacing:-.01em}
.row{display:flex;justify-content:space-between;align-items:flex-end;gap:10px}
.up{color:#00d632}.dn{color:#ff3b30}
.pill{display:inline-block;padding:3px 10px;border-radius:99px;font-size:11px;font-weight:700;border:1px solid}
.tbl{width:100%;border-collapse:collapse}
.tbl th{color:#71717a;font-size:12px;font-weight:600;text-align:left;padding:10px 14px;border-bottom:1px solid #18181b}
.tbl td{padding:14px;border-bottom:1px solid #111113;font-weight:600;font-size:14px;font-variant-numeric:tabular-nums}
.tbl tr:last-child td{border-bottom:0}
.tbl td.r,.tbl th.r{text-align:right}
@media(max-width:800px){.block-container{padding:1rem!important}.ttl{font-size:26px}}
"""


def setup(title: str):
    st.set_page_config(page_title=title, page_icon="◼", layout="wide", initial_sidebar_state="expanded")
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
    st.sidebar.markdown(
        "<div class='num' style='font-size:20px;padding:6px 4px 14px'>SMC<span class='up'>.</span>Terminal</div>",
        unsafe_allow_html=True)


def header(title: str, sub: str):
    st.markdown(f"<h1 class='ttl'>{title}</h1><div class='sub'>{sub}</div>", unsafe_allow_html=True)


def badge(z):
    if not z:
        return "<span class='lbl'>Aucune zone</span>"
    col = AMBER if z["status"] == "EN TEST" else (GREEN if z["side"] == "Demand" else RED)
    return (f"<span class='pill' style='color:{col};border-color:{col}55;background:{col}14'>"
            f"{z['side']} · {z['status']}</span>")


def spark(vals, color, w=120, h=36):
    lo, hi = min(vals), max(vals)
    r = (hi - lo) or 1
    pts = " ".join(f"{i * w / (len(vals) - 1):.1f},{h - (v - lo) / r * h:.1f}" for i, v in enumerate(vals))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline points="{pts}" fill="none" '
            f'stroke="{color}" stroke-width="1.7" stroke-linejoin="round" stroke-linecap="round"/></svg>')
