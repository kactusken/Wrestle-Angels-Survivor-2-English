# Tools

Everything is Python 3 and runs from the project folder or anywhere else; every tool has `--help`
(or prints its usage). Folder locations come from [paths.py](paths.py) and can be moved with the
folder options. `build.py`, `make_patches.py` and everything they import use only the standard
library; the tools marked *Pillow* or *capstone* need `.venv` (`pip install -r requirements.txt`).

Set up from the translation kit (version 581d857). Tools marked *game* are stubs to fill in.

## Used by the build

| Tool | What it does |
|---|---|
| [../build.py](../build.py) | builds the translated image (text steps, code patches, images, write-back) |
| [paths.py](paths.py) | every folder location and the folder options |
| [image.py](image.py) | the output image: fresh copy or fast restore from a journal; checksums |
| [disc.py](disc.py) | reads and writes files in the disc image (PS2) |
| [codepatch.py](codepatch.py) | applies code patch tables, checking the original bytes first |
| [catalog.py](catalog.py) | the image catalogue: which file the build uses, fingerprints, stale renders |
| [gfx.py](gfx.py) | *game*: exports the original images, imports the English ones |
| [scr.py](scr.py) | event scripts `/SCR/*.BIN`: extract to `translation/script/`, build back, check, `dump`/`import` for translating, `wrap`, `propagate` to the other-persona scripts |
| [font.py](font.py) | proportional English font: half-width glyphs in `FONT.BIN`, draw()/width() rewritten, message window caps raised |
| [exetext.py](exetext.py) | the executable's strings (`translation/text/exe.csv`): in place, or moved to a new segment after .bss |
| [pngio.py](pngio.py) | PNG reading and indexed PNG writing without dependencies |
| [blocks.py](blocks.py), [textdb.py](textdb.py) | message block files; every translatable string as one list |
| [elf.py](elf.py) | the PS2 executable: segments, address ↔ file offset (for code patches) |
| [tim2.py](tim2.py) | PS2 TIM2 images: reading, PNG export, writing pixels back |
| [mips_asm.py](mips_asm.py) | a small MIPS assembler for hooks (R3000 encodings, valid on the R5900) |

## Checking

| Tool | What it does |
|---|---|
| [check.py](check.py) | runs every check (`--quick` for the pre-commit hook, `--control` for a lossless-build proof) |
| [lint.py](lint.py) | text: leftover source text, control codes, line/char/byte limits, glossary |
| [status.py](status.py) | how far along the text and images are |
| [records.py](records.py) | fixed-record text tables: `dump` the CSV, `verify` the layout, `measure` unknown data, build step - here the roster and move names in the executable |
| [test_vwf.py](test_vwf.py) | runs the patched draw()/width() in a small MIPS interpreter and checks every kind of character |
| [stepcheck.py](stepcheck.py) | run one build text step against `extracted/` (no image, nothing written) and list what it changed - for testing a step while the image is busy |

## Translating

| Tool | What it does |
|---|---|
| [fill_text.py](fill_text.py) | fills repeated strings from a source → English table |
| [render.py](render.py) | *Pillow*: automatic English renders, only redrawing what changed |
| [letter.py](letter.py) + [letter_ext/](letter_ext) | *Pillow*: hand-lettered menu pictures render.py can't do (tinted lettering, gradients, highlight copies) into translation/images-handmade/ - rerun after changing their English |
| [edit.py](edit.py) | *Pillow*: hand-edit workflow - start, check, approve, reset, sheets |
| [compare.py](compare.py) | *Pillow*: original \| English sheets |
| [contact.py](contact.py) | *Pillow*: every original image on labelled sheets |

## Releasing

Steps and rules: [../docs/RELEASING.md](../docs/RELEASING.md).

| Tool | What it does |
|---|---|
| [../make_patches.py](../make_patches.py) | builds every variant, makes and re-verifies the xdelta patches, README.txt and the zip |
| [publish.py](publish.py) | copies the committed project into the public repository (no history); stops on changes made there |
| [announce.py](announce.py) | drafts the GitHub release notes, Reddit post and romhacking.net submissions with the facts filled in |
| [shots.py](shots.py) | *Pillow*: scales screenshots to the sizes screenshot sites accept, with readable names |

## Research

| Tool | What it does |
|---|---|
| [extract.py](extract.py) | unpacks the disc into `extracted/` and exports the images (*game*: `unpack()`) |
| [sjisscan.py](sjisscan.py) | finds Shift-JIS text in binary files |
| [mipsdis.py](mipsdis.py) | *capstone*: disassembler with reference and call search (ELF or raw@base:64) |
| [bss_scan.py](bss_scan.py) | estimates how far past its end a code module's memory use reaches |
