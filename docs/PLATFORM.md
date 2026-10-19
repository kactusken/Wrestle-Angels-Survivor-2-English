# Platform notes: PlayStation 2 (PS2)

Starting notes for PS2 projects; much of this is still to be confirmed on a real project. Mark what
you verify and add what you learn (here and in the kit's copy).

## Disc
- Images are `.iso` with 2048-byte sectors (DVD, sometimes CD). No EDC/ECC to regenerate.
- Most DVDs carry **ISO9660 + UDF** over the same files. The console and PCSX2 read ISO9660; keep
  UDF consistent anyway (`tools/disc.py` updates both; `disc.py check <iso>` compares them).
- Mastering tools often store files over 1 GB as a single UDF extent whose length overflows into
  the type bits. `disc.py` keeps that layout when it rewrites such a file.
- Big zero-filled padding files (names like `DUMMY`, or joke names) push data to the outer edge of
  the disc for speed. `extract.py` skips them; they are not free space as far as the file system is
  concerned. When a file outgrows its slot on a full disc, `disc.py` can cut the end off one
  (`write_file(..., donors=[...])`, build.py `PADDING_DONORS`) - *verified on a real project*: a
  pack grown by 518 KB moved into the freed sectors and the game loaded it (the game found it
  through the file system, not an LBA table).
- Games often find data through their own tables (LBA tables in the ELF, archive indexes such as
  CRI AFS), not through the file system - check before relocating or growing a file.
- A DVD image is 4+ GB: builds restore only what the last build changed (`tools/image.py`), and
  browser patchers may not cope with patches against it; point players to Delta Patcher / xdelta3.

## Code
- CPU: Emotion Engine, MIPS R5900 (MIPS III + 128-bit multimedia "MMI" instructions). Branch delay
  slots apply; loads are interlocked (no load delay slot). Registers are 64/128-bit.
- The executable (`SLPM_xxx.xx`, `SLUS_xxx.xx`, named in `SYSTEM.CNF`) is an ELF: use
  `tools/elf.py` to turn RAM addresses into file offsets. Overlays and IOP modules (`.IRX`) may
  also be present.
- `tools/mipsdis.py` decodes the 64-bit integer instructions; capstone doesn't know MMI, so those
  words show as `.word` or wrong mnemonics.
- Debugging: PCSX2 has a built-in debugger (memory, breakpoints, disassembly). *Check whether your
  PCSX2 version offers a GDB/remote interface before writing a client.*
- Before chasing a glitch, run the same screen on the untouched disc: a flickering title that turned
  out to be the original game's own behaviour (same in the software renderer) cost two test builds.

## Text
- Shift-JIS is common (`tools/sjisscan.py`); fonts are usually textures, so check whether ASCII /
  half-width glyphs exist before planning a variable-width font. A game whose renderer only draws
  two-byte codes can be taught single-byte ASCII with three small hooks (formatter, glyph lookup,
  width) mapping it to the full-width glyphs - doubling the room in fixed-size fields.
- Text routines that step through a string **two bytes at a time** (line splitters looking for
  button-icon or colour tokens, typewriter effects) lose step after an odd number of single-byte
  characters: tokens after it are missed (no icon, a highlight that never ends). Keep such text
  fully full-width, or widen one space before each token so it lands on an even offset.
- Multi-line dialogs may split lines on single-byte spaces (lines merge and shift): store
  multi-line strings with full-width spaces.
- Much "text" is also a **key**: values in data sheets compared with strings in the executable,
  team names matched against other tables, holder names found with strstr() in the roster. Find
  what reads a table before translating it, change both sides together, and let the build step
  simulate the lookup (FRAMEWORK.md section 5).
- The memory card title is in an `icon.sys` block (magic `PS2D`, title at +0xc0, Shift-JIS, line
  break offset at +6) - often an archive entry; decide with the user whether it is translated.

## Images
- TIM2 (`.tm2`, "TIM2" magic) is the common texture format: 4/8bpp with 16/32-bit CLUTs, alpha
  0x80 = opaque, 8bpp CLUTs usually in CSM1 order (`tools/tim2.py` handles it). Games may also use
  raw GS textures with separate palettes, often swizzled - look before assuming TIM2.
- TIM2 writers vary: some games use image types 0x0a / 0x09 for **swizzled** 8bpp / 4bpp (GS memory
  order: write as PSMT8/PSMT4, read back as PSMCT32 rows - `tim2.swizzle_map()`), and 4bpp CLUTs of
  32 entries with the colours in 0-7 and 16-23. Scrambled-looking text in a decode is the sign.
  Tally the header bytes across all files before trusting a parser. *Verified on a real project.*
- Check a decompressor on the *content* of compressed entries (e.g. TIM2 headers past the first
  bytes), not just sizes: an off-by-one window start passes size checks and leading literals.
- Labels in an atlas are drawn as sprites, and the GS texture filter shows a sprite's last pixel
  row on the next sprite's top edge. In list menus the sprites may be cut on a row grid that isn't
  the middle of the gaps - English descenders hanging lower than the original lettering show as
  specks on the next label. Some atlases cut sprites to each label's own width (a widened label is
  clipped). A probe build with one-pixel marks, one per row, finds the cut lines in a single
  screenshot; `render.py` has the rules (list menus, FIXED_ATLASES, LIST_ATLASES).

## Screenshots
- PCSX2 at the real frame size: Graphics → Rendering → Internal Resolution *Native (PS2)*, and
  Media Capture → Screenshot Size *Internal Resolution (Aspect Uncorrected)*; F8 saves to `snaps/`.
  Most games come out 640x448 (NTSC) or 512x448. Upscaled shots (e.g. 1440x1080 at 3x) scale
  down cleanly with `tools/shots.py`.
- romhacking.net accepts these PS2 sizes (submission form, 2026-10): NTSC-NI 640x240 (224),
  NTSC-I 640x480 (448), PAL-NI 640x288 (256), PAL-I 640x576 (512), VESA 640x480, 800x600,
  1024x768, 1280x1024, DTV 720x480, 1280x720, 1920x1080. `tools/shots.py` defaults to 640x480.
