#!/usr/bin/env python3
"""The executable's table of file positions on the disc: kept in step with the image at build time.

  filetable.py check <iso>      every table entry against the image's file system

The game doesn't look files up by name (except a few: see UNLISTED). It reads them by position
from a table in .data (0x38cfa4-0x38ea0c): 12-byte entries {u32 LBA, u32 sectors, u32 ptr}. A file the
build moves (tools/disc.py relocates files that outgrow their slot) or enlarges in place would
still be read from its old position and length - the first emulator tests showed Japanese in
scenes whose scripts had been moved.

update(d, files, original_disc) sets every entry to its file's current LBA and length. Entries
are matched to files by the original image's LBAs, so it works on a restored (journalled) build.
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

EXE_FILE = '/SLPM_550.56'
ELF_TO_FILE = 0x1ff000                 # address - this = file offset (one PT_LOAD at 0x200000)
TABLE = (0x38cfa4, 0x38ea0c)
STRIDE = 12
SECTOR = 2048
# loaded by name or not at all: not in the table
UNLISTED = {'/BATTLE/ACC00.GSL', '/BATTLE/TL01.GSL', '/BATTLE/WIN00.GSL', '/BATTLE/WIN01.GSL',
            '/BATTLE/WIN02.GSL', '/BGM2/WAS2.PSS', '/IOPRP310.IMG', '/IRX.BIN', '/SLPM_550.56',
            '/SYS/COMBACK.GSL', '/SYS/COMSE.HBS', '/SYS/MAP.GSL', '/SYS/SUCCESS.GSL', '/SYSTEM.CNF'}


def sectors(size):
    return max(1, (size + SECTOR - 1) // SECTOR)


def entries(exe, by_lba):
    """[(file offset of the entry, path)] - entries whose LBA is an original file's."""
    out = []
    for at in range(TABLE[0], TABLE[1], 4):
        off = at - ELF_TO_FILE
        lba, count = struct.unpack_from('<2I', exe, off)
        path = by_lba.get(lba)
        if path and abs(count - sectors(path[1])) <= 1:
            out.append((off, path[0]))
    return out


def original_index(original_disc):
    return {e.lba: (e.path, e.size) for e in original_disc.files()}


def update(d, files, original_disc):
    """Point every entry at its file's current extent (in files' copy of the executable)."""
    exe = files.get(EXE_FILE)
    n = moved = 0
    for off, path in entries(exe, original_index(original_disc)):
        e = d.find(path)
        new = (e.lba, sectors(e.size))
        if struct.unpack_from('<2I', exe, off) != new:
            struct.pack_into('<2I', exe, off, *new)
            moved += 1
        n += 1
    files.put(EXE_FILE, exe)
    print(f'file table: {n} entries, {moved} updated')


def check(iso, original):
    import disc
    d, o = disc.Disc(iso), disc.Disc(original)
    exe = d.read_file(d.find(EXE_FILE))
    bad = []
    seen = set()
    for off, path in entries(o.read_file(o.find(EXE_FILE)), original_index(o)):
        e = d.find(path)
        seen.add(path)
        got = struct.unpack_from('<2I', exe, off)
        if got != (e.lba, sectors(e.size)):
            bad.append(f'{path}: table {got}, disc ({e.lba}, {sectors(e.size)})')
    missing = {e.path for e in o.files()} - seen - UNLISTED
    return bad + [f'{p}: no table entry' for p in sorted(missing)]


def main(argv):
    import paths
    args = paths.configure(argv)
    if len(args) != 2 or args[0] != 'check':
        sys.exit(__doc__)
    problems = check(args[1], paths.ROM)
    print('\n'.join(problems) or 'file table matches the image')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
