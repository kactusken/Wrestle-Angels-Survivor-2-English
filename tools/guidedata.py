#!/usr/bin/env python3
"""Data for the player's guide (docs/guide/index.html), read from the original executable.

  guidedata.py [--check]        fill the page's data block (tools/pagedata.py)
  guidedata.py --json FILE      write the data to FILE instead (the page isn't needed)

Every number comes from the original's tables in extracted/SLPM_550.56 (file offset = RAM address
- 0x1ff000, tools/elf.py); every English name from translation/text/ - roster.csv (ring names,
real names, titles), moves.csv, skills.csv, foreign.csv (countries) and exe.csv (hometowns,
descriptions, CPU promotion and belt names, president skills, eras). Untranslated names fall back
to the Japanese as the patch shows it (full-width letters made half-width). While
docs/guide/index.html doesn't exist, --check passes (nothing to check).

*From the code* (addresses are RAM; record offsets count from the name, as records.py does - the
code's record base is the wrestler id 4 bytes before it):
  0x510110             243 roster records of 0x848: u32 id (1-79 first personas, 101-179 their
                       second personas = record + 79, 201-242 and 301-342 foreign wrestlers,
                       999 the secretary - left out, as every roster loop stops at 241), then
       +0x00 / 0x40 / 0x80 / 0x7f4   name, ring name, short name, title (records.py `roster`)
       +0xc0           class 0-4, drawn as SS / S / M / L / LL (status page 0x2c5880)
       +0xc4           hometown: index into the prefecture/country list 0x38ea20
       +0xc8           birthday: low byte month, next byte day
       +0xcc           starting age
       +0xd8           talent grade 0-5 (6 = rolled at a new game, 0x235250; MANAGEMENT.md 6.1)
       +0xdc           8 skills, skill table index + 1 (-1 = none); table 0x50e000, 0x80 each
       +0x108          alignment 0 Face / 1 Normal / 2 Heel (docs/TECHNICAL.md)
       +0x134 / 0x174  16 stat words each, A and B (below); the 16th is not a rated stat
       +0x1c4          6 move groups (Throw, Hold, Power, Strike, Aerial, Other) of 0xfc: 3
                       words = how many of the list are known at LEVEL 1/2/3, then 6 entries of
                       0x28 (0x20 unused name, move id, move level 1-9; 0x239044)
       +0x7dc          greed, % on salary demands (0x23b4d0, used by 0x3013b0)
       +0x7e4          debut value D: she appears once era x 3 + year + 6 >= D (0x2362c0); at a
                       new game she is already there, D - 6 - 3 x era years past her starting age,
                       when that is 0 or less (0x23f1f0)
       +0x7e8          3 words, one per era: the CPU promotion she starts on (0 = none; 1-6 =
                       the promotion list's first six, 7 = the tenth, via 0x20e030 / 0x46b248)
  0x238d18             match stats from A and B: Special Match LEVEL 1 = A, LEVEL 2 = (A + B) / 2
                       x 120 %, LEVEL 3 = B x 140 % (foreign wrestlers: B x 88 / 94 / 100 %);
                       the callers pick 1-3 (0x2af4c8, 0x2b45bc at random; 0x2ba670 by choice).
                       Management mode starts from A and ages it (0x234c34, 0x23ead8) - not here.
  grades               0-15 at thresholds 100, 200 ... 800, 950, 1100, 1250, 1400, 1550, 1750,
                       1950 (MANAGEMENT.md 8.1), drawn from 0x59ca80 as 0-9, A-E, S
  0x4ff988             223 moves of 264 bytes: name, id `Wnnn`, +0x50 index, +0x54 group,
                       +0x58 two counter moves (move ids), +0x68 two owner wrestler ids (the
                       signature versions)
  0x3a8c40             242 profile description pointers, one per record
  0x38eb68 / 0x38eb90  the ten CPU promotions' names and abbreviations
  0x475d68             6 foreign promotions of 0xc0: name, +0x28 country, +0x48 partnership base
                       cost (0x230180 adds 100 a step), +0x50 7 pairs of wrestler ids
  0x4664a0             28 established belts of 0x30: owner (CPU type code, 100+ foreign
                       promotion, 106 Asia), name, prestige, holders (2 per era, 255 = none),
                       kind per era (1 singles, 2 tag, 3 the third belt, 0 = not in that era)
  0x38eb28 / 0x3cce50  the 16 president skills and their help lines
"""
import argparse
import csv
import json
import struct
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import elf  # noqa: E402
import exetext  # noqa: E402
import pagedata  # noqa: E402
import paths  # noqa: E402

EXE = 'SLPM_550.56'
ROSTER, REC, RECORDS = 0x510110, 0x848, 242          # id word, then the record; 242 = the secretary
DOMESTIC, FIRST_PERSONAS = 158, 79
SKILLS, SKILL_SIZE, SKILL_COUNT = 0x50e000, 0x80, 66
MOVES, MOVE_SIZE, MOVE_COUNT = 0x4ff988, 264, 223
PLACES, PLACE_COUNT = 0x38ea20, 63       # prefectures, then countries, then "unknown"
DESCRIPTIONS = 0x3a8c40
PROMO_NAMES, PROMO_ABBR, PROMO_COUNT = 0x38eb68, 0x38eb90, 10
PROMO_OF_VALUE = [0, 1, 2, 3, 4, 5, 9]                # record value 1-7 -> promotion list index
PROMO_TYPES = 0x46b248                                # type code of each promotion (belt owners)
FOREIGN, FOREIGN_SIZE, FOREIGN_COUNT = 0x475d68, 0xc0, 6
BELTS, BELT_SIZE = 0x4664a0, 0x30
PRESIDENT, PRESIDENT_HELP, PRESIDENT_COUNT = 0x38eb28, 0x3cce50, 16
GRADE_DIGITS = 0x59ca80                               # 16 x 8 bytes: 0-9, A-E, S
ALIGNMENTS = (0x59ccc0, 0x4eebf8, 0x59ccc8)           # Face, Normal, Heel (docs/TECHNICAL.md)
ERAS = (0x46bd88, 0x46be00, 0x46be70)

CLASSES = ['SS', 'S', 'M', 'L', 'LL']                 # 0x2c58b0-0x2c5918: 0x59cc40, 0x59caf8, ...
GROUPS = ['Throw', 'Hold', 'Power', 'Strike', 'Aerial', 'Other']   # the match screen's words
STATS = ['Throw Atk', 'Throw Def', 'Hold Atk', 'Hold Def', 'Power Atk', 'Power Def', 'Strike Atk',
         'Strike Def', 'Aerial Atk', 'Aerial Def', 'Str', 'Dex', 'Sta', 'Rec', 'Spd']
THRESHOLDS = [100, 200, 300, 400, 500, 600, 700, 800, 950, 1100, 1250, 1400, 1550, 1750, 1950]
FOREIGN_PCT = (88, 94, 100)


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def s32(d, o):
    return struct.unpack_from('<i', d, o)[0]


def half(t):
    return unicodedata.normalize('NFKC', t).strip()


def flat(t):
    """A message text as one line: the game's line breaks become spaces."""
    return ' '.join(x.strip() for x in exetext.unescape(t).split('\n') if x.strip())


class Exe:
    def __init__(self):
        p = paths.EXTRACTED / EXE
        if not p.exists():
            sys.exit(f'{paths.show(p)} not found - run tools/extract.py first')
        self.d = p.read_bytes()
        self.elf = elf.Elf(self.d)

    def off(self, addr):
        return self.elf.offset(addr)

    def at(self, addr, n):
        o = self.off(addr)
        return self.d[o:o + n]

    def u32(self, addr):
        return u32(self.d, self.off(addr))

    def s32(self, addr):
        return s32(self.d, self.off(addr))

    def sjis(self, addr, n=64):
        return self.at(addr, n).split(b'\0')[0].decode('cp932')


def read_csv(name):
    p = paths.TEXT / name
    if not p.exists():
        sys.exit(f'{paths.show(p)} not found')
    with open(p, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


class Text:
    """English for the executable's strings (exe.csv by address) and the record tables (by
    field and Japanese), falling back to the Japanese, made half-width."""

    def __init__(self, exe):
        self.exe = exe
        self.ex = {int(r['id'], 16): r['english'] for r in read_csv('exe.csv')}
        self.tables = {}
        for name in ('roster.csv', 'moves.csv', 'skills.csv', 'foreign.csv'):
            self.tables[name] = {(r['field'], r['japanese']): r['english'] for r in read_csv(name)}

    def at(self, addr, n=256):
        ja = self.exe.sjis(addr, n)
        en = self.ex.get(addr)
        return (flat(en) if en else half(ja)), ja

    def table(self, name, field, ja):
        return self.tables[name].get((field, ja)) or half(ja)


def grade(v):
    return sum(v >= t for t in THRESHOLDS)


def levels(a, b, domestic):
    """Stat values at Special Match LEVEL 1, 2, 3 (0x238d18, integer maths as the code)."""
    if domestic:
        return [list(a), [(x + y) // 2 * 120 // 100 for x, y in zip(a, b)], [y * 140 // 100 for y in b]]
    return [[y * p // 100 for y in b] for p in FOREIGN_PCT]


def move_table(exe, text):
    out = []
    for k in range(MOVE_COUNT):
        a = MOVES + MOVE_SIZE * k
        rec = exe.at(a, MOVE_SIZE)
        f = struct.unpack_from('<12i', rec, 0x48)
        if f[2] != k + 1:
            sys.exit(f'guidedata: move {k + 1} has index {f[2]} - not the original executable?')
        ja = exe.sjis(a)
        m = {'id': k + 1, 'w': exe.sjis(a + 0x40, 8), 'n': text.table('moves.csv', 'name', ja), 'ja': ja,
             't': f[3]}
        rev = [x for x in f[4:6] if x]
        if rev:
            m['rev'] = rev
        own = [x for x in f[8:10] if x > 0]
        if own:
            m['own'] = own
        out.append(m)
    return out


def skill_table(exe, text):
    out = []
    for k in range(SKILL_COUNT):
        a = SKILLS + SKILL_SIZE * k
        ja = exe.sjis(a, 0x20)
        s = {'n': text.table('skills.csv', 'name', ja), 'ja': ja}
        help_ja = exe.sjis(a + 0x20, 0x60)
        help_en = text.tables['skills.csv'].get(('help', help_ja))
        if help_en:
            s['d'] = help_en
        out.append(s)
    return out


def wrestlers(exe, text, moves):
    places = [text.at(exe.u32(PLACES + 4 * k))[0] for k in range(PLACE_COUNT)]
    align = [text.at(a)[0] for a in ALIGNMENTS]
    owners = {}
    for m in moves:
        for w in m.get('own', ()):
            owners.setdefault(w, []).append(m['id'])
    out = []
    base = exe.off(ROSTER)
    for i in range(RECORDS):
        o = base + REC * i
        wid = u32(exe.d, o)
        r = exe.d[o + 4:o + REC]
        name = lambda off: r[off:off + 0x40].split(b'\0')[0].decode('cp932')
        domestic = i < DOMESTIC
        ring, real = name(0x40), name(0)
        w = {'i': i, 'id': wid, 'n': text.table('roster.csv', 'ring', ring), 'ja': ring}
        if real != ring:
            w['real'] = text.table('roster.csv', 'name', real)
        if name(0x7f4):
            w['title'] = text.table('roster.csv', 'title', name(0x7f4))
        cls, home, born, age, talent = (s32(r, x) for x in (0xc0, 0xc4, 0xc8, 0xcc, 0xd8))
        w['cls'] = CLASSES[cls]
        w['home'] = places[home]
        w['born'] = [born & 0xff, (born >> 8) & 0xff]
        w['age'] = age
        if domestic:
            w['tal'] = talent if talent < 6 else None
        w['sk'] = [x - 1 for x in struct.unpack_from('<8i', r, 0xdc) if x > 0]
        w['al'] = align[s32(r, 0x108)]
        w['greed'] = s32(r, 0x7dc)
        a = struct.unpack_from('<15i', r, 0x134)
        b = struct.unpack_from('<15i', r, 0x174)
        vals = levels(a, b, domestic)
        w['g'] = [[grade(v) for v in lv] for lv in vals]
        w['v'] = vals
        mv, known = [], []
        for g in range(6):
            go = 0x1c4 + 0xfc * g
            known.append(list(struct.unpack_from('<3i', r, go)))
            ent = []
            for e in range(6):
                mid, lvl = struct.unpack_from('<2i', r, go + 0xc + 0x28 * e + 0x20)
                if mid:
                    ent.append([mid, lvl])
            mv.append(ent)
        w['mv'] = mv
        w['kn'] = known
        if wid in owners:
            w['sig'] = owners[wid]
        if domestic:
            w['alt'] = wid + 100 if wid < 100 else wid - 100
            dv = s32(r, 0x7e4)
            st = []
            for era in range(3):
                ys = dv - 6 - 3 * era
                p = s32(r, 0x7e8 + 4 * era)
                st.append({'y': ys, **({'p': PROMO_OF_VALUE[p - 1]} if p else {})})
            w['st'] = st
        else:
            w['succ'] = wid + 100 if wid < 300 else wid - 100
        d = exe.u32(DESCRIPTIONS + 4 * i)
        w['d'] = text.at(d)[0]
        out.append(w)
    return out


def promotions(exe, text, roster):
    out = []
    for k in range(PROMO_COUNT):
        n, ja = text.at(exe.u32(PROMO_NAMES + 4 * k))
        p = {'i': k, 'n': n, 'ja': ja, 'ab': text.at(exe.u32(PROMO_ABBR + 4 * k))[0],
             'type': exe.s32(PROMO_TYPES + 4 * k),
             'start': [[w['i'] for w in roster if 'st' in w and w['st'][era].get('p') == k] for era in range(3)]}
        out.append(p)
    return out


def foreign(exe, text):
    out = []
    for k in range(FOREIGN_COUNT):
        a = FOREIGN + FOREIGN_SIZE * k
        ja = exe.sjis(a, 0x28)
        country = exe.sjis(a + 0x28, 0x20)
        ids = struct.unpack_from('<14i', exe.at(a + 0x50, 56))
        out.append({'i': k, 'n': half(ja), 'ja': ja, 'country': text.table('foreign.csv', 'country', country),
                    'ap': exe.s32(a + 0x48), 'w': [list(ids[j:j + 2]) for j in range(0, 14, 2)]})
    return out


def belts(exe, text, promos):
    by_type = {p['type']: p['i'] for p in promos}
    out = []
    k = 0
    while True:
        a = BELTS + BELT_SIZE * k
        f = struct.unpack_from('<12i', exe.at(a, BELT_SIZE))
        if f[0] < 0 or not 0x400000 < (f[1] & 0xffffffff) < 0x600000:
            break
        n, ja = text.at(f[1] & 0xffffffff)
        b = {'n': n, 'ja': ja, 'pr': f[2], 'kind': list(f[9:12]),
             'hold': [[x for x in f[3 + 2 * e:5 + 2 * e] if x != 255] for e in range(3)]}
        if f[0] in by_type:
            b['p'] = by_type[f[0]]
        elif 100 <= f[0] < 100 + FOREIGN_COUNT:
            b['f'] = f[0] - 100
        else:
            b['own'] = f[0]
        out.append(b)
        k += 1
    return out


def president(exe, text):
    return [{'n': text.at(exe.u32(PRESIDENT + 4 * k))[0], 'd': text.at(exe.u32(PRESIDENT_HELP + 4 * k))[0]}
            for k in range(PRESIDENT_COUNT)]


def build():
    exe = Exe()
    text = Text(exe)
    digits = [half(exe.sjis(GRADE_DIGITS + 8 * k, 8)) for k in range(16)]
    if digits != [str(x) for x in range(10)] + list('ABCDES'):
        sys.exit(f'guidedata: grade letters {digits} are not the original\'s')
    moves = move_table(exe, text)
    roster = wrestlers(exe, text, moves)
    promos = promotions(exe, text, roster)
    return {
        'notes': {
            'g': 'grades 0-15 of the 15 stats (stats) at Special Match LEVEL 1, 2, 3; shown as grades[g]',
            'v': 'the stat values behind g; LEVEL 1 = A, 2 = (A + B) / 2 x 120 %, 3 = B x 140 %; '
                 'foreign wrestlers B x 88 / 94 / 100 %',
            'mv': 'per move group (groups): [move id, move level] in list order; kn = how many of '
                  'them she knows at LEVEL 1/2/3 (the first n); the rest are learnable',
            'sig': 'signature moves: moves whose record names her id as owner',
            'st': 'per era: y = D - 6 - 3 x era; y <= 0: there at the start, age - y years old; '
                  'y > 0: appears in year y (the code tests era x 3 + year + 6 >= D); p = the CPU '
                  'promotion (promotions[p]) she starts on',
            'tal': 'talent grade 0 (best) - 5; null = rolled at each new game',
            'greed': '% added to her salary demands',
            'alt': 'id of the other persona (record i +/- 79); succ: the foreign successor id',
            'belts': 'kind per era: 1 singles, 2 tag, 3 third belt, 0 not in that era; hold = '
                     'wrestler ids per era; p = CPU promotion, f = foreign promotion, own 106 = Asia',
            'foreign': 'ap = partnership base cost; w = 7 pairs of wrestler ids',
        },
        'eras': [text.at(a)[0] for a in ERAS],
        'grades': digits,
        'thresholds': THRESHOLDS,
        'stats': STATS,
        'groups': GROUPS,
        'classes': CLASSES,
        'wrestlers': roster,
        'skills': skill_table(exe, text),
        'moves': moves,
        'promotions': promos,
        'foreign': foreign(exe, text),
        'belts': belts(exe, text, promos),
        'president': president(exe, text),
    }


def summary(data):
    w = data['wrestlers']
    print(f"guidedata: {len(w)} wrestlers ({sum(1 for x in w if 'alt' in x)} domestic, "
          f"{sum(1 for x in w if 'sig' in x)} with signature moves), {len(data['moves'])} moves, "
          f"{len(data['skills'])} skills, {len(data['promotions'])} CPU promotions, "
          f"{len(data['foreign'])} foreign promotions, {len(data['belts'])} belts, "
          f"{len(data['president'])} president skills")


def main(argv=None):
    argv = paths.configure(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true', help='only check that the page is up to date')
    ap.add_argument('--json', type=Path, metavar='FILE', help='write the data to FILE instead of the page')
    args = ap.parse_args(argv)
    page = paths.DOCS / 'guide' / 'index.html'
    if args.check and not page.exists():
        print(f'guidedata: {paths.show(page)} does not exist yet - nothing to check')
        return 0
    data = build()
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
        summary(data)
        print(f'guidedata: written to {paths.show(args.json)}')
        return 0
    if not page.exists():
        print(f'guidedata: {paths.show(page)} does not exist yet - nothing to fill')
        return 0
    if pagedata.write(page, data, check=args.check) and args.check:
        print(f'guidedata: {paths.show(page)} is up to date')
    elif not args.check:
        summary(data)
    return 0


if __name__ == '__main__':
    sys.exit(main())
