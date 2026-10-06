# ───────────── Moteur SMC Strict ─────────────
def _scan_demand(o, h, l, c, atr, piv_h, n=5, mult=1.2, hold=10):
    N = len(c)
    found = {}
    for j in range(15, N - 1):
        # 1. Impulsion haussière : corps vert >= 1.2 x ATR
        if not (c[j] > o[j] and (c[j] - o[j]) >= mult * atr[j]):
            continue
        # 2. FVG haussier
        if not (l[j + 1] > h[j - 1]):
            continue
        # 3. BOS : clôture au-dessus du dernier sommet swing non cassé
        lvl = None
        for q in reversed(piv_h):
            if q + n >= j:
                continue
            if q + 1 < j and c[q + 1:j].max() > h[q]:
                continue
            lvl = h[q]
            break
        if lvl is None or not (c[j] > lvl or c[j + 1] > lvl):
            continue

        # 4. Remonter au début de la poussée verte
        s = j
        while s - 1 >= 0 and c[s - 1] > o[s - 1]:
            s -= 1

        # 5. Chercher obligatoirement la dernière bougie ROUGE (Close < Open)
        k = s - 1
        while k >= 0 and c[k] == o[k]:  # ignore doji neutre
            k -= 1
        if k < 0 or not (c[k] < o[k]):  # AUCUNE bougie rouge trouvée -> rejet
            continue

        # 6. Bornes géométriques strictes
        # Bas = mèche la plus basse de la base ; Haut = Open de la bougie rouge
        bottom = float(l[k:j].min())
        top = float(max(o[k], c[k]))

        # Vérification creux swing
        if k > n and bottom > l[k - n:k].min():
            continue

        if k not in found:
            found[k] = (j, bottom, top)

    out = []
    for k, (j, bottom, top) in sorted(found.items()):
        touched, alive = None, True
        for t in range(j + 2, N):
            if touched is not None and t - touched >= hold:
                alive = False
                break
            if c[t] < bottom:
                alive = False
                break
            if touched is None and l[t] <= top:
                touched = t
        if alive:
            out.append((k, bottom, top, "EN TEST" if touched is not None else "ACTIVE"))
    return out


def _scan_supply(o, h, l, c, atr, piv_l, n=5, mult=1.2, hold=10):
    N = len(c)
    found = {}
    for j in range(15, N - 1):
        # 1. Impulsion baissière : corps rouge >= 1.2 x ATR
        if not (c[j] < o[j] and (o[j] - c[j]) >= mult * atr[j]):
            continue
        # 2. FVG baissier
        if not (h[j + 1] < l[j - 1]):
            continue
        # 3. BOS : clôture sous le dernier creux swing non cassé
        lvl = None
        for q in reversed(piv_l):
            if q + n >= j:
                continue
            if q + 1 < j and c[q + 1:j].min() < l[q]:
                continue
            lvl = l[q]
            break
        if lvl is None or not (c[j] < lvl or c[j + 1] < lvl):
            continue

        # 4. Remonter au début de la baisse rouge
        s = j
        while s - 1 >= 0 and c[s - 1] < o[s - 1]:
            s -= 1

        # 5. Chercher obligatoirement la dernière bougie VERTE (Close > Open)
        k = s - 1
        while k >= 0 and c[k] == o[k]:
            k -= 1
        if k < 0 or not (c[k] > o[k]):  # AUCUNE bougie verte trouvée -> rejet
            continue

        # 6. Bornes géométriques strictes
        # Haut = mèche la plus haute du sommet ; Bas = Open de la bougie verte
        top = float(h[k:j].max())
        bottom = float(min(o[k], c[k]))

        # Vérification sommet swing
        if k > n and top < h[k - n:k].max():
            continue

        if k not in found:
            found[k] = (j, bottom, top)

    out = []
    for k, (j, bottom, top) in sorted(found.items()):
        touched, alive = None, True
        for t in range(j + 2, N):
            if touched is not None and t - touched >= hold:
                alive = False
                break
            if c[t] > top:
                alive = False
                break
            if touched is None and h[t] >= bottom:
                touched = t
        if alive:
            out.append((k, bottom, top, "EN TEST" if touched is not None else "ACTIVE"))
    return out


def detect(df: pd.DataFrame, n: int = 5) -> list:
    """Retourne les OB vivants avec contrôle strict de couleur et de niveau."""
    if df is None or len(df) < 40:
        return []
    o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    ts = [int(t.timestamp()) for t in df.index]

    N = len(c)
    piv_h = [q for q in range(n, N - n) if h[q] > h[q - n:q].max() and h[q] >= h[q + 1:q + n + 1].max()]
    piv_l = [q for q in range(n, N - n) if l[q] < l[q - n:q].min() and l[q] <= l[q + 1:q + n + 1].min()]

    zones = []
    # Demand
    for k, bot, top, status in _scan_demand(o, h, l, c, atr, piv_h, n):
        if c[k] < o[k] and top > bot:  # Garantie absolue : bougie ROUGE
            zones.append(dict(side="Demand", t0=ts[k], bottom=bot, top=top, status=status))

    # Supply
    for k, bot, top, status in _scan_supply(o, h, l, c, atr, piv_l, n):
        if c[k] > o[k] and top > bot:  # Garantie absolue : bougie VERTE
            zones.append(dict(side="Supply", t0=ts[k], bottom=bot, top=top, status=status))

    return sorted(zones, key=lambda z: z["t0"])
