"""SYS_OFFICEUE_0's date labels (年目 / 月): white letters with a grey edge pixel and a near-black
glow two pixels wide (dark counters, a dark row below), on a dithered navy ground that darkens
towards the silver bar under it.

letter.py's 'interpolate' streaked the old glow's bottom rows sideways (the stray line after 'Yr')
and drew an outline instead of the glow. Here:
  1. the Japanese - white, grey and its glow (pixels darker than the ground, 'dark', within
     'glow' px of the white) - is found in each 'area' and replaced by the ground: each hole pixel
     mirrors the clean pixel the same distance beyond the hole's nearer end in its row, so the
     ground's dither and its darker bottom rows carry on; a mirror that falls in another hole
     takes the nearest clean pixel of the row;
  2. the English (its fill inside the label's box) is drawn like the original: fill, the 'edge' colour at distance <= 1, the 'shade'
     colour out to 'glow' px, then half-blended with the ground out to glow + 1.

Spec keys: 'areas' (one [x, y, w, h] per label, optionally + a column 'right'), 'strip', 'grow', 'fill_rgb', 'edge', 'shade' (rgb), 'glow',
'font', 'cap', 'align'.
"""
import math

import letter


def _hole_mask(src, area, glow, bright, dark):
    ax, ay, aw, ah = area[:4]
    white = {(x, y) for y in range(ay, ay + ah) for x in range(ax, ax + aw) if bright(src[x, y])}
    r = int(math.ceil(glow))
    hole = set(white)
    for x, y in white:
        for dy in range(-r, r + 2):         # the glow hangs a row lower than it reaches sideways
            for dx in range(-r, r + 1):
                q = (x + dx, y + dy)
                if q in hole or not (ax <= q[0] < ax + aw and ay <= q[1] < ay + ah):
                    continue
                if dark(src[q]) and math.hypot(dx, max(0, abs(dy) - (1 if dy > 0 else 0))) <= glow + 0.5:
                    hole.add(q)
    # counters: dark pixels enclosed by the letters (not reached from the area's border)
    return hole


def draw(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    src = im.convert('RGBA').load()
    opx = out.load()
    bright = lambda c: c[0] >= 0x28              # white and its grey edge (the ground's red is <= 0x10)
    dark = lambda c: c[2] < 0x30 or (c[0] >= 0x10 and c[2] <= 0x20)
    cache = {}

    def idx(rgba):
        if rgba not in cache:
            cache[rgba] = letter.nearest(pal, rgba, limit)
        return cache[rgba]

    glow = spec.get('glow', 2.5)
    sa, sb = spec['strip']
    grow = spec.get('grow', 1)
    for area in spec['areas']:
        hole = _hole_mask(src, area, glow, bright, dark)
        hole |= {(x + dx, y + dy) for x, y in hole for dx in range(-grow, grow + 1) for dy in range(-grow, grow + 1)}
        right = area[4] if len(area) > 4 else None
        for x, y in hole:
            q = (x - sa) % (2 * (sb - sa))
            sx = sa + (q if q < sb - sa else 2 * (sb - sa) - 1 - q)
            if right is not None and x >= right:
                # past column 'right' the ground changes (a lighter diagonal band): mirror the
                # clean pixels beyond the hole's right end instead
                end = x
                while (end + 1, y) in hole:
                    end += 1
                m = end + 1 + (end - x)
                if (m, y) not in hole and m < im.width:
                    sx = m
            opx[x, y] = im.getpixel((sx, y))
    # the English
    fill = idx(tuple(spec.get('fill_rgb', [248, 248, 248])) + (255,))
    edge = tuple(spec.get('edge', [64, 72, 72]))
    shade = tuple(spec.get('shade', [0, 8, 8]))
    notes = []
    for text, box in zip(texts, boxes):
        x, y, w, h = box
        r = int(math.ceil(glow)) + 1
        got = letter.text_mask(text, spec['font'], spec['cap'], w, h, spec.get('align', 'left'), slack=r)
        if got is None:
            raise SystemExit(f'officeue: {text!r} does not fit {box}')
        mask, cap, squeeze = got
        if squeeze < 1:
            notes.append(f'{text!r}: squeezed to {squeeze:.0%}')
        pts = {(x + i, y + j) for j, row in enumerate(mask) for i, v in enumerate(row) if v}
        offs = sorted(((dx, dy) for dy in range(-r, r + 2) for dx in range(-r, r + 1)), key=lambda o: math.hypot(*o))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        for yy in range(min(ys) - r, max(ys) + r + 2):
            for xx in range(min(xs) - r, max(xs) + r + 1):
                if (xx, yy) in pts:
                    opx[xx, yy] = fill
                    continue
                # distance to the fill; the glow reaches one row further down (a shadow)
                d = min((math.hypot(dx, dy - (1 if dy < 0 else 0)) for dx, dy in offs if (xx + dx, yy + dy) in pts),
                        default=99)
                if d <= 1:
                    c = edge
                elif d <= glow:
                    c = shade
                elif d <= glow + 1:
                    g = pal[opx[xx, yy]]
                    c = tuple((a + b) // 2 for a, b in zip(shade, g[:3]))
                else:
                    continue
                opx[xx, yy] = idx(c + (255,))
    notes.insert(0, f'capitals {spec["cap"]} px')
    return notes, spec['cap']
