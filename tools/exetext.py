#!/usr/bin/env python3
"""The executable's own text (menus, messages, commentary): extract to a table, build it back.

  exetext.py extract [--force]     write translation/text/exe.csv (keeps existing English by id)
  exetext.py check                 English that can't be stored (encoding, references)
  exetext.py stats                 strings by kind of reference, and where English would go
  exetext.py dump [FROM TO]        one line per string: id, room, japanese (\n escaped)
  exetext.py import FILE [--dry-run]
                                   English from `id<TAB>text` lines (\n = line break); checks
                                   each (characters, room for strings that can't move)

Columns: id (address), refs (references that can be repointed; 0 = in place only, max_bytes is
then a hard limit), reach (ptrN pointers, codeN lui/addiu pairs, sharedN pairs whose lui serves
several strings, gpN gp-relative), max_bytes (room in place, without the NUL), japanese,
english, notes.

Strings are Shift-JIS, NUL-terminated, in .data/.rodata/.sdata (0x376900-0x59e600). Only strings
the code reaches through something this tool can repoint are listed:
  ptr   a 32-bit word anywhere in the data equal to the string's address (pointer tables)
  code  a lui/addiu (or ori) pair building the address, with the lui used by nothing else
  gp    addiu rX, gp, offset (cannot be repointed: in place only)
Strings reached in other ways (fixed records: rosters, move names, venues) are not listed here;
they need their own tables (tools/records.py).

Build (apply): English that fits in the original's room (its bytes, its NUL and the zero padding
after it) is written in place. Longer English goes to a new loadable segment appended to the ELF
right after .bss (EXTRA_BASE); every pointer and lui/addiu pair to the string is patched, and the
start of the heap is moved past the new segment: crt0's SetupHeap(_end, -1) at 0x30e5d8 and
the break sbrk() (0x351a00, behind malloc) keeps at 0x4027c4 - the second is what matters, the
game's allocations start there. The
original string stays where it was, so anything that reaches it some other way still works.

In the table, a line break is written `\\n`. The text is drawn by tools/font.py's draw(): plain
ASCII (no stand-ins needed), `~` becomes the full-width ～ and `\\` is not allowed (¥).
"""
import argparse
import csv
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

EXE_FILE = '/SLPM_550.56'
CSV_NAME = 'exe.csv'
BASE, FILE_OFF = 0x200000, 0x1000
TEXT = (0x200000, 0x3768f8)
DATA = (0x376900, 0x59e600)
GP = 0x5a0bf0
BSS_END = 0x10a8094
EXTRA_BASE = 0x10a8100               # the new segment (16-byte aligned, after .bss)
HEAP_SETUP = [(0x30e5d8, 0x3c04010b), (0x30e5e0, 0x24848094)]   # lui a0, 0x10b / addiu a0, a0, -0x7f6c
# The player number in "Player %s" (0x2be1a8): the code copies "１" (82 50 00) and adds the player
# index to its second byte. English: "1" (31 00 00), and the code adds to the first byte.
PLAYER_DIGIT = [(0x59c780, 0x00005082, 0x00000031),
                (0x2be1cc, 0x93a20041, 0x93a20040),     # lbu v0, 0x41(sp) -> 0x40(sp)
                (0x2be1d8, 0xa3a20041, 0xa3a20040)]     # sb  v0, 0x41(sp) -> 0x40(sp)
# Pointers that share a string with another meaning get their own English (in the new segment):
# the region tables reuse the country list's 中国 ("China") for the Chugoku region.
SPLIT_POINTERS = {0x3cbd70: 'Chugoku', 0x3cd3d8: 'Chugoku', 0x3cdaa0: 'Chugoku'}
SPLIT_OLD = '中国'
HEAP_BREAK = (0x4027c4, BSS_END)     # sbrk()'s current break (0x351a00), initialised to _end
SJIS = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e\x0a])+\x00')
KANA = re.compile(r'[ぁ-んァ-ヶー一-龯]')
REPLACE = {'’': "'", '‘': "'", '“': '"', '”': '"', '…': '...', '—': '―', '–': '-', '~': '～'}


def plausible(t):
    """Text rather than data that happens to decode: two Japanese characters, or one with nothing
    around it but digits, format codes and line breaks."""
    n = len(KANA.findall(t))
    if n >= 2:
        return True
    return n == 1 and re.fullmatch(r'(?:[0-9０-９（]|%\d*d|\n)*' + KANA.pattern + r'(?:[0-9０-９（]|%\d*d|\n)*', t)


class Exe:
    def __init__(self, data):
        self.data = data
        self.words = struct.unpack_from(f'<{(DATA[1] - BASE) // 4}I', data, FILE_OFF)

    def off(self, addr):
        return addr - BASE + FILE_OFF

    def strings(self):
        """{address: bytes} of NUL-terminated Shift-JIS strings starting right after a NUL."""
        out = {}
        seg = self.data[self.off(DATA[0]):self.off(DATA[1])]
        for m in SJIS.finditer(seg):
            s = m.group()[:-1]
            a = DATA[0] + m.start()
            if self.data[self.off(a) - 1] != 0 or not re.search(rb'[\x81-\x9f\xe0-\xef]', s):
                continue
            try:
                t = s.decode('cp932')
            except UnicodeDecodeError:
                continue
            if plausible(t):
                out[a] = s
        return out

    def references(self, targets):
        """{address: [('ptr', at) | ('code', lui_at, lo_at) | ('gp', at) | ('shared', lui_at, lo_at)]}"""
        refs = {a: [] for a in targets}
        for i, w in enumerate(self.words):
            at = BASE + i * 4
            if w in refs and not (TEXT[0] <= at < TEXT[1]):
                refs[w].append(('ptr', at))
        n = (TEXT[1] - BASE) // 4
        words = self.words
        for i in range(n):
            x = words[i]
            if x >> 26 != 0xf:
                continue
            rt, hi = (x >> 16) & 31, (x & 0xffff) << 16
            # follow the register to its next write (or the function's return): every read is a use
            uses = []
            for j in range(i + 1, min(n, i + 256)):
                reads, writes = regs_of(words[j])
                if rt in reads:
                    uses.append(j)
                if rt in writes or words[j] == 0x03e00008:
                    break
            for u in uses:
                y = words[u]
                op, imm = y >> 26, y & 0xffff
                if op not in (9, 0xd) or (y >> 21) & 31 != rt:
                    continue
                v = (hi + (imm - 0x10000 if op == 9 and imm & 0x8000 else imm)) & 0xffffffff
                if v in refs:
                    kind = 'code' if len(uses) == 1 else 'shared'
                    refs[v].append((kind, BASE + i * 4, BASE + u * 4))
        for i in range(n):
            x = words[i]
            if x >> 26 == 9 and (x >> 21) & 31 == 28:
                imm = x & 0xffff
                v = GP + (imm - 0x10000 if imm & 0x8000 else imm)
                if v in refs:
                    refs[v].append(('gp', BASE + i * 4))
        return refs

    def room(self, addr, strings):
        """Bytes available in place: the string, its NUL and the zeros after it."""
        end = self.off(addr) + len(strings[addr]) + 1
        while end < self.off(DATA[1]) and self.data[end] == 0 and (BASE + end - FILE_OFF) not in strings:
            end += 1
        return end - self.off(addr)


def regs_of(x):
    """(registers read, registers written) by one R5900 instruction - conservative."""
    op, rs, rt, rd = x >> 26, (x >> 21) & 31, (x >> 16) & 31, (x >> 11) & 31
    if op == 0:
        fn = x & 0x3f
        if fn in (0, 2, 3, 0x38, 0x3a, 0x3b, 0x3c, 0x3e, 0x3f):   # shifts by constant
            return {rt}, {rd}
        if fn in (8, 9):                                          # jr / jalr
            return {rs}, ({rd} if fn == 9 else set())
        if fn in (0x10, 0x12):                                    # mfhi / mflo
            return set(), {rd}
        if fn in (0x18, 0x19, 0x1a, 0x1b, 0x11, 0x13):            # mult/div/mthi/mtlo
            return {rs, rt}, {rd}
        return {rs, rt}, {rd}
    if op == 0xf:
        return set(), {rt}
    if 8 <= op <= 0xe or op in (0x18, 0x19):                      # immediate arithmetic
        return {rs}, {rt}
    if 0x20 <= op <= 0x27 or op in (0x37, 0x1e, 0x1a, 0x1b, 0x31, 0x35):   # loads
        return {rs}, ({rt} if op not in (0x31, 0x35) else set())
    if 0x28 <= op <= 0x2f or op in (0x3f, 0x1f, 0x2c, 0x2d, 0x39, 0x3d):   # stores
        return {rs, rt}, set()
    if op in (4, 5, 0x14, 0x15):                                  # beq/bne(l)
        return {rs, rt}, set()
    if op in (1, 6, 7, 0x16, 0x17):                               # regimm, blez/bgtz(l)
        return {rs}, ({31} if op == 1 and rt in (0x10, 0x11, 0x12, 0x13) else set())
    if op == 3:                                                   # jal
        return set(), {31}
    if op == 0x1c:                                                # MMI: assume it reads and writes
        return {rs, rt}, {rd}
    return {rs, rt}, set()


def refs_text(refs):
    kinds = {}
    for r in refs:
        kinds[r[0]] = kinds.get(r[0], 0) + 1
    return ' '.join(f'{k}{n}' for k, n in sorted(kinds.items()))


def escape(s):
    return s.replace('\n', '\\n')


def unescape(s):
    return s.replace('\\n', '\n')


def encode(text):
    for a, b in REPLACE.items():
        text = text.replace(a, b)
    if '\\' in text.replace('\\n', ''):
        raise UnicodeEncodeError('cp932', text, text.index('\\'), text.index('\\') + 1, 'backslash is ¥')
    return unescape(text).encode('cp932')


def record_ranges():
    """Address ranges the fixed-record tables (tools/records.py) own: their text is translated
    there, so it is left out here."""
    import records
    out = []
    for t in records.TABLES.values():
        if t['source'] == ('file', EXE_FILE):
            first = t['first'] + records.ELF
            out.append((first, first + t['stride'] * t['count']))
    return out


def in_records(a, ranges):
    return any(lo <= a < hi for lo, hi in ranges)


def csv_path():
    return paths.TEXT / CSV_NAME


def read_rows():
    with open(csv_path(), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


FIELDS = ['id', 'refs', 'reach', 'max_bytes', 'japanese', 'english', 'notes']


def extract(force=False):
    exe = Exe((paths.EXTRACTED / EXE_FILE.lstrip('/')).read_bytes())
    strings = exe.strings()
    refs = exe.references(strings)
    old = {}
    if csv_path().exists():
        if not force:
            sys.exit(f'{paths.show(csv_path())} exists (--force rewrites it, keeping the English)')
        old = {r['id']: r for r in read_rows()}
    rows = []
    owned = record_ranges()
    for a, s in sorted(strings.items()):
        if not refs[a] or in_records(a, owned):
            continue
        ident = f'{a:#x}'
        prev = old.get(ident, {})
        movable = not any(r[0] in ('gp', 'shared') for r in refs[a])
        rows.append({'id': ident, 'refs': len(refs[a]) if movable else 0, 'reach': refs_text(refs[a]),
                     'max_bytes': exe.room(a, strings) - 1,
                     'japanese': escape(s.decode('cp932')), 'english': prev.get('english', ''),
                     'notes': prev.get('notes', '')})
    with open(csv_path(), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f'extract: {len(rows)} strings to {paths.show(csv_path())}')


def plan(data):
    """[(address, english bytes, refs, room)] for every row with English, or SystemExit."""
    exe = Exe(data)
    strings = exe.strings()
    owned = record_ranges()
    rows = [r for r in read_rows() if r['english'].strip() and not in_records(int(r['id'], 16), owned)]
    refs = exe.references({int(r['id'], 16) for r in rows})
    out, errors = [], []
    for r in rows:
        a = int(r['id'], 16)
        if a not in strings or strings[a].decode('cp932') != unescape(r['japanese']):
            errors.append(f'{r["id"]}: the executable has different text there - re-extract')
            continue
        try:
            enc = encode(r['english'])
        except UnicodeEncodeError as x:
            errors.append(f'{r["id"]}: character the game cannot show: {x.object[x.start]!r}')
            continue
        out.append((a, enc, refs[a], exe.room(a, strings)))
    if errors:
        raise SystemExit('exetext: ' + '\n  '.join(errors))
    return out


def apply(path, files):
    """Build step: the executable's English (tools/exetext.py)."""
    if not csv_path().exists():
        return
    data = files.get(EXE_FILE)
    global BASE_DATA
    BASE_DATA = bytes(data)                 # before this step (SPLIT_POINTERS checks the original)
    items = plan(bytes(data))
    extra = bytearray()
    moved = kept = 0
    for a, enc, refs, room in items:
        off = a - BASE + FILE_OFF
        if len(enc) + 1 <= room:
            data[off:off + room] = enc + bytes(room - len(enc))
            kept += 1
            continue
        if any(r[0] in ('gp', 'shared') for r in refs):
            raise SystemExit(f'exetext: {a:#x} needs {len(enc) + 1} bytes, has {room}, and a reference that '
                             f'cannot be repointed ({refs_text(refs)}) - shorten it')
        new = EXTRA_BASE + len(extra)
        extra += enc + b'\0'
        extra += bytes(-len(extra) % 4)
        for r in refs:
            if r[0] == 'ptr':
                struct.pack_into('<I', data, r[1] - BASE + FILE_OFF, new)
            else:
                lui_at, lo_at = r[1], r[2]
                lo_word = struct.unpack_from('<I', data, lo_at - BASE + FILE_OFF)[0]
                ori = lo_word >> 26 == 0xd
                hi = (new >> 16) if ori else ((new + 0x8000) >> 16) & 0xffff
                lui_word = struct.unpack_from('<I', data, lui_at - BASE + FILE_OFF)[0]
                struct.pack_into('<I', data, lui_at - BASE + FILE_OFF, (lui_word & 0xffff0000) | hi)
                struct.pack_into('<I', data, lo_at - BASE + FILE_OFF, (lo_word & 0xffff0000) | (new & 0xffff))
        moved += 1
    split = {}
    for at, text in SPLIT_POINTERS.items():
        off = at - BASE + FILE_OFF
        target = struct.unpack_from('<I', data, off)[0]
        if bytes(BASE_DATA[target - BASE + FILE_OFF:][:len(SPLIT_OLD) * 2 + 1]) != SPLIT_OLD.encode('cp932') + b'\0':
            raise SystemExit(f'exetext: pointer at {at:#x} does not point at {SPLIT_OLD}')
        if text not in split:
            split[text] = EXTRA_BASE + len(extra)
            extra += encode(text) + b'\0'
            extra += bytes(-len(extra) % 4)
        struct.pack_into('<I', data, off, split[text])
    for at, old, new in PLAYER_DIGIT:
        off = at - BASE + FILE_OFF
        if struct.unpack_from('<I', data, off)[0] != old:
            raise SystemExit(f'exetext: unexpected word at {at:#x} (player number)')
        struct.pack_into('<I', data, off, new)
    if extra:
        data = add_segment(data, extra)
    files.put(EXE_FILE, data)
    print(f'executable text: {kept} strings in place, {moved} moved ({len(extra)} bytes after .bss)')


def add_segment(data, extra):
    """Append `extra` as a second PT_LOAD at EXTRA_BASE and start the heap (and sbrk) after it."""
    data = bytearray(data)
    phoff, = struct.unpack_from('<I', data, 0x1c)
    phnum, = struct.unpack_from('<H', data, 0x2c)
    if phnum != 1:
        raise SystemExit('exetext: the executable already has more than one segment')
    if any(data[phoff + 32:phoff + 64]):
        raise SystemExit('exetext: no room for a second program header')
    data += bytes(-len(data) % 16)
    file_off = len(data)
    data += extra
    struct.pack_into('<8I', data, phoff + 32, 1, file_off, EXTRA_BASE, EXTRA_BASE, len(extra), len(extra), 7, 16)
    struct.pack_into('<H', data, 0x2c, 2)
    end = (EXTRA_BASE + len(extra) + 0xff) & ~0xff
    for (at, old), new in zip(HEAP_SETUP, (0x3c040000 | ((end + 0x8000) >> 16), 0x24840000 | (end & 0xffff))):
        off = at - BASE + FILE_OFF
        if struct.unpack_from('<I', data, off)[0] != old:
            raise SystemExit(f'exetext: unexpected code at {at:#x} (heap setup)')
        struct.pack_into('<I', data, off, new)
    at, old = HEAP_BREAK
    if struct.unpack_from('<I', data, at - BASE + FILE_OFF)[0] != old:
        raise SystemExit(f'exetext: unexpected value at {at:#x} (sbrk break)')
    struct.pack_into('<I', data, at - BASE + FILE_OFF, end)
    return data


def dump(lo=0, hi=1 << 32):
    for r in read_rows():
        a = int(r['id'], 16)
        if lo <= a < hi:
            room = r['max_bytes'] + ('' if int(r['refs']) else ' FIXED')
            print(f"{r['id']}\t{room}\t{r['japanese']}" + (f"\t= {r['english']}" if r['english'] else ''))


def import_tsv(path, dry_run=False):
    rows = read_rows()
    by = {r['id']: r for r in rows}
    n, problems = 0, []
    for ln in Path(path).read_text(encoding='utf-8').splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        ident, _, text = ln.partition('\t')
        ident, text = ident.strip(), text.strip()
        r = by.get(ident)
        if r is None:
            problems.append(f'{ident}: no such string')
            continue
        try:
            enc = encode(text)
        except UnicodeEncodeError as x:
            problems.append(f'{ident}: character the game cannot show: {x.object[x.start]!r} in {text!r}')
            continue
        if not int(r['refs']) and len(enc) > int(r['max_bytes']):
            problems.append(f'{ident}: {len(enc)} bytes, this string cannot move and has room for {r["max_bytes"]}: {text!r}')
            continue
        jp_lines, en_lines = r['japanese'].count('\\n'), text.count('\\n')
        if jp_lines != en_lines:
            problems.append(f'{ident}: {en_lines} line breaks, the original has {jp_lines} (warning): {text!r}')
        r['english'] = text
        n += 1
    for p in problems:
        print(p)
    if not dry_run:
        with open(csv_path(), 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows(rows)
    print(f'import: {n} strings' + (' checked (dry run)' if dry_run else ' set') + f', {len(problems)} problems')
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('extract')
    e.add_argument('--force', action='store_true')
    sub.add_parser('check')
    sub.add_parser('stats')
    d = sub.add_parser('dump')
    d.add_argument('range', nargs='*', help='FROM TO addresses (hex)')
    i = sub.add_parser('import')
    i.add_argument('file')
    i.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    if args.cmd == 'extract':
        extract(args.force)
    elif args.cmd == 'check':
        if csv_path().exists():
            items = plan((paths.EXTRACTED / EXE_FILE.lstrip('/')).read_bytes())
            bad = [(a, refs) for a, enc, refs, room in items
                   if len(enc) + 1 > room and any(r[0] in ('gp', 'shared') for r in refs)]
            for a, refs in bad:
                print(f'{a:#x}: too long for its room and not movable ({refs_text(refs)})')
            sys.exit(1 if bad else 0)
    elif args.cmd == 'dump':
        dump(*[int(x, 16) for x in args.range])
    elif args.cmd == 'import':
        import_tsv(args.file, args.dry_run)
    else:
        rows = read_rows()
        kinds = {}
        for r in rows:
            k = 'movable' if int(r['refs']) else 'in place only'
            kinds[k] = kinds.get(k, 0) + 1
        print(f'{len(rows)} strings: ' + ', '.join(f'{n} {k}' for k, n in kinds.items()))


if __name__ == '__main__':
    main()
