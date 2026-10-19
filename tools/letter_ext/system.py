"""Batch 'system': anti-aliased, layered lettering for pictures whose letters are smooth (alpha or
many-shade palettes), gradient-filled, outlined, glowing or drop-shadowed.

draw() is a letter.py drawer ("draw": "system.draw"). It clears each box like letter.py does, then
builds the English as RGBA layers at 4x - glow, outline, fill (flat or a vertical gradient), with
an optional drop shadow under the lot - composites them over the cleared ground and snaps every
changed pixel to the picture's own palette (letter.nearest). Spec keys, besides letter.py's
(english, boxes, ground, pad, clear, font, align, cap, groups, same_size):

  fill      [r, g, b] or {"grad": [[r, g, b], ...]} - stops from the capitals' top to the baseline
  rings     [{"w": px, "rgb": colour, "a", "blur", "dx", "dy", "span": "box"|"text"}] - layers
            grown w px around the fill (any number: bevels, rims, shadows); or the simple keys:
  outline   {"w": px, "rgb": [r, g, b], "a": 0-255}            hard edge around the fill
  glow      {"w": px, "blur": px, "rgb": [r, g, b], "a": 0-255} soft halo outside the outline
  shadow    {"dx": px, "dy": px, "blur": px, "rgb": [r, g, b], "a": 0-255}
  margin    px kept free inside each box (default: what the outline/glow/shadow need)
  squeeze   narrowest horizontal squeeze before the size drops (default 0.72)
  valign    center (default) | top;  dy: nudge the text down (px)
  inpaint   [{"rect": [x, y, w, h], "warm": k}] - pixels of rect whose blue <= red + k (the
            neutral/warm lettering on a cool ground) are rebuilt from a quadratic surface fitted
            to the ground around them (a shaded button the lettering covers); "deg": [dx, dy] fits x^a y^b (a <= dx,
            b <= dy) instead of a quadric; "seed": [rgb, ...] (+ "tol", "near") marks
            the lettering as pixels within near px of those colours instead; "all": true repaints
            the whole rect from the surface; "mode": "row" copies the nearest ground pixel of the
            same row instead (a frame's straight edge); "mode": "rowlerp" blends the nearest ground
            pixels left and right in the row (bands behind a title; "side": "right" or "left" uses
            one side only, "all": true treats the whole rect as lettering, "tile": {"cols": [a, b],
            "rows": [y0, y1], "all": bool} repeats the clean columns a..b over those rows instead (a
            texture; with "all", over every pixel of those rows; "mirror": back and forth; "dy":
            source row offset; "image": take the strip from that original picture)); "mode": "copy", "from": [x, y] copies the
            same-sized rect from there (a clean frame from a twin button)
  repaint   [{"rect": [x, y, w, h], "index": i, "keep": [indices]}] - set every pixel of rect to
            index i ("auto": the rect's commonest) except the kept ones (a flat panel with a border: clears what 'clear' can't)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import letter  # noqa: E402

S = 4


def _font(file, cap):
    """Font whose capital H is `cap` px high at S x."""
    size = cap * S
    f = ImageFont.truetype(str(letter.FONT_DIR / file), round(size / 0.7))
    h = f.getbbox('H')
    return ImageFont.truetype(str(letter.FONT_DIR / file), max(1, round(f.size * size / (h[3] - h[1]))))


def _mask(text, file, cap, squeeze_min, w):
    """(L mask at S x of the text, squeezed to fit w px if it can, capital top row, baseline row)
    or None."""
    f = _font(file, cap)
    l, t, r, b = f.getbbox(text)
    top = f.getbbox('H')[1]
    big = Image.new('L', (r - l + 4 * S, b - min(t, top) + 4 * S), 0)
    ox, oy = -l + 2 * S, -min(t, top) + 2 * S
    ImageDraw.Draw(big).text((ox, oy), text, font=f, fill=255)
    box = big.getbbox()
    if box is None:
        return None
    big = big.crop((box[0], 0, box[2], big.height))
    sq = min(1.0, w * S / big.width)
    if sq < squeeze_min:
        return None
    if sq < 1:
        big = big.resize((max(1, round(big.width * sq)), big.height), Image.LANCZOS)
    return big, oy + top, oy + top + cap * S, sq


def _grow(m, px):
    """Dilate an L mask by px (at S x) with a round-ish brush."""
    if px <= 0:
        return m
    n = int(round(px))
    out = m
    for _ in range(n // 2):
        out = out.filter(ImageFilter.MaxFilter(5))
    if n % 2:
        out = out.filter(ImageFilter.MaxFilter(3))
    return out


def _extent(spec):
    return max([r['w'] + r.get('blur', 0) + max(abs(r.get('dx', 0)), abs(r.get('dy', 0)))
                for r in _rings(spec)] or [0])


def fit(text, spec, cap, w, h):
    """Largest capital height <= cap at which text fits w x h."""
    for c in range(cap, 4, -1):
        got = _mask(text, spec['font'], c, spec.get('squeeze', 0.72), w)
        if got and c <= h:
            return c
    return None


def _over(dst, src):
    """Porter-Duff over, straight alpha tuples."""
    sa = src[3] / 255
    da = dst[3] / 255
    oa = sa + da * (1 - sa)
    if oa <= 0:
        return (0, 0, 0, 0)
    rgb = [(src[k] * sa + dst[k] * da * (1 - sa)) / oa for k in range(3)]
    return tuple(round(v) for v in rgb) + (round(oa * 255),)


def _colour_at(c, t, h=None):
    """Colour c at t: 0-1 over the capitals ('text' span) or a row (px) of the box ('box' span,
    h = box height). c: [r, g, b], {"grad": [rgb, ...]} (evenly spaced over the span) or
    {"grad": [[pos, rgb], ...]} (pos in px from the box top for a box span, 0-1 for text)."""
    if not isinstance(c, dict):
        return tuple(c)
    st = c['grad']
    if isinstance(st[0][0], (int, float)) and isinstance(st[0][1], list):
        pts = [(p, rgb) for p, rgb in st]
    else:
        n = len(st) - 1
        pts = [((k / n) * (h if h else 1), rgb) for k, rgb in enumerate(st)]
    if t <= pts[0][0]:
        return tuple(pts[0][1])
    for (p0, c0), (p1, c1) in zip(pts, pts[1:]):
        if t <= p1:
            f = (t - p0) / max(1e-6, p1 - p0)
            return tuple(round(c0[k] + (c1[k] - c0[k]) * f) for k in range(3))
    return tuple(pts[-1][1])


def _rings(spec):
    """The layers around the fill, outermost first: spec 'rings' ([{w, rgb, a, blur, dx, dy,
    span}], w = growth from the fill in px; rgb may be a gradient, span 'box' or 'text'), or the
    simple keys outline / glow / shadow."""
    if 'rings' in spec:
        return sorted(spec['rings'], key=lambda r: -r['w'])
    out = []
    o, g, sh = spec.get('outline'), spec.get('glow'), spec.get('shadow')
    ow = o['w'] if o else 0
    if sh:
        w = ow + (g['w'] if g else 0)
        out.append({'w': w, 'rgb': sh['rgb'], 'a': sh.get('a', 255), 'blur': sh.get('blur', 0),
                    'dx': sh.get('dx', 0), 'dy': sh.get('dy', 0)})
    if g:
        out.append({'w': ow + g['w'], 'rgb': g['rgb'], 'a': g.get('a', 255), 'blur': g.get('blur', 0)})
    if o:
        out.append({'w': ow, 'rgb': o['rgb'], 'a': o.get('a', 255)})
    return out


def _solve(m, v):
    """Gaussian elimination: m x = v."""
    n = len(v)
    a = [row[:] + [v[i]] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        a[c], a[p] = a[p], a[c]
        if abs(a[c][c]) < 1e-12:
            continue
        for r in range(n):
            if r != c:
                f = a[r][c] / a[c][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [a[i][n] / a[i][i] if abs(a[i][i]) > 1e-12 else 0 for i in range(n)]


def _inpaint(px, pal, r, limit):
    """Rebuild the lettering's pixels in rect from a quadratic surface fitted, per channel, to the
    ground pixels around them (a shaded button: brighter in the middle)."""
    rx, ry, rw, rh = r['rect']
    k = r.get('warm', 0)
    if r.get('mode') == 'copy':     # the same-sized rect at 'from' (a clean copy of a frame)
        sx, sy = r['from']
        for j in range(rh):
            for i in range(rw):
                px[rx + i, ry + j] = px[sx + i, sy + j]
        return
    if r.get('mode') == 'row':      # each lettering pixel: the nearest ground pixel in its row
        for j in range(ry, ry + rh):
            row = [pal[px[i, j]] for i in range(rx, rx + rw)]
            good = [n for n, c in enumerate(row) if c[2] - c[0] > k]
            if not good:
                continue
            for n, c in enumerate(row):
                if c[2] - c[0] <= k:
                    px[rx + n, j] = px[rx + min(good, key=lambda g: abs(g - n)), j]
        return
    if 'seed' in r:     # lettering = pixels near the given colours
        cols, tol, near = r['seed'], r.get('tol', 40), r.get('near', 2)
        seeds = {(i, j) for j in range(ry, ry + rh) for i in range(rx, rx + rw)
                 if min(sum((a - b) ** 2 for a, b in zip(pal[px[i, j]][:3], c)) for c in cols) <= tol * tol}
        is_text = lambda i, j, c: any((i + a, j + b) in seeds for a in range(-near, near + 1)
                                      for b in range(-near, near + 1))
    else:
        is_text = lambda i, j, c: c[2] - c[0] <= k
    if r.get('mode') == 'rowlerp':  # each lettering pixel: blend of the nearest ground left and right
        side = r.get('side', 'both')
        tile = r.get('tile')        # {"cols": [a, b], "rows": [y0, y1]}: textured rows tiled from a clean strip
        src = None
        if tile and tile.get('image'):      # the strip comes from another original picture
            sim = Image.open(letter.paths.ORIGINAL_IMAGES / f"{tile['image']}.png")
            src = (letter.rgba_palette(sim), sim.load())
        for j in range(ry, ry + rh):
            if tile and tile['rows'][0] <= j <= tile['rows'][1]:
                a, b = tile['cols']
                sj = j + tile.get('dy', 0)
                for i in range(rx, rx + rw):
                    if r.get('all') or tile.get('all') or is_text(i, j, pal[px[i, j]]):
                        q = (i - a) % (2 * (b - a)) if tile.get('mirror') else (i - a) % (b - a)
                        si = a + (q if q < b - a else 2 * (b - a) - 1 - q)
                        if src is None:
                            px[i, j] = px[si, sj]
                        else:
                            px[i, j] = letter.nearest(pal, src[0][src[1][si, sj]], limit)
                continue
            row = [pal[px[i, j]] for i in range(rx - 1, rx + rw + 1)]     # one ground pixel each side
            bad = [False] + [r.get('all') or is_text(rx + n, j, c) for n, c in enumerate(row[1:-1])] + [False]
            if side == 'right':
                bad[0] = True
            if side == 'left':
                bad[-1] = True
            for n in range(1, rw + 1):
                if not bad[n]:
                    continue
                a = next((q for q in range(n - 1, -1, -1) if not bad[q]), None)
                b = next((q for q in range(n + 1, rw + 2) if not bad[q]), None)
                if a is None and b is None:
                    continue
                if a is None or b is None:
                    px[rx + n - 1, j] = px[rx - 1 + (b if a is None else a), j]
                    continue
                t = (n - a) / (b - a)
                rgba = tuple(round(row[a][c] + (row[b][c] - row[a][c]) * t) for c in range(4))
                px[rx + n - 1, j] = letter.nearest(pal, rgba, limit)
        return
    cx, cy = rx + rw / 2, ry + rh / 2
    dx, dy = r.get('deg', [2, 2])
    sx, sy = max(1, rw / 2), max(1, rh / 2)
    if dx == 2 and dy == 2:
        terms = lambda i, j: [1, (i - cx), (j - cy), (i - cx) ** 2, (j - cy) ** 2, (i - cx) * (j - cy)]
    else:       # x^a y^b, a <= dx, b <= dy (scaled to -1..1)
        terms = lambda i, j: [((i - cx) / sx) ** a * ((j - cy) / sy) ** b
                              for a in range(dx + 1) for b in range(dy + 1)]
    known, unknown = [], []
    for j in range(ry, ry + rh):
        for i in range(rx, rx + rw):
            c = pal[px[i, j]]
            (unknown if is_text(i, j, c) else known).append((i, j, c))
    coef = []
    for ch in range(3):
        n = len(terms(rx, ry))
        m = [[0.0] * n for _ in range(n)]
        v = [0.0] * n
        for i, j, c in known:
            t = terms(i, j)
            for a in range(n):
                v[a] += t[a] * c[ch]
                for b in range(n):
                    m[a][b] += t[a] * t[b]
        coef.append(_solve(m, v))
    for i, j, _ in (unknown + known if r.get('all') else unknown):
        t = terms(i, j)
        rgb = [min(255, max(0, round(sum(x * y for x, y in zip(coef[ch], t))))) for ch in range(3)]
        px[i, j] = letter.nearest(pal, tuple(rgb) + (255,), limit)


def draw(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    for box in boxes:
        if spec.get('ground', 'transparent') != 'keep':
            letter.clear(out, pal, box, spec['ground'], limit, spec.get('pad', 0))
    for box in spec.get('clear', []):
        letter.clear(out, pal, box, spec.get('clear_ground', spec['ground']), limit)
    px = out.load()
    for r in spec.get('repaint', []):
        rx, ry, rw, rh = r['rect']
        keep = set(r.get('keep', []))
        idx = r.get('index', 'auto')
        if idx == 'auto':       # the rect's most common index
            from collections import Counter
            idx = Counter(px[i, j] for j in range(ry, ry + rh) for i in range(rx, rx + rw)).most_common(1)[0][0]
        for j in range(ry, ry + rh):
            for i in range(rx, rx + rw):
                if px[i, j] not in keep:
                    px[i, j] = idx
    for r in spec.get('inpaint', []):
        _inpaint(px, pal, r, limit)
    margin = spec.get('margin', _extent(spec))
    m = int(round(margin))
    cap = spec.get('cap') or 99
    for text, (x, y, w, h) in zip(texts, boxes):
        if text != '=':
            c = fit(text, spec, min(cap, h - 2 * m), w - 2 * m, h - 2 * m)
            if c is None:
                raise SystemExit(f'letter: {name}: {text!r} does not fit {w}x{h}')
            cap = c
    notes = [f'capitals {cap} px']
    cache = {}
    for text, (x, y, w, h) in zip(texts, boxes):
        if text == '=':
            continue
        mk, top, base, sq = _mask(text, spec['font'], cap, spec.get('squeeze', 0.72), w - 2 * m)
        if sq < 1:
            notes.append(f'{text!r}: squeezed to {sq:.0%}')
        W, H = w * S, h * S
        canvas = Image.new('L', (W, H), 0)
        if spec.get('align') == 'left':
            cx = m * S
        elif spec.get('align') == 'right':
            cx = W - m * S - mk.width
        else:
            cx = (W - mk.width) // 2
        if spec.get('valign') == 'top':
            cy = m * S - top
        else:
            cy = (H - cap * S) // 2 - top
        cy += round(spec.get('dy', 0) * S)
        canvas.paste(mk, (cx, cy))
        fill_y0, fill_y1 = (cy + top) / S, (cy + base) / S
        layers = []     # (L mask at S x, colour, alpha, span), outermost first
        for r in _rings(spec):
            lm = _grow(canvas, r['w'] * S)
            if r.get('blur'):
                lm = lm.filter(ImageFilter.GaussianBlur(r['blur'] * S / 2))
            if r.get('dx') or r.get('dy'):
                sh = Image.new('L', (W, H), 0)
                sh.paste(lm, (round(r.get('dx', 0) * S), round(r.get('dy', 0) * S)))
                lm = sh
            layers.append((lm, r['rgb'], r.get('a', 255), r.get('span', 'box')))
        layers.append((canvas, spec['fill'], 255, 'text'))
        small = [(lm.resize((w, h), Image.BOX).load(), c, a, sp) for lm, c, a, sp in layers]
        for j in range(h):
            tt = (j + 0.5 - fill_y0) / max(1e-6, fill_y1 - fill_y0)
            cols = [_colour_at(c, tt if sp == 'text' else j + 0.5, h if sp == 'box' else None)
                    for _, c, _, sp in small]
            for i in range(w):
                cov = [(lm[i, j], col, a) for (lm, _, a, _), col in zip(small, cols)]
                if not any(v for v, _, _ in cov):
                    continue
                rgba = pal[px[x + i, y + j]]
                for v, col, a in cov:
                    if v:
                        rgba = _over(rgba, col + (round(v * a / 255),))
                key = tuple(v // 2 * 2 for v in rgba)
                if key not in cache:
                    cache[key] = letter.nearest(pal, rgba, limit)
                px[x + i, y + j] = cache[key]
    return notes, cap
