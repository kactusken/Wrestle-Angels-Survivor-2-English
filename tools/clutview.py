#!/usr/bin/env python3
"""4-bit pictures in the colours the game draws them (needs Pillow: run with .venv/bin/python).

  clutview.py [IMAGE...] [--from DIR] [--scale N]
      -> review/images-view/<id>.png: original | English, each drawn region by region in its CLUT
         row (second band: the other state, e.g. selected, when a region has two rows)

A 4-bit (PSMT4) picture is uploaded with a full 256-colour CLUT, and the game picks a 16-colour row
per sprite (TEX0.CSA). Row n is the 8-bit palette's entries 16n..16n+15 in CSM1 order (gfx.swizzle),
because the game loads the CLUT through the 8-bit picture first. tools/gfx.py exports only one
palette, so review/images-original and images-english show these pictures in the wrong colours;
the indices themselves are right. Which row each region uses is in tools/clutrows.json (traced from
the code: evidence, confidence; "clut" when a region uses another file's CLUT).
Pixels outside every listed region are shown dimmed in row 0: the game does not draw them from
this picture (or the region wasn't found). --from DIR shows DIR/<id>.png instead of the build's
English (e.g. an attempt in progress). docs/TECHNICAL.md "Images".
"""
import argparse
import json
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gfx  # noqa: E402
import paths  # noqa: E402

ROWS = Path(__file__).resolve().parent / 'clutrows.json'


def clut_entries(data, offset, psm):
    out = []
    for i in range(256):
        if psm == gfx.PSMCT16:
            v = struct.unpack_from('<H', data, offset + 2 * i)[0]
            out.append(((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 255 if v >> 15 else 0))
        else:
            r, g, b, a = struct.unpack_from('<4B', data, offset + 4 * i)
            out.append((r, g, b, min(255, a * 2)))
    return out


def row_colours(entries, row):
    return [entries[gfx.swizzle(16 * row + k)] for k in range(16)]


class Picture:
    def __init__(self, id_):
        meta = json.loads((paths.ORIGINAL_IMAGES / f'{id_}.json').read_text())
        if meta['psm'] != gfx.PSMT4:
            raise SystemExit(f'{id_} is not a 4-bit picture: nothing to do')
        data = (paths.EXTRACTED / meta['file'].lstrip('/')).read_bytes()
        self.own = clut_entries(data, meta['clut'], meta['clut_psm'])
        self.regions = json.loads(ROWS.read_text(encoding='utf-8')).get(id_, [])
        self.other = {}

    def entries(self, region):
        c = region.get('clut')
        if not c:
            return self.own
        if c['file'] not in self.other:
            self.other[c['file']] = clut_entries((paths.EXTRACTED / c['file'].lstrip('/')).read_bytes(),
                                                 c['offset'], c.get('psm', gfx.PSMCT32))
        return self.other[c['file']]

    def states(self):
        """[[region...]] - first state: the first row listed per rectangle; second: the last (if any differ)."""
        first, last = {}, {}
        for r in self.regions:
            k = tuple(r['rect'])
            first.setdefault(k, r)
            last[k] = r
        a, b = list(first.values()), list(last.values())
        return [a] if a == b else [a, b]

    def draw(self, png, regions):
        im = Image.open(png)
        if im.mode != 'P':
            raise SystemExit(f'{png}: not an indexed PNG (pixel values must be the game\'s indices)')
        idx = im.load()
        w, h = im.size
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        px = out.load()
        dim = row_colours(self.own, 0)
        for y in range(h):
            for x in range(w):
                r, g, b, a = dim[idx[x, y] & 15]
                px[x, y] = (r // 3, g // 3, b // 3, a // 2)
        for reg in regions:
            cols = row_colours(self.entries(reg), reg['row'])
            x0, y0, rw, rh = reg['rect']
            for y in range(max(0, y0), min(h, y0 + rh)):
                for x in range(max(0, x0), min(w, x0 + rw)):
                    px[x, y] = cols[idx[x, y] & 15]
        return out


def checker(size, sq=8):
    im = Image.new('RGB', size, (52, 52, 58))
    d = ImageDraw.Draw(im)
    for y in range(0, size[1], sq):
        for x in range((y // sq) % 2 * sq, size[0], sq * 2):
            d.rectangle([x, y, x + sq - 1, y + sq - 1], fill=(70, 70, 78))
    return im


def view(id_, english_dir=None, scale=2):
    pic = Picture(id_)
    eng = Path(english_dir or paths.ENGLISH_IMAGES) / f'{id_}.png'
    bands = []
    for regions in pic.states():
        tiles = [pic.draw(paths.ORIGINAL_IMAGES / f'{id_}.png', regions)]
        if eng.exists():
            tiles.append(pic.draw(eng, regions))
        tiles = [t.resize((t.width * scale, t.height * scale), Image.NEAREST) for t in tiles]
        band = Image.new('RGB', (sum(t.width + 8 for t in tiles), max(t.height for t in tiles)), (20, 20, 24))
        x = 0
        for t in tiles:
            bg = checker(t.size)
            bg.paste(t, (0, 0), t)
            band.paste(bg, (x, 0))
            x += t.width + 8
        bands.append(band)
    sheet = Image.new('RGB', (max(b.width for b in bands), sum(b.height + 8 for b in bands)), (20, 20, 24))
    y = 0
    for b in bands:
        sheet.paste(b, (0, y))
        y += b.height + 8
    return sheet


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('images', nargs='*')
    ap.add_argument('--from', dest='src', help='folder with the English versions to show')
    ap.add_argument('--scale', type=int, default=2)
    a = ap.parse_args(argv)
    ids = a.images or sorted(json.loads(ROWS.read_text(encoding='utf-8')))
    out = paths.REVIEW / 'images-view'
    out.mkdir(parents=True, exist_ok=True)
    for id_ in ids:
        view(id_, a.src, a.scale).save(out / f'{id_}.png')
    print(f'{len(ids)} picture(s) -> {paths.show(out)}')


if __name__ == '__main__':
    main()
