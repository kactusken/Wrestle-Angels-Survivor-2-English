"""Move-type cards (BATTLE_MATCH_2): the English word runs down the card like the vertical kanji.

Every type card has the same swirl art under its kanji (the game tints each card with its own
CLUT row), so a clean card is rebuilt by a per-pixel vote across all the type cards - the kanji sit
in different places on each, so the art wins. Each card gets the clean art in its label strip,
then the word: rotated 90 degrees (reads top to bottom), as large as the strip allows, filled
with the original's fill indices (a gradient along the word) and the original's dark outline.

A hand-painted blank replaces all that: translation/art-sources/card_blank.png (every card) or
card_blank_<n>.png (card n), 54x69, greyscale, 16 tones (grey = tone * 17; tone = palette index,
which the game tints per card). `python3 tools/letter_ext/cards.py export` writes the original
cards in that form to build/work/cards/ as a starting point. Without a blank, the ground is
rebuilt as below.

Spec keys: cards [[x, y, w, h], ...] one per label (the card's rectangle); strip [x, y, w, h]
inside a card (where the word goes); clear [x, y, w, h] (art rebuilt there, default strip); fill [indices, first to last letter]; outline index;
outline_width px; font; band [x, y, w, h]: filled with the outline index behind the word; tone [x, fade]: the median\nof the card's art from x to the clear area (15-row window), dithered in over `fade` px; mirror x: instead of the vote,
the card's own art between x and the clear area's left edge, reflected into it.

The kanji all sit in the same strip, so the vote can't clean it - hence the band.
"""
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).resolve().parent.parent / 'fonts'
SUPER = 4


def clean_card(im, cards):
    px = im.load()
    w, h = cards[0][2], cards[0][3]
    out = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            out[y][x] = Counter(px[cx + x, cy + y] for cx, cy, _, _ in cards).most_common(1)[0][0]
    return out


def word_mask(text, font_file, length, thick, largest=None):
    """(coverage image, length x thick before rotation; font size): text as large as fits, at most
    `largest`."""
    for size in range(largest or thick * SUPER * 2, 6 * SUPER, -1):
        font = ImageFont.truetype(str(FONT_DIR / font_file), size)
        l, t, r, b = font.getbbox(text)
        cap = font.getbbox('H')
        ch = cap[3] - cap[1]
        if r - l <= length * SUPER and ch <= thick * SUPER:
            big = Image.new('L', (length * SUPER, thick * SUPER), 0)
            ImageDraw.Draw(big).text(((length * SUPER - (r - l)) // 2 - l, (thick * SUPER - ch) // 2 - cap[1]),
                                     text, font=font, fill=255)
            return big.resize((length, thick), Image.BOX), size
    raise SystemExit(f'cards: {text!r} does not fit {length}x{thick}')


ART_SOURCES = Path(__file__).resolve().parent.parent.parent / 'translation' / 'art-sources'


def blank(path, w, h):
    """A hand-painted clean card: greyscale (or RGB), 16 tones - tone n = grey n * 17 = palette index n."""
    im = Image.open(path).convert('L')
    if im.size != (w, h):
        raise SystemExit(f'cards: {path} is {im.size[0]}x{im.size[1]}, expected {w}x{h}')
    return [[min(15, (im.getpixel((x, y)) + 8) // 17) for x in range(w)] for y in range(h)]


def export(im, cards, folder, scale=8):
    """The type cards for hand painting: card_<n>.png (actual size, greyscale tones) and an enlarged
    copy of each, plus card_all.png."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    px = im.load()
    sheet = Image.new('L', (len(cards) * (cards[0][2] + 4), cards[0][3]), 0)
    for n, (cx, cy, w, h) in enumerate(cards):
        g = Image.new('L', (w, h))
        g.putdata([px[cx + x, cy + y] * 17 for y in range(h) for x in range(w)])
        g.save(folder / f'card_{n}.png')
        g.resize((w * scale, h * scale), Image.NEAREST).save(folder / f'card_{n}_x{scale}.png')
        sheet.paste(g, (n * (w + 4), 0))
    sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST).save(folder / 'card_all.png')


def draw(name, im, out, pal, texts, boxes, spec):
    cards = [tuple(c) for c in spec['cards']]
    art = clean_card(im, cards)
    w, h = cards[0][2], cards[0][3]
    shared = ART_SOURCES / 'card_blank.png'
    blanks = [ART_SOURCES / f'card_blank_{n}.png' for n in range(len(cards))]
    if shared.exists() or any(b.exists() for b in blanks):
        px = out.load()
        for n, (cx, cy, _, _) in enumerate(cards):
            path = blanks[n] if blanks[n].exists() else shared
            if path.exists():
                b = blank(path, w, h)
                for y in range(h):
                    for x in range(w):
                        px[cx + x, cy + y] = b[y][x]
        return draw_words(name, im, out, pal, texts, cards, dict(spec, painted=True))
    return draw_words(name, im, out, pal, texts, cards, spec, art)


def draw_words(name, im, out, pal, texts, cards, spec, art=None):
    sx, sy, sw, sh = spec['strip']
    ow = spec.get('outline_width', 2)
    fills = spec['fill']
    px = out.load()
    # one size for every card: the largest the longest word allows
    size = min(word_mask(t.upper(), spec['font'], sh - 2 * ow, sw - 2 * ow)[1] for t in texts)
    clear = spec.get('clear', spec['strip'])
    for (cx, cy, _, _), text in zip(cards, texts):
        qx, qy, qw, qh = clear
        if spec.get('painted'):         # the hand-painted blank is already in place
            pass
        elif 'tone' in spec:              # the card's own tone per row, blended in from the art
            lo, fade = spec['tone']
            src = im.load()
            for y in range(qh):
                near = range(max(0, y - 7), min(qh, y + 8))             # 15 rows: no streaks
                row = sorted(src[cx + x, cy + qy + yy] for yy in near for x in range(lo, qx))
                tone = row[len(row) // 2]
                for x in range(qw):
                    a = x / fade if x < fade else 1.0
                    keep = ((x * 7 + y * 3) % 8) / 8 >= a          # ordered dither across the fade
                    px[cx + qx + x, cy + qy + y] = art[qy + y][qx + x] if keep else tone
        elif 'mirror' in spec:            # the card's own art left of the label, reflected into it
            lo = spec['mirror']
            src = im.load()
            for y in range(qh):
                for x in range(qw):
                    k = (x + 1) % (2 * (qx - lo))
                    sx_ = qx - k if k <= qx - lo else lo + (k - (qx - lo))
                    px[cx + qx + x, cy + qy + y] = src[cx + sx_, cy + qy + y]
        else:
            for y in range(qh):
                for x in range(qw):
                    px[cx + qx + x, cy + qy + y] = art[qy + y][qx + x]
        if 'band' in spec:              # a dark band behind the word (the vote can't clean the strip)
            bx, by, bw, bh = spec['band']
            for y in range(bh):
                for x in range(bw):
                    px[cx + bx + x, cy + by + y] = spec['outline']
        m = word_mask(text.upper(), spec['font'], sh - 2 * ow, sw - 2 * ow, size)[0].rotate(-90, expand=True)
        ink = [[m.getpixel((x, y)) >= 110 for x in range(m.width)] for y in range(m.height)]
        ox, oy = cx + sx + ow, cy + sy + ow
        rows = [y for y in range(m.height) if any(ink[y])]
        top, bot = rows[0], rows[-1]
        for y in range(-ow, m.height + ow):
            for x in range(-ow, m.width + ow):
                inside = 0 <= y < m.height and 0 <= x < m.width and ink[y][x]
                if inside:
                    k = min(len(fills) - 1, (y - top) * len(fills) // max(1, bot - top + 1))
                    px[ox + x, oy + y] = fills[k]
                elif any(0 <= y + dy < m.height and 0 <= x + dx < m.width and ink[y + dy][x + dx]
                         for dy in range(-ow, ow + 1) for dx in range(-ow, ow + 1) if dx * dx + dy * dy <= ow * ow + 1):
                    px[ox + x, oy + y] = spec['outline']
    return [f'{len(texts)} cards, font size {size / SUPER:.1f} px'], 0


if __name__ == '__main__':
    import json
    import sys
    root = Path(__file__).resolve().parent.parent.parent
    if sys.argv[1:] != ['export']:
        sys.exit('usage: cards.py export')
    spec = json.loads((root / 'translation/letters/BATTLE_MATCH_2.json').read_text(encoding='utf-8'))
    export(Image.open(root / 'review/images-original/BATTLE_MATCH_2.png'), [tuple(c) for c in spec['cards']],
           root / 'build/work/cards')
    print('build/work/cards/: card_0..7.png (54x69), enlarged copies, card_all.png')
