"""Drawing for the 'office' batch (gym and office menus, gym banners).

panel(): letter.draw_group on a dithered panel (SYS_GYM_M_0). 'interpolate' snaps each cleared row
to one flat index and streaks where its side samples touch the old outline; here the cleared area
is rebuilt from the panel's own pattern instead. Spec key 'restore':
  {'checker': [x0, x1, even, odd]   columns x0..x1: index `even` where (x + y) is even, else `odd`
   'rows': [r_even, r_odd],         other columns: copied from the original's clean row r_even
                                    (y even) or r_odd (y odd)
   'band': [y0, y1],                the rows above apply to y0..y1; above and below them (the
   'top': [c_even, c_odd],          panel's bevels) each row is copied from its own pixels in
   'bottom': [c_even, c_odd],       column c_even (x even) or c_odd, within columns bevel_x
   'bevel_x': [x0, x1]}             (default: the checker columns)
"""
import letter


def _restore(im, spec):
    r = spec['restore']
    cx0, cx1, even, odd = r['checker']
    re_, ro = r['rows']
    y0, y1 = r['band']
    bx0, bx1 = r.get('bevel_x', (cx0, cx1))
    src = im.load()

    def clear(out, pal, box, ground, limit, pad=0):
        x, y, w, h = box
        px = out.load()
        for j in range(max(0, y - pad), min(out.height, y + h + pad)):
            for i in range(max(0, x - pad), min(out.width, x + w + pad)):
                if j < y0 or j > y1:
                    if bx0 <= i <= bx1:
                        ce, co = r['top'] if j < y0 else r['bottom']
                        px[i, j] = src[ce if i % 2 == 0 else co, j]
                    else:
                        px[i, j] = src[i, j]
                elif cx0 <= i <= cx1:
                    px[i, j] = even if (i + j) % 2 == 0 else odd
                else:
                    px[i, j] = src[i, re_ if j % 2 == 0 else ro]
    return clear


def panel(name, im, out, pal, texts, boxes, spec):
    saved = letter.clear
    letter.clear = _restore(im, spec)
    try:
        return letter.draw_group(name, im, out, pal, texts, boxes, spec)
    finally:
        letter.clear = saved


# ---------------------------------------------------------------- styled banners and buttons
#
# styled(): lettering for the gym banners (DIR_A/DIR_B), the CPU-turn banner (CMTRN) and the
# training button (G_BUTTON): gradient fill, thick outlines, glows and drop shadows that
# draw_group's flat fill can't give. Learnt from the original, in RGBA:
#   - fill: the original letters' fill pixels (spec 'fill': a Python expression of r, g, b, a,
#     inside 'fill_area'; 'flood' and 'min_blob' for letters whose rim shares their colours);
#     their most common colour on each row becomes the fill gradient, laid on the English by
#     relative height ('fill_stops' [[pos, 'rrggbb'], ...]: a gradient sampled from one tall
#     stroke by hand instead); 'fill_mode' bevel / rows+bevel shades the fill by distance and
#     direction to its edge (all of it, or only 'bevel' px in from the 'bevel_sectors' edges);
#   - layers: every other pixel near the fill, by distance ('step', default half a pixel) and by direction to
#     the nearest fill pixel (8 sectors) - outlines, glows and shadows; 'learn_over': 'transparent'
#     learns them only where the ground is transparent and lays them over the new ground (a glow
#     over a stripe), 'any' takes them as they are (letters on a plate);
#   - ground: in 'region' (the original lettering and its effects) 'transparent', 'interpolate'
#     (each row from the columns just left and right of the region) or 'columns' (a plate, see
#     _ground); elsewhere the original.
# The English: 'font' ('shear': lean for an italic, 'tracking': px between letters), capitals 'cap' px high (or the most that fits), squeezed down to 72% before
# it gets smaller, in 'text_box' (x, y, w, h: the fill only; the layers spread 'reach' px beyond),
# 'align' center | right | left. Colours snap to the palette (letter.nearest).
from collections import Counter  # noqa: E402
import math  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

SECTORS = 8


class Bins:
    """Colour counts in coarse bins (32 levels per channel): best() is the mean colour of the
    fullest bin, so a sheen of near-identical greys outvotes one flat colour."""
    def __init__(self):
        self.n, self.sum = Counter(), {}

    def __setitem__(self, rgba, _):
        k = tuple(v >> 5 for v in rgba)
        self.n[k] += 1
        t = self.sum.setdefault(k, [0, 0, 0, 0])
        for i in range(4):
            t[i] += rgba[i]

    def __getitem__(self, rgba):
        return 0

    def best(self):
        k = self.n.most_common(1)[0][0]
        return tuple(round(v / self.n[k]) for v in self.sum[k])


def _offsets(reach):
    r = int(math.ceil(reach))
    return sorted(((dx, dy) for dy in range(-r, r + 1) for dx in range(-r, r + 1)
                   if 0 < dx * dx + dy * dy <= reach * reach), key=lambda o: o[0] ** 2 + o[1] ** 2)


def _nearest(mask, x, y, offs):
    """(distance, sector) from (x, y) to the nearest pixel of mask (a set), or None. The sector is
    the direction away from the mask, averaged over its pixels up to 1.5 px further than the
    nearest (a smooth normal: a staircase edge doesn't flip it from row to row)."""
    d0 = None
    sx = sy = 0.0
    for dx, dy in offs:
        d = math.hypot(dx, dy)
        if d0 is not None and d > d0 + 1.5:
            break
        if (x + dx, y + dy) in mask:
            if d0 is None:
                d0 = d
            sx -= dx / d
            sy -= dy / d
    if d0 is None:
        return None
    ang = math.atan2(sy, sx)                    # direction from the mask to (x, y)
    return d0, int(round(ang / (2 * math.pi / SECTORS))) % SECTORS


def _stops(stops, t):
    """Colour at t (0 = capital top, 1 = baseline) of a gradient [[pos, 'rrggbb'], ...]."""
    t = min(1.0, max(0.0, t))
    pts = [(p, tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))) for p, c in stops]
    for (p0, c0), (p1, c1) in zip(pts, pts[1:]):
        if p0 <= t <= p1:
            f = (t - p0) / max(1e-9, p1 - p0)
            return tuple(round(c0[k] + (c1[k] - c0[k]) * f) for k in range(3)) + (255,)
    return pts[-1][1] + (255,)


def _over(top, bottom):
    ta, ba = top[3] / 255, bottom[3] / 255
    a = ta + ba * (1 - ta)
    if a == 0:
        return (0, 0, 0, 0)
    c = [(top[k] * ta + bottom[k] * ba * (1 - ta)) / a for k in range(3)]
    return tuple(round(v) for v in c) + (round(a * 255),)


def _ground(rgba, spec):
    """Ground (RGBA rows) for the whole picture: the original outside 'region'."""
    w, h = rgba.size
    src = rgba.load()
    g = [[src[x, y] for x in range(w)] for y in range(h)]
    rx, ry, rw, rh = spec['region']
    if spec['ground'] == 'columns':
        # a plate shaded across, flat down its middle rows ('flat': [y0, y1]): each column of the
        # flat rows is the most common 'plate' colour (a Python expression of r, g, b, a) found in
        # it, then a running median over 'smooth' columns either side; the other rows keep their
        # plate pixels and fill the rest from the nearest one
        plate = eval('lambda r, g, b, a: ' + spec['plate'])
        f0, f1 = spec['flat']
        col = {}
        for x in range(rx, rx + rw):
            c = Bins()
            for y in range(f0, f1 + 1):
                if plate(*src[x, y]):
                    c[src[x, y]] += 1
            if c.n:
                col[x] = c.best()
        smooth = spec.get('smooth', 6)        # columns either side: a running median
        for x in range(rx, rx + rw):
            win = [col[k] for k in range(x - smooth, x + smooth + 1) if k in col]
            if not win:
                win = [col[min(col, key=lambda k: abs(k - x))]]
            c = tuple(sorted(v[i] for v in win)[len(win) // 2] for i in range(4))
            for y in range(f0, f1 + 1):
                g[y][x] = c
        for y in list(range(ry, f0)) + list(range(f1 + 1, ry + rh)):
            ok = [x for x in range(rx, rx + rw) if plate(*src[x, y])]
            for x in range(rx, rx + rw):
                if ok:
                    g[y][x] = src[min(ok, key=lambda k: abs(k - x)), y]
        return g
    for y in range(ry, ry + rh):
        a = src[max(0, rx - 1), y]
        b = src[min(w - 1, rx + rw), y]
        for x in range(rx, rx + rw):
            if spec['ground'] == 'transparent':
                g[y][x] = (0, 0, 0, 0)
            else:
                t = (x - rx + 1) / (rw + 1)
                g[y][x] = tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(4))
    return g


def _mask(text, spec, cap, box):
    """Set of (x, y) for the English fill: capitals `cap` px, in box; None if it can't fit."""
    bx, by, bw, bh = box
    font_file = letter.FONT_DIR / spec['font']
    for c in range(cap, 5, -1):
        size = c * letter.SUPER
        font = ImageFont.truetype(str(font_file), round(size / 0.7))
        cap_px = font.getbbox('H')[3] - font.getbbox('H')[1]
        font = ImageFont.truetype(str(font_file), round(font.size * size / cap_px))
        l, t, r, b = font.getbbox(text)
        top = font.getbbox('H')[1]
        track = spec.get('tracking', 0) * letter.SUPER
        shear = spec.get('shear', 0)
        extra = track * len(text) + round(shear * size)
        big = Image.new('L', (r - l + 4 * letter.SUPER + extra, b - top + 4 * letter.SUPER), 0)
        d = ImageDraw.Draw(big)
        if track:
            pen = -l + 2 * letter.SUPER
            for i, ch in enumerate(text):
                d.text((pen, -top + 2 * letter.SUPER), ch, font=font, fill=255)
                pen += font.getlength(text[:i + 1]) - font.getlength(text[:i]) + track
        else:
            d.text((-l + 2 * letter.SUPER, -top + 2 * letter.SUPER), text, font=font, fill=255)
        if shear:
            # italic: the capital top leans right by shear x the capital height, the baseline stays
            base = 2 * letter.SUPER + size
            big = big.transform(big.size, Image.AFFINE, (1, shear, -shear * base, 0, 1, 0), Image.BICUBIC)
        ink = big.getbbox()
        big = big.crop((ink[0], 0, ink[2], big.height))
        squeeze = min(1.0, bw * letter.SUPER / big.width)
        if squeeze < letter.SQUEEZE_MIN:
            continue
        nw = max(1, round(big.width * squeeze / letter.SUPER))
        small = big.resize((nw, round(big.height / letter.SUPER)), Image.BOX)
        cap_top = 2                      # capitals start 2 px down (2 * SUPER at 4x)
        if c > bh:
            continue
        ox = {'left': bx, 'right': bx + bw - nw}.get(spec.get('align'), bx + (bw - nw) // 2)
        oy = by + (bh - c) // 2 - cap_top
        sp = small.load()
        pts = {(ox + i, oy + j) for j in range(small.height) for i in range(small.width) if sp[i, j] >= 128}
        return pts, c, squeeze, (by + (bh - c) // 2, by + (bh - c) // 2 + c)
    return None


def styled(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    rgba = Image.open(letter.paths.ORIGINAL_IMAGES / f'{name}.png').convert('RGBA')
    src = rgba.load()
    W, H = rgba.size
    ground = _ground(rgba, spec)
    reach = spec.get('reach', 8)
    step = spec.get('step', letter.STEP)       # distance resolution of the layers
    offs = _offsets(reach)
    # the original's fill and its gradient
    fx, fy, fw, fh = spec.get('fill_area', spec['region'])
    test = eval('lambda r, g, b, a: ' + spec['fill'])
    fill = {(x, y) for y in range(fy, fy + fh) for x in range(fx, fx + fw) if test(*src[x, y])}
    if 'flood' in spec:
        # letters whose fill shares colours with their rim: the outside is flooded from 'seed'
        # pixels (glow) through 'pass' pixels (rim); fill is what the flood doesn't reach
        seed = eval('lambda r, g, b, a: ' + spec['flood']['seed'])
        thru = eval('lambda r, g, b, a: ' + spec['flood']['pass'])
        todo = [(x, y) for y in range(H) for x in range(W) if seed(*src[x, y])]
        seen = set(todo)
        while todo:
            x, y = todo.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= n[0] < W and 0 <= n[1] < H and n not in seen and thru(*src[n]):
                    seen.add(n)
                    todo.append(n)
        fill -= seen
    if spec.get('min_blob'):
        # stray pixels of a fill colour in the rim are not letters
        left, keep = set(fill), set()
        while left:
            blob, todo = set(), [left.pop()]
            while todo:
                x, y = todo.pop()
                blob.add((x, y))
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n in left:
                        left.discard(n)
                        todo.append(n)
            if len(blob) >= spec['min_blob']:
                keep |= blob
        fill = keep
    mode = spec.get('fill_mode', 'rows')        # rows | bevel | rows+bevel
    inner, inner_d, bevelled = {}, {}, set()
    if 'bevel' in mode:
        # the fill's shading by distance and direction to its edge (a bevel or a sheen); with
        # rows+bevel only the 'bevel_sectors' edges (2 = below), up to 'bevel' px in
        outside = {(x, y) for y in range(H) for x in range(W)} - fill
        ioffs = _offsets(spec.get('bevel', 6))
        secs = set(spec.get('bevel_sectors', range(SECTORS)))
        for x, y in fill:
            got = _nearest(outside, x, y, ioffs)
            if mode == 'rows+bevel' and (got is None or got[1] not in secs):
                continue
            k = (round(got[0] / step), got[1]) if got else (None, None)
            inner.setdefault(k, Bins())[src[x, y]] += 1
            inner_d.setdefault(k[0], Bins())[src[x, y]] += 1
            bevelled.add((x, y))
    rtest = eval('lambda r, g, b, a: ' + spec.get('rows_fill', 'True'))
    rows = {}
    for y in range(fy, fy + fh):
        c = Bins()
        for x in range(fx, fx + fw):
            if (x, y) in fill and (x, y) not in bevelled and rtest(*src[x, y]):
                c[src[x, y]] += 1
        if c.n:
            rows[y] = c.best()
    ftop, fbot = (min(rows), max(rows)) if rows else (0, 0)
    # the layers
    by_key, by_d = {}, {}
    rx, ry, rw, rh = spec['region']
    for y in range(ry, ry + rh):
        for x in range(rx, rx + rw):
            if (x, y) in fill:
                continue
            if spec.get('learn_over', 'transparent') == 'transparent' and ground[y][x][3] != 0:
                continue
            got = _nearest(fill, x, y, offs)
            if got is None:
                continue
            d, s = got
            k = round(d / step)
            by_key.setdefault((k, s), Bins())[src[x, y]] += 1
            by_d.setdefault(k, Bins())[src[x, y]] += 1
    notes = []
    caps = []
    px = out.load()
    cache = {}
    for text, box in zip(texts, boxes):
        got = _mask(text, spec, spec.get('cap', 99), box)
        if got is None:
            raise SystemExit(f'office.styled: {name}: {text!r} does not fit {box}')
        mask, cap, squeeze, (ctop, cbot) = got
        caps.append(cap)
        if squeeze < 1:
            notes.append(f'{text!r}: squeezed to {squeeze:.0%}')
        # the area to redraw: the region and the English with its layers
        xs = [p[0] for p in mask]
        ys = [p[1] for p in mask]
        r = int(math.ceil(reach))
        x0, x1 = max(0, min(min(xs) - r, rx)), min(W, max(max(xs) + r + 1, rx + rw))
        y0, y1 = max(0, min(min(ys) - r, ry)), min(H, max(max(ys) + r + 1, ry + rh))
        if inner:
            region_out = {(x, y) for y in range(y0 - 8, y1 + 8) for x in range(x0 - 8, x1 + 8)} - mask
        for y in range(y0, y1):
            for x in range(x0, x1):
                got = _nearest(region_out, x, y, ioffs) if (x, y) in mask and inner else None
                k = (round(got[0] / step), got[1]) if got else (None, None)
                if (x, y) in mask and mode == 'bevel':
                    c = (inner.get(k) or inner_d.get(k[0]) or inner_d.get(None)).best()
                elif (x, y) in mask and k in inner:
                    c = inner[k].best()
                elif (x, y) in mask and 'fill_stops' in spec:
                    c = _stops(spec['fill_stops'], (y - ctop) / max(1, cbot - ctop - 1))
                elif (x, y) in mask:
                    rel = (y - ctop) / max(1, cbot - ctop - 1)
                    oy = min(fbot, max(ftop, round(ftop + rel * (fbot - ftop))))
                    while oy not in rows:
                        oy += 1
                    c = rows[oy]
                else:
                    near = _nearest(mask, x, y, offs)
                    c = ground[y][x]
                    if near is not None:
                        k = round(near[0] / step)
                        layer = by_key.get((k, near[1])) or by_d.get(k)
                        if layer:
                            lc = layer.best()
                            if spec.get('learn_over', 'transparent') == 'transparent':
                                c = _over(lc, c)
                            else:
                                c = lc
                    elif not (rx <= x < rx + rw and ry <= y < ry + rh):
                        continue            # outside the region and the English: as it was
                if c not in cache:
                    cache[c] = letter.nearest(pal, c, limit)
                px[x, y] = cache[c]
    notes.insert(0, f'capitals {min(caps)} px')
    return notes, min(caps)
