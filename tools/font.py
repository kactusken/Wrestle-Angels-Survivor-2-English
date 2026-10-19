#!/usr/bin/env python3
"""English font: the game's own half-width glyphs, drawn proportionally.

  font.py widths                 print the advance of every ASCII character
  font.py sheet OUT.png          the English glyphs at 4x with their advances (needs Pillow)

The game draws text one character at a time through pao::basic_Font (vtable 0x4046d0):
  0x20d720 width(this, str)      11 px per byte (a full-width character counts 22)
  0x20d750 draw(this, x, y, p)   bytes < 0x80: glyph 0x1ed + code, 12 px sprite, x += 11
                                 Shift-JIS: 22 px sprite, x += 22 (0x8140 full-width space: 20)
Glyphs are 22x22, 4 bits per pixel, in /SYS/FONT.BIN (glyph n at n * 242), ordered by JIS row
(tools/font.py glyph_index). The half-width set (0x21-0x7e) is a condensed outlined gothic placed
in an 11 px grid: most letters fill columns 0-11, narrow ones (i, l, punctuation) are centred.

The half-width set is JIS-Roman: 0x5c is ¥ and 0x7e an overline, so English '~' is written as
the full-width ～ (tools/scr.py) and backslash stays reserved for control codes.

The English build:
  - FONT.BIN: every half-width glyph is moved to column 0 (digits stay put: they keep a fixed
    width so numbers line up); '_', '`' and '^' get the space, comma and double-quote art, because
    the script tokenizer splits on ' ', ',' and '"' (tools/scr.py encodes them as these stand-ins);
  - ZERO_WIDTH (0x81ad) is drawn as nothing, with no advance (see ZERO_WIDTH below);
  - code: draw() and width() are rewritten to take each ASCII character's advance from a 96-byte
    table (0x20-0x7f). The new draw() is shorter than the old one and fits in its place; width()
    jumps to a copy after it. The table goes where the two cursor-arrow functions were (0x20da20
    ▲, 0x20dab0 ▼): they are merged into one body behind the ▼ entry point.

  - the message window's 40-byte line cap and "show everything" value are raised (MESSAGE_BOX);
  - two other routines that measure text at 11 px a byte use the table too (MEASURE_TEXT/_LINE).

Everything here is checked against the original bytes before it is written.
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mips_asm  # noqa: E402

FONT_FILE = '/SYS/FONT.BIN'
EXE_FILE = '/SLPM_550.56'
CELL, SIZE = 22, 242          # glyph is 22x22 at 4 bpp
ASCII_BASE = 0x1ed            # glyph of single-byte code c: ASCII_BASE + c

# Script stand-ins: the tokenizer (0x30a248) ends a token at ' ', '\t', ',', ')', '\\', '//' and
# strips '"' at a token's ends, so the scripts carry these instead (tools/scr.py encode()).
STAND_INS = {' ': '_', ',': '`', '"': '^'}

SPACE = 5          # advance of ' ' and its stand-in
DIGIT = 10         # every digit: fixed, so columns of numbers stay aligned
OVERLAP = 2        # outline columns a glyph shares with the next one (2: chosen on a preview)
MIN_ADVANCE = 3
EXTRA = {}         # per-character adjustments found in game, e.g. {'f': -1}

ASCII_SPRITE = 14  # sprite width drawn for half-width glyphs (widest glyph: columns 0-12)

# The script engine only takes a line as dialogue when its first byte is Shift-JIS, '%' or '\'
# (0x229fc0: any other first byte makes it a label). tools/scr.py starts English lines with this
# unassigned code (JIS row 2, never used by the game), which draw() skips without moving.
ZERO_WIDTH = 0x81ad

# --- the code -------------------------------------------------------------------------------
DRAW, WIDTH, ARROW_UP, ARROW_DOWN = 0x20d750, 0x20d720, 0x20da20, 0x20dab0
REGION_A = (0x20d720, 0x20d880)   # width() + draw()
REGION_B = (0x20da20, 0x20db40)   # ▲ + ▼
REGION_SHA1 = {REGION_A: 'e3f65dc0deb2bfdcafb87fa7ea3e2e7c927727ff',   # `font.py hashes`
               REGION_B: '871595fa44a6a231dca962276174a44b468a72ab'}
TABLE = 0x20da28
GLYPH_CACHE, FONT_ASSIGN, SPRITE, SET_MODE = 0x5e0000 - 0x500, 0x308e30, 0x302cd0, 0x302fe0

ASM_A = f'''
width_stub:                         ; 0x20d720: the vtable and four calls still come here
    j     width
    nop
    .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
draw:                               ; 0x20d750: (this, x, y, p) -> new x
    addiu sp, sp, -0x50
    sq    s0, 0x20(sp)
    sq    s1, 0x30(sp)
    sq    s2, 0x40(sp)
    sd    ra, 0x10(sp)
    move  s0, a1
    move  s1, a2
    move  s2, a0
    lbu   a1, 0(a3)
    andi  v0, a1, 0x80
    bnez  v0, sjis
    sltiu v0, a1, 0x20
    bnez  v0, done                  ; control code: nothing drawn, x unchanged
    move  v0, s0
    lui   v1, %hi(TABLE-0x20)
    addu  v1, v1, a1
    lbu   v1, %lo(TABLE-0x20)(v1)   ; advance from the table
    b     glyph
    addiu t1, zero, {ASCII_SPRITE}
sjis:
    lbu   v0, 1(a3)
    sll   a1, a1, 8
    or    a1, a1, v0
    ori   v0, zero, ZERO_WIDTH
    beq   a1, v0, advance           ; the line-start marker: nothing drawn, x unchanged
    move  v1, zero
    ori   v0, zero, 0x8140
    beq   a1, v0, advance           ; full-width space: 20 px, nothing drawn
    addiu v1, zero, 0x14
    ori   v0, zero, 0x849f
    bne   a1, v0, wide
    addiu v1, zero, 0x16
    ori   a1, zero, 0x815c          ; as the original: 0x849f is drawn as 0x815c
wide:
    addiu t1, zero, 0x16
glyph:
    sw    v1, 4(sp)
    sw    t1, 8(sp)
    lui   a0, %hi(GLYPH_CACHE)
    jal   FONT_ASSIGN               ; -> v0: u in bits 0-15, v in bits 16-31
    addiu a0, a0, %lo(GLYPH_CACHE)
    lw    a0, 0(s2)
    move  a1, s0
    move  a2, s1
    move  a3, v0
    dsrl  t0, v0, 16
    lw    t1, 8(sp)
    jal   SPRITE                    ; (ctx, x, y, u, v, w, h): uses the low 16 bits of each
    addiu t2, zero, 0x16
    lw    v1, 4(sp)
advance:
    addu  v0, s0, v1
done:
    ld    ra, 0x10(sp)
    lq    s0, 0x20(sp)
    lq    s1, 0x30(sp)
    lq    s2, 0x40(sp)
    jr    ra
    addiu sp, sp, 0x50

width:                              ; (this, str) -> pixels
    lui   t1, %hi(TABLE-0x20)
    addiu t1, t1, %lo(TABLE-0x20)
    move  v0, zero
w_loop:
    lbu   v1, 0(a1)
    beqz  v1, w_done
    andi  t0, v1, 0x80
    bnez  t0, w_wide
    sltiu t0, v1, 0x20
    bnez  t0, w_ctl
    addu  t2, t1, v1
    lbu   t2, 0(t2)
    addiu a1, a1, 1
    b     w_loop
    addu  v0, v0, t2
w_ctl:
    addiu a1, a1, 1
    b     w_loop
    addiu v0, v0, 11                ; as the original
w_wide:
    addiu a1, a1, 2
    b     w_loop
    addiu v0, v0, 0x16
w_done:
    jr    ra
    nop
'''

ASM_B = '''
arrow_up:                           ; 0x20da20: (this, x, y) draws ▲ (0x81a3)
    b     arrow
    ori   t3, zero, 0x81a3
table:
    .byte {table}
.align 4
'''

ASM_B2 = '''
arrow_down:                         ; 0x20dab0: (this, x, y) draws ▼ (0x81a5)
    ori   t3, zero, 0x81a5
arrow:
    addiu sp, sp, -0x50
    sq    s0, 0x20(sp)
    sq    s1, 0x30(sp)
    sq    s2, 0x40(sp)
    sd    ra, 0x10(sp)
    move  s0, a2
    move  s1, a1
    move  s2, a0
    sw    t3, 4(sp)
    lw    a0, 0(s2)
    jal   SET_MODE
    addiu a1, zero, 2
    lui   a0, %hi(GLYPH_CACHE)
    lw    a1, 4(sp)
    jal   FONT_ASSIGN
    addiu a0, a0, %lo(GLYPH_CACHE)
    lw    a0, 0(s2)
    move  a1, s1
    move  a2, s0
    move  a3, v0
    dsrl  t0, v0, 16
    addiu t1, zero, 0x16
    jal   SPRITE
    addiu t2, zero, 0x16
    ld    ra, 0x10(sp)
    lq    s0, 0x20(sp)
    lq    s1, 0x30(sp)
    lq    s2, 0x40(sp)
    jr    ra
    addiu sp, sp, 0x50
'''

# The message window (0x231a98) draws each of its 3 lines with at most 0x28 bytes (20 full-width
# characters = 440 px); English lines are ended by their line break well before the box edge, so
# the byte cap is raised and the pixel width (tools/scr.py LINE_PX) is the limit. The typewriter's
# "show everything" value 0x96 (150 bytes, enough for 3 x 40 + 2) is raised too, or a long English
# message would never count as fully shown at the instant text speed or after a button press.
LINE_BYTES = 0x60
MESSAGE_BOX = [  # (address, original word, new word)
    (0x231ac4, 0x2a220028, 0x2a220000 | LINE_BYTES),   # slti  v0, s1, 0x28
    (0x231ae0, 0x240b0028, 0x240b0000 | LINE_BYTES),   # addiu t3, zero, 0x28
    (0x231b4c, 0x26020028, 0x26020000 | LINE_BYTES),   # addiu v0, s0, 0x28
    (0x231b68, 0x240b0028, 0x240b0000 | LINE_BYTES),
    (0x231bac, 0x26020028, 0x26020000 | LINE_BYTES),
    (0x231bc8, 0x240b0028, 0x240b0000 | LINE_BYTES),
    (0x232ec0, 0x24020096, 0x24027fff),                 # instant speed: progress = 0x96
    (0x232f34, 0x24030096, 0x24037fff),                 # show the whole message now
]

# Two other places measure text at 11 px a byte themselves (22 a Shift-JIS character), not
# through width(): they are rewritten to use the table too.
#   0x22f290 a text block (vtable 0x404c80) appends a line to its buffer and adds up its width,
#            which centres it (memory card messages, other centred notices);
#   0x2b7998 the pixel width of a string's first line.
MEASURE_TEXT = (0x22f2c0, 0x22f314)   # the per-character part of 0x22f290's loop
MEASURE_LINE = (0x2b7998, 0x2b79fc)
REGION_SHA1.update({MEASURE_TEXT: '22f9c86108a9a640c63b5f83e49584b637cf108a',
                    MEASURE_LINE: '9b12d2297a75cb2426d0e5467df49f0e33c9788a'})
ASM_MEASURE_TEXT = '''
add:                                ; from 0x22f358: v1 = signed byte, a1 = byte, a0 = length
    slt   t0, v1, zero
    bnez  t0, sjis
    addu  v0, s2, a0
    sb    a1, 0(v0)
    addiu a0, a0, 1
    lui   v1, %hi(TABLE-0x20)
    addu  v1, v1, a1
    b     tail
    lbu   v1, %lo(TABLE-0x20)(v1)   ; advance from the table
sjis:
    sb    a1, 0(v0)
    lbu   v0, 1(s1)
    addu  t0, s2, a0
    sb    v0, 1(t0)
    addiu a0, a0, 2
    addiu s1, s1, 1
    addiu v1, zero, 0x16
tail:
    addiu s1, s1, 1
    sw    a0, 0x10(s0)
    lw    v0, 0x14(s0)
    addu  v0, v0, v1                ; 0x22f314 stores it
'''
ASM_MEASURE_LINE = '''
line_width:                         ; (str) -> width of the first line (up to NUL, LF or 128 bytes)
    move  a2, zero
    addiu t1, a0, 0x80
    addiu t2, zero, 0xa
loop:
    lb    v1, 0(a0)
    beqz  v1, end
    nop
    beq   v1, t2, end
    slt   t0, v1, zero
    bnez  t0, sjis
    lui   t0, %hi(TABLE-0x20)
    addu  t0, t0, v1
    lbu   t0, %lo(TABLE-0x20)(t0)
    b     next
    addu  a2, a2, t0
sjis:
    addiu a2, a2, 0x16
    addiu a0, a0, 1
next:
    addiu a0, a0, 1
    sltu  v0, a0, t1
    bnez  v0, loop
    nop
end:
    jr    ra
    move  v0, a2
'''

SYMBOLS = {'ZERO_WIDTH': ZERO_WIDTH, 'TABLE': TABLE, 'GLYPH_CACHE': GLYPH_CACHE, 'FONT_ASSIGN': FONT_ASSIGN,
           'SPRITE': SPRITE, 'SET_MODE': SET_MODE}


# --- glyphs ---------------------------------------------------------------------------------
def glyph_index(code):
    """FONT.BIN glyph number for a single byte or a Shift-JIS code (as 0x308c98 computes it)."""
    if code < 0x100:
        return code + ASCII_BASE
    hi, lo = code >> 8, code & 0xff
    hi = (hi - 0x81 if hi < 0xa0 else hi - 0xc1) * 2 + 0x21
    if lo >= 0x9f:
        hi, lo = hi + 1, lo - 0x7e
    else:
        lo = lo - 0x1f - (lo >= 0x80)
    n = (hi - 0x21) * 94 + (lo - 0x21)
    return n if n < 0x582 else n - 0x316


def unpack(data, n):
    g = data[n * SIZE:(n + 1) * SIZE]
    px = []
    for b in g:
        px += [b & 15, b >> 4]
    return px


def pack(px):
    return bytes(px[i] | (px[i + 1] << 4) for i in range(0, len(px), 2))


def columns(px):
    return [x for x in range(CELL) if any(px[y * CELL + x] for y in range(CELL))]


def shifted(px, dx):
    out = [0] * (CELL * CELL)
    for y in range(CELL):
        for x in range(CELL):
            if 0 <= x + dx < CELL:
                out[y * CELL + x] = px[y * CELL + x + dx]
    return out


def english_font(data):
    """(new FONT.BIN bytes, {code: advance} for 0x20-0x7f)."""
    data = bytearray(data)
    art = {c: unpack(data, glyph_index(c)) for c in range(0x20, 0x7f)}
    art[0x20] = [0] * (CELL * CELL)    # the original cell for 0x20 isn't empty
    for real, stand in STAND_INS.items():
        art[ord(stand)] = art[ord(real)]
    widths = {0x7f: 0}
    for c in range(0x20, 0x7f):
        px = art[c]
        cols = columns(px)
        if not cols:
            widths[c] = SPACE
        elif chr(c).isdigit():
            widths[c] = DIGIT
        else:
            px = shifted(px, cols[0])
            widths[c] = max(MIN_ADVANCE, cols[-1] - cols[0] + 1 - OVERLAP)
        widths[c] += EXTRA.get(chr(c), 0)
        n = glyph_index(c)
        data[n * SIZE:(n + 1) * SIZE] = pack(px)
    return bytes(data), widths


def text_width(text, widths):
    """Pixel width of English text as the patched game measures it (no stand-ins needed)."""
    w = 0
    for ch in text:
        c = ord(ch)
        w += widths[c] if c < 0x80 else 22
    return w


# --- code -------------------------------------------------------------------------------------
def code(widths):
    """[(address, new bytes)] for the executable."""
    a, sym = mips_asm.assemble(ASM_A, REGION_A[0], SYMBOLS)
    assert sym['draw'] == DRAW, hex(sym['draw'])
    if REGION_A[0] + len(a) > REGION_A[1]:
        raise SystemExit(f'font.py: draw()/width() need {len(a)} bytes, room for {REGION_A[1] - REGION_A[0]}')
    a += bytes(REGION_A[1] - REGION_A[0] - len(a))
    table = ', '.join(str(widths[c]) for c in range(0x20, 0x80))
    b1, b1sym = mips_asm.assemble(ASM_B.format(table=table), REGION_B[0], dict(SYMBOLS, arrow=ARROW_DOWN + 4))
    if REGION_B[0] + len(b1) > ARROW_DOWN:
        raise SystemExit('font.py: width table overruns the ▼ function')
    b1 += bytes(ARROW_DOWN - REGION_B[0] - len(b1))
    assert b1sym['table'] == TABLE
    b2, _ = mips_asm.assemble(ASM_B2, ARROW_DOWN, SYMBOLS)
    b = b1 + b2
    if REGION_B[0] + len(b) > REGION_B[1]:
        raise SystemExit('font.py: arrow function too long')
    b += bytes(REGION_B[1] - REGION_B[0] - len(b))
    out = [(REGION_A[0], a), (REGION_B[0], b)]
    for (lo, hi), src in ((MEASURE_TEXT, ASM_MEASURE_TEXT), (MEASURE_LINE, ASM_MEASURE_LINE)):
        m, _ = mips_asm.assemble(src, lo, SYMBOLS)
        if lo + len(m) > hi:
            raise SystemExit(f'font.py: the code for {lo:#x} needs {len(m)} bytes, room for {hi - lo}')
        out.append((lo, m + bytes(hi - lo - len(m))))
    return out


def region_hashes(exe, to_offset):
    return {r: hashlib.sha1(bytes(exe[to_offset(r[0]):to_offset(r[1])])).hexdigest()
            for r in (REGION_A, REGION_B, MEASURE_TEXT, MEASURE_LINE)}


def apply(files, to_offset):
    """Build step: English glyphs into FONT.BIN, proportional draw()/width() into the executable."""
    font, widths = english_font(files.get(FONT_FILE))
    files.put(FONT_FILE, font)
    exe = files.get(EXE_FILE)
    for r, h in region_hashes(exe, lambda a: to_offset(EXE_FILE, a)).items():
        if h != REGION_SHA1[r]:
            raise SystemExit(f'font.py: unexpected code at {r[0]:#x}-{r[1]:#x} (SHA-1 {h}) - wrong executable, '
                             f'or an earlier step changed it')
    for addr, new in code(widths):
        off = to_offset(EXE_FILE, addr)
        exe[off:off + len(new)] = new
    for addr, old, new in MESSAGE_BOX:
        off = to_offset(EXE_FILE, addr)
        if struct.unpack_from('<I', exe, off)[0] != old:
            raise SystemExit(f'font.py: unexpected code at {addr:#x}')
        struct.pack_into('<I', exe, off, new)
    files.put(EXE_FILE, exe)
    print(f'font: proportional half-width text ({sum(widths[c] for c in range(0x61, 0x7b)) / 26:.1f} px '
          f'average lower case)')
    return widths


def load_widths(font_path):
    """Advances computed from an unpacked original FONT.BIN (for lint and the wrap tool)."""
    return english_font(Path(font_path).read_bytes())[1]


def main(argv=None):
    import paths
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('widths')
    sh = sub.add_parser('sheet')
    sh.add_argument('out')
    sub.add_parser('hashes', help='SHA-1 of the original code regions (for REGION_SHA1)')
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    font_path = paths.EXTRACTED / FONT_FILE.lstrip('/')
    if args.cmd == 'widths':
        w = load_widths(font_path)
        print(' '.join(f'{chr(c)}={w[c]}' for c in range(0x20, 0x7f)))
    elif args.cmd == 'hashes':
        import elf
        exe = (paths.EXTRACTED / EXE_FILE.lstrip('/')).read_bytes()
        e = elf.Elf(exe)
        for r, h in region_hashes(exe, e.offset).items():
            print(f'{r[0]:#x}-{r[1]:#x} {h}')
    else:
        from PIL import Image, ImageDraw
        font, w = english_font(font_path.read_bytes())
        img = Image.new('RGB', (16 * 26 * 4, 6 * 26 * 4), (40, 40, 60))
        dr = ImageDraw.Draw(img)
        for i, c in enumerate(range(0x20, 0x80)):
            px = unpack(font, glyph_index(c))
            ox, oy = (i % 16) * 26 * 4, (i // 16) * 26 * 4
            for y in range(CELL):
                for x in range(CELL):
                    v = px[y * CELL + x] * 17
                    if v:
                        dr.rectangle([ox + x * 4, oy + y * 4, ox + x * 4 + 3, oy + y * 4 + 3], fill=(v, v, v))
            dr.line([ox + w[c] * 4, oy, ox + w[c] * 4, oy + 88], fill=(255, 80, 80))
        img.save(args.out)


if __name__ == '__main__':
    main()
