#!/usr/bin/env python3
"""Run the patched draw()/width() (tools/font.py) in a small MIPS interpreter: python3 tools/test_vwf.py

The glyph cache (0x308e30) and sprite (0x302cd0) calls are stubbed and recorded. Checks the advance
and the sprite drawn for ASCII, Shift-JIS, the full-width space, the zero-width marker and control
codes, and width() of mixed strings, against tools/font.py's table. Exit status 1 on a mismatch.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font  # noqa: E402
import paths  # noqa: E402

M64 = (1 << 64) - 1


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


class CPU:
    def __init__(self, code):
        self.mem = {}
        for addr, b in code:
            for i, x in enumerate(b):
                self.mem[addr + i] = x
        self.r = [0] * 32
        self.calls = []

    def rb(self, a):
        return self.mem.get(a & 0xffffffff, 0)

    def wb(self, a, v):
        self.mem[a & 0xffffffff] = v & 0xff

    def rd(self, a, n):
        return int.from_bytes(bytes(self.rb(a + i) for i in range(n)), 'little')

    def wr(self, a, v, n):
        for i in range(n):
            self.wb(a + i, v >> (8 * i))

    def call(self, pc, args, stubs):
        RA = 0xdead0
        self.r = [0] * 32
        self.r[29] = 0x7f0000
        self.r[31] = RA
        for i, v in enumerate(args):
            self.r[4 + i if i < 4 else 8 + i - 4] = v & M64
        delay = None
        for _ in range(100000):
            if pc == RA:
                return self.r[2]
            if pc in stubs:
                self.r[2] = stubs[pc](self) & M64
                pc = self.r[31]
                continue
            x = self.rd(pc, 4)
            nxt = pc + 4 if delay is None else delay
            delay = None
            target = self.step(x, pc)
            if target is not None:
                # execute delay slot
                y = self.rd(pc + 4, 4)
                t2 = self.step(y, pc + 4)
                assert t2 is None, 'branch in delay slot'
                pc = target
                continue
            pc = nxt
        raise RuntimeError('runaway')

    def step(self, x, pc):
        r = self.r
        op, rs, rt, rd, sh, fn, imm = x >> 26, (x >> 21) & 31, (x >> 16) & 31, (x >> 11) & 31, (x >> 6) & 31, x & 63, x & 0xffff
        simm = sx(imm, 16)
        def setr(i, v):
            if i:
                r[i] = v & M64
        def s32(v):
            return sx(v, 32) & M64
        if x == 0:
            return None
        if op == 0:
            if fn == 0x21:
                setr(rd, s32(r[rs] + r[rt]))
            elif fn == 0x25:
                setr(rd, r[rs] | r[rt])
            elif fn == 0x00:
                setr(rd, s32((r[rt] << sh) & 0xffffffff))
            elif fn == 0x3a:
                setr(rd, r[rt] >> sh)
            elif fn == 0x2a:
                setr(rd, int(sx(r[rs], 64) < sx(r[rt], 64)))
            elif fn == 0x2b:
                setr(rd, int(r[rs] < r[rt]))
            elif fn == 0x2d:
                setr(rd, r[rs])
            elif fn == 0x08:
                return r[rs] & 0xffffffff
            else:
                raise NotImplementedError(hex(x))
            return None
        if op == 2:
            return (pc & 0xf0000000) | ((x & 0x3ffffff) << 2)
        if op == 3:
            r[31] = pc + 8
            return (pc & 0xf0000000) | ((x & 0x3ffffff) << 2)
        if op in (4, 5):
            eq = r[rs] == r[rt]
            if eq == (op == 4):
                return pc + 4 + (simm << 2)
            # not taken: still execute the delay slot (handled by caller only when taken)
            y = self.rd(pc + 4, 4)
            self.step(y, pc + 4)
            self.skip = True
            return pc + 8
        if op in (0x14, 0x15):                 # beql / bnel: the delay slot only runs when taken
            eq = r[rs] == r[rt]
            if eq == (op == 0x14):
                return pc + 4 + (simm << 2)
            return pc + 8
        if op == 9:
            setr(rt, s32(r[rs] + simm))
        elif op == 0xa:
            setr(rt, int(sx(r[rs], 64) < simm))
        elif op == 0xb:
            setr(rt, int((r[rs] & M64) < (simm & M64)))
        elif op == 0xc:
            setr(rt, r[rs] & imm)
        elif op == 0xd:
            setr(rt, r[rs] | imm)
        elif op == 0xf:
            setr(rt, s32(imm << 16))
        elif op == 0x24:
            setr(rt, self.rb(r[rs] + simm))
        elif op == 0x20:
            setr(rt, sx(self.rb(r[rs] + simm), 8) & M64)
        elif op == 0x28:
            self.wb(r[rs] + simm, r[rt])
        elif op == 0x25:
            setr(rt, self.rd(r[rs] + simm, 2))
        elif op == 0x29:
            self.wr(r[rs] + simm, r[rt], 2)
        elif op == 0x23:
            setr(rt, s32(self.rd(r[rs] + simm, 4)))
        elif op == 0x2b:
            self.wr(r[rs] + simm, r[rt], 4)
        elif op == 0x37:
            setr(rt, self.rd(r[rs] + simm, 8))
        elif op == 0x3f:
            self.wr(r[rs] + simm, r[rt], 8)
        elif op == 0x1e:
            setr(rt, self.rd(r[rs] + simm, 8))
        elif op == 0x1f:
            self.wr(r[rs] + simm, r[rt], 8)
        else:
            raise NotImplementedError(hex(x))
        return None


def main(argv=None):
    paths.configure(sys.argv[1:] if argv is None else argv)
    widths = font.load_widths(paths.EXTRACTED / font.FONT_FILE.lstrip('/'))
    code = font.code(widths)
    fails = 0

    def run(fn, args, stubs=None):
        cpu = CPU(code)
        sprites = []
        def assign(c):
            cpu.calls.append(('assign', c.r[5]))
            return (0x40 << 16) | 0x20     # u=0x20, v=0x40
        def sprite(c):
            sprites.append((c.r[5] & 0xffff, c.r[6] & 0xffff, c.r[7] & 0xffff, c.r[8] & 0xffff, c.r[9], c.r[10]))
            return 0
        s = {font.FONT_ASSIGN: assign, font.SPRITE: sprite}
        s.update(stubs or {})
        out = cpu.call(fn, args, s)
        return cpu, out, sprites

    def check(what, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f'{"ok  " if ok else "FAIL"} {what}: {got!r}' + ('' if ok else f' (expected {want!r})'))

    STR = 0x100000
    def draw(text_bytes, x=100):
        cpu = CPU(code)
        for i, b in enumerate(text_bytes + b'\0'):
            cpu.wb(STR + i, b)
        sprites = []
        def assign(c):
            cpu.calls.append(c.r[5])
            return (0x40 << 16) | 0x20
        def sprite(c):
            sprites.append((c.r[5] & 0xffff, c.r[6] & 0xffff, c.r[7] & 0xffff, c.r[8] & 0xffff, c.r[9], c.r[10]))
            return 0
        out = cpu.call(font.DRAW, [0x200000, x, 50, STR], {font.FONT_ASSIGN: assign, font.SPRITE: sprite})
        return out & 0xffffffff, cpu.calls, sprites

    for ch in 'AiW .,_`^':
        out, calls, spr = draw(ch.encode())
        check(f'draw {ch!r} advance', out - 100, widths[ord(ch)])
        check(f'draw {ch!r} sprite', spr, [(100, 50, 0x20, 0x40, font.ASCII_SPRITE, 0x16)])
    out, calls, spr = draw('あ'.encode('cp932'))
    check('draw あ advance', out - 100, 22)
    check('draw あ glyph code', calls, [0x82a0])
    check('draw あ sprite width', spr[0][4], 0x16)
    out, calls, spr = draw('　'.encode('cp932'))
    check('draw full-width space', (out - 100, spr), (20, []))
    out, calls, spr = draw(bytes([0x81, 0xad]))
    check('draw zero-width marker', (out - 100, spr), (0, []))
    out, calls, spr = draw(bytes([0x84, 0x9f]))
    check('draw 0x849f as 0x815c', calls, [0x815c])
    out, calls, spr = draw(b'\n')
    check('draw control code', (out - 100, spr), (0, []))

    cpu = CPU(code)
    for i, b in enumerate("Hi, it's%chr　あ\n".encode('cp932') + b'\0'):
        cpu.wb(STR + i, b)
    out = cpu.call(font.WIDTH_STUB if hasattr(font, 'WIDTH_STUB') else font.WIDTH, [0, STR], {})
    want = sum(widths[ord(c)] for c in "Hi, it's%chr") + 22 + 22 + 11
    check('width() mixed string', out & 0xffffffff, want)
    # The two routines that measure text themselves, run inside the original code around them.
    exe = (paths.EXTRACTED / font.EXE_FILE.lstrip('/')).read_bytes()
    original = [(0x22f290, exe[0x22f290 - 0x1ff000:0x22f380 - 0x1ff000])]
    text = "Hi, it's%chr　あ"
    want = sum(widths[ord(c)] for c in "Hi, it's%chr") + 22 + 22
    cpu = CPU(original + code)
    for i, b in enumerate(text.encode('cp932') + b'\0'):
        cpu.wb(STR + i, b)
    this = 0x300000
    cpu.call(0x22f290, [this, STR], {0x22f5b0: lambda c: 0})
    check('text block width (0x22f290)', cpu.rd(this + 0x14, 4), want)
    check('text block buffer', bytes(cpu.rb(this + 0x1c + i) for i in range(cpu.rd(this + 0x10, 4))),
          text.encode('cp932'))
    cpu = CPU(code)
    for i, b in enumerate((text + '\nmore').encode('cp932') + b'\0'):
        cpu.wb(STR + i, b)
    check('first line width (0x2b7998)', cpu.call(font.MEASURE_LINE[0], [STR], {}) & 0xffffffff, want)
    print('all ok' if not fails else f'{fails} failures')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
