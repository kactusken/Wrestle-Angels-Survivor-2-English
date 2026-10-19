#!/usr/bin/env python3
"""Build the translated image from the original. Standard library only.

  python3 build.py [--name NAME] [--unlocks all|none|GROUP,...] [--clean]
      -> build/NAME.<ext> (default NAME: "<game> (English)")

Steps (default folders shown; move any of them with the folder options - see --help):
  1. verify the original in rom/ (size + SHA-1; --skip-verify skips the hash)
  2. prepare build/NAME: a fresh copy of the original, or - much faster for big images - the last
     build with every range it wrote restored from the original (tools/image.py; --clean copies)
  3. text: translation/script/ and translation/text/ into the game's files (TEXT_STEPS)
  4. code patches picked by --unlocks (CODE_PATCHES, tools/codepatch.py)
  5. images: for every catalogued image the English file the catalogue picks (hand-made >
     approved > rendered), imported by tools/gfx.py; the final set is copied to review/images-english/
  6. write every changed file back into the image (files that fit in place first), then the
     executable with its file table pointing at every file's final place (tools/filetable.py)

Test builds: --boot PART starts the game straight in PART (BOOT_PATCHES, once known);
--no-translation skips text and images, and gameplay patches unless --unlocks is given - on its
own the result is byte-identical to the original (tools/check.py --control proves it).
Developer flags (never for releases): --no-text FILE skips one text file; --debug-log prints the
game's debug messages to the emulator's console. --unlocks all leaves out the debug-* groups.
"""
import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'tools'))
import catalog  # noqa: E402
import codepatch  # noqa: E402
import disc  # noqa: E402
import elf  # noqa: E402
import exetext  # noqa: E402
import font  # noqa: E402
import gfx  # noqa: E402
import filetable  # noqa: E402
import image  # noqa: E402
import paths  # noqa: E402
import records  # noqa: E402
import scr  # noqa: E402

# Gameplay patches: (group, file, address, original, new, description) - see tools/codepatch.py.
# docs/PATCHES.md has a section per group; docs/HIDDEN_CONTENT.md the code behind them.
CODE_PATCHES = [
    # Gallery isSeen(i) (0x2212b0) tests bit i of the CG bitfield at 0xeac300; only the gallery
    # calls it. Returning 1 shows every CG without writing the save ("Gallery").
    ('gallery', '/SLPM_550.56', 0x2212e8, 0x0002102b, 0x24020001, 'Gallery: every CG viewable'),  # sltu v0,zero,v0 -> li v0,1
    # The battle pause menu's jump table (0x4c20e0) has a 5th case, the developers' DebugCheat
    # window, that no menu item reaches. "Skip to end of match" (case 3) opens it instead.
    ('debug-cheat', '/SLPM_550.56', 0x4c20ec, 0x0025b194, 0x0025b1e0,
     'Battle pause menu: "Skip to end of match" opens the debug cheat window'),
    # The boot sequence (0x20bb50) has an unused state 3 that creates the move check; going there
    # after the warning screen and creating ScnSelect (the script viewer) instead, the way the
    # orphaned DebugSelect menu does at 0x20be84 ("Script viewer").
    ('debug-menu', '/SLPM_550.56', 0x20bc24, 0x24030002, 0x24030003,
     'Boot: the script viewer opens after the warning screen'),  # li v1,2 -> li v1,3
    ('debug-menu', '/SLPM_550.56', 0x20bc48, 0x24040110, 0x2404006c, None),  # new(0x110) -> new(0x6c)
    ('debug-menu', '/SLPM_550.56', 0x20bc5c, 0x26040028, 0x26040024, None),  # vtable field +0x28 -> +0x24
    ('debug-menu', '/SLPM_550.56', 0x20bc60, 0x24635ac8, 0x24634490, None),  # WazaTest vtable -> ScnSelect
    ('debug-menu', '/SLPM_550.56', 0x20bc64, 0x0c0c15fe, 0x0c08cf12, None),  # jal 0x233c48
    ('debug-menu', '/SLPM_550.56', 0x20bc6c, 0x0c0c15fe, 0x00000000, None),
    ('debug-menu', '/SLPM_550.56', 0x20bc70, 0x26040090, 0x00000000, None),
]
UNLOCK_GROUPS = sorted({p[0] for p in CODE_PATCHES})
# Groups named debug-* change how the game plays or starts: only when named, never in "all".
PLAYER_GROUPS = sorted(g for g in UNLOCK_GROUPS if not g.startswith('debug-'))

# --debug-log (developer): the game's debug printf 0x2086f8 was emptied (483 callers); jumping to
# the real printf 0x353ae8 prints the messages to the emulator's EE console.
DEBUG_LOG_PATCHES = [
    ('/SLPM_550.56', 0x2086f8, 0x27bdff80, 0x080d4eba),  # addiu sp,sp,-0x80 -> j 0x353ae8
    ('/SLPM_550.56', 0x2086fc, 0xffa50048, 0x00000000),  # sd a1,0x48(sp) -> nop
]

# --boot: (part, file, address, original, new) - patches that start the game in a given part.
BOOT_PATCHES = {
}


EXE = '/SLPM_550.56'
_ELF = {}


def to_offset(name, addr):
    """File offset of a RAM address in file `name`: the main executable is an ELF."""
    if name != EXE:
        raise SystemExit(f'build.py to_offset(): no address mapping for {name}')
    if name not in _ELF:
        _ELF[name] = elf.Elf(bytes(FILES.get(name)))
    return _ELF[name].offset(addr)


def font_step(path, files):
    """English font: proportional half-width glyphs (tools/font.py)."""
    font.apply(files, to_offset)


# Text steps: (text file or folder under translation/, function(path, files)). Each inserts the
# English into the game's files through `files` and stops with a clear message if anything doesn't fit.
# Zero-padding files a grown file may take room from when the disc is full (PS2 disc.py
# take_from_padding: their end is cut off) - e.g. ['/DUMMY.DAT']; check they are all zeros.
PADDING_DONORS = []

TEXT_STEPS = [
    ('script', scr.apply),          # /SCR/*.BIN event scripts (+ text/speakers.csv, text/choices.csv)
    ('text/roster.csv', records.step),   # wrestler names and titles (executable, fixed records)
    ('text/moves.csv', records.step),    # move names (executable, fixed records)
    ('text/skills.csv', records.step),   # special skill names (executable, fixed records)
    ('text/coaches.csv', records.step),  # coach names (executable, fixed records)
    ('text/venues.csv', records.step),   # venue names (executable, fixed records)
    ('text/symbols.csv', records.step),  # single full-width digits/letters filled into %s
    ('text/exe.csv', exetext.apply),  # the executable's own text (before the font code: same file)
    ('.', font_step),               # /SYS/FONT.BIN + draw()/width() in the executable
]
FILES = None  # this build's Files (to_offset reads the executable's segments from it)


class Files:
    """The game's files for this build: read from the image on first use, written back at the end."""

    def __init__(self, d):
        self.d, self.data, self.changed = d, {}, set()

    def get(self, name):
        if name not in self.data:
            self.data[name] = bytearray(self.d.read_file(self.d.find(name)))
        return self.data[name]

    def put(self, name, data):
        self.data[name] = bytearray(data)
        self.changed.add(name)


def unlock_groups(value):
    if value == 'all':
        return set(PLAYER_GROUPS)
    if value == 'none':
        return set()
    groups = {g.strip() for g in value.split(',') if g.strip()}
    if groups - set(UNLOCK_GROUPS):
        raise argparse.ArgumentTypeError(f'expected all, none or some of {",".join(UNLOCK_GROUPS) or "(no groups yet)"}'
                                         f' (all = {",".join(PLAYER_GROUPS)})')
    return groups


def images_step(files):
    final = catalog.final_images()
    missing, changed, _ = catalog.stale()
    if missing or changed:
        print(f'note: {len(missing) + len(changed)} automatic renders are out of date - run tools/render.py '
              f'(building with the frozen files there are)')
    n = gfx.import_images({k: p for k, (tag, p) in final.items()}, files)
    if paths.ENGLISH_IMAGES.exists():
        shutil.rmtree(paths.ENGLISH_IMAGES)
    if final:
        paths.ENGLISH_IMAGES.mkdir(parents=True)
        for name, (tag, p) in final.items():
            shutil.copyfile(p, paths.ENGLISH_IMAGES / f'{name}.png')
        counts = {}
        for tag, _ in final.values():
            counts[tag] = counts.get(tag, 0) + 1
        print(f'images: {n} imported (' + ', '.join(f'{c} {t}' for t, c in sorted(counts.items())) + ')')


def verify_original(original):
    """SHA-1 of the original image, once: the result is remembered with the file's size and
    modification time (build/original.verified), so later builds only re-hash a changed file
    (a DVD image takes ~20 s to hash)."""
    st = original.stat()
    stamp = f'{original.resolve()} {st.st_size} {st.st_mtime_ns} {paths.ORIGINAL["sha1"]}'
    memo = paths.BUILD / 'original.verified'
    if memo.exists() and memo.read_text() == stamp:
        return
    print('verifying the original...')
    if image.sha1(original) != paths.ORIGINAL['sha1']:
        sys.exit(f'{original.name} does not match the expected SHA-1 {paths.ORIGINAL["sha1"]}')
    paths.BUILD.mkdir(parents=True, exist_ok=True)
    memo.write_text(stamp)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], epilog=paths.FOLDER_HELP,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--name', default=f'{paths.GAME_FILE} (English)')
    ap.add_argument('--skip-verify', action='store_true', help="don't hash the original image")
    ap.add_argument('--clean', action='store_true', help='copy the original instead of restoring the last build')
    ap.add_argument('--no-translation', action='store_true', help='skip text and images (alone: identical to the original)')
    ap.add_argument('--unlocks', type=unlock_groups, metavar='all|none|GROUP,...',
                    help='gameplay patches: all (default; not the debug-* groups), none or some groups; none with '
                         '--no-translation')
    ap.add_argument('--boot', choices=sorted(BOOT_PATCHES), help='TEST BUILD: start the game in this part')
    ap.add_argument('--no-text', action='append', default=[], metavar='FILE',
                    help='developer: leave this text file untranslated (repeatable)')
    ap.add_argument('--debug-log', action='store_true', help="developer: the game's debug messages in the EE console")
    args = ap.parse_args(paths.configure(sys.argv[1:] if argv is None else argv))
    if args.unlocks is None:
        args.unlocks = set() if args.no_translation else set(PLAYER_GROUPS)

    original = paths.ROM
    if not original.exists():
        sys.exit(f'put the original image in {paths.show(paths.ROM_DIR)} (or pass --rom): {paths.ORIGINAL_NAME}')
    if original.stat().st_size != paths.ORIGINAL['size']:
        sys.exit(f'{original.name}: {original.stat().st_size} bytes, expected {paths.ORIGINAL["size"]} - not the right image')
    if not args.skip_verify:
        verify_original(original)

    out = paths.BUILD / (args.name + original.suffix)
    with image.prepare(original, out, clean=args.clean) as f:
        d = disc.Disc(f, writable=True)
        files = Files(d)
        global FILES
        FILES = files

        if not args.no_translation:
            for rel, step in TEXT_STEPS:
                if rel in args.no_text:
                    print(f'text: skipped {rel} (--no-text)')
                    continue
                step(paths.TRANSLATION / rel, files)

        codepatch.apply(files, CODE_PATCHES, args.unlocks, to_offset)

        if not args.no_translation:
            images_step(files)

        if args.boot:
            codepatch.apply(files, [(args.boot, *p, f'TEST BUILD: boots into {args.boot}') for p in BOOT_PATCHES[args.boot]],
                            {args.boot}, to_offset)
        if args.debug_log:
            codepatch.apply(files, [('log', *p, 'DEVELOPER BUILD: debug messages in the EE console') for p in DEBUG_LOG_PATCHES[:1]]
                            + [('log', *p, None) for p in DEBUG_LOG_PATCHES[1:]], {'log'}, to_offset)

        def fits(name):
            return (len(files.data[name]) + disc.SECTOR - 1) // disc.SECTOR <= d.allocated_sectors(d.find(name))
        def write(name):
            d.write_file(d.find(name), bytes(files.data[name]), relocate=True,
                         **({'donors': PADDING_DONORS} if PADDING_DONORS else {}))
            print(f'patched {name}')
        # the executable last: its file table (tools/filetable.py) gets every file's final place
        for name in sorted(files.changed - {filetable.EXE_FILE}, key=lambda n: (not fits(n), n)):  # fixed order: same disc layout every build
            write(name)
        if not args.no_translation:
            o = disc.Disc(original)
            filetable.update(d, files, o)
            o.close()
        if filetable.EXE_FILE in files.changed:
            write(filetable.EXE_FILE)
    disc.companion_files(out)
    print(f'done: {paths.show(out)}  ({len(files.changed)} files patched)')
    return out


if __name__ == '__main__':
    main()
