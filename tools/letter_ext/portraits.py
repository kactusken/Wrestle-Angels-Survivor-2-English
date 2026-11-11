"""Portrait name tags (SYS_GM_CHR_n): white lettering with a navy outline across the top of each
128x128 portrait, partly over the hair.

The old tag is removed pixel by pixel - only colours on the line from the outline navy to the white
fill, inside the tag band - so the hair under it stays; those pixels become transparent (the
picture's background). The English (the ring name, as on the original tag) is drawn centred in
the band: white fill, navy outline `outline_width` px.

With clear_tag false the Japanese tag stays and the English goes in its own band (e.g. small along
the bottom of the portrait) - no art is removed, only covered by the letters.

draw_pixel instead uses the hand-drawn pixel font (pixelfont.py), see its docstring.

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


def body_span(im, pal, rows):
    """(left, right): the columns opaque on every one of these rows (the character's body there):
    on each row the opaque run through the middle column (else the widest)."""
    px = im.load()
    left, right = 0, im.width - 1
    mid = im.width // 2
    for y in rows:
        runs, start = [], None          # opaque runs (gaps between an arm and the body split them)
        for x in range(im.width + 1):
            solid = x < im.width and pal[px[x, y]][3] > 0
            if solid and start is None:
                start = x
            elif not solid and start is not None:
                runs.append((start, x - 1))
                start = None
        if not runs:
            return None
        a, b = max(runs, key=lambda r: (r[0] <= mid <= r[1], r[1] - r[0]))
        left, right = max(left, a), min(right, b)
    return (left, right) if left <= right else None


def draw_pixel(name, im, out, pal, texts, boxes, spec):
    """The ring name in the hand-drawn pixel font (pixelfont.py): white, a navy outline all round
    (diagonals too) and, with 'shadow', one more navy pixel below and right. Kept inside the
    character's body (the opaque columns of the rows it covers) with 'margin' px to spare: centred
    on the portrait, shifted if the body is off-centre, on two lines if one doesn't fit.

    Spec keys: band [x, y, w, h] (the last line's 9 font rows start at band y + 'top');
    line_pitch; margin; shadow; max_lines; body (default true; false = centred in the band like the
    old tags, not kept inside the character)."""
    import pixelfont
    bx, by, bw, bh = spec['band']
    top = by + spec.get('top', 2)
    pitch = spec.get('line_pitch', 10)
    margin = spec.get('margin', 1)
    shadow = spec.get('shadow', False)
    pad = 1 + (1 if shadow else 0)
    text = texts[0]
    words = text.split(' ')
    layouts = [[text]] + ([[' '.join(words[:k]), ' '.join(words[k:])] for k in range(1, len(words))]
                          if spec.get('max_lines', 2) > 1 else [])
    best = None
    for lines in layouts:
        ys = [top - pitch * (len(lines) - 1 - k) for k in range(len(lines))]
        placed, over = [], 0
        for line, y in zip(lines, ys):
            rows = pixelfont.text_rows(line)
            w = len(rows[0])
            ink_rows = [y + j for j in range(pixelfont.ROWS) if any(rows[j])]
            span = (body_span(im, pal, range(min(ink_rows) - 1, max(ink_rows) + 2 + (1 if shadow else 0)))
                    if spec.get('body', True) else None)
            lo, hi = (span[0] + margin + 1, span[1] - margin - pad + 1) if span else (bx + 1, bx + bw - pad)
            x = bx + (bw - w) // 2
            x = max(lo, min(x, hi - w)) if hi - lo >= w else (lo + hi - w) // 2
            over = max(over, w - (hi - lo))
            placed.append((rows, x, y))
        key = (max(over, 0), len(lines), max(len(r[0][0]) for r in placed))
        if best is None or key < best[0]:
            best = (key, placed)
    (over, nlines, _), placed = best
    white = letter.nearest(pal, WHITE + (255,), len(pal))
    navy = letter.nearest(pal, NAVY + (255,), len(pal))
    ink = set()
    for rows, x, y in placed:
        ink |= {(x + i, y + j) for j, r in enumerate(rows) for i, v in enumerate(r) if v}
    px = out.load()
    halo = {(x + dx, y + dy) for x, y in ink for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    if shadow:
        halo |= {(x + 1, y + 1) for x, y in halo}
    # close 1-2 px holes in the dark plate along each row (word gaps, beside x/v/y), so no art shows
    # through between words as stray dots
    for yy in {y for _, y in halo}:
        xs = sorted(x for x, y in halo if y == yy)
        for a, b in zip(xs, xs[1:]):
            if 1 < b - a <= 3:
                halo |= {(x, yy) for x in range(a + 1, b)}
    for x, y in halo - ink:
        if 0 <= x < out.width and 0 <= y < out.height:
            px[x, y] = navy
    for x, y in ink:
        px[x, y] = white
    notes = [f'{text!r}: {nlines} line(s)' + (f', {over} px outside the body' if over > 0 else '')]
    return notes, 7
