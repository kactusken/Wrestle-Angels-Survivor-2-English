#!/usr/bin/env python3
"""Hand-lettered English for menu pictures the automatic renderer can't do (needs Pillow: run with
.venv/bin/python).

  letter.py                 draw every picture with a spec (translation/letters/) into
                            translation/images-handmade/
  letter.py <image>...      only these
  letter.py --preview OUT   also write OUT/<image>.png: original above English, 3x, on a dark ground
  letter.py --sync          copy the specs' English and boxes into translation/graphics.csv

tools/render.py expects white lettering on a flat or transparent ground. These pictures have
lettering in a colour the game tints when it draws it (MENU1's grey-blue) or lettering on a
gradient (OFFICEUE). For each label, given as a box and an English text in the picture's spec:

  1. style: the label's fill is the pixels of the fill index (spec 'fill'). Every other pixel in
     the box is filed by its distance to the fill. The most common original index at each distance
     (in half-pixel steps) becomes the style: outline, then halo, then ground;
  2. ground: 'transparent' clears the box to the transparent index. 'interpolate' rebuilds each
     row from the pixels left and right of the box, snapped to the palette, for gradients;
  3. English: drawn at 4x in the font, scaled to the box (squeezed horizontally down to SQUEEZE_MIN
     before the size drops), thresholded to a fill mask, and coloured by the style from its
     distance to the new fill.

The result keeps the original palette and indices: tools/gfx.py imports it as it is.
"""
import argparse
import csv
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

FONT_DIR = Path(__file__).resolve().parent / 'fonts'
SUPER = 4               # supersampling for the text mask
SQUEEZE_MIN = 0.72      # narrowest horizontal squeeze before the size drops
STEP = 0.5              # distance resolution of a style

# Specs: translation/letters/<image>.json, one per picture (agents and people can work on different
# pictures without touching the same file). Keys:
#   english   ' | '-separated labels ('=' leaves a label as it is); boxes [[x, y, w, h], ...]
#   fill      palette indices of the letter fill, or 'bright' (white-ish opaque pixels)
#   ground    transparent | interpolate;  font: file in tools/fonts;  cap: capital height in px
#   pad       pixels around each box also cleared;  clear: more [x, y, w, h] areas to clear
#   reach     outline + halo width in px (default: learnt, up to 8 - set it for 'interpolate')
#   align     center (default) | left;  upper: capitals
#   groups    [{'labels': [box numbers], other keys}] - labels drawn with their own settings (a
#             normal and a highlighted copy of a menu);  same_size: every group at one size
#   draw      'module.function' in tools/letter_ext/ - draws a group instead of draw_group() (same
#             arguments and result), for lettering this file can't do
#   notes     for the catalogue;  catalogue: {source, width, height, bpp, category, japanese} for a
#             picture not in translation/graphics.csv yet (`letter.py --sync` adds the row)
SPEC_DIR_NAME = 'letters'


def spec_dir():
    return paths.TRANSLATION / SPEC_DIR_NAME


def load_specs():
    import json
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted(spec_dir().glob('*.json'))}


def rows():
    with open(paths.TRANSLATION / 'graphics.csv', encoding='utf-8') as f:
        return {r['image']: r for r in csv.DictReader(f)}


def boxes_of(s):
    if isinstance(s, list):
        return [tuple(b) for b in s]
    return [tuple(int(v) for v in b.split(',')) for b in s.split(';') if b.strip()]


def rgba_palette(im):
    pal = im.getpalette()
    n = len(pal) // 3
    tr = im.info.get('transparency', b'')
    if isinstance(tr, int):
        tr = bytes(255 if i != tr else 0 for i in range(n))
    return [tuple(pal[3 * i:3 * i + 3]) + (tr[i] if i < len(tr) else 255,) for i in range(n)]


def nearest(pal, rgba, limit):
    """Palette index closest to rgba (premultiplied), among the first `limit` entries."""
    r, g, b, a = rgba
    best, bi = None, 0
    for i, (pr, pg, pb, pa) in enumerate(pal[:limit]):
        d = ((pr * pa - r * a) ** 2 + (pg * pa - g * a) ** 2 + (pb * pa - b * a) ** 2) / 255 ** 2 + (pa - a) ** 2
        if best is None or d < best:
            best, bi = d, i
    return bi


def distances(mask, w, h, reach=8):
    """Euclidean distance of each pixel to the nearest True pixel of mask (capped at reach)."""
    pts = [(x, y) for y in range(h) for x in range(w) if mask[y][x]]
    out = [[reach] * w for _ in range(h)]
    for x, y in pts:
        for yy in range(max(0, y - reach), min(h, y + reach + 1)):
            for xx in range(max(0, x - reach), min(w, x + reach + 1)):
                d = math.hypot(xx - x, yy - y)
                if d < out[yy][xx]:
                    out[yy][xx] = d
    return out


def fill_indices(im, pal, box, spec):
    if spec['fill'] != 'bright':
        return set(spec['fill'])
    x, y, w, h = box
    px = im.load()
    c = Counter(px[i, j] for j in range(y, y + h) for i in range(x, x + w))
    bright = [i for i in c if sum(pal[i][:3]) >= 600 and pal[i][3] >= 200]
    return set(bright)


def learn_style(im, pal, boxes, fills, ground, reach=8):
    """({distance step: index} around the fill, the fill's most common index, the smallest label's
    fill height) - learnt from all the picture's labels together."""
    px = im.load()
    by, fill, heights = defaultdict(Counter), Counter(), []
    for x, y, w, h in boxes:
        mask = [[px[x + i, y + j] in fills for i in range(w)] for j in range(h)]
        dist = distances(mask, w, h)
        for j in range(h):
            for i in range(w):
                if mask[j][i]:
                    fill[px[x + i, y + j]] += 1
                else:
                    by[round(dist[j][i] / STEP)][px[x + i, y + j]] += 1
        ink = [j for j in range(h) if any(mask[j])]
        heights.append((ink[-1] - ink[0] + 1) if ink else h)
    style = {}
    for k in sorted(by):
        idx, _ = by[k].most_common(1)[0]
        if (ground == 'transparent' and pal[idx][3] == 0) or k * STEP > reach:
            break
        style[k] = idx
    return style, fill.most_common(1)[0][0], min(heights)


def clear(out, pal, box, ground, limit, pad=0):
    x, y, w, h = box
    x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(out.width, x + w + pad), min(out.height, y + h + pad)
    px = out.load()
    if ground == 'transparent':
        t = next(i for i, p in enumerate(pal[:limit]) if p[3] == 0)
        for j in range(y0, y1):
            for i in range(x0, x1):
                px[i, j] = t
        return
    left, right = max(0, x0 - 1), min(out.width - 1, x1)

    def side(xs, j):
        # median of a 3x3 patch just outside the box: one stray outline pixel doesn't streak the row
        got = sorted((pal[px[i, jj]] for i in xs for jj in range(max(0, j - 1), min(out.height, j + 2))),
                     key=lambda p: sum(p[:3]))
        return got[len(got) // 2]

    cache = {}
    for j in range(y0, y1):
        a = side(range(max(0, left - 2), left + 1), j)
        b = side(range(right, min(out.width, right + 3)), j)
        for i in range(x0, x1):
            t = (i - left) / (right - left)
            rgba = tuple(round(a[k] + (b[k] - a[k]) * t) for k in range(4))
            if rgba not in cache:
                cache[rgba] = nearest(pal, rgba, limit)
            px[i, j] = cache[rgba]


def text_mask(text, font_file, cap, w, h, align='center', slack=0):
    """Rows of booleans ((h + slack) x w): the text's fill, capitals `cap` px high and centred in h,
    descenders allowed `slack` rows below h; None if it can't fit."""
    for c in range(cap, 5, -1):
        size = c * SUPER
        font = ImageFont.truetype(str(FONT_DIR / font_file), round(size / 0.7))
        cap_px = font.getbbox('H')[3] - font.getbbox('H')[1]
        font = ImageFont.truetype(str(FONT_DIR / font_file), round(font.size * size / cap_px))
        l, t, r, b = font.getbbox(text)
        tw = r - l
        squeeze = min(1.0, (w * SUPER) / tw)
        if squeeze < SQUEEZE_MIN:
            continue
        top = font.getbbox('H')[1]
        big = Image.new('L', (tw + 2 * SUPER, size + 6 * SUPER), 0)
        ImageDraw.Draw(big).text((-l + SUPER, -top + SUPER), text, font=font, fill=255)
        nw = max(1, round(big.width * squeeze / SUPER))
        small = big.resize((nw, max(1, round(big.height / SUPER))), Image.BOX)
        ink = small.getbbox()
        if ink is None:
            return None
        small = small.crop(ink)
        if small.width > w or c > h:
            continue
        out = [[False] * w for _ in range(h + slack)]
        ox = 0 if align == 'left' else (w - small.width) // 2
        oy = (h - c) // 2 + ink[1] - 1     # capitals centred
        oy = max(0, oy)
        if oy + small.height > h + slack:
            continue
        sp = small.load()
        for j in range(small.height):
            for i in range(small.width):
                if sp[i, j] >= 128:
                    out[oy + j][ox + i] = True
        return out, c, squeeze
    return None


def letter(name, row, spec):
    """(new picture, notes). row: {'english', 'boxes'} (a spec holds both)."""
    src = paths.ORIGINAL_IMAGES / f'{name}.png'
    im = Image.open(src)
    if im.mode != 'P':
        raise SystemExit(f'letter: {src}: not an indexed image')
    pal = rgba_palette(im)
    out = im.copy()
    all_texts = [t.strip() for t in row['english'].split('|')]
    all_boxes = boxes_of(row['boxes'])
    if len(all_texts) != len(all_boxes):
        raise SystemExit(f'letter: {name}: {len(all_texts)} texts for {len(all_boxes)} boxes')
    groups = []
    for group in spec.get('groups') or [{}]:
        g = {k: v for k, v in spec.items() if k != 'groups'} | group
        labels = g.get('labels', range(len(all_boxes)))
        texts = [all_texts[i].upper() if g.get('upper') else all_texts[i] for i in labels]
        groups.append((g, texts, [all_boxes[i] for i in labels]))
    if spec.get('same_size'):
        # measure every group first: a highlighted copy must match the normal one letter for letter
        cap = min(drawer(g)(name, im, im.copy(), pal, t, b, g)[1] for g, t, b in groups)
        groups = [(g | {'cap': cap}, t, b) for g, t, b in groups]
    notes = []
    drawn = []                          # per group: the fill pixels of each label (absolute)
    for g, texts, boxes in groups:
        if 'copy_of' in g:              # the same letter shapes as another group, shifted
            src, (dx, dy) = g['copy_of']
            g = g | {'_fills': [{(x + dx, y + dy) for x, y in f} for f in drawn[src]]}
        g['_record'] = []
        notes += drawer(g)(name, im, out, pal, texts, boxes, g)[0]
        drawn.append(g['_record'])
    return out, notes


def drawer(spec):
    if 'draw' not in spec:
        return draw_group
    import importlib
    module, _, func = spec['draw'].rpartition('.')
    sys.path.insert(0, str(Path(__file__).resolve().parent / 'letter_ext'))
    return getattr(importlib.import_module(module), func)


def draw_group(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    fills = set().union(*(fill_indices(im, pal, box, spec) for box in boxes))
    style, fill, ink_h = learn_style(im, pal, boxes, fills, spec['ground'], spec.get('reach', 8))
    for box in boxes:
        clear(out, pal, box, spec['ground'], limit, spec.get('pad', 0))
    for box in spec.get('clear', []):
        clear(out, pal, box, spec['ground'], limit)
    reach = max(style) * STEP if style else 0
    inner = [(int(w - 2 * reach), int(h - 2 * reach)) for _, _, w, h in boxes]
    # one size for the whole picture: the largest every label fits at (squeezed if need be)
    cap = spec.get('cap') or round(ink_h * 0.8)
    for text, (iw, ih) in zip(texts, inner):
        if text != '=':
            got = text_mask(text, spec['font'], min(cap, ih), iw, ih, slack=int(reach))
            if got is None:
                raise SystemExit(f'letter: {name}: {text!r} does not fit {iw}x{ih}')
            cap = min(cap, got[1])
    notes = []
    px = out.load()
    r = int(reach)
    for box, text, (iw, ih) in zip(boxes, texts, inner):
        if text == '=':
            continue
        x, y, w, h = box
        full = [[False] * w for _ in range(h)]
        if '_fills' in spec:
            for fx, fy in spec['_fills'][len(spec['_record'])]:
                if 0 <= fx - x < w and 0 <= fy - y < h:
                    full[fy - y][fx - x] = True
        else:
            mask, size, squeeze = text_mask(text, spec['font'], cap, iw, ih, spec.get('align', 'center'), int(reach))
            if squeeze < 1:
                notes.append(f'{text!r}: squeezed to {squeeze:.0%}')
            for j in range(min(len(mask), h - r)):
                for i in range(iw):
                    full[j + r][i + r] = mask[j][i]
        if '_record' in spec:
            spec['_record'].append({(x + i, y + j) for j in range(h) for i in range(w) if full[j][i]})
        dist = distances(full, w, h)
        for j in range(h):
            for i in range(w):
                if full[j][i]:
                    px[x + i, y + j] = fill
                else:
                    k = round(dist[j][i] / STEP)
                    if k in style:
                        px[x + i, y + j] = style[k]
    notes.insert(0, f'capitals {cap} px')
    return notes, cap


def preview(name, out, folder):
    orig = Image.open(paths.ORIGINAL_IMAGES / f'{name}.png').convert('RGBA')
    new = out.convert('RGBA')
    sheet = Image.new('RGBA', (orig.width, orig.height * 2 + 4), (255, 255, 255, 255))
    for k, im in enumerate((orig, new)):
        bg = Image.new('RGBA', im.size, (40, 40, 90, 255))
        bg.alpha_composite(im)
        sheet.paste(bg, (0, k * (orig.height + 4)))
    sheet = sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST)
    Path(folder).mkdir(parents=True, exist_ok=True)
    sheet.save(Path(folder) / f'{name}.png')


def sync(specs):
    """Copy each spec's English, boxes and notes into translation/graphics.csv (font 'hand'); add a
    catalogue row for a picture that has none."""
    path = paths.TRANSLATION / 'graphics.csv'
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fields, table = reader.fieldnames, list(reader)
    by = {r['image']: r for r in table}
    added = 0
    for name, spec in specs.items():
        row = by.get(name)
        if row is None:
            cat = spec.get('catalogue')
            if not cat:
                raise SystemExit(f'letter: {name} is not in graphics.csv and its spec has no catalogue entry')
            row = {k: '' for k in fields} | {'image': name, 'status': 'todo'} | {k: str(v) for k, v in cat.items()}
            table.append(row)
            by[name] = row
            added += 1
        row['english'] = spec['english']
        row['boxes'] = ';'.join(','.join(str(v) for v in b) for b in spec['boxes'])
        row['font'] = 'hand'
        if spec.get('notes'):
            row['notes'] = spec['notes']
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(table)
    print(f'graphics.csv: {len(specs)} rows from specs ({added} new)')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('images', nargs='*')
    ap.add_argument('--preview')
    ap.add_argument('--sync', action='store_true', help='copy the specs into translation/graphics.csv')
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    specs = load_specs()
    if args.sync:
        sync(specs)
        return
    names = args.images or list(specs)
    paths.HANDMADE.mkdir(parents=True, exist_ok=True)
    for name in names:
        if name not in specs:
            raise SystemExit(f'letter: no spec {paths.show(spec_dir() / (name + ".json"))}')
        out, notes = letter(name, specs[name], specs[name])
        out.save(paths.HANDMADE / f'{name}.png', transparency=Image.open(
            paths.ORIGINAL_IMAGES / f'{name}.png').info.get('transparency'))
        print(f'{name}: {paths.show(paths.HANDMADE / (name + ".png"))}' + ''.join(f'\n  ~ {n}' for n in notes))
        if args.preview:
            preview(name, out, args.preview)


if __name__ == '__main__':
    main()
