#!/usr/bin/env python3
"""How a picture's sprites come together on screen (needs Pillow: run with .venv/bin/python).

  screenmock.py [IMAGE...] [--scale N]
      -> review/bounds/<IMAGE>_ingame.png: one row per scene in tools/layouts.json, one column
         per version (jp / cur / new / alt, as in translation/image-choices.csv)

tools/layouts.json (traced from the code) lists, per picture, scenes - a selection, the end of an
animation - and the draws that make each: texture rect, screen position and size, CLUT row for
4-bit pictures, alpha; a negative size means mirrored, running left/up from xy. Each draw is cut from the picture, scaled with bilinear filtering (the
game's TEX1) inside its own rect (the game clamps to it), and composited in drawing order over a
dark ground. Only this picture's draws are shown: whatever the game draws around or on top of them
is in each draw's "note". Use it to see cuts, seams and overlaps that only show on screen.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import choose  # noqa: E402
import clutview  # noqa: E402
import gfx  # noqa: E402
import paths  # noqa: E402

LAYOUTS = Path(__file__).resolve().parent / 'layouts.json'
FONT = Path(__file__).resolve().parent / 'fonts/Barlow-Medium.ttf'


def layouts():
    return json.loads(LAYOUTS.read_text(encoding='utf-8')) if LAYOUTS.exists() else {}


def sprite(id_, png, draw, pic):
    """RGBA of one draw's rect from png, in the game's colours."""
    u, v, w, h = draw['rect']
    if pic is not None:
        reg = {'rect': [u, v, w, h], 'row': draw.get('row', 0)}
        if 'clut' in draw:
            reg['clut'] = draw['clut']
        im = pic.draw(png, [reg])
    else:
        im = Image.open(png).convert('RGBA')
    im = im.crop((u, v, u + w, v + h))
    sw, sh = draw.get('wh', [w, h])
    if (round(abs(sw)), round(abs(sh))) != (w, h):
        im = im.resize((max(1, round(abs(sw))), max(1, round(abs(sh)))), Image.BILINEAR)
    if sw < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if sh < 0:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    a = draw.get('alpha')
    if a is not None and a < 128:
        im.putalpha(im.getchannel('A').point(lambda p: p * a // 128))
    return im


def scene_image(id_, png, scene, pic, box):
    size = scene.get('size', [640, 448])
    screen = Image.new('RGBA', tuple(size), (40, 34, 44, 255))
    for d in scene['draws']:
        im = sprite(id_, png, d, pic)
        x, y = d['xy']
        w, h = d.get('wh', d['rect'][2:])
        x, y = round(x + min(0, w)), round(y + min(0, h))      # negative size: mirrored, runs left/up
        layer = Image.new('RGBA', screen.size, (0, 0, 0, 0))
        layer.paste(im, (x, y))
        screen.alpha_composite(layer)
    return screen.crop(box)


def bbox(scenes, margin=12):
    xs, ys = [], []
    for s in scenes:
        for d in s['draws']:
            w, h = d.get('wh', d['rect'][2:])
            xs += [d['xy'][0], d['xy'][0] + w]
            ys += [d['xy'][1], d['xy'][1] + h]
    W, H = scenes[0].get('size', [640, 448])
    return (max(0, int(min(xs)) - margin), max(0, int(min(ys)) - margin),
            min(W, int(max(xs)) + margin), min(H, int(max(ys)) + margin))


def mock(id_, scale=2):
    lay = layouts().get(id_)
    if not lay:
        raise SystemExit(f'{id_}: no layout in {LAYOUTS.name}')
    meta = json.loads((paths.ORIGINAL_IMAGES / f'{id_}.json').read_text())
    pic = clutview.Picture(id_) if meta['psm'] == gfx.PSMT4 else None
    scenes = lay['scenes']
    vers = [(v, choose.version_path(id_, v)) for v in ('jp', 'cur', 'new', 'alt')]
    vers = [(v, p) for v, p in vers if p]
    font = ImageFont.truetype(str(FONT), 16)
    rows = []                                   # one row per scene: its name, then the versions
    for sc in scenes:
        box = bbox([sc])
        tiles = [scene_image(id_, p, sc, pic, box) for _, p in vers]
        tiles = [t.resize((t.width * scale, t.height * scale), Image.NEAREST) for t in tiles]
        rows.append((sc['name'], tiles))
    W = max(sum(t.width + 10 for t in ts) for _, ts in rows) + 10
    H = 26 + sum(22 + ts[0].height + 12 for _, ts in rows)
    sheet = Image.new('RGB', (max(W, 400), H), (18, 18, 22))
    d = ImageDraw.Draw(sheet)
    x = 10
    for (v, _), t in zip(vers, rows[0][1]):
        d.text((x, 4), v, fill=(255, 255, 255), font=font)
        x += t.width + 10
    y = 26
    for name, ts in rows:
        d.text((10, y), name, fill=(200, 210, 255), font=font)
        x = 10
        for t in ts:
            sheet.paste(t.convert('RGB'), (x, y + 22))
            x += t.width + 10
        y += 22 + ts[0].height + 12
    out = paths.REVIEW / 'bounds' / f'{id_}_ingame.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('images', nargs='*')
    ap.add_argument('--scale', type=int, default=2)
    a = ap.parse_args(argv)
    ids = a.images or sorted(layouts())
    for id_ in ids:
        print(paths.show(mock(id_, a.scale)))


if __name__ == '__main__':
    main()
