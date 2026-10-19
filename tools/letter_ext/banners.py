"""Styled titles for tools/letter.py (spec "draw": "banners.draw"), chosen by the spec's "mode":

  subtitle   PAR_SUBTITnn: the game's own English title letters (PAR_SUBTIT00-12, and the "EX" of
             SUBTIT16) cut out of the originals and set again. Each letter pixel is read as
             (position on its picture's colour ramp, blend towards white); in the new picture it
             takes the same position on the new picture's ramp (blue, red, gold). The white
             outline and its soft edge are rebuilt from the distance to the new letters. Letters
             the originals lack are made from others: W = M turned 180 degrees, and a narrow
             letter missing from the narrow titles = the wide one squeezed.
  month      PAR_MONTHnn: a heavy italic word on a rising slant, the original's blue gloss
             gradient, white outline and soft white edge.
  map        MAP_*: a title across a banner that the game draws in two pieces (strip + rounded
             end, see SPLIT); white letters, black outline, soft shadow, on the band's colour.
  sysmap     SYS_MAP_0: the same title on the assembled screen, plus its sample text lines.

Spec keys used here besides letter.py's: mode, font, cap, shear, angle, and per mode the
measured geometry (see each function).
"""
import math
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import letter  # noqa: E402
import paths  # noqa: E402

FONT_DIR = letter.FONT_DIR
WHITE = (255, 255, 255)


def draw(name, im, out, pal, texts, boxes, spec):
    return {'subtitle': subtitle, 'month': month, 'map': map_banner, 'sysmap': sys_map}[spec['mode']](
        name, im, out, pal, texts, boxes, spec)


# ---------------------------------------------------------------- shared

def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


class Snap:
    """RGBA -> nearest palette index, cached."""

    def __init__(self, pal, avoid=()):
        self.pal, self.cache, self.avoid = pal, {}, set(avoid)

    def __call__(self, rgba):
        rgba = tuple(max(0, min(255, round(v))) for v in rgba)
        if rgba[3] == 0:
            rgba = (0, 0, 0, 0)
        if rgba not in self.cache:
            r, g, b, a = rgba
            best, bi = None, 0
            for i, (pr, pg, pb, pa) in enumerate(self.pal):
                if i in self.avoid:
                    continue
                d = ((pr * pa - r * a) ** 2 + (pg * pa - g * a) ** 2 + (pb * pa - b * a) ** 2) / 255 ** 2 \
                    + 2 * (pa - a) ** 2
                if best is None or d < best:
                    best, bi = d, i
            self.cache[rgba] = bi
        return self.cache[rgba]


def over(top, bottom):
    """Porter-Duff over, straight RGBA tuples (alpha 0..255)."""
    ta, ba = top[3] / 255, bottom[3] / 255
    a = ta + ba * (1 - ta)
    if a <= 0:
        return (0, 0, 0, 0)
    return tuple((top[k] * ta + bottom[k] * ba * (1 - ta)) / a for k in range(3)) + (a * 255,)


def text_image(text, font_file, cap, super_=4, shear=0.0, tracking=0.0):
    """L image (super_ x scale) of the text: capitals `cap` px high, sheared to the right by
    `shear` (x per y). Returns (image, cap top row in it, baseline row in it)."""
    size = cap * super_
    font = ImageFont.truetype(str(FONT_DIR / font_file), round(size / 0.7))
    h = font.getbbox('H')
    font = ImageFont.truetype(str(FONT_DIR / font_file), round(font.size * size / (h[3] - h[1])))
    h = font.getbbox('H')
    pad = 4 * super_ + int(abs(shear) * size * 1.6)
    width = sum(font.getlength(ch) for ch in text) + tracking * super_ * len(text) + 2 * pad
    img = Image.new('L', (int(width), int(size * 1.6) + 2 * pad), 0)
    d = ImageDraw.Draw(img)
    x = pad
    top = pad
    for ch in text:
        d.text((x, top - h[1]), ch, font=font, fill=255)
        x += font.getlength(ch) + tracking * super_
    base = top + size
    if shear:
        # x' = x + shear * (base - y): letters lean right, the baseline stays put
        img = img.transform(img.size, Image.AFFINE, (1, shear, -shear * base, 0, 1, 0), Image.BICUBIC)
    bb = img.getbbox()
    img = img.crop((bb[0] - 2 * super_, 0, bb[2] + 2 * super_, img.height))
    return img, top, base


def down(img, s):
    """Box-average an L image by s: coverage 0..1 per pixel, as a list of rows."""
    small = img.resize((img.width // s, img.height // s), Image.BOX)
    px = small.load()
    return [[px[x, y] / 255 for x in range(small.width)] for y in range(small.height)]


# ---------------------------------------------------------------- subtitle

ORIG = paths.ORIGINAL_IMAGES
SOURCES = {          # PAR_SUBTIT titles already in English: text, letter set
    '00': ('MANAGEMENT', 'wide'), '01': ('SPECIAL MATCH', 'wide'), '03': ('OPEN LEAGUE', 'wide'),
    '05': ('GALLERY', 'wide'), '06': ('OPTION', 'wide'), '07': ('LOAD', 'wide'),
    '08': ('OFFICE', 'wide'), '09': ('GYM', 'wide'), '10': ('BATTLE', 'wide'),
    '11': ('MATCH MAKE', 'wide'), '02': ('ONE NIGHT TOURNAMENT', 'narrow'),
    '16': ('EX', 'ex'),
}
TITLE_ROWS = 37      # rows above the chrome bar


def is_whiteish(c):
    return min(c[:3]) >= 200 and max(c[:3]) - min(c[:3]) < 30


def ramp_of(im, pal):
    """The picture's letter colour ramp, dark to bright: the most common strongly coloured or dark
    opaque colour of each title row."""
    px = im.load()
    cols = []
    for y in range(TITLE_ROWS):
        c = Counter()
        for x in range(im.width):
            p = pal[px[x, y]]
            if p[3] >= 200 and not is_whiteish(p) and (max(p[:3]) - min(p[:3]) > 40 or max(p[:3]) < 60):
                c[p[:3]] += 1
        if c:
            cols.append(c.most_common(1)[0][0])
    ramp = sorted(set(cols), key=lum)
    return ramp


def ramp_at(ramp, f):
    """Colour at normalised luminance f (0 = darkest, 1 = brightest) along the ramp."""
    lo, hi = lum(ramp[0]), lum(ramp[-1])
    L = lo + f * (hi - lo)
    for a, b in zip(ramp, ramp[1:]):
        if lum(a) <= L <= lum(b):
            t = 0 if lum(b) == lum(a) else (L - lum(a)) / (lum(b) - lum(a))
            return tuple(a[k] + (b[k] - a[k]) * t for k in range(3))
    return ramp[-1] if f > 0.5 else ramp[0]


def decompose(ramp, c):
    """(f, t): c ~ (1 - t) * ramp_at(f) + t * white."""
    best = None
    for fi in range(51):
        r = ramp_at(ramp, fi / 50)
        for ti in range(41):
            t = ti / 40
            e = sum(((1 - t) * r[k] + t * 255 - c[k]) ** 2 for k in range(3))
            if best is None or e < best[0]:
                best = (e, fi / 50, t)
    return best[1], best[2]


@lru_cache(None)
def source_glyphs(sid):
    """{letter: glyph} from PAR_SUBTIT<sid>; glyph = {(x, y): (f, t)} with x from 0, y absolute."""
    text, _ = SOURCES[sid]
    im = Image.open(ORIG / f'PAR_SUBTIT{sid}_0.png')
    pal = letter.rgba_palette(im)
    ramp = ramp_of(im, pal)
    px = im.load()
    dec = {}
    pts = {}
    for y in range(TITLE_ROWS):
        for x in range(im.width):
            p = pal[px[x, y]]
            if p[3] < 200:
                continue
            if p not in dec:
                dec[p] = decompose(ramp, p)
            f, t = dec[p]
            if t < 0.8:
                pts[(x, y)] = (f, t)
    # 8-connected components
    seen, comps = set(), []
    for p in pts:
        if p in seen:
            continue
        stack, comp = [p], []
        seen.add(p)
        while stack:
            q = stack.pop()
            comp.append(q)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (q[0] + dx, q[1] + dy)
                    if n in pts and n not in seen:
                        seen.add(n)
                        stack.append(n)
        if len(comp) >= 8:
            comps.append(comp)
    comps.sort(key=lambda c: sum(p[0] for p in c) / len(c))
    letters = [ch for ch in text if ch != ' ']
    if sid == '16':
        comps = comps[:2]
    if len(comps) != len(letters):
        raise SystemExit(f'banners: PAR_SUBTIT{sid}: {len(comps)} letter shapes for {text!r}')
    out = {}
    for ch, comp in zip(letters, comps):
        x0 = min(p[0] for p in comp)
        out.setdefault(ch, {(x - x0, y): pts[(x, y)] for x, y in comp})
    # measured spacing: per-row gap between neighbours, and word gaps
    gaps, spaces = [], []
    words = text.split(' ')
    k = 0
    for wi, w in enumerate(words):
        for li in range(len(w)):
            if k + 1 < len(comps):
                g = row_gap(comps[k], comps[k + 1])
                (spaces if li == len(w) - 1 else gaps).append(g)
            k += 1
    return out, gaps, spaces, min(y for c in comps for _, y in c)


def row_gap(a, b):
    ra, rb = defaultdict(list), defaultdict(list)
    for x, y in a:
        ra[y].append(x)
    for x, y in b:
        rb[y].append(x)
    return min(min(rb[y]) - max(ra[y]) - 1 for y in ra if y in rb) if set(ra) & set(rb) else 0


def glyph_set(kind):
    """{letter: glyph aligned to the set's top row}, letter gap, word gap."""
    glyphs, gaps, spaces = {}, [], []
    top = None
    for sid, (_, k) in SOURCES.items():
        if k != kind:
            continue
        g, ga, sp, t = source_glyphs(sid)
        top = t if top is None else top
        for ch, gl in g.items():
            if ch not in glyphs:
                glyphs[ch] = {(x, y - t + top): v for (x, y), v in gl.items()}
        gaps += ga
        spaces += sp
    gaps.sort()
    spaces.sort()
    return glyphs, (gaps[len(gaps) // 2] if gaps else 5), (spaces[len(spaces) // 2] if spaces else 12), top


def turn(gl):
    """Glyph turned 180 degrees (M -> W keeps an italic slant)."""
    w = max(x for x, _ in gl)
    y0, y1 = min(y for _, y in gl), max(y for _, y in gl)
    return {(w - x, y0 + y1 - y): v for (x, y), v in gl.items()}


def squeeze(gl, factor):
    """Glyph narrowed horizontally (coverage resampled)."""
    w = max(x for x, _ in gl) + 1
    y0, y1 = min(y for _, y in gl), max(y for _, y in gl)
    S = 8
    cov = Image.new('L', (w * S, (y1 - y0 + 1)), 0)
    fimg = Image.new('L', cov.size, 0)
    for (x, y), (f, t) in gl.items():
        for s in range(S):
            cov.putpixel((x * S + s, y - y0), round((1 - t) * 255))
            fimg.putpixel((x * S + s, y - y0), round(f * 255))
    nw = max(1, round(w * factor))
    c2 = cov.resize((nw, cov.height), Image.BOX)
    f2 = fimg.resize((nw, cov.height), Image.BOX)
    out = {}
    for y in range(c2.height):
        for x in range(nw):
            c = c2.getpixel((x, y)) / 255
            if c > 0.2:
                # undo the darkening of f by averaging with empty columns
                f = f2.getpixel((x, y)) / 255 / max(c, 1e-3)
                out[(x, y + y0)] = (min(1.0, f), 1 - c)
    return out


def subtitle(name, im, out, pal, texts, boxes, spec):
    text = texts[0].upper()
    kind = spec.get('set', 'wide')
    wide, wgap, wspace, wtop = glyph_set('wide')
    if kind == 'ex':
        # E and X from SUBTIT16 itself, the rest from the wide set (same height)
        glyphs, gap, space, top = dict(wide), wgap, wspace, wtop
        exg, _, _, extop = source_glyphs('16')
        for c, gl in exg.items():
            glyphs[c] = {(x, y - extop + wtop): v for (x, y), v in gl.items()}
    else:
        glyphs, gap, space, top = glyph_set(kind)
        glyphs = dict(glyphs)
    made = []
    for ch in sorted(set(text) - {' '}):
        if ch in glyphs:
            continue
        if ch == 'W' and 'M' in glyphs:
            glyphs['W'] = turn(glyphs['M'])
        elif ch in wide:
            # the set's letters are narrower than the wide ones by about this much
            common = [c for c in glyphs if c in wide]
            ratio = sum(max(x for x, _ in glyphs[c]) + 1 for c in common) / \
                sum(max(x for x, _ in wide[c]) + 1 for c in common)
            glyphs[ch] = squeeze(wide[ch], ratio)
        else:
            raise SystemExit(f'banners: {name}: no letter {ch!r}')
        made.append(ch)
    # lay out: each letter as close to the previous as the measured per-row gap allows
    placed, last, space_next = [], None, False
    for ch in text:
        if ch == ' ':
            space_next = True
            continue
        gl = glyphs[ch]
        x = 0
        if last is not None:
            g = space if space_next else gap
            pts = [(qx + last[0], qy) for qx, qy in last[1]]
            x = max(q for q, _ in pts) - 60
            while row_gap(pts, [(qx + x, qy) for qx, qy in gl]) < g:
                x += 1
        placed.append((x, gl))
        last, space_next = (x, gl), False
    x0 = min(x + min(q for q, _ in gl) for x, gl in placed)
    x1 = max(x + max(q for q, _ in gl) for x, gl in placed)
    width = x1 - x0 + 1
    margin = spec.get('margin', 8)
    notes = []
    if width > im.width - 2 * margin:
        raise SystemExit(f'banners: {name}: {text!r} is {width} px wide, room {im.width - 2 * margin}')
    shift = (im.width - width) // 2 - x0
    ramp = ramp_of(im, pal)
    snap = Snap(pal)
    cells = {}
    for x, gl in placed:
        for (gx, gy), v in gl.items():
            cells[(gx + x + shift, gy)] = v
    # the outline style, learnt from an English original: RGBA by distance from the letters
    style = outline_style()
    opx = out.load()
    t_idx = next(i for i, p in enumerate(pal) if p[3] == 0)
    # clear everything above the chrome bar (the first fully drawn row)
    ipx = im.load()
    bar = next(y for y in range(30, im.height) if all(pal[ipx[x, y]][3] > 0 for x in range(im.width)))
    for y in range(bar):
        for xx in range(im.width):
            opx[xx, y] = t_idx
    mask = [[(x, y) in cells for x in range(im.width)] for y in range(TITLE_ROWS)]
    dist = letter.distances(mask, im.width, TITLE_ROWS, 6)
    for y in range(TITLE_ROWS):
        for xx in range(im.width):
            if (xx, y) in cells:
                f, t = cells[(xx, y)]
                c = ramp_at(ramp, f)
                opx[xx, y] = snap(tuple((1 - t) * c[k] + t * 255 for k in range(3)) + (255,))
            else:
                k = round(dist[y][xx] / letter.STEP)
                if k in style:
                    opx[xx, y] = snap(style[k])
    notes.append(f'{text}: {kind} letters, {width} px wide' + (f'; made: {", ".join(made)}' if made else ''))
    return notes, 0


@lru_cache(None)
def outline_style():
    im = Image.open(ORIG / 'PAR_SUBTIT00_0.png')
    pal = letter.rgba_palette(im)
    ramp = ramp_of(im, pal)
    px = im.load()
    mask = []
    for y in range(TITLE_ROWS):
        row = []
        for x in range(im.width):
            p = pal[px[x, y]]
            row.append(p[3] >= 200 and decompose_cached(tuple(ramp), p)[1] < 0.8)
        mask.append(row)
    dist = letter.distances(mask, im.width, TITLE_ROWS, 6)
    by = defaultdict(Counter)
    for y in range(TITLE_ROWS):
        for x in range(im.width):
            if not mask[y][x]:
                by[round(dist[y][x] / letter.STEP)][pal[px[x, y]]] += 1
    style = {}
    for k in sorted(by):
        c, _ = by[k].most_common(1)[0]
        if c[3] == 0:
            break
        style[k] = c
    for k in range(1, max(style)):      # distances that never occur on the pixel grid
        style.setdefault(k, style.get(k - 1, style[min(style)]))
    return style


@lru_cache(None)
def decompose_cached(ramp, c):
    return decompose(list(ramp), c)


# ---------------------------------------------------------------- month banners

MONTH_SLOPE = 0.3      # the month banners rise 0.3 px per px; their gloss runs along u = y + 0.3 x


@lru_cache(None)
def month_style():
    """From all twelve originals: {u: RGBA} of the letter fill, and {distance step: RGBA} around it."""
    tab, by = defaultdict(Counter), defaultdict(Counter)
    for n in range(1, 13):
        im = Image.open(ORIG / f'PAR_MONTH{n:02d}_0.png')
        pal = letter.rgba_palette(im)
        px = im.load()
        fill = {i for i, p in enumerate(pal) if p[3] == 255 and p[2] > 100 and p[0] < 5 and p[1] < 30}
        for y in range(im.height):
            for x in range(im.width):
                if px[x, y] in fill:
                    tab[round(y + MONTH_SLOPE * x)][pal[px[x, y]]] += 1
        if n == 10:
            mask = [[px[x, y] in fill for x in range(im.width)] for y in range(im.height)]
            dist = letter.distances(mask, im.width, im.height, 8)
            for y in range(im.height):
                for x in range(im.width):
                    if not mask[y][x]:
                        by[round(dist[y][x] / letter.STEP)][pal[px[x, y]]] += 1
    grad = {u: c.most_common(1)[0][0] for u, c in tab.items()}
    style = {}
    for k in sorted(by):
        if k < 3:
            continue          # the blend next to the fill comes from the coverage
        c, _ = by[k].most_common(1)[0]
        if c[3] == 0:
            break
        style[k] = c
    for k in range(0, max(style)):
        style.setdefault(k, (255, 255, 255, 255))
    return grad, style


def month(name, im, out, pal, texts, boxes, spec):
    grad, style = month_style()
    lo, hi = min(grad), max(grad)
    text = texts[0]
    S = 4
    cap = spec['cap']
    mask, top, base = text_image(text, spec['font'], cap, S, spec.get('shear', 0.0), spec.get('tracking', 0.0))
    if spec.get('xscale', 1) != 1:
        mask = mask.resize((round(mask.width * spec['xscale']), mask.height), Image.BICUBIC)
    # the baseline rises MONTH_SLOPE px per px, letters keep their italic lean (vertical shear)
    lift = MONTH_SLOPE * mask.width
    rot = mask.transform((mask.width, int(mask.height + lift)), Image.AFFINE,
                         (1, 0, 0, MONTH_SLOPE, 1, -lift), Image.BICUBIC)
    bb = rot.getbbox()
    rot = rot.crop(bb)
    cov = down(rot.resize((rot.width - rot.width % S, rot.height - rot.height % S)), S)
    h, w = len(cov), len(cov[0])
    right = spec.get('right', 260)
    ox = right - w
    # vertical: the cap band's middle on the gloss line u = mid
    mid = spec.get('mid', 121)
    us = [y + MONTH_SLOPE * (x + ox) for y in range(h) for x in range(w) if cov[y][x] >= 0.5]
    oy = round(mid - (min(us) + max(us)) / 2)
    if ox < 4 or oy < 4 or oy + h > im.height - 4:
        raise SystemExit(f'banners: {name}: {text!r} does not fit ({ox}, {oy}, {w}x{h})')
    snap = Snap(pal)
    opx = out.load()
    t_idx = next(i for i, p in enumerate(pal) if p[3] == 0)
    W, H = im.width, im.height
    full = [[0.0] * W for _ in range(H)]
    for y in range(h):
        for x in range(w):
            full[y + oy][x + ox] = cov[y][x]
    m = [[full[y][x] >= 0.5 for x in range(W)] for y in range(H)]
    dist = letter.distances(m, W, H, 8)
    for y in range(H):
        for x in range(W):
            c = full[y][x]
            g = grad[min(hi, max(lo, round(y + MONTH_SLOPE * x)))]
            if c >= 0.97:
                opx[x, y] = snap(g)
            elif c > 0.03:
                t = 1 - c
                opx[x, y] = snap(tuple(g[k] * (1 - t) + 255 * t for k in range(3)) + (255,))
            else:
                k = round(dist[y][x] / letter.STEP)
                opx[x, y] = snap(style[k]) if k in style else t_idx
    return [f'{text}: capitals {cap} px, {w}x{h} at ({ox}, {oy})'], cap


# The MAP_* banners: the game draws the strip (rows 0-63, x 0-255) and, to its right, the rounded
# end kept below it (rows 64-127, x 0-63) - matched against the assembled banner in SYS_MAP_0.
# Banner coordinates: x 0-319, y 0-63.
SPLIT = 256


class MapView:
    def __init__(self, img, dy=0, split=True):
        self.px, self.dy, self.split = img.load(), dy, split
        self.w, self.h = 320, 64

    def _at(self, x, y):
        if self.split and x >= SPLIT:
            return x - SPLIT, y + 64
        return x, y + self.dy

    def __getitem__(self, xy):
        return self.px[self._at(*xy)]

    def __setitem__(self, xy, v):
        self.px[self._at(*xy)] = v


def banner_title(name, src, dst, pal, text, spec):
    """English title on a banner band: src/dst MapView of the original / output."""
    fill = {i for i, p in enumerate(pal) if sum(p[:3]) > 700 and p[3] == 255}
    white = max(fill, key=lambda i: sum(pal[i][:3]))
    rows = range(spec.get('top', 14), spec.get('bottom', 42))
    cols = [x for x in range(88, src.w) if any(src[x, y] in fill for y in range(17, 39))]
    x0, x1 = cols[0] - 4, cols[-1] + 5
    # ground: each band row's most common colour
    ground = {}
    for y in rows:
        c = Counter(i for i in (src[x, y] for x in range(60, 316))
                    if i not in fill and not (pal[i][3] == 255 and lum(pal[i]) < 40))
        ground[y] = c.most_common(1)[0][0]
        # the band's top rows are shaded: take the colour just left of the lettering
        left_px = src[x0 - 1, y]
        if left_px not in fill and not (pal[left_px][3] == 255 and lum(pal[left_px]) < 40):
            ground[y] = left_px
    for y in rows:
        for x in range(x0, x1 + 1):
            dst[x, y] = ground[y]
    # the English: white fill, black outline to 2 px, a soft dark edge to 3 px
    S = 4
    cap = spec['cap']
    right = spec.get('right', 280)
    left = spec.get('left', 96)
    notes = []
    for cs in range(cap, 8, -1):
        mask, top, base = text_image(text, spec['font'], cs, S, spec.get('shear', 0.0), spec.get('tracking', 0.0))
        sq = min(1.0, (right - left) * S / mask.width)
        if sq >= spec.get('squeeze_min', 0.82):
            break
    if sq < 1:
        mask = mask.resize((round(mask.width * sq), mask.height), Image.BICUBIC)
        notes.append(f'{text!r}: squeezed to {sq:.0%}')
    if cs < cap:
        notes.append(f'{text!r}: capitals {cs} px')
    # align the text's cap top on a row (top is in supersampled pixels)
    shift = (-top) % S
    if shift:
        m2 = Image.new('L', (mask.width, mask.height + shift), 0)
        m2.paste(mask, (0, shift))
        mask, top = m2, top + shift
    mask = mask.crop((0, 0, mask.width - mask.width % S, mask.height - mask.height % S))
    cov = down(mask, S)
    h, w = len(cov), len(cov[0])
    cols = [x for x in range(w) if any(cov[y][x] > 0.02 for y in range(h))]
    cap_top = spec.get('cap_top', 21) + (spec['cap'] - cs) // 2
    ox = right - cols[-1] - 1
    oy = cap_top - top // S
    full = {}
    for y in range(h):
        for x in range(w):
            if cov[y][x] > 0.02:
                full[(x + ox, y + oy)] = cov[y][x]
    bx = min(x0, ox + cols[0]) - 4
    bw = max(x1, ox + cols[-1]) + 6 - bx
    m = [[full.get((x + bx, y), 0) >= 0.5 for x in range(bw)] for y in range(64)]
    dist = letter.distances(m, bw, 64, 4)
    snap = Snap(pal)
    out_w = spec.get('outline', 2.0)
    soft = spec.get('soft', 3.0)
    for y in rows:
        for xx in range(bw):
            x = xx + bx
            if not (0 <= x < 320):
                continue
            d = dist[y][xx]
            c = full.get((x, y), 0)
            if d > soft and c <= 0.02:
                continue
            g = pal[ground[y]]
            if d <= out_w or c >= 0.5:
                col = over((0, 0, 0, 255), g)
            elif d <= soft:
                col = over((0, 0, 0, 170), g)
            else:
                col = g
            if c > 0.02:
                col = over((255, 255, 255, 255 * min(1, c)), col)
            dst[x, y] = white if c >= 0.97 else snap(col)
    if ox + cols[0] < left:
        raise SystemExit(f'banners: {name}: {text!r} does not fit')
    notes.insert(0, f'{text}: capitals {cs} px, x {ox + cols[0]}-{ox + cols[-1]}')
    return notes, cs


def map_banner(name, im, out, pal, texts, boxes, spec):
    return banner_title(name, MapView(im), MapView(out), pal, texts[0], spec)


def sys_map(name, im, out, pal, texts, boxes, spec):
    dy = spec.get('dy', 14)
    return banner_title(name, MapView(im, dy, False), MapView(out, dy, False), pal, texts[0], spec)
