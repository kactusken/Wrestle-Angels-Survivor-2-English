"""Lettering by palette index with coverage antialiasing (spec "draw": "plates.draw"), for small
4bpp/8bpp labels where letter.py's learnt style comes out ragged: SYS_BEL_4's cut-out list headers,
SYS_BEL_0's button hints, and the status screens' labels.

Each label is drawn into its cell (the box, or `cell` [w, h] at box - `inset` [dx, dy]):

  1. ground, by `plate`:
       'template'  rebuild the plate: the transparent ring copied from the `template` cell of the
                   original (`ring_indices`), the inside an elliptic gradient (`grad`:
                   [[index, half-width, half-height], ... innermost first], else `grad_outer`)
       'rows'      the old letters' pixels (`glyph` indices, inside the cell) take the most common
                   index of their row among `ground_ok` (`ground_default` if none)
       'clear'     the `clear` [x, y, w, h] areas (absolute) are set to `ground_index`
       'keep'      nothing (the box is clean already)
  2. the English at `cap` px (one size for the whole group, the largest every label fits at),
     squeezed down to `squeeze_min` before the size drops, `maxw` px wide at most (default: cell
     width - 2 * `margin`), capitals' top at row `text_top` of the cell (default: centred);
     `dx`/`dy` shift; `align` center | left (`left` px from the cell's edge)
  `patches` (before the labels): ['rect', x, y, w, h, index], ['tile', x, y, w, h, source x,
     period] (columns of the original repeated), ['copy', x, y, w, h, dx, dy] (from the original).
     `status_patches`: status.py's [x, y, w, h, mode, ...] patches, applied first.
  3. colours: `ramp` [[min coverage, index], ...] (highest first; coverage of the pixel by the 4x
     letters) - else `fill_index` for coverage >= 0.5 and `aa` for 0.25..0.5 next to the fill;
     then `ring` [[max distance from the fill, index], ...] (outline, halo), then the ground.
     `ring_on`: only ground pixels with these indices take the ring.

Spec keys besides: font, cap, squeeze_min (0.84).
"""
import math
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

import letter

SS = 4


def coverage(text, font_file, cap, maxw, squeeze_min, tracking=0):
    """(coverage rows [0..1], row of the capitals' top, squeeze) or None if it doesn't fit."""
    path = str(letter.FONT_DIR / font_file)
    probe = ImageFont.truetype(path, 400)
    hb = probe.getbbox('H')
    font = ImageFont.truetype(path, round(400 * cap * SS / (hb[3] - hb[1])))
    top = font.getbbox('H')[1]
    widths = [font.getlength(ch) for ch in text]
    l, t, r, b = font.getbbox(text)
    tw = r - l + tracking * SS * (len(text) - 1)
    squeeze = min(1.0, maxw * SS / tw)
    if squeeze < squeeze_min:
        return None
    big = Image.new('L', (tw + 4 * SS, (cap + 8) * SS), 0)
    d = ImageDraw.Draw(big)
    if tracking:
        x = -l + SS
        for ch, wd in zip(text, widths):
            d.text((x, -top + SS), ch, font=font, fill=255)
            x += wd + tracking * SS
    else:
        d.text((-l + SS, -top + SS), text, font=font, fill=255)
    while True:
        nw = max(1, round(big.width * squeeze / SS))
        small = big.resize((nw, big.height // SS), Image.BOX)
        ink = small.point(lambda v: 255 if v > 25 else 0).getbbox()
        small = small.crop((ink[0], 0, ink[2], small.height))
        if small.width <= maxw:
            break
        squeeze -= 0.01
        if squeeze < squeeze_min:
            return None
    px = small.load()
    return [[px[i, j] / 255 for i in range(small.width)] for j in range(small.height)], 1, squeeze


def gradient_index(i, j, w, h, grad, outer):
    cx, cy = (w - 1) / 2, (h - 1) / 2
    for idx, a, b in grad:
        if ((i - cx) / a) ** 2 + ((j - cy) / b) ** 2 < 1:
            return idx
    return outer


def cell_of(box, spec):
    bx, by, bw, bh = box
    if 'cell' in spec:
        dx, dy = spec.get('inset', [0, 0])
        return bx - dx, by - dy, spec['cell'][0], spec['cell'][1]
    return bx, by, bw, bh


def maxw_of(spec, cw):
    return spec.get('maxw') or cw - 2 * spec.get('margin', 2)


def fit(texts, boxes, spec):
    cap = spec['cap']
    while cap > 5:
        if all(t == '=' or coverage(t, spec['font'], cap, maxw_of(spec, cell_of(b, spec)[2]),
                                    spec.get('squeeze_min', 0.84), spec.get('tracking', 0))
               for t, b in zip(texts, boxes)):
            return cap
        cap -= 1
    raise SystemExit('plates: labels do not fit')


def ground(src, px, cell, spec):
    """{(i, j): ground index} for the cell, after rebuilding it."""
    cx, cy, cw, ch = cell
    mode = spec.get('plate', 'keep')
    out = {}
    if mode == 'template':
        tx, ty = spec['template']
        ring = set(spec.get('ring_indices', [0, 9, 10, 11]))
        for j in range(ch):
            for i in range(cw):
                t = src[tx + i, ty + j]
                if t in ring and not (2 <= j < ch - 2 and 4 <= i < cw - 4):
                    px[cx + i, cy + j] = t
                else:
                    px[cx + i, cy + j] = out[(i, j)] = gradient_index(i, j, cw, ch, spec['grad'],
                                                                      spec['grad_outer'])
        return out
    if mode == 'rows':
        glyph, ok = set(spec['glyph']), spec['ground_ok']
        for j in range(ch):
            votes = Counter(src[cx + i, cy + j] for i in range(cw) if src[cx + i, cy + j] in ok)
            g = votes.most_common(1)[0][0] if votes else spec.get('ground_default')
            for i in range(cw):
                if src[cx + i, cy + j] in glyph and g is not None:
                    px[cx + i, cy + j] = g
    elif mode == 'clear':
        for x, y, w, h in spec['clear']:
            for j in range(y, y + h):
                for i in range(x, x + w):
                    px[i, j] = spec['ground_index']
    for j in range(ch):
        for i in range(cw):
            out[(i, j)] = px[cx + i, cy + j]
    return out


def draw(name, im, out, pal, texts, boxes, spec):
    cap = spec.get('cap') if spec.get('_fixed') else fit(texts, boxes, spec)
    src, px = im.load(), out.load()
    notes = []
    if spec.get('status_patches'):     # status.py's patch list (x, y, w, h, mode, ...)
        status = letter.drawer({'draw': 'status.draw'}).__globals__
        status['patch'](out, pal, spec['status_patches'])
        px = out.load()
    for patch in spec.get('patches', []):
        kind, x0, y0, w, h, *arg = patch
        for j in range(y0, y0 + h):
            for i in range(x0, x0 + w):
                if kind == 'rect':            # ['rect', x, y, w, h, index]
                    px[i, j] = arg[0]
                elif kind == 'tile':          # ['tile', x, y, w, h, source x, period]: repeat
                    px[i, j] = src[arg[0] + (i - arg[0]) % arg[1], j]   # columns of the original
                elif kind == 'copy':          # ['copy', x, y, w, h, dx, dy]: from the original
                    px[i, j] = src[i + arg[0], j + arg[1]]
    if spec.get('plate') == 'clear':
        ground(src, px, (0, 0, 0, 0), spec)
        spec = spec | {'plate': 'keep'}
    for text, box in zip(texts, boxes):
        if text == '=':
            continue
        cell = cx, cy, cw, ch = cell_of(box, spec)
        gr = ground(src, px, cell, spec)
        got = coverage(text, spec['font'], cap, maxw_of(spec, cw), spec.get('squeeze_min', 0.84),
                       spec.get('tracking', 0))
        if got is None:
            raise SystemExit(f'plates: {name}: {text!r} does not fit at {cap} px')
        rows, top, squeeze = got
        if squeeze < 1:
            notes.append(f'{text!r}: squeezed to {squeeze:.0%}')
        tw, th = len(rows[0]), len(rows)
        if spec.get('align') == 'left':
            ox = spec.get('left', 0)
        else:
            ox = (cw - tw) // 2
        ox += spec.get('dx', 0)
        oy = (spec['text_top'] if 'text_top' in spec else (ch - cap) // 2) - top + spec.get('dy', 0)
        cov = {(ox + i, oy + j): rows[j][i] for j in range(th) for i in range(tw) if rows[j][i] > 0}
        fills = [p for p, c in cov.items() if c >= 0.5]
        ring = spec.get('ring', [])
        reach = max([r for r, _ in ring] + [1])
        R = math.ceil(reach)
        dist = {}
        for fx, fy in fills:
            for yy in range(fy - R, fy + R + 1):
                for xx in range(fx - R, fx + R + 1):
                    d = math.hypot(xx - fx, yy - fy)
                    if d < dist.get((xx, yy), 99):
                        dist[(xx, yy)] = d
        ramp = spec.get('ramp')
        for p in set(dist) | set(cov):
            i, j = p
            if p not in gr:
                continue
            c, d = cov.get(p, 0), dist.get(p, 99)
            idx = None
            if ramp:
                idx = next((k for m, k in ramp if c >= m), None)
            elif d == 0:
                idx = spec['fill_index']
            elif d <= 1 and c >= spec.get('aa_min', 0.25) and 'aa' in spec:
                idx = spec['aa']
            if idx is None and d > 0:
                if 'ring_on' in spec and gr[p] not in spec['ring_on']:
                    continue
                idx = next((k for r, k in ring if d <= r), None)
            if idx is not None:
                px[cx + i, cy + j] = idx
    notes.insert(0, f'capitals {cap} px')
    return notes, cap


def laplace(val, unknown, iterations=300):
    order = sorted(unknown, key=lambda t: (t[1], t[0]))
    for _ in range(iterations):
        for i, j in order:
            nb = [val[q] for q in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)) if q in val]
            if nb:
                val[i, j] = sum(nb) / len(nb)


def draw_icons(name, im, out, pal, texts, boxes, spec):
    """status.draw_icons() (SYS_COM_P2_0: a letter in a shaded oval, indices = a brightness ramp)
    with a better ground and lettering:
      - the oval is rebuilt only under the kanji grown by `grow` px (default 1); the rest of the
        oval's own shading stays as the original drew it, and is what the fill grows from;
      - the English is coverage-antialiased: `ramp` [[min coverage, 'fill' | 'mid' | index], ...]
        ('mid' is the index halfway between fill and ring), then an outline of `ring_reach` px in the
        ring index.
    `kanji_hi` / `kanji_lo`: the old letters are the region's indices >= hi or <= lo (else: what
    differs from a fill of the oval by `contrast`).
    `fill` / `ring`: one index for every icon (else learnt per icon); `overrides` as in
    status.draw_icons() (fill, ring, bg) win over both."""
    from collections import Counter
    margin, contrast, cap = spec.get('margin', 1), spec.get('contrast', 3), spec.get('cap', 11)
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
        edge = {}
        for i, j in region:
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (i + di, j + dj)
                if q not in region and x <= q[0] < x + w and y <= q[1] < y + h and src[q] not in clear_idx:
                    edge[q] = float(src[q])
        val = dict(edge)
        mean = sum(val.values()) / max(1, len(val))
        val.update({p: mean for p in region})
        laplace(val, region)
        diff = {p: src[p] - val[p] for p in region}
        kanji = {p for p in region if abs(diff[p]) >= contrast}
        up = [p for p in kanji if diff[p] > 0]
        down = [p for p in kanji if diff[p] < 0]
        main, other = (up, down) if len(up) >= len(down) else (down, up)
        fill = Counter(src[p] for p in main).most_common(1)[0][0]
        ring = Counter(src[p] for p in other).most_common(1)[0][0] if other else (1 if fill > 8 else 15)
        o = spec.get('overrides', {}).get(text, {})
        fill, ring = o.get('fill', spec.get('fill', fill)), o.get('ring', spec.get('ring', ring))
        # second pass: keep the oval's own pixels, fill only the kanji grown by `grow`
        if 'kanji_hi' in spec:        # by index: the bright letters and their dark outline
            kanji = {p for p in region if src[p] >= spec['kanji_hi'] or src[p] <= spec['kanji_lo']}
        unknown = set(kanji)
        for _ in range(spec.get('grow', 1)):
            unknown |= {(i + di, j + dj) for i, j in unknown for di in (-1, 0, 1) for dj in (-1, 0, 1)}
        unknown &= region
        val = dict(edge)
        val.update({p: float(src[p]) for p in region - unknown})
        val.update({p: mean for p in unknown})
        laplace(val, unknown)
        if 'bg' in o:
            val.update({p: o['bg'] for p in region})
        for p in region:
            v = max(1, min(15, round(val[p])))
            px[p] = v + 1 if v in clear_idx else v
        got = coverage(text, spec['font'], cap, spec.get('tw', 34), spec.get('squeeze_min', 0.8))
        if got is None:
            raise SystemExit(f'plates: {name}: {text!r} does not fit')
        rows, top, squeeze = got
        tw = len(rows[0])
        ys = [j for _, j in kanji]
        cx = x + w // 2 + spec.get('dx', 0)
        cyy = (min(ys) + max(ys) + 1) / 2 if ys else y + h / 2
        ox = cx - tw // 2
        oy = round(cyy - cap / 2) - top + spec.get('dy', 0)
        cov = {(ox + i, oy + j): c for j, row in enumerate(rows) for i, c in enumerate(row) if c > 0}
        fills = {p for p, c in cov.items() if c >= 0.5}
        mid = round((fill + ring) / 2)
        if mid in clear_idx:
            mid += 1 if fill > ring else -1
        ramp = [[m, fill if k == 'fill' else mid if k == 'mid' else k]
                for m, k in spec.get('ramp', [[0.5, 'fill'], [0.3, 'mid']])]
        rr = spec.get('ring_reach', 1.45)
        R = math.ceil(rr)
        near = set()
        for fx, fy in fills:
            for dy in range(-R, R + 1):
                for dx in range(-R, R + 1):
                    if math.hypot(dx, dy) <= rr:
                        near.add((fx + dx, fy + dy))
        for p in near | set(cov):
            if not (x <= p[0] < x + w and y <= p[1] < y + h):
                continue
            k = next((k for m, k in ramp if cov.get(p, 0) >= m), None)
            px[p] = k if k is not None else ring
        notes.append(f'{text!r}: {cap} px, fill {fill}, ring {ring}' + (f', squeezed to {squeeze:.0%}' if squeeze < 1 else ''))
    return notes, cap
