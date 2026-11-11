"""SYS_MENU_0's panel: a flat blue (0058b0) with bevelled edges. letter.py's 'interpolate' ground
blends each cleared row towards the dark right bevel (a darker band right of the labels) and leaves
the Japanese halo's bottom rows below the last label. Here the cleared area is rebuilt from the
panel itself: each pixel is the darker of a clean column's value at that row (top and bottom
bevels) and the right bevel's most common value at that column; pixels of the original far enough
from the Japanese stay as they were. Then letter.draw_group draws the labels on it ('keep').

Spec keys (on the group): 'panel': {'area': [x, y, w, h], 'column': x (a clean column),
'bevel_x': first column of the right bevel, 'rows': [y0, y1] (rows the right bevel's modes come
from), 'keep_from': distance from the Japanese beyond which original pixels stay}
"""
from collections import Counter

import letter


def _lum(c):
    return c[0] * 3 + c[1] * 6 + c[2]


def panel(name, im, out, pal, texts, boxes, spec):
    p = spec['panel']
    src = im.convert('RGBA').load()
    ax, ay, aw, ah = p['area']
    col = p['column']
    bx = p['bevel_x']
    r0, r1 = p['rows']
    ipx = im.load()
    # the right bevel: each column's most common colours over rows r0..r1
    right, blue = {}, {src[col, y] for y in range(ay, ay + ah)}
    for x in range(bx, ax + aw):
        c = Counter(src[x, y] for y in range(r0, r1)).most_common(2)
        right[x] = c[0][0]
        blue |= {k for k, _ in c}
    # the Japanese: its fill and halo (anything in the area that isn't a panel blue)
    marks = [(x, y) for y in range(ay, ay + ah) for x in range(ax, ax + aw) if src[x, y] not in blue]
    keep = p.get('keep_from', 3)
    near = set()
    for x, y in marks:
        for dy in range(-keep, keep + 1):
            for dx in range(-keep, keep + 1):
                near.add((x + dx, y + dy))
    opx = out.load()
    cache = {}
    for y in range(ay, ay + ah):
        for x in range(ax, ax + aw):
            if (x, y) not in near:
                opx[x, y] = ipx[x, y]
                continue
            c = src[col, y]
            if x in right and _lum(right[x]) < _lum(c):
                c = right[x]
            if c not in cache:
                cache[c] = letter.nearest(pal, c, len(pal))
            opx[x, y] = cache[c]
    return letter.draw_group(name, im, out, pal, texts, boxes, spec | {'ground': 'keep', 'clear': []})
