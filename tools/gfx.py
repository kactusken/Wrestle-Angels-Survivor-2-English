#!/usr/bin/env python3
"""Game images: export every original and import the English ones.

  gfx.py export [OUT]      every image to OUT/<id>.png + <id>.json (default build/work/gfx)

The images are `.GSL` files (docs/TECHNICAL.md "Images"): DMA chains of GIF packets. Each upload
is set up by A+D register writes (BITBLTBUF 0x50, TRXPOS 0x51, TRXREG 0x52, TRXDIR 0x53 - the
upper bits of the register field hold junk) and followed by an IMAGE GIF tag with the pixels,
stored linearly. Pictures are PSMT8 (psm 0x13) or PSMT4 (psm 0x14); each is followed by its CLUT,
a 16x16 PSMCT32 upload (psm 0), 8-bit CLUTs in the usual CSM1 order (bits 3 and 4 of the index
swapped), alpha 0x80 = opaque.

Ids are `<folder>_<file>_<n>` (n = picture number in the file), e.g. SYS_MENU_0.

Some `.BIN` files (BIN_FILES) are packs of the same packets: a table of u32 entry offsets (ended
by 0 or by the first entry), one picture per entry. Their CLUTs may also be 16-bit (PSMCT16,
psm 2: 5-5-5 + alpha bit). Their ids number the entries: SYS_OPTION_1 = OPTION.BIN's entry 1.
CHAIN_FILES have no table: chains back to back, split where each starts (SYS_GM_CHR_n = chain n).

export_all(extracted, out) -> count
    out/<id>.png: indexed PNG, pixel value = the game's index, palette and tRNS from the CLUT;
    out/<id>.json: file, offset, width, height, psm.
import_images(images, files) -> count
    images: {id: indexed PNG in the original palette}; writes the indices back in place.
"""
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pngio  # noqa: E402

PSMT8, PSMT4, PSMCT32, PSMCT16 = 0x13, 0x14, 0x00, 0x02
BIN_FILES = ['/BATTLE/BT_LIST.BIN', '/SYS/OPTION.BIN', '/SYS/BEL.BIN', '/SYS/GALETC.BIN']
# packs with no table: DMA chains back to back (each starts with the same GIF set-up words)
CHAIN_FILES = ['/SYS/GM_CHR.BIN']
CHAIN_MARK = bytes.fromhex('acb81200')          # at +12 of every chain start (16-byte aligned)


def uploads(d):
    """[(registers, pixel offset, pixel bytes)] in file order."""
    out, i, n = [], 0, len(d)
    while i + 16 <= n:
        lo, _ = struct.unpack_from('<QQ', d, i)
        qwc = lo & 0xffff
        j, end, regs = i + 16, min(n, i + 16 + qwc * 16), {}
        while j + 16 <= end:
            glo, ghi = struct.unpack_from('<QQ', d, j)
            j += 16
            nloop, flg, nreg = glo & 0x7fff, (glo >> 58) & 3, ((glo >> 60) & 15) or 16
            if flg == 0:
                for _ in range(nloop):
                    for r in range(nreg):
                        if j + 16 > end:
                            break
                        data, addr = struct.unpack_from('<QQ', d, j)
                        j += 16
                        if (ghi >> (4 * r)) & 15 == 0xe:
                            regs[addr & 0xff] = data
            elif flg == 2:
                out.append((dict(regs), j, nloop * 16))
                j += nloop * 16
            else:
                j += nloop * 16
        i += 16 + qwc * 16
    return out


def info(regs):
    b, r = regs.get(0x50, 0), regs.get(0x52, 0)
    return {'psm': (b >> 56) & 63, 'w': r & 0xfff, 'h': (r >> 32) & 0xfff}


def swizzle(i):
    return (i & 0xe7) | ((i & 8) << 1) | ((i & 16) >> 1)


def pictures(d, clut_psms=(PSMCT32,)):
    """[(n, info, pixel offset, clut offset)] - every picture with the CLUT upload after it
    (info['clut_psm'] is the CLUT's format)."""
    ups = [(info(r), o, s) for r, o, s in uploads(d)]
    out = []
    for k, (inf, o, s) in enumerate(ups):
        if inf['psm'] not in (PSMT8, PSMT4):
            continue
        clut = next(((inf2, o2) for inf2, o2, _ in ups[k + 1:] if inf2['psm'] in clut_psms), None)
        if clut is not None:
            out.append((len(out), dict(inf, clut_psm=clut[0]['psm']), o, clut[1]))
    return out


def bin_entries(d):
    """[(start, end)] of a pack's entries (offset table at the start)."""
    first = struct.unpack_from('<I', d, 0)[0]
    offs = []
    for k in range(first // 4):
        v = struct.unpack_from('<I', d, 4 * k)[0]
        if v == 0:
            break
        offs.append(v)
    return [(a, offs[i + 1] if i + 1 < len(offs) else len(d)) for i, a in enumerate(offs)]


def bin_pictures(d):
    """Like pictures() for a pack: n = entry number, offsets in the whole file."""
    out = []
    for e, (a, b) in enumerate(bin_entries(d)):
        pics = pictures(d[a:b], (PSMCT32, PSMCT16))
        if pics:
            _, inf, o, c = pics[0]
            out.append((e, inf, a + o, a + c))
    return out


def chain_pictures(d):
    """Like bin_pictures() for a pack of back-to-back chains: n = chain number."""
    starts, i = [], d.find(CHAIN_MARK)
    while i >= 0:
        if (i - 12) % 16 == 0:
            starts.append(i - 12)
        i = d.find(CHAIN_MARK, i + 1)
    out = []
    for k, a in enumerate(starts):
        b = starts[k + 1] if k + 1 < len(starts) else len(d)
        pics = pictures(d[a:b], (PSMCT32, PSMCT16))
        if pics:
            _, inf, o, c = pics[0]
            out.append((k, inf, a + o, a + c))
    return out


def file_pictures(name, d):
    if name in BIN_FILES:
        return bin_pictures(d)
    if name in CHAIN_FILES:
        return chain_pictures(d)
    return pictures(d)


def palette(d, clut, psm, clut_psm=PSMCT32):
    if clut_psm == PSMCT16:
        raw = []
        for i in range(256):
            v = struct.unpack_from('<H', d, clut + 2 * i)[0]
            raw.append(((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3, 0x80 if v >> 15 else 0))
    else:
        raw = [struct.unpack_from('<4B', d, clut + 4 * i) for i in range(256)]
    if psm == PSMT8:
        raw = [raw[swizzle(i)] for i in range(256)]
    else:
        raw = raw[:16]
    return [(r, g, b) for r, g, b, _ in raw], [min(255, a * 2) for _, _, _, a in raw]


def pixels(d, off, inf):
    w, h = inf['w'], inf['h']
    if inf['psm'] == PSMT8:
        return [list(d[off + y * w:off + (y + 1) * w]) for y in range(h)]
    rows = []
    for y in range(h):
        row = []
        for b in d[off + y * w // 2:off + (y + 1) * w // 2]:
            row += [b & 15, b >> 4]
        rows.append(row)
    return rows


def ident(name, n):
    return name.strip('/').replace('/', '_').rsplit('.', 1)[0] + f'_{n}'


def gsl_files(extracted):
    gsl = [p for p in Path(extracted).rglob('*') if p.suffix.upper() == '.GSL' and p.is_file()]
    packs = [Path(extracted) / f.lstrip('/') for f in BIN_FILES + CHAIN_FILES]
    return sorted(gsl + [p for p in packs if p.exists()])


def export_all(extracted, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in gsl_files(extracted):
        d = p.read_bytes()
        name = '/' + p.relative_to(extracted).as_posix()
        for n, inf, off, clut in file_pictures(name, d):
            pal, alpha = palette(d, clut, inf['psm'], inf['clut_psm'])
            i = ident(name, n)
            pngio.write(out / f'{i}.png', pixels(d, off, inf), pal, alpha)
            (out / f'{i}.json').write_text(json.dumps({'file': name, 'offset': off, 'clut': clut, **inf}))
            count += 1
    return count


def import_images(images, files):
    done = 0
    for i, path in sorted(images.items()):
        name, _, n = i.rpartition('_')
        file = '/' + name.replace('_', '/', 1) + '.GSL'
        if file.replace('.GSL', '.BIN') in BIN_FILES + CHAIN_FILES:
            file = file.replace('.GSL', '.BIN')
        d = files.get(file)
        pic = next((x for x in file_pictures(file, bytes(d)) if x[0] == int(n)), None)
        if pic is None:
            raise SystemExit(f'gfx: {i}: no picture {n} in {file}')
        _, inf, off, clut = pic
        png = pngio.read(path)
        if (png.width, png.height) != (inf['w'], inf['h']) or png.palette is None:
            raise SystemExit(f'gfx: {path}: must be an indexed {inf["w"]}x{inf["h"]} PNG in the original palette')
        top = 256 if inf['psm'] == PSMT8 else 16
        if any(v >= top for row in png.rows for v in row):
            raise SystemExit(f'gfx: {path}: uses colours beyond the original {top}')
        if inf['psm'] == PSMT8:
            raw = bytes(v for row in png.rows for v in row)
        else:
            flat = [v for row in png.rows for v in row]
            raw = bytes(flat[k] | (flat[k + 1] << 4) for k in range(0, len(flat), 2))
        d[off:off + len(raw)] = raw
        files.put(file, d)
        done += 1
    return done


def main(argv=None):
    import paths
    args = paths.configure(sys.argv[1:] if argv is None else argv)
    if not args or args[0] != 'export':
        sys.exit(__doc__)
    out = Path(args[1]) if len(args) > 1 else paths.WORK / 'gfx'
    print(f'{export_all(paths.EXTRACTED, out)} images to {paths.show(out)}')


if __name__ == '__main__':
    main()
