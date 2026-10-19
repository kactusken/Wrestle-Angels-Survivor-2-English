"""Portrait name tags (SYS_GM_CHR_n): white lettering with a navy outline across the top of each
128x128 portrait, partly over the hair.

The old tag is removed pixel by pixel - only colours on the line from the outline navy to the white
fill, inside the tag band - so the hair under it stays; those pixels become transparent (the
picture's background). The English (the ring name, as on the original tag) is drawn centred in
the band: white fill, navy outline `outline_width` px.

With clear_tag false the Japanese tag stays and the English goes in its own band (e.g. small along
the bottom of the portrait) - no art is removed, only covered by the letters.

Spec keys: band [x, y, w, h]; clear_tag (default true); cap (capital height px); font; outline_width; tolerance (colour
distance from the navy-white line still counted as tag ink).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import letter  # noqa: E402

NAVY, WHITE = (13, 0, 73), (255, 255, 255)


def on_tag_line(rgba, tol):
    """Is this colour a blend of the navy outline and the white fill (anti-aliasing included)?"""
    r, g, b, a = rgba
    if a == 0:
        return False                    # (semi-transparent pixels count: the tag's soft glow)
    v = [WHITE[i] - NAVY[i] for i in range(3)]
    t = sum((c - n) * d for c, n, d in zip((r, g, b), NAVY, v)) / sum(d * d for d in v)
    t = max(0.0, min(1.0, t))
    p = [NAVY[i] + t * v[i] for i in range(3)]
    # the glow (semi-transparent) is matched loosely, solid pixels tightly: hair stays
    return sum((c - q) ** 2 for c, q in zip((r, g, b), p)) ** 0.5 <= (tol if a < 255 else min(tol, 24))


def draw(name, im, out, pal, texts, boxes, spec):
    bx, by, bw, bh = spec['band']
    tol = spec.get('tolerance', 40)
    ow = spec.get('outline_width', 2)
    px = out.load()
    clear = next(i for i, p in enumerate(pal) if p[3] == 0)
    for y in range(by, by + bh) if spec.get('clear_tag', True) else ():
        for x in range(bx, bx + bw):
            if on_tag_line(pal[px[x, y]], tol):
                px[x, y] = clear
    white = letter.nearest(pal, WHITE + (255,), len(pal))
    navy = letter.nearest(pal, NAVY + (255,), len(pal))
    text = texts[0]
    inner_w, inner_h = bw - 2 * ow, bh - 2 * ow
    got = letter.text_mask(text, spec['font'], spec['cap'], inner_w, inner_h, 'center', ow)
    if got is None:
        raise SystemExit(f'portraits: {name}: {text!r} does not fit')
    mask, size, squeeze = got
    full = [[False] * bw for _ in range(bh)]
    for j in range(min(len(mask), bh - ow)):
        for i in range(inner_w):
            full[j + ow][i + ow] = mask[j][i]
    for j in range(bh):
        for i in range(bw):
            if full[j][i]:
                continue
            if any(0 <= j + dy < bh and 0 <= i + dx < bw and full[j + dy][i + dx]
                   for dy in range(-ow, ow + 1) for dx in range(-ow, ow + 1) if dx * dx + dy * dy <= ow * ow + 1):
                px[bx + i, by + j] = navy
    for j in range(bh):
        for i in range(bw):
            if full[j][i]:
                px[bx + i, by + j] = white
    return [f'{text!r}: capitals {size} px' + (f', squeezed {squeeze:.0%}' if squeeze < 1 else '')], size
