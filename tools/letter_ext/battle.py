"""Lettering for the BATTLE pictures (match screens): gradient fills, layered menu labels, slanted
banners, stamps.

draw() is letter.draw_group() with these additions, set in the spec (or a group):
  fill      as in letter.py, or
            'colour'    opaque pixels with a clear hue (not white, grey or black);
            'enclosed'  every pixel shut in by the dark outline (not reachable from the box's edge
                        without crossing a near-black pixel, 'dark': r+g+b at most this, default 90)
                        - for multi-layer lettering whose rings share colours with the fill
  grad      'own' (default): each label's fill is sampled row by row from its own Japanese letters
            and laid on the English by height (top of the capitals .. baseline); 'group': one
            gradient learnt from every label of the group; 'flat': letter.py's single colour
  layers    'rows': the rings around the fill (outline, bevel, plate, glow) are learnt by distance
            AND by row in the box, so a plate that is pink at the top and blue at the bottom stays
            so ('reach' caps the distance, default 12)
  slant     italic shear in pixels per pixel of height (the banners lean right)
  texture   true: each fill pixel is copied from the nearest original fill pixel (keeps a stamp's
            grain instead of a row gradient)
  upper     capitals (as in letter.py)
  rotate    90: the English runs down the box, letters' tops to the right (vertical Japanese)
  ground    as in letter.py, or 'clone': the box is refilled with the original picture shifted by
            'clone': [dx, dy] (the art beside the label, instead of letter.py's smeared rows);
            'column': each column of the box takes its most common index in 'sample_rows'
"""
from collections import Counter

import letter

NB = 32     # gradient bins over the letter height


def enclosed(im, pal, box, dark=90, barrier='dark'):
    """Pixels of the box shut in by near-black (barrier 'dark') or near-white ('bright') opaque
    pixels (absolute (x, y))."""
    x, y, w, h = box
    px = im.load()

    def open_(i, j):
        r, g, b, a = pal[px[x + i, y + j]]
        if barrier == 'bright':
            return not (a >= 200 and r + g + b >= 600)
        if barrier == 'grey':
            return not (a >= 200 and max(r, g, b) - min(r, g, b) < 48)
        return not (a >= 200 and r + g + b <= dark)
    seen = [[False] * w for _ in range(h)]
    st = [(i, j) for i in range(w) for j in (0, h - 1)] + [(i, j) for j in range(h) for i in (0, w - 1)]
    st = [(i, j) for i, j in st if open_(i, j)]
    for i, j in st:
        seen[j][i] = True
    while st:
        i, j = st.pop()
        for u, v in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= u < w and 0 <= v < h and not seen[v][u] and open_(u, v):
                seen[v][u] = True
                st.append((u, v))
    return {(x + i, y + j) for j in range(h) for i in range(w) if not seen[j][i] and open_(i, j)}


def fill_pixels(im, pal, box, spec):
    """The original letter fill in the box: a set of absolute (x, y)."""
    x, y, w, h = box
    px = im.load()
    f = spec.get('fill')
    if f == 'enclosed':
        return enclosed(im, pal, box, spec.get('dark', 90), spec.get('barrier', 'dark'))
    if f == 'colour':
        def ok(i):
            r, g, b, a = pal[i]
            return a >= spec.get('alpha_min', 200) and max(r, g, b) - min(r, g, b) >= 48
    else:
        idx = letter.fill_indices(im, pal, box, spec)

        def ok(i):
            return i in idx
    return {(i, j) for j in range(y, y + h) for i in range(x, x + w) if ok(px[i, j])}


def fill_rows(im, pts):
    """{bin: Counter of indices} over the fill's own height."""
    px = im.load()
    if not pts:
        return {}
    top = min(j for _, j in pts)
    bot = max(j for _, j in pts)
    rows = {}
    for i, j in pts:
        k = min(NB - 1, int((j - top) / max(1, bot - top) * NB))
        rows.setdefault(k, Counter())[px[i, j]] += 1
    return rows


def gradient(rows, pal=None):
    """bin -> index, gaps filled from the nearest learnt bin. With pal, the brightest of the
    indices common in a bin wins (an enclosed fill also holds bits of dark inner outlines)."""
    def pick(c):
        if pal:
            top = c.most_common(1)[0][1]
            near = [i for i, n in c.items() if n >= 0.4 * top]
            return max(near, key=lambda i: sum(pal[i][:3]))
        return c.most_common(1)[0][0]
    have = {k: pick(c) for k, c in rows.items()}
    if not have:
        return None
    return [have[min(have, key=lambda b: abs(b - k))] for k in range(NB)]


def box_mask(box, pts):
    x, y, w, h = box
    return [[(x + i, y + j) in pts for i in range(w)] for j in range(h)]


RB = 40     # row bins per letter height for 'layers': 'rows'


def learn_rows(im, boxes, fills, reach):
    """{(distance step, row bin): index} around the fill; rows are measured from the top of each
    label's fill in fill heights (RB bins per height), so they carry over to English of another
    size."""
    px = im.load()
    by = {}
    for box, pts in zip(boxes, fills):
        x, y, w, h = box
        mask = box_mask(box, pts)
        ys = [j - y for _, j in pts]
        top, span = min(ys), max(1, max(ys) - min(ys))
        dist = letter.distances(mask, w, h, int(reach) + 1)
        for j in range(h):
            for i in range(w):
                if not mask[j][i] and dist[j][i] <= reach:
                    key = (round(dist[j][i] / letter.STEP), round((j - top) / span * RB))
                    by.setdefault(key, Counter())[px[x + i, y + j]] += 1
    return {k: c.most_common(1)[0][0] for k, c in by.items()}


def learn_dir(im, boxes, fills, reach, bare=None):
    """{(distance step, direction sector): index} around the fill (see nearest()); where the
    original is just the ground ('bare' after clearing), the key is left out."""
    px = im.load()
    gp = bare.load() if bare else None
    by = {}
    for box, pts in zip(boxes, fills):
        x, y, w, h = box
        for (i, j), key in nearest(box_mask(box, pts), w, h, reach).items():
            v = px[x + i, y + j]
            by.setdefault(key, Counter())[None if gp and gp[x + i, y + j] == v else v] += 1
    out = {k: c.most_common(1)[0][0] for k, c in by.items()}
    return {k: v for k, v in out.items() if v is not None}


def row_style(table, k, j):
    for dj in (0, 1, -1, 2, -2, 3, -3, 4, -4, 6, -6, 8, -8, 12, -12):
        if (k, j + dj) in table:
            return table[(k, j + dj)]
    return None


def draw(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    fills = [fill_pixels(im, pal, b, spec) for b in boxes]
    px_in = im.load()
    index_set = {px_in[p] for pts in fills for p in pts}
    rows_mode = spec.get('layers') in ('rows', 'dir')
    dir_mode = spec.get('layers') == 'dir'
    if rows_mode:
        reach = spec.get('reach', 12)
        if dir_mode:
            bare = im.copy()            # the ground the English goes on: rings that match it are not rings
            clear_all(im, bare, pal, boxes, spec)
            table = learn_dir(im, boxes, fills, reach, bare)
        else:
            table = learn_rows(im, boxes, fills, reach)
        style = {}
        heights = []
        for pts in fills:
            ys = [j for _, j in pts]
            heights.append(max(ys) - min(ys) + 1 if ys else 0)
        ink_h = min(heights)
        flat = Counter(px_in[p] for pts in fills for p in pts).most_common(1)[0][0]
        trans = next(i for i, p in enumerate(pal) if p[3] == 0)
        rim = spec.get('rim', reach)        # room kept around the English for the rings
    else:
        reach = spec.get('reach', 8)
        style, flat, ink_h = letter.learn_style(im, pal, boxes, index_set, spec['ground'], spec.get('reach', 8))
        rim = max(style) * letter.STEP if style else 0
    mode = spec.get('grad', 'own')
    learnt = [fill_rows(im, pts) for pts in fills]
    if mode == 'group':
        allrows = {}
        for rows in learnt:
            for k, c in rows.items():
                allrows.setdefault(k, Counter()).update(c)
        grads = [gradient(allrows, None if spec.get('pick') == 'common' else pal)] * len(boxes)
    elif mode == 'flat':
        grads = [None] * len(boxes)
    else:
        grads = [gradient(rows, None if spec.get('pick') == 'common' else pal) for rows in learnt]
    clear_all(im, out, pal, boxes, spec)
    slant = spec.get('slant', 0)
    rim_y = spec.get('rim_y', rim)
    inner = [(int(w - 2 * rim), int(h - 2 * rim_y)) for _, _, w, h in boxes]
    cap = spec.get('cap') or round(ink_h * 0.8)
    rot = spec.get('rotate', 0)
    for text, (iw, ih) in zip(texts, inner):
        if rot:
            iw, ih = ih, iw
        if text != '=':
            got = letter.text_mask(text, spec['font'], min(cap, ih), iw - round(ih * slant), ih, slack=int(rim_y))
            if got is None:
                raise SystemExit(f'letter: {name}: {text!r} does not fit {iw}x{ih}')
            cap = min(cap, got[1])
    notes = []
    px = out.load()
    r, ry = int(rim), int(rim_y)
    for n, (box, text, (iw, ih)) in enumerate(zip(boxes, texts, inner)):
        if text == '=':
            continue
        x, y, w, h = box
        full = [[False] * w for _ in range(h)]
        if rot:
            # written along the box's height, letters' tops to the right (read top to bottom)
            mask, size, squeeze = letter.text_mask(text, spec['font'], cap, ih, iw, 'center')
            for a in range(min(len(mask), iw)):
                for b in range(ih):
                    if mask[a][b]:
                        full[ry + b][r + iw - 1 - a] = True
        else:
            sw = round(ih * slant)
            mask, size, squeeze = letter.text_mask(text, spec['font'], cap, iw - sw, ih,
                                                   spec.get('align', 'center'), int(rim_y))
            for j in range(min(len(mask), h - ry)):
                shift = round((ih - 1 - j) * slant)
                for i in range(iw - sw):
                    if mask[j][i]:
                        full[j + ry][i + r + shift] = True
        if squeeze < 1:
            notes.append(f'{text!r}: squeezed to {squeeze:.0%}')
        ink_rows = [j for j in range(h) if any(full[j])]
        top = ink_rows[0] if ink_rows else 0
        span = max(1, size - 1)     # the gradient runs from the capitals' top to the baseline
        if rot:
            span = max(1, ink_rows[-1] - top)       # ... or along the whole word
        dist = letter.distances(full, w, h, int(reach) + 2)
        evec = nearest(full, w, h, reach) if dir_mode else {}
        src = sorted(fills[n])
        for j in range(h):
            for i in range(w):
                if full[j][i]:
                    if spec.get('texture') and src:
                        px[x + i, y + j] = texture_at(im, src, x + i, y + j)
                    elif grads[n]:
                        k = min(NB - 1 - spec.get('foot', 2), max(0, int((j - top) / span * NB)))
                        px[x + i, y + j] = grads[n][k]
                    else:
                        px[x + i, y + j] = flat
                elif dir_mode:
                    got = table.get(evec.get((i, j)))
                    if got is not None:
                        px[x + i, y + j] = got
                elif rows_mode:
                    if dist[j][i] <= reach:
                        got = row_style(table, round(dist[j][i] / letter.STEP), round((j - top) / span * RB))
                        if got is not None:
                            px[x + i, y + j] = got
                        elif spec['ground'] == 'transparent':
                            px[x + i, y + j] = trans
                else:
                    k = round(dist[j][i] / letter.STEP)
                    if k in style:
                        px[x + i, y + j] = style[k]
    notes.insert(0, f'capitals {cap} px')
    return notes, cap


def clear_all(im, out, pal, boxes, spec):
    limit = len(pal)
    for box in boxes:
        if spec['ground'] == 'clone':
            clone(im, out, box, spec['clone'])
        elif spec['ground'] == 'column':
            column(im, out, box, spec['sample_rows'])
        else:
            letter.clear(out, pal, box, spec['ground'], limit, spec.get('pad', 0))
    for box in spec.get('clear', []):
        letter.clear(out, pal, box, spec['ground'], limit)


def column(im, out, box, rows):
    """Refill the box column by column with each column's most common index in the sample rows
    (a ticket's plain paper, without its fine print)."""
    x, y, w, h = box
    src, px = im.load(), out.load()
    for i in range(x, x + w):
        c = Counter(src[i, j] for j in rows)
        v = c.most_common(1)[0][0]
        for j in range(y, y + h):
            px[i, j] = v


def clone(im, out, box, d):
    x, y, w, h = box
    src, px = im.load(), out.load()
    for j in range(y, y + h):
        for i in range(x, x + w):
            px[i, j] = src[min(im.width - 1, max(0, i + d[0])), min(im.height - 1, max(0, j + d[1]))]


def texture_at(im, src, x, y):
    """Index of the original fill pixel nearest (x, y) (rows weigh double: grain runs in bands)."""
    px = im.load()
    best = min(src, key=lambda p: (p[0] - x) ** 2 + 4 * (p[1] - y) ** 2)
    return px[best]


def banner(name, im, out, pal, texts, boxes, spec):
    """A whole-picture title on a soft glow (WIN01/02): the letters as draw() makes them, then the
    glow rebuilt around the English. The glow is learnt as a function of a blurred letter mask:
    blur the original letters (opaque pixels) by 'blur': [rx, ry], pair each blurred value with
    the glow index found there, and use the pairs on the blurred English."""
    from PIL import Image, ImageFilter
    W, H = im.size
    src, px = im.load(), out.load()
    trans = next(i for i, p in enumerate(pal) if p[3] == 0)
    solid = spec.get('solid', 250)
    glow_idx = sorted({src[i, j] for j in range(H) for i in range(W) if 0 < pal[src[i, j]][3] < solid})

    def blurred(get):
        m = Image.new('L', (W, H), 0)
        mp = m.load()
        for j in range(H):
            for i in range(W):
                if get(i, j):
                    mp[i, j] = 255
        return m.filter(ImageFilter.GaussianBlur(tuple(spec.get('blur', (40, 12))))).load()
    ob = blurred(lambda i, j: pal[src[i, j]][3] >= solid)
    pairs = {}
    for j in range(H):
        for i in range(W):
            a = pal[src[i, j]][3]
            if a < solid:
                pairs.setdefault(ob[i, j], []).append(a)
    curve = {v: sorted(a)[len(a) // 2] for v, a in pairs.items()}
    keys = sorted(curve)
    top = 0
    for v in keys:                  # more letter nearby never means less glow
        top = curve[v] = max(top, curve[v])
    # the original picture without its glow: the letters go, then draw() adds the English
    for j in range(H):
        for i in range(W):
            if pal[src[i, j]][3] < solid:
                px[i, j] = trans
    notes, cap = draw(name, im, out, pal, texts, boxes, spec | {'ground': 'transparent'})
    for j in range(H):              # the rings' outer, half-transparent steps belong to the glow
        for i in range(W):
            if pal[px[i, j]][3] < solid:
                px[i, j] = trans
    eb = blurred(lambda i, j: pal[px[i, j]][3] >= solid)
    by_alpha = {}
    for i in glow_idx:
        by_alpha.setdefault(pal[i][3], i)
    alphas = sorted(by_alpha)
    for j in range(H):
        for i in range(W):
            if pal[px[i, j]][3] == 0:
                v = eb[i, j]
                k = min(keys, key=lambda q: abs(q - v)) if v not in curve else v
                a = curve[k]
                px[i, j] = by_alpha[min(alphas, key=lambda q: abs(q - a))]
    err = sum(abs(curve[min(keys, key=lambda q: abs(q - ob[i, j]))] - pal[src[i, j]][3])
              for j in range(0, H, 4) for i in range(0, W, 4) if pal[src[i, j]][3] < solid)
    notes.append(f'glow learnt (sampled error {err})')
    return notes, cap


def stamp(name, im, out, pal, texts, boxes, spec):
    """A tilted rubber stamp (MAN01/02): a frame around a see-through panel ('panel': its palette
    indices) with lettering on it. The panel's tilt and extent come from the panel pixels (their
    principal axis); the lettering inside is replaced by the panel index, and the English is drawn
    upright in the panel's own frame and turned with it. Lines are split at ' / '. Fill: the
    nearest original letter pixel (keeps the ink's grain); rings: learnt by distance as in
    letter.py ('reach')."""
    import math
    from PIL import Image, ImageDraw, ImageFont
    src, px = im.load(), out.load()
    bx, by, bw, bh = boxes[0]
    W, H = im.size
    panel_idx = set(spec['panel'])
    # the frame: the ring of opaque-ish pixels reached first from the outside
    solid = [[pal[src[i, j]][3] > 0 and src[i, j] not in panel_idx for i in range(W)] for j in range(H)]
    seen = [[False] * W for _ in range(H)]
    st = [(i, j) for i in range(W) for j in (0, H - 1)] + [(i, j) for j in range(H) for i in (0, W - 1)]
    outside = set()
    while st:                                   # transparent area around the stamp
        i, j = st.pop()
        if seen[j][i] or solid[j][i]:
            continue
        seen[j][i] = True
        outside.add((i, j))
        st += [(u, v) for u, v in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)) if 0 <= u < W and 0 <= v < H]
    st = [(u, v) for (i, j) in outside for u, v in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1))
          if 0 <= u < W and 0 <= v < H and solid[v][u]]
    frame = set()
    while st:                                   # the frame (and its bevel), 8-connected
        i, j = st.pop()
        if (i, j) in frame or not (0 <= i < W and 0 <= j < H) or not solid[j][i]:
            continue
        frame.add((i, j))
        st += [(i + di, j + dj) for di in (-1, 0, 1) for dj in (-1, 0, 1) if di or dj]
    inside = [(i, j) for j in range(by, by + bh) for i in range(bx, bx + bw)
              if (i, j) not in outside and (i, j) not in frame]
    pts = [p for p in inside if src[p] in panel_idx]
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    # text direction: the panel's top edge (topmost panel pixel in each column, least squares)
    tops = {}
    for x, y in pts:
        tops[x] = min(tops.get(x, y), y)
    xs = sorted(tops)
    xs = xs[len(xs) // 5: len(xs) * 4 // 5]
    if spec.get('edge') == 'bottom':
        bots = {}
        for x, y in pts:
            bots[x] = max(bots.get(x, y), y)
        tops = bots
    ax = sum(xs) / len(xs)
    ay = sum(tops[x] for x in xs) / len(xs)
    slope = sum((x - ax) * (tops[x] - ay) for x in xs) / sum((x - ax) ** 2 for x in xs)
    ang = math.atan(slope) + math.radians(spec.get('turn', 0))
    ca, sa = math.cos(ang), math.sin(ang)
    e2 = (-sa, ca)
    if spec.get('shear'):
        # the letters' uprights follow the panel's left edge (the stamp is a parallelogram)
        lefts = {}
        for x, y in pts:
            u, wv = (x - mx) * ca + (y - my) * sa, -(x - mx) * sa + (y - my) * ca
            lefts[round(wv)] = min(lefts.get(round(wv), u), u)
        ws = sorted(lefts)
        ws = ws[len(ws) // 5: len(ws) * 4 // 5]
        aw = sum(ws) / len(ws)
        au = sum(lefts[v] for v in ws) / len(ws)
        c = sum((v - aw) * (lefts[v] - au) for v in ws) / sum((v - aw) ** 2 for v in ws)
        ex, ey = c * ca - sa, c * sa + ca
        nrm = math.hypot(ex, ey)
        e2 = (ex / nrm, ey / nrm)
    det = ca * e2[1] - sa * e2[0]

    def uv(x, y):
        dx, dy = x - mx, y - my
        return (dx * e2[1] - dy * e2[0]) / det, (ca * dy - sa * dx) / det
    cu = [uv(*p) for p in inside]
    band_v = sorted(v for u, v in cu)
    vmid = (band_v[0] + band_v[-1]) / 2
    us = sorted(u for u, v in cu if abs(v - vmid) < (band_v[-1] - band_v[0]) / 4)
    v0, v1 = band_v[len(band_v) // 100], band_v[-len(band_v) // 100 - 1]
    u0, u1 = us[len(us) // 100], us[-len(us) // 100 - 1]
    ground = Counter(src[p] for p in inside if src[p] in panel_idx).most_common(1)[0][0]
    fill_idx = set(spec['fill'])
    fill_pts = [p for p in inside if src[p] in fill_idx]
    # rings: distance from the original letters -> most common index (stop at the panel)
    reach = spec.get('reach', 2.5)
    x0, y0 = min(p[0] for p in inside), min(p[1] for p in inside)
    x1, y1 = max(p[0] for p in inside) + 1, max(p[1] for p in inside) + 1
    w, h = x1 - x0, y1 - y0
    fset = set(fill_pts)
    mask = [[(x0 + i, y0 + j) in fset for i in range(w)] for j in range(h)]
    vec = nearest(mask, w, h, reach)
    inset_set = set(inside)
    by_d = {}
    for (i, j), key in vec.items():
        if (x0 + i, y0 + j) in inset_set:
            by_d.setdefault(key, Counter())[src[x0 + i, y0 + j]] += 1
    style = {k: c.most_common(1)[0][0] for k, c in by_d.items()}
    # English, upright in the panel's frame
    lines = [t.strip() for t in texts[0].split(' / ')]
    S = 4
    pw, ph = (u1 - u0 - 2 * spec.get('margin', 8)), (v1 - v0 - 2 * spec.get('margin_y', spec.get('margin', 8)))
    font_file = str(letter.FONT_DIR / spec['font'])
    gap = spec.get('line_gap', 0.25)
    cap = spec.get('cap', 60)
    while True:
        font = ImageFont.truetype(font_file, round(cap * S / 0.7))
        hb = font.getbbox('H')
        font = ImageFont.truetype(font_file, round(font.size * cap * S / (hb[3] - hb[1])))
        hb = font.getbbox('H')
        widths = [font.getbbox(t)[2] - font.getbbox(t)[0] for t in lines]
        tot_h = cap * S * len(lines) + gap * cap * S * (len(lines) - 1)
        squeeze = min(1.0, pw * S / max(widths))
        if squeeze >= spec.get('squeeze_min', 0.8) and tot_h <= ph * S:
            break
        cap -= 1
    big = Image.new('L', (int(max(widths)) + 4 * S, int(tot_h) + 6 * S), 0)
    d = ImageDraw.Draw(big)
    for k, t in enumerate(lines):
        l = font.getbbox(t)[0]
        tw = widths[k]
        yy = k * cap * S * (1 + gap) - hb[1] + S
        d.text(((big.width - tw) / 2 - l, yy), t, font=font, fill=255)
    bp = big.load()
    cx_, cy_ = big.width / 2, (tot_h + 2 * S) / 2
    off_u, off_v = (u0 + u1) / 2 + spec.get('shift', [0, 0])[0], (v0 + v1) / 2 + spec.get('shift', [0, 0])[1]

    def cover(x, y):
        hit = 0
        for a in range(S):
            for b in range(S):
                u, v = uv(x + (a + 0.5) / S - 0.5, y + (b + 0.5) / S - 0.5)
                X = (u - off_u) * S / squeeze + cx_
                Y = (v - off_v) * S + cy_
                if 0 <= X < big.width and 0 <= Y < big.height and bp[int(X), int(Y)] >= 128:
                    hit += 1
        return hit / (S * S)
    for p in inside:
        px[p] = ground
    eng = [[cover(x0 + i, y0 + j) >= 0.5 for i in range(w)] for j in range(h)]
    evec = nearest(eng, w, h, reach)
    # fill: the original ink's colour by height in the panel's frame, one gradient per line
    fv = [uv(*p)[1] for p in fill_pts]
    lo, hi = min(fv), max(fv)
    rows = {}
    for p, v in zip(fill_pts, fv):
        rows.setdefault(min(NB - 1, int((v - lo) / max(1, hi - lo) * NB)), Counter())[src[p]] += 1
    vgrad = gradient(rows)
    evs = [uv(x0 + i, y0 + j)[1] for j in range(h) for i in range(w) if eng[j][i]]
    ev0, ev1 = min(evs), max(evs)
    for j in range(h):
        for i in range(w):
            p = (x0 + i, y0 + j)
            if p not in inset_set:
                continue
            if eng[j][i]:
                if spec.get('texture'):
                    px[p] = texture_at(im, fill_pts, *p)
                else:
                    t = (uv(*p)[1] - ev0) / max(1, ev1 - ev0)
                    px[p] = vgrad[min(NB - 1, max(0, int(t * NB)))]
            elif (i, j) in evec and evec[(i, j)] in style:
                px[p] = style[evec[(i, j)]]
    return [f'capitals {cap} px, tilt {math.degrees(ang):.1f} deg' + (f', squeezed to {squeeze:.0%}' if squeeze < 1 else '')], cap


def nearest(mask, w, h, reach, sectors=8):
    """{(i, j): (distance step, direction sector)} for the pixels within reach of mask: the
    direction is from the nearest mask pixel outwards, so a bevel lit from one side keeps it."""
    import math
    r = int(math.ceil(reach))
    out = {}
    best = {}
    for y in range(h):
        for x in range(w):
            if not mask[y][x]:
                continue
            for yy in range(max(0, y - r), min(h, y + r + 1)):
                for xx in range(max(0, x - r), min(w, x + r + 1)):
                    if mask[yy][xx]:
                        continue
                    d = math.hypot(xx - x, yy - y)
                    if d <= reach and d < best.get((xx, yy), 99):
                        best[(xx, yy)] = d
                        sec = int((math.atan2(yy - y, xx - x) + math.pi) / (2 * math.pi) * sectors) % sectors
                        out[(xx, yy)] = (round(d / letter.STEP), sec)
    return out
