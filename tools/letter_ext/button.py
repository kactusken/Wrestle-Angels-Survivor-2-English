"""SYS_G_BUTTON_0 (練習開始, dim and lit): a parametric redraw instead of office.styled.

office.styled learns each layer from the original by distance and direction and rebuilds the plate
from coarse colour bins: on the lit plate that gave blocky pink squares and a patch edge, round
the i dots star-shaped specks, and in the dim state a blotchy halo. Here every part is drawn from
a rule, with the colours read off the original:

  plate   shaded across, flat down its middle: each column's colour is the median of its plate
          pixels in 'profile_rows' (rows by the bevels the Japanese doesn't reach), smoothed
          over 'smooth' columns either side, and fills every row of 'flat' (snapped to the
          palette by error diffusion over the indices the original plate uses, so the gradient
          neither bands nor picks up a stray hue). The bevel rows stay as they are.
          Colours are matched premultiplied, alpha included (the dim plate is see-through at
          alpha ~150, only its lettering and glow are opaque); original pixels less opaque than 'keep_alpha_below'
          (the dim plate's see-through bevels and its left end: columns < 'keep_x_below', rows
          outside 'keep_rows') stay; elsewhere they were the Japanese glow and are redrawn. The text band can't be sampled: the dim state's glow is the same mauve as the
          plate's right end, so column medians there would turn the whole plate mauve.
  text    one mask (4x coverage, italic 'shear', squeezed to 'width' if needed) for both states,
          centred on 'centre'; per state:
          lit:  'glow' colours by distance round the letters ([[max d, rgb], ...]), then a
                'shadow' extrusion down-right ('depth' px) over it, then the fill: a vertical
                gradient 'fill_stops' over the capital height
          dim:  'glow' colours by distance, fill blended into the first glow colour by coverage

Spec keys (group level): 'state' lit|dim, 'region' [x0, y0, x1, y1] (inclusive, the plate's inside),
'flat' [y0, y1], 'plate' (Python expression of r, g, b: a plate pixel), 'smooth', 'baseline_y'.
Shared (top level): 'font', 'cap', 'shear', 'width', 'centre' (x).
"""
import math

from PIL import Image, ImageDraw, ImageFont

import letter

S = 4
BAYER = [[-0.25, 0.25], [0.5, 0.0]]


def text_cov(text, font_file, cap, shear, width):
    size = cap * S
    font = ImageFont.truetype(str(letter.FONT_DIR / font_file), round(size / 0.7))
    h = font.getbbox('H')
    font = ImageFont.truetype(str(letter.FONT_DIR / font_file), round(font.size * size / (h[3] - h[1])))
    l, t, r, b = font.getbbox(text)
    top = font.getbbox('H')[1]
    pad = 4 * S
    big = Image.new('L', (r - l + 2 * pad + round(shear * size), b - top + 2 * pad), 0)
    ImageDraw.Draw(big).text((-l + pad, -top + pad), text, font=font, fill=255)
    base = pad + size
    big = big.transform(big.size, Image.AFFINE, (1, shear, -shear * base, 0, 1, 0), Image.BICUBIC)
    ink = big.getbbox()
    big = big.crop((ink[0], 0, ink[2], big.height))
    sq = min(1.0, width * S / big.width)
    nw = round(big.width * sq / S)
    small = big.resize((nw, big.height // S), Image.BOX)
    px = small.load()
    cov = {(i, j): px[i, j] / 255 for j in range(small.height) for i in range(nw) if px[i, j]}
    return cov, nw, pad // S, sq          # pad // S = the capital top row


def plate_profile(src, region, flat, test, smooth, profile_rows):
    x0, y0, x1, y1 = region
    f0, f1 = flat

    def smooth_row(vals):
        xs = sorted(vals)
        if not xs:
            return None
        full = {}
        for x in range(x0, x1 + 1):
            if x in vals:
                full[x] = vals[x]
            else:
                lo = max((q for q in xs if q < x), default=None)
                hi = min((q for q in xs if q > x), default=None)
                if lo is None or hi is None:
                    full[x] = vals[lo if hi is None else hi]
                else:
                    t = (x - lo) / (hi - lo)
                    full[x] = tuple(vals[lo][k] + (vals[hi][k] - vals[lo][k]) * t for k in range(4))
        out = {}
        for x in range(x0, x1 + 1):
            win = [full[q] for q in range(x - smooth, x + smooth + 1) if q in full]
            out[x] = tuple(sum(c[k] for c in win) / len(win) for k in range(4))
        return out

    pooled = {}
    for x in range(x0, x1 + 1):
        col = sorted((src[x, y] for y in profile_rows if test(*src[x, y][:3])), key=lambda c: sum(c[:3]))
        if col:
            pooled[x] = col[len(col) // 2]
    base = smooth_row(pooled)
    rows = {y: base for y in range(f0, f1 + 1)}
    return rows


def draw(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    src = im.convert('RGBA').load()
    o = out.load()
    cache = {}

    rx0, ry0, rx1, ry1 = spec['region']
    allowed = sorted({im.getpixel((x, y)) for y in range(ry0, ry1 + 1) for x in range(rx0, rx1 + 1)
                      if pal[im.getpixel((x, y))][3] == 255})

    def idx(rgb):
        # the nearest of the opaque colours this state of the original uses: no stray hue
        rgb = tuple(max(0, min(255, round(v))) for v in rgb)
        if rgb not in cache:
            cache[rgb] = min(allowed, key=lambda i: sum((pal[i][k] - rgb[k]) ** 2 for k in range(3)))
        return cache[rgb]

    x0, y0, x1, y1 = spec['region']
    test = eval('lambda r, g, b: ' + spec['plate'])
    rows = plate_profile(src, spec['region'], spec['flat'], test, spec.get('smooth', 8), spec['profile_rows'])
    # error diffusion (Floyd-Steinberg, serpentine) over the colours the original plate uses, so
    # the gradient doesn't band and no stray hue comes in
    x_0, y_0, x_1, y_1 = spec['region']
    used = sorted({im.getpixel((x, y)) for y in range(y_0, y_1 + 1) for x in range(x_0, x_1 + 1)
                   if test(*src[x, y][:3])})
    pm = {i: [pal[i][k] * pal[i][3] / 255 for k in range(3)] + [pal[i][3]] for i in used}
    keep_a = spec.get('keep_alpha_below', 0)    # see-through plate pixels (the dim bevels): kept
    keep_x = spec.get('keep_x_below', 9999)     # ... in the left columns and outside keep_rows only
    keep_rows = spec.get('keep_rows', [9999, -1])
    err = {}
    for n, (y, prof) in enumerate(sorted(rows.items())):
        xs_ = range(x0, x1 + 1) if n % 2 == 0 else range(x1, x0 - 1, -1)
        step = 1 if n % 2 == 0 else -1
        for x in xs_:
            if src[x, y][3] < keep_a and (x < keep_x or not keep_rows[0] < y < keep_rows[1]):
                continue
            # premultiplied: the dim plate is see-through (alpha ~150), its glow opaque
            a = prof[x][3] / 255
            want = [prof[x][k] * a + err.get((x, y), (0, 0, 0, 0))[k] for k in range(3)] + \
                   [prof[x][3] + err.get((x, y), (0, 0, 0, 0))[3]]
            best = min(used, key=lambda i: sum((pm[i][k] - want[k]) ** 2 for k in range(4)))
            o[x, y] = best
            e = [want[k] - pm[best][k] for k in range(4)]
            for (dx, dy), f in (((step, 0), 7 / 16), ((-step, 1), 3 / 16), ((0, 1), 5 / 16), ((step, 1), 1 / 16)):
                q = (x + dx, y + dy)
                if x0 <= q[0] <= x1 and q[1] in rows:
                    old_e = err.get(q, (0, 0, 0, 0))
                    err[q] = tuple(old_e[k] + e[k] * f for k in range(4))
    # the text
    cov, w, ctop, sq = text_cov(texts[0], spec['font'], spec['cap'], spec.get('shear', 0), spec['width'])
    ox = round(spec['centre'] - w / 2)
    oy = spec['cap_top'] - ctop
    fill = {(ox + i, oy + j): c for (i, j), c in cov.items()}
    solid = {p for p, c in fill.items() if c >= 0.5}
    glow = spec['glow']
    reach = glow[-1][0]
    r = int(math.ceil(reach)) + 1
    offs = sorted(((dx, dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1)), key=lambda q: math.hypot(*q))
    depth = spec.get('depth', 0)
    shadow = set()
    for k in range(1, depth + 1):
        for dx, dy in ((k, k), (k, k - 1), (k - 1, k)):
            shadow |= {(x + dx, y + dy) for x, y in solid}
    shadow -= solid
    xs = [p[0] for p in solid]
    ys = [p[1] for p in solid]
    cap = spec['cap']
    stops = spec.get('fill_stops')
    for y in range(min(ys) - r, max(ys) + r + depth + 1):
        for x in range(min(xs) - r, max(xs) + r + depth + 1):
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            ground = pal[o[x, y]][:3]
            if spec['state'] == 'dim':
                c = fill.get((x, y), 0)
                if c >= 0.98:
                    o[x, y] = idx(spec['fill_rgb'])
                    continue
                d = next((math.hypot(dx, dy) for dx, dy in offs if (x + dx, y + dy) in solid), None)
                g = None
                if d is not None:
                    for top, rgb in glow:
                        if d <= top:
                            g = rgb
                            break
                    if g is None and d <= reach + 1:      # soft outer edge: half way to the plate
                        g = tuple((a + b) / 2 for a, b in zip(glow[-1][1], ground))
                if c > 0.02:
                    base = g or glow[0][1]
                    o[x, y] = idx(tuple(base[k] + (spec['fill_rgb'][k] - base[k]) * c for k in range(3)))
                elif g is not None:
                    o[x, y] = idx(g)
                continue
            # lit
            if (x, y) in solid:
                t = (y - spec['cap_top']) / max(1, cap - 1)
                o[x, y] = idx(letter_stop(stops, t))
                continue
            if (x, y) in shadow:
                k = min(math.hypot(x - a, y - b) for a, b in solid if abs(x - a) <= depth and abs(y - b) <= depth)
                o[x, y] = idx(spec['shadow'][0] if k <= 1.0 else spec['shadow'][1])
                continue
            d = next((math.hypot(dx, dy) for dx, dy in offs if (x + dx, y + dy) in solid), None)
            if d is None:
                continue
            for top, rgb in glow:
                if d <= top:
                    o[x, y] = idx(rgb)
                    break
            else:
                if d <= reach + 1:
                    o[x, y] = idx(tuple((a + b) / 2 for a, b in zip(glow[-1][1], ground)))
    notes = [f'capitals {cap} px'] + ([f'{texts[0]!r}: squeezed to {sq:.0%}'] if sq < 1 else [])
    return notes, cap


def letter_stop(stops, t):
    t = min(1.0, max(0.0, t))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if p0 <= t <= p1:
            f = (t - p0) / max(1e-9, p1 - p0)
            return tuple(c0[k] + (c1[k] - c0[k]) * f for k in range(3))
    return stops[-1][1]
