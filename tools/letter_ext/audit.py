"""Lettering for pictures found by the `audit` batch (spec "draw": "audit.draw").

letter.draw_group() working on palette indices only, for 4bpp pictures whose PNG palette is just
one of the CLUT's 16 rows (the game picks another row, so colours can't be trusted), and for
labels on buttons:

  fill      palette indices of the letter fill (required; no 'bright')
  grad      true: the fill is sampled row by row from the Japanese letters (by height between the
            ink's top and bottom) and laid on the English the same way; else the most common index
  ground    'rows'   each row of the box takes the most common index of the original row at the
                     columns `ground_cols` (a clean strip of the button, absolute x; default: the
                     whole box; 'edges': the two columns either side of the box), not counting the fill and `ground_skip` indices
                     (`ground_default` when nothing else is left)
            'split'  `split`: [x, left index, edge index, right index] - flat two-tone bar
            'copy'   the box is copied from the original at box + `ground_off` [dx, dy]
            'inpaint' only the old letters' pixels (`fill`, grown by `inpaint_grow`, default 3)
                     are rebuilt from the colours around them - for letters on art
            'transparent' | 'interpolate'   as in letter.py
  reach     outline width in px; the outline indices are learnt by distance from the fill
            (most common index at each distance), or given as `ring`: [index at d=1, d=2, ...]
  hollow    true: the letters themselves are not drawn (left as ground) - with `ring` and
            `ring_from` (px), for a glow sprite drawn around letters that sit in another sprite
  rotate    'cw' / 'ccw': vertical text, letters turned 90 degrees clockwise (read top to
            bottom) / anticlockwise (read bottom to top)
  shadow    {'offset': [dx, dy], 'index': n}: a drop shadow in palette index n
  clear     more [x, y, w, h] areas cleared like the boxes, or [x, y, w, h, dx, dy] copied from
            the original at +dx, +dy (patching letters that reach into a plate);  cap, font, align, upper, pad as in
            letter.py
"""
from collections import Counter, defaultdict

import letter


def ground_fill(im, out, box, spec, limit, pal):
    x, y, w, h = box
    mode = spec['ground']
    pad = spec.get('pad', 0)
    x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(out.width, x + w + pad), min(out.height, y + h + pad)
    src, dst = im.load(), out.load()
    if mode == 'rows':
        cols = spec.get('ground_cols') or range(x0, x1)
        if cols == 'edges':
            cols = [c for c in (x0 - 2, x0 - 1, x1, x1 + 1) if 0 <= c < im.width]
        skip = set(spec['fill']) | set(spec.get('ground_skip', []))
        for j in range(y0, y1):
            got = Counter(src[c, j] for c in cols if src[c, j] not in skip)
            idx = got.most_common(1)[0][0] if got else spec.get('ground_default', src[cols[0], j])
            for i in range(x0, x1):
                dst[i, j] = idx
    elif mode == 'split':     # `split`: [x, left index, edge index, right index] - a two-tone bar
        sx, left, edge, right = spec['split']
        for j in range(y0, y1):
            for i in range(x0, x1):
                dst[i, j] = left if i < sx else edge if i == sx else right
    elif mode == 'copy':
        dx, dy = spec['ground_off']
        for j in range(y0, y1):
            for i in range(x0, x1):
                dst[i, j] = src[i + dx, j + dy]
    elif mode == 'inpaint':
        # only the old lettering (fill pixels, grown by `inpaint_grow` px) is replaced, from the
        # pixels around it, ring by ring - the picture behind (gradients, streaks) stays
        grow = spec.get('inpaint_grow', 3)
        fills = set(spec['fill'])
        seed = [(i, j) for j in range(y0, y1) for i in range(x0, x1) if src[i, j] in fills]
        hole = set()
        for i, j in seed:
            for jj in range(j - grow, j + grow + 1):
                for ii in range(i - grow, i + grow + 1):
                    if x0 <= ii < x1 and y0 <= jj < y1:
                        hole.add((ii, jj))
        col = {}
        while hole:
            done = {}
            for i, j in hole:
                nb = [col.get((ii, jj)) or pal[dst[ii, jj]] for ii in (i - 1, i, i + 1) for jj in (j - 1, j, j + 1)
                      if (ii, jj) not in hole and 0 <= ii < out.width and 0 <= jj < out.height]
                if nb:
                    done[(i, j)] = tuple(sum(c[k] for c in nb) / len(nb) for k in range(4))
            if not done:
                break
            col.update(done)
            hole -= set(done)
        cache = {}
        for (i, j), c in col.items():
            c = tuple(round(v) for v in c)
            if c not in cache:
                cache[c] = letter.nearest(pal, c, limit)
            dst[i, j] = cache[c]
    else:
        letter.clear(out, pal, (x0, y0, x1 - x0, y1 - y0), mode, limit)


def learn(im, boxes, fills, reach):
    """(ring: {distance step: index}, gradient: [(rel height, index)], flat fill index)"""
    px = im.load()
    rings, grad, flat = defaultdict(Counter), defaultdict(Counter), Counter()
    for x, y, w, h in boxes:
        mask = [[px[x + i, y + j] in fills for i in range(w)] for j in range(h)]
        ink = [j for j in range(h) if any(mask[j])]
        if not ink:
            continue
        top, bot = ink[0], ink[-1]
        dist = letter.distances(mask, w, h, max(8, int(reach) + 2))
        for j in range(h):
            for i in range(w):
                v = px[x + i, y + j]
                if mask[j][i]:
                    flat[v] += 1
                    grad[round(16 * (j - top) / max(1, bot - top))][v] += 1
                elif dist[j][i] <= reach:
                    rings[round(dist[j][i] / letter.STEP)][v] += 1
    ring = {k: c.most_common(1)[0][0] for k, c in rings.items()}
    gradient = {k: c.most_common(1)[0][0] for k, c in grad.items()}
    return ring, gradient, flat.most_common(1)[0][0]


def draw(name, im, out, pal, texts, boxes, spec):
    limit = len(pal)
    fills = set(spec['fill'])
    reach = spec.get('reach', 1.5)
    ring, gradient, flat = learn(im, boxes, fills, reach)
    if 'ring' in spec:
        ring = {}
        start = spec.get('ring_from', 0)     # hollow glow: nothing nearer than this
        for k in range(1, int(reach / letter.STEP) + 1):
            d = k * letter.STEP - start
            if d > 0:
                ring[k] = spec['ring'][min(len(spec['ring']) - 1, max(0, round(d + 0.49) - 1))]
    ring = {k: v for k, v in ring.items() if 0 < k * letter.STEP <= reach}
    for box in boxes:
        ground_fill(im, out, box, spec, limit, pal)
    for box in spec.get('clear', []):
        if len(box) == 6:   # [x, y, w, h, dx, dy]: copied from the original at +dx, +dy
            ground_fill(im, out, box[:4], {**spec, 'ground': 'copy', 'ground_off': box[4:], 'pad': 0}, limit, pal)
        else:
            ground_fill(im, out, box, spec, limit, pal)
    r = int(reach)
    inner = [(w - 2 * r, h - 2 * r) for _, _, w, h in boxes]
    cap = spec.get('cap') or 10
    rot = spec.get('rotate')
    if rot:     # vertical text: measured along the box's height
        inner = [(ih, iw) for iw, ih in inner]
    for text, (iw, ih) in zip(texts, inner):
        if text != '=':
            got = letter.text_mask(text, spec['font'], min(cap, ih), iw, ih, slack=r)
            if got is None:
                raise SystemExit(f'letter: {name}: {text!r} does not fit {iw}x{ih}')
            cap = min(cap, got[1])
    notes = []
    px = out.load()
    for box, text, (iw, ih) in zip(boxes, texts, inner):
        if text == '=':
            continue
        x, y, w, h = box
        mask, size, squeeze = letter.text_mask(text, spec['font'], cap, iw, ih, spec.get('align', 'center'), r)
        if squeeze < 1:
            notes.append(f'{text!r}: squeezed to {squeeze:.0%}')
        full = [[False] * w for _ in range(h)]
        if rot == 'cw':     # letters' tops face right, read top to bottom
            for j in range(min(len(mask), w - r)):
                for i in range(iw):
                    if mask[j][i]:
                        full[i + r][w - 1 - r - j] = True
        elif rot == 'ccw':  # letters' tops face left, read bottom to top
            for j in range(min(len(mask), w - r)):
                for i in range(iw):
                    if mask[j][i]:
                        full[h - 1 - r - i][j + r] = True
        else:
            for j in range(min(len(mask), h - r)):
                for i in range(iw):
                    full[j + r][i + r] = mask[j][i]
        ink = [j for j in range(h) if any(full[j])]
        top, bot = (ink[0], ink[-1]) if ink else (0, h)
        dist = letter.distances(full, w, h, max(8, int(reach) + 2))
        if spec.get('shadow'):      # drop shadow: {'offset': [dx, dy], 'index': palette index}
            (sx, sy), sidx = spec['shadow']['offset'], spec['shadow']['index']
            for j in range(h):
                for i in range(w):
                    if full[j][i]:
                        for k in range(1, max(abs(sx), abs(sy)) + 1):
                            ii, jj = i + round(sx * k / max(abs(sx), abs(sy))), j + round(sy * k / max(abs(sx), abs(sy)))
                            if 0 <= ii < w and 0 <= jj < h and not full[jj][ii]:
                                px[x + ii, y + jj] = sidx
        for j in range(h):
            for i in range(w):
                if full[j][i]:
                    if spec.get('hollow'):
                        continue
                    if spec.get('grad'):
                        k = round(16 * (j - top) / max(1, bot - top))
                        px[x + i, y + j] = gradient.get(k, flat)
                    else:
                        px[x + i, y + j] = spec.get('fill_index', flat)
                else:
                    k = round(dist[j][i] / letter.STEP)
                    if k in ring:
                        px[x + i, y + j] = ring[k]
    notes.insert(0, f'capitals {cap} px')
    return notes, cap
