#!/usr/bin/env python3
"""Pick which version of each image goes into the game (needs Pillow: run with .venv/bin/python).

  choose.py table                  write or refresh translation/image-choices.csv (keeps your
                                   picks and notes); edit its "pick" column
  choose.py export IMAGE [VERSION] [--force]
                                   put one version in translation/images-handmade/ to edit by hand:
                                   IMAGE.png (edit this), IMAGE_original.png, IMAGE_bounds.png (a
                                   guide layer: put it over the image) and IMAGE_bounds_view.png
                                   (4x, in the game's colours, guide drawn on). VERSION defaults to
                                   the row's pick, else cur.
  choose.py view [IMAGE...] [--version V] [--scale N]
                                   just look: review/bounds/<IMAGE>.png - the picture (V, default
                                   cur) in game colours with every sprite outlined and numbered, and
                                   a list of the sprites underneath (what the code draws each for);
                                   4-bit pictures show the normal and selected states side by side
  choose.py check [IMAGE...] [--version V]
                                   is each pick (or V) inside the game's sprites? (tools/bounds.py;
                                   default: every row with a pick). The table's "bounds" column has
                                   the same per version: ok, outside (drawn where the game never
                                   shows it), spill (reaching into another sprite); empty = not traced
  choose.py apply [IMAGE...] [--dry-run] [--force]
                                   install the picks not installed yet (default: all)

Versions (the "pick" column; empty = not decided, nothing happens):
  cur   what the build has now            new   the improved attempt
  alt   the attempt with other wording    mine  your hand edit (choose.py export, then edit)
  jp    keep the Japanese original (the row becomes "keep" in graphics.csv)
"options" lists the versions an image has; contact sheets show them side by side under the same
names (build/work/imgfix/sheets.py). Attempts live in translation/images-candidates/
(<IMAGE>__new.png, __alt.png; candidates.json has a note and the spec each was drawn from).

apply: new/alt copy the attempt to images-handmade/ and approve it (tools/edit.py approve: snapped
to the palette, moved to images-approved/, graphics.csv marked done) and install its spec into
translation/letters/ (graphics.csv's English and boxes follow); mine approves your hand edit; jp
sets the row to keep; cur changes nothing. Every version is checked with tools/bounds.py first:
a version that draws outside the game's sprites is refused unless --force. The "installed" column
records what went in.
"""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bounds  # noqa: E402
import catalog  # noqa: E402
import edit  # noqa: E402
import paths  # noqa: E402

VERSIONS = ('cur', 'new', 'alt', 'mine', 'jp')
COLUMNS = ['image', 'pick', 'suggest', 'options', 'bounds', 'review', 'attempt', 'notes', 'installed']


def choices_csv():
    return paths.TRANSLATION / 'image-choices.csv'


def candidates_dir():
    return paths.TRANSLATION / 'images-candidates'


def candidates():
    f = candidates_dir() / 'candidates.json'
    return json.loads(f.read_text(encoding='utf-8')) if f.exists() else {}


def version_path(id_, v):
    """The PNG for version v of image id_, or None."""
    if v == 'cur':
        tag, p = catalog.own_source(id_)
        p = paths.APPROVED / f'{id_}.png' if tag == 'HAND' else p    # a hand edit isn't "cur"
        return p if p and p.exists() else None
    if v in ('new', 'alt'):
        p = candidates_dir() / f'{id_}__{v}.png'
        return p if p.exists() else None
    if v == 'mine':
        p = catalog.handmade_png(id_)
        return p if p.exists() else None
    if v == 'jp':
        return catalog.original_png(id_)
    raise SystemExit(f'unknown version {v!r}: use one of {", ".join(VERSIONS)}')


def options(id_):
    return [v for v in VERSIONS if version_path(id_, v)]


def read_choices():
    f = choices_csv()
    if not f.exists():
        raise SystemExit(f'{paths.show(f)} not found: run choose.py table')
    return list(csv.DictReader(open(f, encoding='utf-8', newline='')))


def write_choices(rows):
    with open(choices_csv(), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, COLUMNS, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in COLUMNS})


def bounds_summary(id_, sprites):
    """'cur ok, new outside+spill' - the bounds check per version; '' when the picture isn't traced."""
    if id_ not in sprites:
        return ''
    if not bounds.rects(id_, sprites):
        return 'never drawn by the game'
    out = []
    for v in options(id_):
        if v == 'jp':
            continue
        probs = [k for k, _ in bounds.check(id_, version_path(id_, v), sprites, boxes=False)
                 if k not in bounds.NOTES]
        out.append(f'{v} ' + ('+'.join(sorted(set(probs))) if probs else 'ok'))
    return ', '.join(out)


def table():
    old = {r['image']: r for r in read_choices()} if choices_csv().exists() else {}
    cand = candidates()
    sprites = bounds.sprite_table()
    rows = []
    for r in catalog.rows():
        id_ = r['image']
        if r['status'] not in ('done', 'keep') or r['dup_of']:
            continue
        c = cand.get(id_, {})
        prev = old.get(id_, {})
        rows.append({'image': id_, 'pick': prev.get('pick', ''), 'suggest': c.get('suggest', ''),
                     'options': ' '.join(options(id_)), 'bounds': bounds_summary(id_, sprites),
                     'review': c.get('review', ''),
                     'attempt': ' | '.join(f'{k}: {c[f]}' for k, f in (('cur', 'cur_issue'), ('new', 'attempt'),
                                                                          ('alt', 'alt_note')) if c.get(f)),
                     'notes': prev.get('notes', ''),
                     'installed': prev.get('installed', '')})
    rows.sort(key=lambda r: (r['image'].startswith('SYS_GM_CHR_'), not r['options'].count(' new'),
                             int(r['image'].rsplit('_', 1)[1]) if r['image'].startswith('SYS_GM_CHR_') else 0,
                             r['image']))
    write_choices(rows)
    n = sum(1 for r in rows if ' new' in r['options'])
    print(f'{paths.show(choices_csv())}: {len(rows)} images, {n} with an attempt; fill in "pick" '
          f'({" / ".join(VERSIONS)}), then: .venv/bin/python tools/choose.py apply')


def game_views(id_, png, scale=4):
    """[RGBA...] of png as the game shows it, scaled: one per state for 4-bit pictures (normal,
    then selected when a region has a second CLUT row), else one."""
    meta = json.loads((paths.ORIGINAL_IMAGES / f'{id_}.json').read_text())
    if meta['psm'] == 0x14 and id_ in bounds.sprite_table():
        import clutview
        pic = clutview.Picture(id_)
        ims = [pic.draw(png, st) for st in pic.states()]
    else:
        ims = [Image.open(png).convert('RGBA')]
    return [im.resize((im.width * scale, im.height * scale), Image.NEAREST) for im in ims]


def preview(id_, png, guide, out, scale=4, legend=False):
    """The picture in game colours with the guide layer drawn on; with legend, every sprite
    numbered and listed underneath (rect and what the code draws it for)."""
    views = game_views(id_, png, scale)
    g = Image.open(guide).convert('RGBA').resize(views[0].size, Image.NEAREST)
    regs = {}
    for r in bounds.sprite_table().get(id_, []):
        regs.setdefault(tuple(r['rect']), []).append(r)
    names = ['normal', 'selected'] if len(views) > 1 else ['']
    lines = []
    if legend:
        for i, (rect, rs) in enumerate(regs.items(), 1):
            notes = '; '.join(dict.fromkeys(
                r.get('note', '') + (f' (CLUT row {r["row"]})' if 'row' in r else '') for r in rs))
            lines.append(f'{i:>3}  {rect[0]},{rect[1]} {rect[2]}x{rect[3]}  {notes}'[:170])
        if not regs:
            lines.append('no sprites: ' + ('the game never draws this picture' if id_ in bounds.sprite_table()
                                            else 'not traced'))
    font = ImageFont.truetype(str(Path(__file__).resolve().parent / 'fonts/Barlow-Medium.ttf'), 15)
    gap, head, lh = 12, 24, 19
    W = max(sum(v.width + gap for v in views) - gap, 900 if legend else 0)
    H = head + views[0].height + (len(lines) * lh + 12 if lines else 0)
    sheet = Image.new('RGBA', (W, H), (24, 24, 28, 255))
    d = ImageDraw.Draw(sheet)
    x = 0
    for v, name in zip(views, names):
        bg = Image.new('RGBA', v.size, (60, 60, 66, 255))
        dd = ImageDraw.Draw(bg)
        for y in range(0, bg.height, 16):
            for xx in range((y // 16) % 2 * 16, bg.width, 32):
                dd.rectangle([xx, y, xx + 15, y + 15], fill=(80, 80, 88, 255))
        bg.alpha_composite(v)
        bg.alpha_composite(g)
        if legend:
            dd = ImageDraw.Draw(bg)
            for i, rect in enumerate(regs, 1):
                tx, ty = rect[0] * scale + 3, rect[1] * scale + 2
                dd.rectangle([tx - 1, ty - 1, tx + 9 * len(str(i)) + 2, ty + 16], fill=(255, 0, 0, 255))
                dd.text((tx + 1, ty - 1), str(i), fill=(255, 255, 255, 255), font=font)
        sheet.alpha_composite(bg, (x, head))
        d.text((x + 2, 3), f'{id_} {name}', fill=(220, 220, 220, 255), font=font)
        x += v.width + gap
    y = head + views[0].height + 8
    for line in lines:
        d.text((4, y), line, fill=(220, 220, 220, 255), font=font)
        y += lh
    sheet.save(out)


def view(ids, v=None, scale=4):
    out = paths.REVIEW / 'bounds'
    out.mkdir(parents=True, exist_ok=True)
    table_ = bounds.sprite_table()
    ids = ids or sorted(table_)
    for id_ in ids:
        src = version_path(id_, v or 'cur') or catalog.original_png(id_)
        guide = out / f'{id_}_bounds.png'
        bounds.guide(id_, guide)
        preview(id_, src, guide, out / f'{id_}.png', scale if len(ids) == 1 else min(scale, 2), legend=True)
    print(f'{len(ids)} picture(s) -> {paths.show(out)}/<IMAGE>.png (numbered sprites, list underneath; '
          f'<IMAGE>_bounds.png is the guide layer)')


def export(id_, v, force=False):
    v = v or next((r['pick'] for r in read_choices() if r['image'] == id_ and r['pick']), '') \
        if choices_csv().exists() else v
    v = v or 'cur'
    src = version_path(id_, v)
    if src is None:
        raise SystemExit(f'{id_} has no version {v!r} (it has: {" ".join(options(id_))})')
    paths.HANDMADE.mkdir(parents=True, exist_ok=True)
    dst = catalog.handmade_png(id_)
    if dst.exists() and v != 'mine' and not force:
        raise SystemExit(f'{paths.show(dst)} exists (a hand edit in progress): finish it, or --force to replace it')
    if v != 'mine':
        shutil.copyfile(src, dst)
    shutil.copyfile(catalog.original_png(id_), paths.HANDMADE / f'{id_}_original.png')
    guide = paths.HANDMADE / f'{id_}_bounds.png'
    n = bounds.guide(id_, guide)
    preview(id_, dst, guide, paths.HANDMADE / f'{id_}_bounds_view.png', legend=True)
    print(f'{id_}: version {v} -> {paths.show(dst)} (edit this; same size, the game\'s palette)')
    print(f'  guide layer {id_}_bounds.png: {n} sprite(s) - red tint = never drawn, red line = sprite edge '
          f'(inside it), cyan dots = label boxes' if n else
          f'  no sprite rectangles traced for {id_}: the guide only shows the label boxes')
    print(f'  preview {id_}_bounds_view.png; when done: choose.py check {id_}, set its pick to "mine", '
          f'choose.py apply {id_}')


def check_one(id_, v):
    p = version_path(id_, v)
    if p is None:
        return [('missing', f'no version {v!r}')]
    if v == 'jp':
        return []
    probs = bounds.check(id_, p, boxes=False)
    return [x for x in probs if x[0] not in bounds.NOTES]


def check(ids, version=None):
    rows = read_choices()
    sel = [r for r in rows if (r['image'] in ids if ids else r['pick'])]
    bad = 0
    for r in sel:
        v = version or r['pick'] or 'cur'
        probs = check_one(r['image'], v)
        if probs and probs[0][0] == 'untraced':
            print(f"{r['image']} ({v}): not traced - can't check")
            continue
        if probs:
            bad += 1
        print(f"{r['image']} ({v}): " + ('OK' if not probs else '\n  ' + '\n  '.join(f'{k}: {m}' for k, m in probs)))
    print(f'{len(sel)} checked, {bad} with problems')
    return 1 if bad else 0


def install_spec(id_, v):
    spec = candidates().get(id_, {}).get(v, {}).get('spec')
    if not spec:
        return False
    src = candidates_dir() / spec
    shutil.copyfile(src, paths.TRANSLATION / 'letters' / f'{id_}.json')
    s = json.loads(src.read_text(encoding='utf-8'))
    table_ = catalog.rows()
    row = catalog.by_id(table_)[id_]
    if 'english' in s:
        row['english'] = s['english']
    if 'boxes' in s:
        row['boxes'] = ';'.join(','.join(str(v) for v in b) for b in s['boxes'])
    catalog.write_rows(table_)
    return True


def set_keep(id_):
    table_ = catalog.rows()
    row = catalog.by_id(table_)[id_]
    row['status'] = 'keep'
    if 'kept Japanese (image-choices.csv)' not in row['notes']:
        row['notes'] = (row['notes'] + '; ' if row['notes'] else '') + 'kept Japanese (image-choices.csv)'
    catalog.write_rows(table_)


def apply(ids, dry=False, force=False):
    rows = read_choices()
    todo = [r for r in rows if r['pick'] and r['pick'] != r['installed'] and (not ids or r['image'] in ids)]
    if not todo:
        print('nothing to install (every pick is installed)')
        return 0
    failed = []
    for r in todo:
        id_, v = r['image'], r['pick'].strip()
        if v not in VERSIONS:
            print(f'{id_}: unknown pick {v!r} - use {", ".join(VERSIONS)}')
            failed.append(id_)
            continue
        if v in ('new', 'alt') and catalog.handmade_png(id_).exists():
            print(f'{id_}: a hand edit is in progress in images-handmade/ - pick "mine", or remove it first')
            failed.append(id_)
            continue
        probs = check_one(id_, v)
        if probs and probs[0][0] == 'missing':
            print(f'{id_}: {probs[0][1]} (it has: {" ".join(options(id_))})')
            failed.append(id_)
            continue
        real = [p for p in probs if p[0] != 'untraced']
        if real and not force:
            print(f'{id_} ({v}): not installed - outside the game\'s sprites (--force to install anyway):')
            for k, m in real:
                print(f'  {k}: {m}')
            failed.append(id_)
            continue
        if dry:
            print(f'{id_}: would install {v}' + (' (untraced: not checked)' if probs else ''))
            continue
        if v == 'cur':
            print(f'{id_}: keeps the current version')
        elif v == 'jp':
            set_keep(id_)
            print(f'{id_}: keeps the Japanese original (graphics.csv: keep)')
        else:
            if v != 'mine':
                paths.HANDMADE.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(version_path(id_, v), catalog.handmade_png(id_))
            if not edit.approve(id_, force=force):
                failed.append(id_)
                continue
            for s in ('_bounds', '_bounds_view'):
                (paths.HANDMADE / f'{id_}{s}.png').unlink(missing_ok=True)
            if v in ('new', 'alt') and install_spec(id_, v):
                print(f'  spec -> translation/letters/{id_}.json (graphics.csv English and boxes updated)')
        r['installed'] = v
        write_choices(rows)
    print(f'{len(todo) - len(failed)} of {len(todo)} installed' + (f'; not: {" ".join(failed)}' if failed else '')
          + ('' if dry else '; rebuild with python3 build.py'))
    return 1 if failed else 0


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('table')
    e = sub.add_parser('export')
    e.add_argument('image')
    e.add_argument('version', nargs='?')
    e.add_argument('--force', action='store_true')
    w = sub.add_parser('view')
    w.add_argument('images', nargs='*')
    w.add_argument('--version', choices=VERSIONS)
    w.add_argument('--scale', type=int, default=4)
    c = sub.add_parser('check')
    c.add_argument('images', nargs='*')
    c.add_argument('--version', choices=VERSIONS, help='check this version instead of the pick')
    a = sub.add_parser('apply')
    a.add_argument('images', nargs='*')
    a.add_argument('--dry-run', action='store_true')
    a.add_argument('--force', action='store_true')
    args = ap.parse_args(argv)
    if args.cmd == 'table':
        return table()
    if args.cmd == 'export':
        return export(args.image, args.version, args.force)
    if args.cmd == 'view':
        return view(args.images, args.version, args.scale)
    if args.cmd == 'check':
        return check(args.images, args.version)
    return apply(args.images, args.dry_run, args.force)


if __name__ == '__main__':
    sys.exit(main())
