#!/usr/bin/env python3
"""Do our image edits stay inside the sprites the game draws? (standard library only)

  bounds.py [IMAGE...] [--file PNG] [--verbose]
      check the build's English version of each image (default: every translated image with
      sprite data); --file checks that PNG instead (one IMAGE)
  bounds.py IMAGE --clip OUT [--file PNG]
      write OUT: the version clipped to its sprites - pixels past an edge back to the original's,
      spilled pieces filled from their own sprite (the letter stops at its sprite's edge, as the
      game cuts it, and nothing leaks next door)
  bounds.py --guide IMAGE [--out PNG]
      write a guide layer: same size as the picture, transparent where the game draws, red tint
      where it never draws, a red line on each sprite's edge (the line pixels are inside the
      sprite) and a cyan dotted line on our label boxes. Put it on a layer over the image.

A picture is often a sheet of sprites: the game cuts rectangles (u, v, w, h) out of it.
tools/sprites.json (8-bit pictures) and tools/clutrows.json (4-bit pictures) list them, traced
from the code (evidence and confidence per rect; an empty list = the game never draws it). Only pixels that differ from the original are
checked:
  outside   changed pixels just past a drawn rect: the game never shows them (a letter cut off)
  unseen    (note) changed pixels reaching far from any rect: a label the game never draws
  spill     a thin blob of visible pixels hugging a sprite's edge, with no body of its own in that
            sprite, that continues a bigger blob in the neighbouring sprite: a letter reaching
            across (the piece shows up when this sprite is drawn). Blobs are connected visible
            pixels, so this works where letters stand on transparency (menus); a letter on an
            opaque plate is part of the plate's blob and can't be told apart this way.
  split     lettering cut across two sprites that the game does not draw side by side at the same
            size (tools/layouts.json says which are; without a layout, only where the original's
            own pixels already run across): a word in pieces on screen. Each piece is a real part
            of a letter (thicker than a spill).
  hidden    (note) a sprite noticeably more covered on screen than the original's (another sprite of
            the same picture drawn on top of it, tools/layouts.json; a highlight copy laid exactly
            over its own label doesn't count). The game covers some labels on purpose - the front
            tile over its neighbours - so only more than the original counts.
  flat      (note) new lettering on a sprite's edge row or column where the original kept clear:
            its outline is cut flat on screen. Aim for none: keep the original's margin.
  touch     (note, not a failure) new letters that touch their sprite's edge: the part beyond is
            not drawn, so an outline may be cut flat. The originals do this too.
Colour changes are judged in the colours the game shows (4-bit pictures in their CLUT row).
  box       (note) one of our label boxes (graphics.csv) is not inside one drawn sprite (only for the
            build's own version: an attempt or hand edit may have moved its labels)
Exit status 1 if any image has a problem (outside, spill, split, size). docs/TECHNICAL.md "Images" / "Sprite rectangles".
"""
import argparse
import csv
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog  # noqa: E402
import paths  # noqa: E402
import gfx  # noqa: E402
import pngio  # noqa: E402

TOOLS = Path(__file__).resolve().parent
INK = 120                      # colour change (sum of |dR|+|dG|+|dB|) that counts as new ink
FLAT_MIN = 3                    # 'flat': this many edge pixels
HIDDEN_MORE = 10                # 'hidden': this many points more of a sprite covered than in the original
SPILL_DEPTH = 6                 # a piece hugging a sprite edge (thinner than this) that continues a letter
NOTES = ('touch', 'box', 'unused', 'unseen', 'hidden', 'flat')       # reported, but not a failure
SPRITE_FILES = (TOOLS / 'sprites.json', TOOLS / 'clutrows.json')
LAYOUTS = TOOLS / 'layouts.json'


def sprite_table():
    out = {}
    for f in SPRITE_FILES:
        if f.exists():
            for k, v in json.loads(f.read_text(encoding='utf-8')).items():
                out.setdefault(k, []).extend(v)
    return out


def rects(id_, table=None):
    """Distinct (x, y, w, h) the game samples from this picture, [] when not traced."""
    regs = (table if table is not None else sprite_table()).get(id_, [])
    seen = []
    for r in regs:
        t = tuple(r['rect'])
        if t not in seen:
            seen.append(t)
    return seen


def layouts():
    return json.loads(LAYOUTS.read_text(encoding='utf-8')) if LAYOUTS.exists() else {}


def joined(id_, lay=None):
    """{frozenset({rect, rect})}: sprites the game draws edge to edge at the same scale (layouts.json),
    so lettering may run from one into the other."""
    out = set()
    for sc in (lay if lay is not None else layouts()).get(id_, {}).get('scenes', []):
        ds = [(tuple(d['rect']), d['xy'], d.get('wh', d['rect'][2:])) for d in sc['draws']]
        for a in ds:
            for b in ds:
                (u1, v1, w1, h1), (x1, y1), (sw1, sh1) = a
                (u2, v2, w2, h2), (x2, y2), (sw2, sh2) = b
                if sw1 < 0 or sw2 < 0 or sh1 < 0 or sh2 < 0:
                    continue
                kx, ky = sw1 / w1, sh1 / h1
                if abs(sw2 / w2 - kx) > 1e-3 or abs(sh2 / h2 - ky) > 1e-3:
                    continue
                if (u1 + w1 == u2 and v1 == v2 and h1 == h2 and abs(x1 + sw1 - x2) < 0.5 and abs(y1 - y2) < 0.5) or \
                   (v1 + h1 == v2 and u1 == u2 and w1 == w2 and abs(y1 + sh1 - y2) < 0.5 and abs(x1 - x2) < 0.5):
                    out.add(frozenset((a[0], b[0])))
    return out


def covered(id_, alpha, lay=None):
    """{(x, y) of the picture: scene name}: texture pixels the game covers with a later, opaque draw
    of the same picture (layouts.json); alpha[y][x] is the picture's alpha."""
    out = {}
    for sc in (lay if lay is not None else layouts()).get(id_, {}).get('scenes', []):
        ds = sc['draws']
        for i, d in enumerate(ds):
            (u, v, w, h), (x0, y0) = d['rect'], d['xy']
            sw, sh = d.get('wh', [w, h])
            for e in ds[i + 1:]:
                if e.get('alpha', 128) < 100:
                    continue
                if list(e['xy']) == list(d['xy']) and list(e.get('wh', e['rect'][2:])) == [sw, sh]:
                    continue                    # the same item's highlight copy, laid exactly over it
                (eu, ev, ew, eh), (ex, ey) = e['rect'], e['xy']
                esw, esh = e.get('wh', [ew, eh])
                ax0, ax1 = x0 + min(0, sw), x0 + max(0, sw)
                ay0, ay1 = y0 + min(0, sh), y0 + max(0, sh)
                bx0, bx1 = ex + min(0, esw), ex + max(0, esw)
                by0, by1 = ey + min(0, esh), ey + max(0, esh)
                for sy in range(int(max(ay0, by0)), int(min(ay1, by1) + 0.999)):
                    for sx in range(int(max(ax0, bx0)), int(min(ax1, bx1) + 0.999)):
                        tx = eu + int((sx + 0.5 - ex) * ew / esw) if esw > 0 else eu + ew - 1 - int((ex - sx - 0.5) * ew / -esw)
                        ty = ev + int((sy + 0.5 - ey) * eh / esh) if esh > 0 else ev + eh - 1 - int((ey - sy - 0.5) * eh / -esh)
                        if not (eu <= tx < eu + ew and ev <= ty < ev + eh) or alpha[ty][tx] < 200:
                            continue
                        px = u + int((sx + 0.5 - x0) * w / sw) if sw > 0 else u + w - 1 - int((x0 - sx - 0.5) * w / -sw)
                        py = v + int((sy + 0.5 - y0) * h / sh) if sh > 0 else v + h - 1 - int((y0 - sy - 0.5) * h / -sh)
                        if u <= px < u + w and v <= py < v + h:
                            out.setdefault((px, py), sc['name'])
    return out


def clut(file, offset, psm):
    data = (paths.EXTRACTED / file.lstrip('/')).read_bytes()
    out = []
    for i in range(256):
        if psm == gfx.PSMCT16:
            v = struct.unpack_from('<H', data, offset + 2 * i)[0]
            out.append(((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 255 if v >> 15 else 0))
        else:
            r, g, b, a = struct.unpack_from('<4B', data, offset + 4 * i)
            out.append((r, g, b, min(255, a * 2)))
    return out


def rgba(id_, png, table):
    """Rows of (r, g, b, a) as the game shows the picture. 4-bit pictures: each pixel in the CLUT
    row of the first region that covers it (tools/clutrows.json, as tools/clutview.py), else row 0."""
    meta = json.loads((paths.ORIGINAL_IMAGES / f'{id_}.json').read_text())
    if meta['psm'] == gfx.PSMT4:
        own = clut(meta['file'], meta['clut'], meta['clut_psm'])
        lut = {}
        for reg in table.get(id_, []):
            c = reg.get('clut')
            ent = clut(c['file'], c['offset'], c.get('psm', gfx.PSMCT32)) if c else own
            lut.setdefault(tuple(reg['rect']), [ent[gfx.swizzle(16 * reg.get('row', 0) + k)] for k in range(16)])
        row0 = [own[gfx.swizzle(k)] for k in range(16)]
        rows = []
        for y, row in enumerate(png.rows):
            out = []
            for x, v in enumerate(row):
                cols = next((c for (rx, ry, rw, rh), c in lut.items() if rx <= x < rx + rw and ry <= y < ry + rh), row0)
                out.append(cols[v & 15])
            rows.append(out)
    elif png.palette is not None:
        alpha = png.alpha or []
        cols = [tuple(c) + ((alpha[i] if i < len(alpha) else 255),) for i, c in enumerate(png.palette)]
        rows = [[cols[v] for v in row] for row in png.rows]
    else:
        rows = [[(v, v, v, 255) if isinstance(v, int) else (v + (255,) if len(v) == 3 else v) for v in row]
                for row in png.rows]
    return [[(0, 0, 0, 0) if c[3] == 0 else c for c in row] for row in rows]


def check(id_, path, table=None, boxes=True, bad=None):
    """[(kind, message)] for the PNG at path against the original's sprites; the outside and spill
    pixels go into the dict `bad` ({(x, y): kind}) when one is given."""
    table = sprite_table() if table is None else table
    rs = rects(id_, table)
    if id_ in table and not rs:
        return [('unused', 'the game never draws this picture (tools/sprites.json)')]
    if not rs:
        return [('untraced', 'no sprite rectangles known (tools/sprites.json)')]
    o, n = pngio.read(catalog.original_png(id_)), pngio.read(path)
    if (o.width, o.height) != (n.width, n.height):
        return [('size', f'{n.width}x{n.height}, the original is {o.width}x{o.height}')]
    oc, nc = rgba(id_, o, table), rgba(id_, n, table)
    diff = {(x, y) for y in range(o.height) for x in range(o.width) if oc[y][x] != nc[y][x]}

    def key(p):
        x, y = p
        return frozenset(i for i, (rx, ry, rw, rh) in enumerate(rs) if rx <= x < rx + rw and ry <= y < ry + rh)

    keys = {p: key(p) for p in diff}
    out = []
    outside = [p for p, k in keys.items() if not k]
    cut, unseen = [], []
    for comp in components(outside):
        def gap(p):                             # distance to the nearest drawn rect
            x, y = p
            return min(max(rx - x, 0, x - (rx + rw - 1)) + max(ry - y, 0, y - (ry + rh - 1))
                       for rx, ry, rw, rh in rs)
        far = max(gap(p) for p in comp)
        (cut if far < SPILL_DEPTH else unseen).extend(comp)   # a thin overhang is a cut letter
    if bad is not None:
        bad.update({p: 'outside' for p in cut})
    if cut:
        out.append(('outside', f'{len(cut)} changed pixel(s) just past a sprite\'s edge, where the game never '
                               f'draws (a letter cut off): {span(cut)}'))
    if unseen:
        out.append(('unseen', f'{len(unseen)} changed pixel(s) in an area the game never draws at all, '
                              f'{span(unseen)}'))

    def ink(p):
        x, y = p
        c, d = oc[y][x], nc[y][x]
        return abs(c[3] - d[3]) >= 128 or (min(c[3], d[3]) and sum(abs(c[i] - d[i]) for i in range(3)) >= INK)

    # letters: blobs of visible pixels of the new picture, each within one sprite
    vis = {}
    for y in range(n.height):
        for x in range(n.width):
            if nc[y][x][3]:
                k = key((x, y))
                if k:
                    vis[(x, y)] = k
    comps = components(vis, same=lambda p, q: vis[p] == vis[q])
    comp_of = {p: i for i, c in enumerate(comps) for p in c}
    touch = 0
    for i, comp in enumerate(comps):
        if not any(p in diff for p in comp):
            continue                           # the original's own pixels
        home = vis[comp[0]]

        def depth(p):                          # distance to the nearest edge of its sprite
            x, y = p
            return min(min(x - rs[j][0], rs[j][0] + rs[j][2] - 1 - x, y - rs[j][1], rs[j][1] + rs[j][3] - 1 - y)
                       for j in home)
        if min(depth(p) for p in comp) > 0:
            continue
        touch += 1
        across = {comp_of[(x + dx, y + dy)] for x, y in comp for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if (x + dx, y + dy) in comp_of and vis[(x + dx, y + dy)] != home}
        big = [j for j in across if len(comps[j]) > len(comp)]
        if max(depth(p) for p in comp) < SPILL_DEPTH and big:
            src = comps[max(big, key=lambda j: len(comps[j]))]
            if bad is not None:
                bad.update({p: 'spill' for p in comp})
            out.append(('spill', f'{len(comp)} pixel(s) at {span(comp)} are a piece of a letter in the next '
                                 f'sprite ({span(src)}): they show up when this sprite is drawn'))
    # split: a substantial piece of new lettering on each side of the edge between two sprites
    # that are not drawn edge to edge, where the original's pixels don't already run across
    lay = layouts()
    join = joined(id_, lay)

    def depth_in(comp, home):
        return max(min(min(x - rs[j][0], rs[j][0] + rs[j][2] - 1 - x, y - rs[j][1], rs[j][1] + rs[j][3] - 1 - y)
                       for j in home) for x, y in comp)
    pairs = {}
    for (x, y), k in vis.items():
        for q in ((x + 1, y), (x, y + 1)):
            k2 = vis.get(q)
            if not k2 or k & k2:
                continue
            if not ((x, y) in diff or q in diff) or (oc[y][x][3] and oc[q[1]][q[0]][3]):
                continue
            if any(frozenset((rs[a], rs[b])) in join for a in k for b in k2):
                continue
            i, j = comp_of[(x, y)], comp_of[q]
            pairs.setdefault((min(i, j), max(i, j)), []).append((x, y))
    def piece(i, starts):                       # the changed pixels of blob i connected to the edge
        allowed = {p for p in comps[i] if p in diff}
        todo = [p for p in starts if p in allowed]
        seen = set(todo)
        while todo:
            x, y = todo.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in allowed and q not in seen:
                        seen.add(q)
                        todo.append(q)
        return seen
    for (i, j), pts in pairs.items():
        side = {i: set(), j: set()}
        for x, y in pts:
            for q in ((x, y), (x + 1, y), (x, y + 1)):
                if q in comp_of and comp_of[q] in side:
                    side[comp_of[q]].add(q)
        def body(pt):                           # letter body, not outline: visible all round (own sprite)
            x, y = pt
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    qx, qy = x + dx, y + dy
                    if not any(rs[j][0] <= qx < rs[j][0] + rs[j][2] and rs[j][1] <= qy < rs[j][1] + rs[j][3]
                               for j in vis[pt]):
                        continue                # past its own sprite's edge
                    if not nc[qy][qx][3]:
                        return False
            return True
        if sum(1 for x, y in pts for q in ((x + 1, y), (x, y + 1)) if q in vis and comp_of.get(q) in side
               and comp_of[q] != comp_of[(x, y)] and body((x, y)) and body(q)) < 3:
            continue                            # two labels' outlines meeting at the edge: each whole
        a, b = piece(i, side[i]), piece(j, side[j])
        if a and b and depth_in(a, vis[comps[i][0]]) >= SPILL_DEPTH and depth_in(b, vis[comps[j][0]]) >= SPILL_DEPTH:
            if bad is not None:
                bad.update({p: 'split' for p in pts})
            out.append(('split', f'lettering runs across a sprite edge at {span(pts)} ({len(pts)} px): '
                                 f'{span(comps[i])} | {span(comps[j])}; the game does not draw these two '
                                 f'sprites side by side at the same size'))
    if id_ in lay:                              # covered by the picture's own later draws, vs the original
        hn = covered(id_, [[c[3] for c in row] for row in nc], lay)
        ho = covered(id_, [[c[3] for c in row] for row in oc], lay)
        for rx, ry, rw, rh in rs:
            def share(img, cov):
                px = [(x, y) for y in range(ry, ry + rh) for x in range(rx, rx + rw) if img[y][x][3]]
                return (100 * sum(1 for q in px if q in cov) // len(px)) if px else 0
            a, b = share(oc, ho), share(nc, hn)
            if b > a + HIDDEN_MORE:
                scenes = sorted({hn[q] for q in hn if rx <= q[0] < rx + rw and ry <= q[1] < ry + rh})
                out.append(('hidden', f'sprite {rx},{ry},{rw},{rh}: {b}% of it is covered on screen, the '
                                      f'original {a}% ({"; ".join(scenes)})'))
    # flat: new lettering on a sprite's edge row/column where the original kept clear - cut flat on screen
    for rx, ry, rw, rh in rs:
        edges = {'top': [(x, ry) for x in range(rx, rx + rw)], 'bottom': [(x, ry + rh - 1) for x in range(rx, rx + rw)],
                 'left': [(rx, y) for y in range(ry, ry + rh)], 'right': [(rx + rw - 1, y) for y in range(ry, ry + rh)]}
        for side, pts in edges.items():
            pts = [(x, y) for x, y in pts if x < n.width and y < n.height]
            k = [(x, y) for x, y in pts if nc[y][x][3] > 64 and not oc[y][x][3] and (x, y) in diff]
            if len(k) >= FLAT_MIN:
                out.append(('flat', f'sprite {rx},{ry},{rw},{rh}: {len(k)} px of new lettering on its {side} edge, '
                                    f'where the original kept clear - cut flat on screen'))
    if touch:
        out.append(('touch', f'{touch} new letter(s) touch their sprite\'s edge (an outline may be cut flat)'))
    if boxes:
        for i, (bx, by, bw, bh) in enumerate(label_boxes(id_)):
            def inside(r):
                rx, ry, rw, rh = r
                return max(0, min(bx + bw, rx + rw) - max(bx, rx)) * max(0, min(by + bh, ry + rh) - max(by, ry))
            best = max((inside(r) for r in rs), default=0)
            if not best:
                out.append(('box', f'label box {i} ({bx},{by},{bw},{bh}) is in no drawn sprite'))
            elif best < bw * bh:
                r = next(r for r in rs if inside(r) == best)
                out.append(('box', f'label box {i} ({bx},{by},{bw},{bh}) sticks out of its sprite '
                                   f'{",".join(map(str, r))} by {bw * bh - best} px'))
    return out


def span(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return f'x {min(xs)}-{max(xs)} y {min(ys)}-{max(ys)}'


def components(pts, same=None):
    left, out = set(pts), []
    while left:
        start = left.pop()
        comp, todo = [start], [start]
        while todo:
            x, y = todo.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in left and (same is None or same((x, y), q)):
                        left.discard(q)
                        comp.append(q)
                        todo.append(q)
        out.append(comp)
    return out


def clip(id_, path, out, table=None):
    """Write path clipped to its sprites; returns how many pixels changed. Pixels past a sprite's
    edge (never drawn) go back to the original's; a spilled piece takes the colour of the nearest
    clean pixel of its own sprite, so the neighbour looks as if the letter had stopped at its edge.
    Both PNGs must be indexed with the same palette (approved images and attempts are)."""
    table = sprite_table() if table is None else table
    bad = {}
    check(id_, path, table, boxes=False, bad=bad)
    bad = {p: k for p, k in bad.items() if k != 'split'}      # a split word needs a redraw, not a clip
    o, n = pngio.read(catalog.original_png(id_)), pngio.read(path)
    if n.palette is None or list(n.palette) != list(o.palette):
        raise SystemExit(f'{path}: not indexed in the original palette - snap it first (edit.py approve)')
    rs = rects(id_, table)

    def key(x, y):
        return frozenset(i for i, (rx, ry, rw, rh) in enumerate(rs) if rx <= x < rx + rw and ry <= y < ry + rh)
    rows = [list(r) for r in n.rows]
    for (x, y), kind in bad.items():
        if kind == 'outside':
            rows[y][x] = o.rows[y][x]
            continue
        k = key(x, y)
        for d in range(1, 64):
            near = [(x + dx * d, y + dy * d) for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))]
            near = [(a, b) for a, b in near if 0 <= a < n.width and 0 <= b < n.height
                    and (a, b) not in bad and key(a, b) == k]
            if near:
                a, b = near[0]
                rows[y][x] = n.rows[b][a]
                break
        else:
            rows[y][x] = o.rows[y][x]
    pngio.write(out, rows, n.palette, n.alpha)
    return len(bad)


def label_boxes(id_):
    for r in csv.DictReader(open(paths.GRAPHICS_CSV, encoding='utf-8')):
        if r['image'] == id_:
            return [tuple(int(v) for v in b.split(',')) for b in r['boxes'].split(';') if b.strip()]
    return []


def guide(id_, out):
    """Write the guide layer for id_ (indexed PNG with transparency)."""
    o = pngio.read(catalog.original_png(id_))
    w, h = o.width, o.height
    rs = rects(id_)
    CLEAR, TINT, EDGE, BOX = 0, 1, 2, 3
    rows = [[TINT if rs else CLEAR] * w for _ in range(h)]
    for rx, ry, rw, rh in rs:
        for y in range(max(0, ry), min(h, ry + rh)):
            for x in range(max(0, rx), min(w, rx + rw)):
                if rows[y][x] == TINT:
                    rows[y][x] = CLEAR
    for rx, ry, rw, rh in rs:
        for x in range(max(0, rx), min(w, rx + rw)):
            for y in (ry, ry + rh - 1):
                if 0 <= y < h:
                    rows[y][x] = EDGE
        for y in range(max(0, ry), min(h, ry + rh)):
            for x in (rx, rx + rw - 1):
                if 0 <= x < w:
                    rows[y][x] = EDGE
    for bx, by, bw, bh in label_boxes(id_):
        for x in range(bx, bx + bw):
            for y in (by, by + bh - 1):
                if 0 <= x < w and 0 <= y < h and x % 2 == 0 and rows[y][x] != EDGE:
                    rows[y][x] = BOX
        for y in range(by, by + bh):
            for x in (bx, bx + bw - 1):
                if 0 <= x < w and 0 <= y < h and y % 2 == 0 and rows[y][x] != EDGE:
                    rows[y][x] = BOX
    pngio.write(out, rows, [(0, 0, 0), (255, 0, 0), (255, 0, 0), (0, 230, 255)], [0, 90, 255, 255])
    return len(rs)


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('images', nargs='*')
    ap.add_argument('--file', help='check this PNG instead of the build\'s English (one IMAGE)')
    ap.add_argument('--clip', metavar='OUT', help='write the version clipped to its sprites (one IMAGE)')
    ap.add_argument('--guide', metavar='IMAGE', help='write the guide layer for IMAGE')
    ap.add_argument('--out', help='where --guide writes (default review/bounds/<IMAGE>_bounds.png)')
    ap.add_argument('--verbose', action='store_true', help='also list untraced and clean images')
    a = ap.parse_args(argv)
    if a.guide:
        out = Path(a.out) if a.out else paths.REVIEW / 'bounds' / f'{a.guide}_bounds.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        n = guide(a.guide, out)
        print(f'{paths.show(out)}: {n} sprite rectangle(s)' + ('' if n else ' - none traced, nothing tinted'))
        return 0
    if a.clip:
        if len(a.images) != 1:
            raise SystemExit('--clip needs exactly one IMAGE')
        src = Path(a.file) if a.file else catalog.final_images()[a.images[0]][1]
        n = clip(a.images[0], src, Path(a.clip))
        print(f'{paths.show(Path(a.clip))}: {n} pixel(s) clipped')
        return 0
    if a.file and len(a.images) != 1:
        raise SystemExit('--file needs exactly one IMAGE (the id whose original to compare with)')
    table = sprite_table()
    final = catalog.final_images()
    ids = a.images or sorted(i for i in final if i in table)
    bad = untraced = 0
    for id_ in ids:
        path = Path(a.file) if a.file else (final.get(id_, (None, None))[1])
        if path is None:
            print(f'{id_}: no English version in the build')
            continue
        probs = check(id_, path, table, boxes=not a.file)
        if probs and probs[0][0] == 'untraced':
            untraced += 1
            if a.verbose or a.images:
                print(f'{id_}: {probs[0][1]}')
            continue
        if any(k not in NOTES for k, _ in probs):
            bad += 1
            print(f'{id_} ({paths.show(path)}):')
            for kind, msg in probs:
                print(f'  {kind}: {msg}')
        elif probs and (a.verbose or a.images):
            print(f'{id_}: OK; ' + '; '.join(m for _, m in probs))
        elif a.verbose or a.images:
            print(f'{id_}: OK')
    print(f'{len(ids)} image(s) checked, {bad} with problems' + (f', {untraced} untraced' if untraced else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
