#!/usr/bin/env python3
"""Roster group pictures for the player's guide: the wrestlers' portraits side by side, one picture
per group (who is there at the start of which era, the later rookies, the second personas).

  rostercards.py              write docs/guide/roster/<group>.webp
  rostercards.py --list       only print the groups and who is in them

Needs Pillow, and the original portraits in review/images-original (SYS_GM_CHR_<n>.png, chain n
of /SYS/GM_CHR.BIN = roster record n, 0-157, from tools/gfx.py). The groups come from
tools/guidedata.py, so they follow the same data as the guide's roster table: each wrestler's
debut value puts her at the start of an era or makes her a rookie in a later year.

The portraits are 128x128 busts with the Japanese ring name across the top (and, in the English
build, the English name in small pixel letters across the chest), so this takes the original
picture, crops the name tag off, and draws the patch's English ring name in a band under it -
on the guide's teal-steel grid with a red-to-magenta title stroke, written as WebP. The foreign wrestlers
(records 158-241) have no portrait in GM_CHR.BIN and are not drawn. The owner made an exception
to the no-game-art rule for these (2026-10-26): docs/guide/roster/ only.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import guidedata  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('needs Pillow: .venv/bin/pip install -r requirements.txt, then run with .venv/bin/python')

OUT = paths.DOCS / 'guide' / 'roster'
FONTS = Path(__file__).resolve().parent / 'fonts'

ART = (0, 18, 128, 118)      # a GM_CHR portrait below its name tag (rows 0-17); 118+ is empty
CELL_W, CELL_H = 160, 166    # one wrestler: the bust scaled to 160x125 and a name band
PER_ROW = 10                 # at most; rows are balanced
PAD, TITLE_H = 28, 92
# the guide's Survivor 2 palette: deep teal-steel panels, silver grid, the logo's red-to-magenta "2"
BG, GRID, INK, MUTED = (8, 42, 60), (185, 210, 220, 30), (243, 247, 250), (170, 195, 205)
STROKE_A, STROKE_B, BAND = (196, 18, 31), (226, 55, 154), (4, 24, 36, 215)


def when(ws, era):
    """When a group turns up in an era: 'years 2-5', or 'at the start or in years 1-3'."""
    ys = sorted({w['st'][era]['y'] for w in ws})
    later = [y for y in ys if y > 0]
    span = '' if not later else f'year {later[0]}' if len(later) == 1 else f'years {later[0]}-{later[-1]}'
    if ys[0] <= 0:
        return 'at the start' + (f' or in {span}' if span else '')
    return span


def groups(data):
    """[(file stem, title, subtitle, [wrestlers])] in guide order."""
    W = [w for w in data['wrestlers'] if 'st' in w]           # the domestic records, 0-157
    E = data['eras']
    P = {p['i']: p['n'] for p in data['promotions']}
    first = [w for w in W if w['id'] < 100]
    second = [w for w in W if w['id'] > 100]
    at_start = lambda w, era: w['st'][era]['y'] <= 0
    key = lambda w: (w['st'][2]['y'], w['id'])
    every = [w for w in first if at_start(w, 0)]
    rivals = [w for w in first if not at_start(w, 0) and at_start(w, 1)]
    new_era = [w for w in first if not at_start(w, 1) and at_start(w, 2)]
    rookies = sorted([w for w in first if not at_start(w, 2)], key=key)
    cpu = sorted({P[s['p']] for w in every for s in w['st'] if 'p' in s})
    alt1 = sorted([w for w in second if w['st'][2]['y'] <= 3], key=key)
    alt2 = sorted([w for w in second if 3 < w['st'][2]['y'] <= 6], key=key)
    alt3 = sorted([w for w in second if w['st'][2]['y'] > 6], key=key)

    def alts(ws):
        return f'Rookies in {E[0]} {when(ws, 0)}, {E[1]} {when(ws, 1)}, {E[2]} {when(ws, 2)}'

    out = [
        ('every-era', 'There from the start',
         f'At the start of every era, free or on a CPU roster ({", ".join(cpu)})', every),
        ('warring-rivals', f'From {E[1]}',
         f'There from the start in {E[1]} and {E[2]}; rookies in {E[0]} {when(rivals, 0)}', rivals),
        ('new-era', f'From {E[2]}',
         f'There from the start only in {E[2]}; rookies in {E[0]} {when(new_era, 0)} and {E[1]} '
         f'{when(new_era, 1)}', new_era),
        ('rookies', 'Later rookies', f'Rookies in every era ({E[2]}: {when(rookies, 2)})', rookies),
        ('second-personas-1', 'Second personas, part 1', alts(alt1), alt1),
        ('second-personas-2', 'Second personas, part 2', alts(alt2), alt2),
        ('second-personas-3', 'Second personas, part 3', alts(alt3), alt3),
    ]
    placed = [w['i'] for g in out for w in g[3]]
    twice = {w['n'] for w in W if placed.count(w['i']) > 1}
    if twice:
        sys.exit(f'rostercards: in two groups: {", ".join(sorted(twice))}')
    missing = [w['n'] for w in W if w['i'] not in placed]
    if missing:
        sys.exit(f'rostercards: not in any group: {", ".join(missing)}')
    empty = [g[0] for g in out if not g[3]]
    if empty:
        sys.exit(f'rostercards: empty group(s): {", ".join(empty)} - the data changed, regroup')
    return out


def figure(n):
    src = paths.ORIGINAL_IMAGES / f'SYS_GM_CHR_{n}.png'
    if not src.is_file():
        sys.exit(f'rostercards: {paths.show(src)} is missing - export the pictures first (tools/extract.py)')
    im = Image.open(src).convert('RGBA')
    if im.size != (128, 128):
        sys.exit(f'rostercards: {paths.show(src)} is {im.size[0]}x{im.size[1]}, not a 128x128 portrait')
    crop = im.crop(ART)
    return crop.resize((CELL_W, CELL_W * crop.height // crop.width), Image.LANCZOS)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def fit(draw, text, name, size, width):
    f = font(name, size)
    while draw.textlength(text, font=f) > width and size > 10:
        size -= 1
        f = font(name, size)
    return f


def poster(title, subtitle, members):
    rows = -(-len(members) // PER_ROW)
    cols = -(-len(members) // rows)
    sub_font = font('Barlow-Medium.ttf', 18)
    probe = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    W = max(PAD * 2 + cols * CELL_W, PAD * 2 + int(probe.textlength(subtitle, font=sub_font)) + 4)
    H = PAD + TITLE_H + rows * CELL_H + PAD
    im = Image.new('RGBA', (W, H), BG + (255,))
    grid = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(grid)
    for x in range(0, W, 32):
        g.line([(x, 0), (x, H)], fill=GRID)
    for y in range(0, H, 32):
        g.line([(0, y), (W, y)], fill=GRID)
    im.alpha_composite(grid)
    d = ImageDraw.Draw(im)
    # title with the red-to-magenta brush stroke under it
    tf = font('BarlowCondensed-ExtraBoldItalic.ttf', 46)
    tw = d.textlength(title, font=tf)
    sx, sy = PAD, PAD + 52
    stroke = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    s = ImageDraw.Draw(stroke)
    length = int(min(tw + 60, W * 0.6))
    for i in range(length):
        a = 255 if i < length * 0.55 else int(255 * (1 - (i - length * 0.55) / (length * 0.45)))
        t = min(1, i / (length * 0.6))
        c = tuple(int(STROKE_A[k] + (STROKE_B[k] - STROKE_A[k]) * t) for k in range(3))
        s.line([(sx + i + 5, sy), (sx + i, sy + 9)], fill=c + (a,))
    im.alpha_composite(stroke)
    d.text((PAD, PAD - 6), title, font=tf, fill=INK)
    d.text((PAD + 2, PAD + 66), subtitle, font=sub_font, fill=MUTED)
    x0 = (W - cols * CELL_W) // 2
    for i, w in enumerate(members):
        r, c = divmod(i, cols)
        x = x0 + c * CELL_W
        y = PAD + TITLE_H + r * CELL_H
        fig = figure(w['i'])
        im.alpha_composite(fig, (x, y))
        band = Image.new('RGBA', (CELL_W - 6, 30), BAND)
        im.alpha_composite(band, (x + 3, y + fig.height + 2))
        f = fit(d, w['n'], 'BarlowCondensed-Bold.ttf', 20, CELL_W - 16)
        d.text((x + CELL_W / 2, y + fig.height + 17), w['n'], font=f, fill=INK, anchor='mm')
    return im.convert('RGB')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', action='store_true', help='only print the groups')
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    gs = groups(guidedata.build())
    if args.list:
        for stem, title, sub, members in gs:
            print(f'{stem}: {title} ({len(members)}) - {sub}\n    {", ".join(w["n"] for w in members)}')
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, title, sub, members in gs:
        out = OUT / f'{stem}.webp'
        poster(title, sub, members).save(out, 'WEBP', quality=86, method=6)
        print(f'{paths.show(out)}: {len(members)} wrestlers, {out.stat().st_size // 1024} KB')


if __name__ == '__main__':
    main()
