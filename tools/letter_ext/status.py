"""Batch 'status': labels on bevelled panels (status screens).

draw() is a letter.py drawer ("draw": "status.draw"). It is letter.draw_group() with one change:
the ground under the old label is rebuilt by `patches` instead of by clearing each box, because the
Japanese often runs into the panel's bevel, where row interpolation would smear the bevel across
the label. Panels are flat along a row (only the ends are shaded), and a screen's panels share one
piece of art, so the ground can be copied from a clean column or from a clean twin panel.

Spec keys, besides letter.py's (english, boxes, fill, font, cap, reach, align, groups, same_size):
  patches   [[x, y, w, h, mode, a, b], ...] applied in order to the output before lettering:
              "col"    every column of the area = the column at x = a, shifted b rows
              "copy"   the area = the output at (x + a, y + b)  (a clean twin, possibly patched)
              "fill"   the area = palette index a, or the index at pixel a = [x, y]
              "heal"   [x, y, w, h, "heal", [y0, y1], amax | {"sat": n, "tol": n}]: the lettering's pixels
                       become panel (see heal())
              "inpaint" [x, y, w, h, "inpaint", {"sat", "lmin", "lmax", "bmin", "expr"}]: pixels that aren't
                       panel (see panel_test()) are filled smoothly from the panel around them
                       (a Laplace fill), for vignetted panels and tabs
              "interp" letter.py's row interpolation;  "transparent": cleared
  ground    learnt style stops at the transparent index if "transparent" (as in letter.py)
  align     center (default) | left | right;  dy: nudge the text down (px)
Boxes are where the English goes (including its outline); they are not cleared.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import letter  # noqa: E402



def patch(out, pal, patches):
    px = out.load()
    for p in patches:
        x, y, w, h, mode = p[:5]
        if mode == 'col':
            a, b = p[5], p[6] if len(p) > 6 else 0
            col = [px[a, j + b] for j in range(y, y + h)]
            for j in range(h):
                for i in range(x, x + w):
                    px[i, y + j] = col[j]
        elif mode == 'copy':
            a, b = p[5], p[6]
            src = [[px[i + a, j + b] for i in range(x, x + w)] for j in range(y, y + h)]
            for j in range(h):
                for i in range(w):
                    px[x + i, y + j] = src[j][i]
        elif mode == 'fill':
            if isinstance(p[5], list):      # [x, y]: the index at that pixel
                p = p[:5] + [px[p[5][0], p[5][1]]]
            for j in range(y, y + h):
                for i in range(x, x + w):
                    px[i, j] = p[5]
        elif mode == 'inpaint':
            inpaint(out, pal, (x, y, w, h), p[5] if len(p) > 5 else {})
        elif mode == 'heal':
            heal(out, pal, (x, y, w, h), p[5] if len(p) > 5 else None, p[6] if len(p) > 6 else 250)
        elif mode in ('interp', 'transparent'):
            letter.clear(out, pal, (x, y, w, h), 'interpolate' if mode == 'interp' else 'transparent', len(pal))
        else:
            raise SystemExit(f'status: unknown patch mode {mode!r}')


def panel_test(pal, opts):
    """Is a palette index panel (not lettering)? Colourful (max - min of RGB >= sat), brightness
    (sum of RGB) within [lmin, lmax], blue - red >= bmin."""
    sat, lmin, lmax, bmin = (opts.get('sat', 0), opts.get('lmin', 0), opts.get('lmax', 765),
                             opts.get('bmin', -999))

    expr = opts.get('expr')       # or a Python expression in r, g, b: True for panel

    def test(v):
        r, g, b = pal[v][:3]
        if expr:
            return eval(expr, {}, {'r': r, 'g': g, 'b': b})
        return max(r, g, b) - min(r, g, b) >= sat and lmin <= r + g + b <= lmax and b - r >= bmin
    return test


def inpaint(out, pal, rect, opts, iterations=400):
    x, y, w, h = rect
    px = out.load()
    test = panel_test(pal, opts)
    grow = opts.get('grow', 0)      # also treat panel pixels this close to lettering as unknown
    bad = {(i, j) for j in range(y, y + h) for i in range(x, x + w) if not test(px[i, j])}
    for _ in range(grow):
        bad |= {(i + di, j + dj) for i, j in bad for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if x <= i + di < x + w and y <= j + dj < y + h}
    val = {}
    for j in range(y - 1, y + h + 1):
        for i in range(x - 1, x + w + 1):
            inside = x <= i < x + w and y <= j < y + h
            if 0 <= i < out.width and 0 <= j < out.height and (i, j) not in bad and (inside or test(px[i, j])):
                val[i, j] = list(pal[px[i, j]][:4])
    # start from the mean of the known pixels in the row
    for j in range(y, y + h):
        row = [val[i, j] for i in range(x - 1, x + w + 1) if (i, j) in val]
        mean = [sum(c[k] for c in row) / len(row) for k in range(4)] if row else [0, 0, 0, 255]
        for i in range(x, x + w):
            if (i, j) in bad:
                val[i, j] = list(mean)
    order = sorted(bad, key=lambda t: (t[1], t[0]))
    for _ in range(iterations):
        for i, j in order:
            nb = [val[k] for k in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)) if k in val]
            if nb:
                val[i, j] = [sum(c[k] for c in nb) / len(nb) for k in range(4)]
    cache = {}
    for i, j in bad:
        rgba = tuple(max(0, min(255, round(v))) for v in val[i, j])
        if rgba not in cache:
            cache[rgba] = letter.nearest(pal, rgba, len(pal))
        px[i, j] = cache[rgba]


def heal(out, pal, rect, mid, amax, tol=40):
    """Rebuild a panel under grey lettering and its shadow. The panel is modelled as a colour per
    column (from the column's panel pixels in the rows `mid` [y0, y1], where the panel
    is flat down each column; columns without one are blended from their neighbours) plus a colour
    offset per row (the median difference of the row's panel pixels from that, for the shaded top
    and bottom rows). Panel pixels (alpha < amax, or with amax {"sat": n} colourful ones) within
    `tol` (sum of RGB differences) of the model stay, so dithering survives; every other pixel
    becomes the model's colour."""
    x, y, w, h = rect
    px = out.load()
    src = {(i, j): px[i, j] for j in range(y, y + h) for i in range(x, x + w)}
    # amax {"sat": n, "lmax": n, "bmin": n, "keep": n, "tol": n}: panel = colourful (max - min of RGB >= sat)
    # and not bright (sum of RGB <= lmax)
    if isinstance(amax, dict):
        sat, lmax, keep = amax.get('sat', 0), amax.get('lmax', 765), amax.get('keep', 999)
        tol = amax.get('tol', tol)
        bmin = amax.get('bmin', -999)     # blue - red >= bmin: a blue panel under a dark halo
        ok = {k for k, v in src.items() if max(pal[v][:3]) - min(pal[v][:3]) >= sat and sum(pal[v][:3]) <= lmax
              and pal[v][2] - pal[v][0] >= bmin}
        # strongly blue pixels (blue - red >= keep) are glow, never lettering: always kept
        kept = {k for k, v in src.items() if pal[v][2] - pal[v][0] >= keep}
        ok -= kept
    else:
        kept = set()
        ok = {k for k, v in src.items() if pal[v][3] < amax}
    y0, y1 = mid if mid else (y, y + h - 1)
    # a column's colour: its panel pixels' upper quartile by brightness (shadows are darker),
    # then a running median across columns (window 7) to drop columns the lettering filled
    raw = {}
    for i in range(x, x + w):
        got = sorted((pal[src[i, j]] for j in range(y0, y1 + 1) if (i, j) in ok), key=lambda p: sum(p[:3]))
        if len(got) >= 2:
            raw[i] = got[(3 * len(got)) // 4]
    cols = {}
    for i in raw:
        near = [raw[k] for k in range(i - 3, i + 4) if k in raw]
        cols[i] = tuple(sorted(p[c] for p in near)[len(near) // 2] for c in range(4))
    known = sorted(cols)
    cache = {}

    def snap(rgba):
        rgba = tuple(max(0, min(255, round(v))) for v in rgba)
        if rgba not in cache:
            cache[rgba] = letter.nearest(pal, rgba, len(pal))
        return cache[rgba]

    def blend(a, b, t):
        return tuple(a[k] + (b[k] - a[k]) * t for k in range(4))

    def col(i):
        if i in cols:
            return cols[i]
        lo = [k for k in known if k < i]
        hi = [k for k in known if k > i]
        if lo and hi:
            return blend(cols[lo[-1]], cols[hi[0]], (i - lo[-1]) / (hi[0] - lo[-1]))
        return cols[lo[-1] if lo else hi[0]]

    def far(a, b):
        return sum(abs(a[k] - b[k]) for k in range(3)) > tol

    for j in range(y, y + h):
        offset = (0, 0, 0, 0)
        if not y0 <= j <= y1:
            diffs = [tuple(pal[src[i, j]][k] - col(i)[k] for k in range(4)) for i in range(x, x + w) if (i, j) in ok]
            if diffs:
                offset = tuple(sorted(d[k] for d in diffs)[len(diffs) // 2] for k in range(4))
        for i in range(x, x + w):
            want = tuple(col(i)[k] + offset[k] for k in range(4))
            if (i, j) in kept or ((i, j) in ok and not far(pal[src[i, j]], want)):
                continue
            px[i, j] = snap(want)


def draw(name, im, out, pal, texts, boxes, spec):
    fills = set().union(*(letter.fill_indices(im, pal, box, spec) for box in boxes))
    style, fill, ink_h = letter.learn_style(im, pal, boxes, fills, spec.get('ground', 'interpolate'),
                                            spec.get('reach', 8))
    if 'fill_index' in spec:
        fill = spec['fill_index']
    patch(out, pal, spec.get('patches', []))
    reach = max(style) * letter.STEP if style else 0
    r = int(reach)
    inner = [(int(w - 2 * reach), int(h - 2 * reach)) for _, _, w, h in boxes]
    cap = spec.get('cap') or round(ink_h * 0.8)
    for text, (iw, ih) in zip(texts, inner):
        if text != '=':
            got = letter.text_mask(text, spec['font'], min(cap, ih), iw, ih, slack=r)
            if got is None:
                raise SystemExit(f'status: {name}: {text!r} does not fit {iw}x{ih}')
            cap = min(cap, got[1])
    notes = []
    px = out.load()
    dy = spec.get('dy', 0)
    for box, text, (iw, ih) in zip(boxes, texts, inner):
        if text == '=':
            continue
        x, y, w, h = box
        mask, size, squeeze = letter.text_mask(text, spec['font'], cap, iw, ih, spec.get('align', 'center'), r)
        if squeeze < 1:
            notes.append(f'{text!r}: squeezed to {squeeze:.0%}')
        if spec.get('align') == 'right':     # push the text against the box's right edge
            last = max((i for row in mask for i, v in enumerate(row) if v), default=iw - 1)
            mask = [[False] * (iw - 1 - last) + row[:last + 1] for row in mask]
        full = [[False] * w for _ in range(h)]
        for j in range(len(mask)):
            for i in range(iw):
                if mask[j][i] and 0 <= j + r + dy < h:
                    full[j + r + dy][i + r] = True
        dist = letter.distances(full, w, h)
        for j in range(h):
            for i in range(w):
                if full[j][i]:
                    px[x + i, y + j] = fill
                else:
                    k = round(dist[j][i] / letter.STEP)
                    if k in style:
                        px[x + i, y + j] = style[k]
    notes.insert(0, f'capitals {cap} px')
    return notes, cap


def draw_icons(name, im, out, pal, texts, boxes, spec):
    """Icons: a letter in a shaded oval (SYS_COM_P2_0, 4-bit). The exported CLUT looks wrong, but
    the indices run as a brightness ramp (1 dark .. 15 light), so this works on index numbers.
    Each box is an icon's cell. Inside the oval (each row's run of non-transparent pixels, less
    `margin` px at both ends) the background is rebuilt by a Laplace fill from the oval's edge; the
    kanji is whatever differs from that by `contrast` or more. The English is drawn in the kanji's
    main index with a 4-neighbour ring in its outline index (the most common kanji index on the
    other side of the background). spec 'overrides': {english: {fill, ring, bg}} for icons where
    that guess is wrong (bg: a flat background index)."""
    from collections import Counter
    margin, contrast, cap = spec.get('margin', 2), spec.get('contrast', 3), spec.get('cap', 12)
    clear_idx = set(spec.get('transparent', [0, 8]))
    src, px = im.load(), out.load()
    notes = []
    for text, (x, y, w, h) in zip(texts, boxes):
        if text == '=':
            continue
        region = set()
        for j in range(y + spec.get('top', 2), y + h - spec.get('bottom', 2)):
            run = [i for i in range(x, x + w) if src[i, j] not in clear_idx]
            if run:
                region |= {(i, j) for i in range(run[0] + margin, run[-1] - margin + 1)}
        val = {}
        for i, j in region:
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (i + di, j + dj)
                if q not in region and x <= q[0] < x + w and y <= q[1] < y + h and src[q] not in clear_idx:
                    val[q] = float(src[q])
        unknown = sorted(region, key=lambda t: (t[1], t[0]))
        mean = sum(val.values()) / max(1, len(val))
        for p in unknown:
            val[p] = mean
        for _ in range(300):
            for i, j in unknown:
                nb = [val[q] for q in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)) if q in val]
                val[i, j] = sum(nb) / len(nb)
        diff = {p: src[p] - val[p] for p in region}
        kanji = [p for p in region if abs(diff[p]) >= contrast]
        up = [p for p in kanji if diff[p] > 0]
        down = [p for p in kanji if diff[p] < 0]
        main, other = (up, down) if len(up) >= len(down) else (down, up)
        fill = Counter(src[p] for p in main).most_common(1)[0][0]
        ring = Counter(src[p] for p in other).most_common(1)[0][0] if other else (1 if fill > 8 else 15)
        o = spec.get('overrides', {}).get(text, {})
        fill, ring = o.get('fill', fill), o.get('ring', ring)
        if 'bg' in o:
            val.update({p: o['bg'] for p in region})
        for p in region:
            px[p] = max(1, min(15, round(val[p]))) if round(val[p]) not in clear_idx else round(val[p]) + 1
        got = letter.text_mask(text, spec['font'], cap, spec.get('tw', 34), spec.get('th', 18), slack=4)
        if got is None:
            raise SystemExit(f'status: {name}: {text!r} does not fit')
        mask, size, squeeze = got
        rows = [j for j, row in enumerate(mask) if any(row)]
        cols = [i for row in mask for i, v in enumerate(row) if v]
        mw, top, bot = max(cols) + 1 - min(cols), rows[0], rows[-1]
        ys = [j for _, j in kanji]
        cx = x + w // 2 + spec.get('dx', 0)
        cy = (min(ys) + max(ys) + 1) // 2 if ys else y + h // 2
        ox, oy = cx - mw // 2 - min(cols), cy - (top + bot + 1) // 2
        on = {(ox + i, oy + j) for j, row in enumerate(mask) for i, v in enumerate(row) if v}
        for p in on:
            px[p] = fill
        for i, j in on:
            for q in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if q not in on:
                    px[q] = ring
        notes.append(f'{text!r}: {size} px, fill {fill}, ring {ring}' + (f', squeezed to {squeeze:.0%}' if squeeze < 1 else ''))
    return notes, cap
