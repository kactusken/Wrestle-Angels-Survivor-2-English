"""SYS_MENU1_0 (4bpp, tinted by the game): the lettering is an alpha ramp - indices 8..12 are the
dark navy at alpha 0..216, 13..15 opaque and brighter, 15 the fill - with a faint black halo
(index 5, alpha 20) and, about 3..4 px out, a thin dark ring (3/4 dark blue, then 2 and 1 black
at falling alpha).

letter.draw_group learns one index per half-pixel distance, so the fill is hard-edged and the
ring only lands where a distance rounds to exactly 3.5 px - a dotted, noisy outline. Here the
fill is antialiased through the ramp (4x coverage, nearest of the ramp's colours) and the ring is
drawn by distance bands, so it is continuous.

Spec keys: 'font', 'cap', 'solid' (coverage drawn as full fill), 'ramp' (indices from the halo to the fill), 'halo', 'ring':
[[max distance, index], ...] past the halo's 'halo_to'; every label is clipped to its box (a list
menu's sprites are cut on its rows).
"""
import math

from PIL import Image, ImageDraw, ImageFont

import letter

S = 4


def coverage(text, font_file, cap, w):
    """(rows of 0..1 coverage, width, capital top row in it) - squeezed to w px if needed."""
    size = cap * S
    font = ImageFont.truetype(str(letter.FONT_DIR / font_file), round(size / 0.7))
    cap_px = font.getbbox('H')[3] - font.getbbox('H')[1]
    font = ImageFont.truetype(str(letter.FONT_DIR / font_file), round(font.size * size / cap_px))
    l, t, r, b = font.getbbox(text)
    top = font.getbbox('H')[1]
    big = Image.new('L', (r - l + 2 * S, b - top + 2 * S), 0)
    ImageDraw.Draw(big).text((-l + S, -top + S), text, font=font, fill=255)
    ink = big.getbbox()
    big = big.crop((ink[0], 0, ink[2], big.height))
    sq = min(1.0, w * S / big.width)
    nw = max(1, round(big.width * sq / S))
    small = big.resize((nw, big.height // S), Image.BOX)
    px = small.load()
    return [[px[i, j] / 255 for i in range(nw)] for j in range(small.height)], nw, 1, sq


def draw(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    o = out.load()
    trans = next(i for i, p in enumerate(pal) if p[3] == 0)
    for x, y, w, h in spec.get('clear', []):
        for j in range(y, y + h):
            for i in range(x, x + w):
                o[i, j] = trans
    ramp = spec['ramp']
    halo = spec['halo']
    halo_to = spec['halo_to']
    ring = spec['ring']
    reach = ring[-1][0]
    # premultiplied colour over the halo for each ramp index
    def over(i):
        p = pal[i]
        a = p[3] / 255
        hp = pal[halo]
        ha = hp[3] / 255
        return [p[k] * a + hp[k] * ha * (1 - a) for k in range(3)], a + ha * (1 - a)
    ramp_cols = [(i,) + over(i) for i in ramp]
    fill_col, fill_a = over(ramp[-1])
    notes = []
    cap = spec['cap']
    for text, (bx, by, bw, bh) in zip(texts, boxes):
        r = int(math.ceil(reach))
        cov, cw, ctop, sq = coverage(text, spec['font'], cap, bw - 2 * r)
        if sq < 1:
            notes.append(f'{text!r}: squeezed to {sq:.0%}')
        ox = bx + (bw - cw) // 2
        oy = by + (bh - cap) // 2 + spec.get('dy', 0) - ctop
        solid = {(ox + i, oy + j) for j, row in enumerate(cov) for i, v in enumerate(row) if v >= 0.5}
        offs = sorted(((dx, dy) for dy in range(-r - 1, r + 2) for dx in range(-r - 1, r + 2)),
                      key=lambda q: math.hypot(*q))
        for yy in range(by, by + bh):
            for xx in range(bx, bx + bw):
                j, i = yy - oy, xx - ox
                c = cov[j][i] if 0 <= j < len(cov) and 0 <= i < cw else 0
                c = min(1.0, c / spec.get('solid', 0.75))     # stems solid, only the edges ramp
                if c > 0.02:
                    # the fill's colour at coverage c over the halo: nearest ramp entry
                    tgt = [fill_col[k] * c for k in range(3)]
                    ta = fill_a * c + (pal[halo][3] / 255) * (1 - c)
                    best = min(ramp_cols + [(halo,) + over(halo)],
                               key=lambda e: sum((e[1][k] - tgt[k]) ** 2 for k in range(3)) + (255 * (e[2] - ta)) ** 2)
                    o[xx, yy] = best[0]
                    continue
                d = next((math.hypot(dx, dy) for dx, dy in offs if (xx + dx, yy + dy) in solid), None)
                if d is None:
                    continue
                if d <= halo_to:
                    o[xx, yy] = halo
                    continue
                for top, idx in ring:
                    if d <= top:
                        o[xx, yy] = idx
                        break
    notes.insert(0, f'capitals {cap} px')
    return notes, cap
