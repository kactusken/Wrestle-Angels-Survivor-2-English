#!/usr/bin/env python3
"""Event scripts (/SCR/*.BIN): extract the text to translation/script/, build it back.

  scr.py extract [NNN...] [--force]   write translation/script/NNN.txt (keeps existing English)
  scr.py roundtrip                    parse + rebuild every script unchanged: must be identical
  scr.py propagate [--dry-run]        1NN/3NN repeat 0NN/2NN for a character's other persona:
                                      copy English to blocks with the same id and source
  scr.py wrap [NNN...] [--all]        re-break English lines to the message box (overflowing
                                      blocks only, or every block with --all)
  scr.py check [NNN...]               script-specific checks (also run by tools/check.py)
  scr.py dump NNN [--untranslated]    one line per block: id, speaker, source (for translating)
  scr.py import NNN FILE              English from `id<TAB>text` lines ('|' = line break,
                                      the rest is word-wrapped to the box)

Format (docs/TECHNICAL.md "Event scripts"): a table of u32 offsets ending with the file size and
a 0 word (padded with zeros to 16 bytes), then segments (one scene each), each a CRLF text ending in NUL, padded with zeros to 16
bytes (the last one is not padded). The engine reads the text at run time; a file may hold
0x40000 bytes (0x200cb8 "Script Size is too large!!").

Lines are commands (`cg kaiwa_001_1`, `if ...`, `item "ほめる", LB_...`), labels, `//` comments,
speaker lines `\\c(001)【石川 涼美】` and message lines (`text\\ntext\\b`). Every message line is
one block; its JP lines are the message's screen lines (split at \\n), and the EN lines replace
them. Speaker names (anything in 【】) come from translation/text/speakers.csv and choice labels
(`item "..."`) from translation/text/choices.csv.

How English is stored (encode()):
  - ' ', ',' and '"' end tokens in the game's tokenizer: they're written as '_', '`' and '^',
    which tools/font.py draws as a space, comma and double quote;
  - '~' is the full-width ～ (the half-width set is JIS-Roman: 0x7e is an overline);
  - curly quotes, … and dashes become ASCII; other characters must exist in Shift-JIS;
  - a line whose first byte would be ASCII (not '%' or '\\') starts with the zero-width marker
    tools/font.py ZERO_WIDTH, or the engine would take it for a label.
Box: 3 lines of LINE_PX pixels (tools/font.py widths). `\\n` codes are written by the build.
"""
import argparse
import csv
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blocks  # noqa: E402
import font  # noqa: E402
import paths  # noqa: E402

DIR = '/SCR/'
MAX_SIZE = 0x40000
LINE_PX = 440        # message box line, pixels (Japanese lines stay within 20 full-width = 440)
MAX_LINES = 3
COMMANDS = set('''if endif add alarm bg bgfill bgmv bglc bto bgm cg cgh cgmv cgmvas cglc cglcas cga
cgbc call dd ddb ddw ddm da daa dam down er ercg go item let mto nop pt pause pauseabs return site se
sel sub ts th up use wait wto select null l c r r2 r3'''.split())
SPEAKERS_CSV = 'speakers.csv'
CHOICES_CSV = 'choices.csv'
NAME = re.compile(r'【([^】\r\n]*)】')
ITEM = re.compile(r'^(\s*item\s+")([^"]*)(".*)$')

HEADER = '''# /SCR/{name}.BIN - {title}
# One block per message line of the event script. JP lines are the screen lines of the original
# message; write the English as EN lines - one line on screen each, at most {lines} lines of
# {px} pixels (about 44 characters; `python3 tools/scr.py wrap {name}` re-breaks overflowing
# blocks). Comments give the speaker and the scene.
# Keep codes verbatim: %chr (a wrestler's name) and \\c() (speaker change); the end-of-message
# code and the line breaks are written by the build.
# Speaker names in 【】 are translated in translation/text/speakers.csv, not here.
# '~' is shown as the full-width ～; don't use \\ or // in the English.
'''


# --- container --------------------------------------------------------------------------------
def parse(data):
    """[segment text bytes without the NUL], checking the layout as it goes."""
    offs, i = [], 0
    while True:
        o, = struct.unpack_from('<I', data, i)
        i += 4
        if o == 0:
            break
        offs.append(o)
    if offs[-1] != len(data) or offs[0] != i + (-i % 16) or any(data[i:offs[0]]):
        raise ValueError(f'unexpected script layout (table {i} bytes, first {offs[0]}, end {offs[-1]}, size {len(data)})')
    segs = []
    for a, b in zip(offs, offs[1:]):
        s = data[a:b]
        segs.append(s[:s.index(b'\0')])
    return segs


def build(segs):
    table = 4 * (len(segs) + 2)
    out = bytearray(table + (-table % 16))
    offs = []
    for k, s in enumerate(segs):
        offs.append(len(out))
        out += s + b'\0'
        if k + 1 < len(segs):
            out += bytes(-len(out) % 16)
    offs.append(len(out))
    struct.pack_into(f'<{len(offs) + 1}I', out, 0, *offs, 0)
    return bytes(out)


# --- lines -------------------------------------------------------------------------------------
def kind(line):
    """'comment', 'blank', 'speaker', 'item', 'command', 'label' or 'text'."""
    t = line.strip()
    if not t:
        return 'blank'
    if t.startswith('//'):
        return 'comment'
    if t.startswith('\\c('):
        return 'speaker'
    if ITEM.match(line):
        return 'item'
    first = re.split(r'[\s,]', t, 1)[0]
    if first in COMMANDS:
        return 'command'
    if re.fullmatch(r'[A-Za-z_]\w*:', first):
        return 'label'
    if ord(t[0]) < 0x80 and t[0] not in '%\\':
        return 'label'      # the engine takes any other ASCII first byte as a label: never shown
    if any(ord(c) > 0x7f for c in t.split('//')[0]) or t.startswith('%'):
        return 'text'
    return 'command'


def split_text(line):
    """(lead, [screen lines], tail) of a message line: lead = indentation, tail = trailing \\b."""
    lead = line[:len(line) - len(line.lstrip())]
    body = line[len(lead):]
    tail = ''
    m = re.search(r'(\\b)+(\\c\([^)]*\)【[^】]*】)?\s*$', body)   # a few lines run on into the next speaker
    if m:
        body, tail = body[:m.start()], body[m.start():]
    return lead, body.split('\\n'), tail


def has_source_text(parts):
    s = NAME.sub('', '\\n'.join(parts))
    s = re.sub(r'\\c\([^)]*\)', '', s)
    return any(ord(c) > 0x7f for c in s)


def decode(b):
    s = b.decode('cp932')
    if s.encode('cp932') != b:
        raise ValueError(f'line does not survive cp932 round trip: {b!r}')
    return s


# --- English -----------------------------------------------------------------------------------
REPLACE = {'’': "'", '‘': "'", '“': '"', '”': '"', '…': '...', '—': '―', '–': '-', '~': '～',
           '\u3000': ' ', '！': '!', '？': '?'}


def normalize(text):
    for a, b in REPLACE.items():
        text = text.replace(a, b)
    return text


def encode(text):
    """English text (one script line's worth) -> what the script stores (str, cp932-safe)."""
    text = normalize(text)
    out = []
    for ch in text:
        out.append(font.STAND_INS.get(ch, ch))
    s = ''.join(out)
    if MARK in s:
        raise UnicodeEncodeError('cp932', s, s.index(MARK), s.index(MARK) + 1, 'reserved character')
    s.encode('cp932')  # raises on characters the game can't show
    return s


# The zero-width marker is unassigned in Shift-JIS (no codec writes it): lines carry this
# private-use character until encode_line() turns them into bytes.
MARK = '\ue000'
ZERO_WIDTH = bytes([font.ZERO_WIDTH >> 8, font.ZERO_WIDTH & 0xff])


def encode_line(ln):
    a, mark, b = ln.partition(MARK)
    return a.encode('cp932') + (ZERO_WIDTH + b.encode('cp932') if mark else b'')


def line_start(s):
    """Prefix the zero-width marker when the engine would not see `s` as a message."""
    if s and ord(s[0]) < 0x80 and s[0] not in '%\\':
        return MARK + s
    return s


def table(name):
    """{japanese: english} from translation/text/<name> (rows with English only)."""
    p = paths.TEXT / name
    if not p.exists():
        return {}
    with open(p, encoding='utf-8', newline='') as f:
        return {r['japanese']: r['english'] for r in csv.DictReader(f) if (r.get('english') or '').strip()}


def translate_names(s, speakers):
    return NAME.sub(lambda m: '【' + encode(speakers[m.group(1)]) + '】' if m.group(1) in speakers else m.group(0), s)


# --- block files -------------------------------------------------------------------------------
def script_names():
    return sorted(p.stem for p in (paths.EXTRACTED / DIR.strip('/')).glob('*.BIN'))


def block_path(name):
    return paths.SCRIPT / f'{name}.txt'


def scene_title(seg_lines):
    for ln in seg_lines[:6]:
        m = re.match(r'//\s*(\d{3}\s.*)$', ln.strip())
        if m:
            return m.group(1).replace('\u3000', ' ').strip()
    return ''


def extract_one(name, force=False):
    data = (paths.EXTRACTED / DIR.strip('/') / f'{name}.BIN').read_bytes()
    segs = parse(data)
    out_path = block_path(name)
    old = {}
    if out_path.exists():
        if not force:
            return False
        old = {b.id: b for b in blocks.BlockFile(out_path).blocks}
    title = ''
    body = []
    for k, seg in enumerate(segs):
        lines = [decode(b) for b in seg.split(b'\r\n')]
        if k == 0:
            m = re.match(r'//\s*char\d+：(.*)', lines[1].strip()) if len(lines) > 1 else None
            title = m.group(1) if m else ''
        scene = scene_title(lines)
        speaker = ''
        first = True
        for n, ln in enumerate(lines):
            kd = kind(ln)
            if kd == 'speaker':
                m = NAME.search(ln)
                speaker = m.group(1).replace('\u3000', ' ') if m else ''
                continue
            if kd != 'text':
                continue
            lead, parts, tail = split_text(ln)
            if not has_source_text(parts):
                continue
            ident = f'{k}.{n}'
            body.append(f'@ {ident}')
            if first and scene:
                body.append(f'# scene {scene}')
                first = False
            if speaker:
                body.append(f'# {speaker}')
            if not tail:
                body.append('# (no \\b: the original line has no end-of-message code)')
            body += [f'JP {p}' for p in parts]
            if ident in old:
                body += [f'EN {e}' for e in old[ident].english]
            body.append('')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(HEADER.format(name=name, title=title, lines=MAX_LINES, px=LINE_PX) + '\n' +
                        '\n'.join(body), encoding='utf-8')
    return True


def english_lines(block):
    return [normalize(e) for e in block.english]


def rebuild(name, data, speakers, choices, bf=None):
    """Script bytes with the English of block file `bf` (None: names and choices only)."""
    segs = parse(data)
    eng = {b.id: b.english for b in bf.blocks if b.english} if bf else {}
    new = []
    for k, seg in enumerate(segs):
        lines = [decode(b) for b in seg.split(b'\r\n')]
        for n, ln in enumerate(lines):
            kd = kind(ln)
            ident = f'{k}.{n}'
            if kd == 'text' and ident in eng:
                lead, parts, tail = split_text(ln)
                body = '\\n'.join(encode(e) for e in eng[ident])
                ln = lead + line_start(body) + tail
            elif kd == 'item':
                m = ITEM.match(ln)
                if m.group(2) in choices:
                    ln = m.group(1) + encode(choices[m.group(2)]) + m.group(3)
            if kd in ('text', 'speaker', 'item'):
                ln = translate_names(ln, speakers)
            lines[n] = ln
        new.append(b'\r\n'.join(encode_line(ln) for ln in lines))
    out = build(new)
    if len(out) > MAX_SIZE:
        raise SystemExit(f'{DIR}{name}.BIN: {len(out)} bytes, the game takes at most {MAX_SIZE}')
    return out


# --- checks --------------------------------------------------------------------------------------
_WIDTHS = None


def widths():
    global _WIDTHS
    if _WIDTHS is None:
        _WIDTHS = font.load_widths(paths.EXTRACTED / font.FONT_FILE.lstrip('/'))
    return _WIDTHS


def line_px(text):
    s = re.sub(r'%chr', 'X' * 9, normalize(text))       # a wrestler's name: ~9 letters
    s = re.sub(r'\\c\([^)]*\)', '', s)
    return font.text_width(s, widths())


def check_block(b):
    """[(severity, message)] for one block's English."""
    out = []
    en = english_lines(b)
    if not en:
        return out
    if len(en) > MAX_LINES:
        out.append(('error', f'{len(en)} lines, the box shows {MAX_LINES}'))
    for i, e in enumerate(en):
        try:
            enc = encode(e)
        except UnicodeEncodeError as x:
            out.append(('error', f'character the game cannot show: {x.object[x.start]!r} in {e!r}'))
            continue
        px = line_px(e)
        if px > LINE_PX:
            out.append(('error', f'{px} px, the box line is {LINE_PX}: {e!r}'))
        nbytes = len(enc.encode('cp932')) + (2 if i == 0 else 0)
        if nbytes > font.LINE_BYTES:
            out.append(('error', f'{nbytes} bytes, the window draws {font.LINE_BYTES} per line: {e!r}'))
        if '//' in e:
            out.append(('error', f'"//" starts a script comment: {e!r}'))
        if re.search(r'\\(?!c\()', e):
            out.append(('error', f'backslash code other than \\c() in the English (screen lines are separate EN lines): {e!r}'))
    return out


def check(names=None):
    errors = 0
    for name in names or script_names():
        p = block_path(name)
        if not p.exists():
            continue
        for b in blocks.BlockFile(p).blocks:
            for sev, msg in check_block(b):
                if sev == 'error':
                    errors += 1
                print(f'{paths.show(p)}:{b.line} [{b.id}] {sev}: {msg}')
    return errors


# --- whole-project helpers -----------------------------------------------------------------------
def propagate(dry_run=False):
    """1NN repeats 0NN (and 3NN repeats 2NN) for a character's other persona: copy the English of
    blocks with the same id and the same source text."""
    filled = 0
    for name in script_names():
        if name[0] not in '13':
            continue
        base = f'{int(name[0]) - 1}{name[1:]}'
        p, q = block_path(name), block_path(base)
        if not (p.exists() and q.exists()):
            continue
        bf, ref = blocks.BlockFile(p), blocks.BlockFile(q)
        changed = False
        for blk in bf.blocks:
            other = ref.get(blk.id)
            if blk.english or not other or not other.english or bf.source(blk) != ref.source(other):
                continue
            blk.english = other.english
            filled += 1
            changed = True
        if changed and not dry_run:
            bf.save()
    print(f'propagate: {filled} blocks filled from the paired script' + (' (dry run)' if dry_run else ''))


def dump(name, untranslated=False):
    """A compact view for translating: one line per block (id, speaker, source joined with ' / ')."""
    bf = blocks.BlockFile(block_path(name))
    for blk in bf.blocks:
        if untranslated and blk.english:
            continue
        notes = [t[2:] for t in blk.tagged('#')]
        scene = next((n[6:] for n in notes if n.startswith('scene ')), '')
        speaker = next((n for n in notes if not n.startswith(('scene ', '('))), '')
        if scene:
            print(f'## {scene}')
        line = f'{blk.id}\t{speaker}\t' + ' / '.join(bf.source(blk))
        if blk.english:
            line += '\t= ' + ' | '.join(blk.english)
        print(line)


def import_tsv(name, tsv):
    """Set English from `id<TAB>text` lines ('|' forces a line break; the rest is word-wrapped)."""
    bf = blocks.BlockFile(block_path(name))
    n, bad = 0, []
    for ln in Path(tsv).read_text(encoding='utf-8').splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        ident, _, text = ln.partition('\t')
        blk = bf.get(ident.strip())
        if blk is None:
            bad.append(f'no block {ident.strip()!r}')
            continue
        text = text.strip()
        lines = []
        for part in text.split('|'):
            lines += wrap_words(' '.join(part.split()))
        blk.english = lines
        n += 1
    bf.save()
    for msg in bad:
        print(f'{name}: {msg}')
    print(f'import: {n} blocks set in {paths.show(block_path(name))}')


def wrap_words(text, limit=LINE_PX):
    words, lines, cur = text.split(' '), [], ''
    for w in words:
        cand = w if not cur else cur + ' ' + w
        if cur and line_px(cand) > limit:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def wrap(names=None, everything=False):
    n = 0
    for name in names or script_names():
        p = block_path(name)
        if not p.exists():
            continue
        bf = blocks.BlockFile(p)
        changed = False
        for b in bf.blocks:
            en = b.english
            if not en:
                continue
            if not everything and len(en) <= MAX_LINES and all(line_px(e) <= LINE_PX for e in en):
                continue
            new = wrap_words(' '.join(e.strip() for e in en))
            if new != en:
                b.english = new
                changed = True
                n += 1
        if changed:
            bf.save()
    print(f'wrap: {n} blocks re-broken')


# --- build step ----------------------------------------------------------------------------------
def apply(path, files):
    """Build step: every script with its English, speaker names and choices."""
    speakers, choices = table(SPEAKERS_CSV), table(CHOICES_CSV)
    errors = check()
    if errors:
        raise SystemExit(f'scr: {errors} errors in translation/script (python3 tools/scr.py check)')
    done = 0
    for name in script_names():
        fname = f'{DIR}{name}.BIN'
        p = block_path(name)
        bf = blocks.BlockFile(p) if p.exists() else None
        data = bytes(files.get(fname))
        new = rebuild(name, data, speakers, choices, bf)
        if new != data:
            files.put(fname, new)
            done += 1
    print(f'scripts: {done} files with English')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('extract')
    e.add_argument('names', nargs='*')
    e.add_argument('--force', action='store_true', help='rewrite existing files (English is kept by block id)')
    sub.add_parser('roundtrip')
    pr = sub.add_parser('propagate')
    pr.add_argument('--dry-run', action='store_true')
    w = sub.add_parser('wrap')
    w.add_argument('names', nargs='*')
    w.add_argument('--all', action='store_true')
    c = sub.add_parser('check')
    c.add_argument('names', nargs='*')
    dp = sub.add_parser('dump')
    dp.add_argument('name')
    dp.add_argument('--untranslated', action='store_true')
    im = sub.add_parser('import')
    im.add_argument('name')
    im.add_argument('file')
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    if args.cmd == 'extract':
        n = sum(extract_one(x, args.force) for x in (args.names or script_names()))
        print(f'extract: {n} files written to {paths.show(paths.SCRIPT)}')
    elif args.cmd == 'roundtrip':
        bad = 0
        for name in script_names():
            data = (paths.EXTRACTED / DIR.strip('/') / f'{name}.BIN').read_bytes()
            if build(parse(data)) != data or rebuild(name, data, {}, {}) != data:
                print(f'{name}: rebuild differs')
                bad += 1
        print(f'roundtrip: {len(script_names()) - bad}/{len(script_names())} identical')
        sys.exit(1 if bad else 0)
    elif args.cmd == 'propagate':
        propagate(args.dry_run)
    elif args.cmd == 'wrap':
        wrap(args.names, args.all)
    elif args.cmd == 'dump':
        dump(args.name, args.untranslated)
    elif args.cmd == 'import':
        import_tsv(args.name, args.file)
        sys.exit(1 if check([args.name]) else 0)
    else:
        sys.exit(1 if check(args.names) else 0)


if __name__ == '__main__':
    main()
