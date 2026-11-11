# Images with text

Every image with text has a row in `translation/graphics.csv` (columns: see `tools/catalog.py`).
The build uses, in this order: a hand edit in `translation/images-handmade/`, an approved image in
`translation/images-approved/`, an automatic render in `translation/images-rendered/`, else the
original. All three hold indexed PNGs in the game's palette.

## Automatic renders

Plain labels (one background + one text colour, optionally an outline) are drawn by
`.venv/bin/python tools/render.py` from the row's `english` (`' / '` forces a line break; `font`,
`align`, `boxes` hints). It only redraws rows that changed since they were drawn. Look at the
result with `tools/compare.py`, then `tools/edit.py approve <image>` freezes it.

## Hand edits

1. Find the image: `.venv/bin/python tools/edit.py list <words>`, or `review/compare/`, or
   `review/contact-sheets/`.
2. `.venv/bin/python tools/edit.py start <image>` → edit `translation/images-handmade/<image>.png`
   (same size; the original palette is best, RGB works too and is snapped on approve; transparent
   stays transparent). `<image>_original.png` next to it is for reference.
   - Aseprite: opens indexed; save as PNG.
   - GIMP: keep Image › Mode › Indexed; File › Export As › PNG over the same file.
   - Photoshop: Image › Mode › Indexed Color with the existing palette.
3. `.venv/bin/python tools/edit.py check <image>` → `OK`, or `!` lines saying what to fix;
   `<image>_check.png` shows the original above yours.
4. `python3 build.py` and look at it in the emulator.
5. `.venv/bin/python tools/edit.py approve <image>` → moved to `images-approved/`, marked done.

Undo: `edit.py reset <image>`. Several images: names, commas, ranges (`0013_020-0013_052`) or
patterns (`0013_*`).

## Choosing between versions, and staying inside the sprites

`translation/image-choices.csv` lists every translated image with the versions it has: `jp` (the
original), `cur` (the build's), `new` and `alt` (attempts in `translation/images-candidates/`) and
`mine` (your hand edit). Fill in the `pick` column, then `.venv/bin/python tools/choose.py apply`
installs each pick (approved like a hand edit). `choose.py table` refreshes the list and keeps
your picks; the contact sheets in `build/work/imgfix/sheets/` use the same names.

Most pictures are sheets of sprites: the game cuts rectangles out of them (`tools/sprites.json`,
`tools/clutrows.json`, traced from the code). Pixels outside a rectangle never show, and a letter
that reaches into the next rectangle shows up there. To see them:
`.venv/bin/python tools/choose.py view [<image>...] [--version new]` → `review/bounds/<image>.png`,
the picture in the game's colours with every sprite outlined and numbered and a list underneath
(what each is drawn for; 4-bit pictures show the normal and selected states side by side).

For pictures whose sprites are put together on screen (tiles side by side, a glow over a label,
highlight copies), `.venv/bin/python tools/screenmock.py <image>` → `review/bounds/<image>_ingame.png`
shows every version as the game assembles it (positions from `tools/layouts.json`).

To edit one version by hand:

1. `.venv/bin/python tools/choose.py export <image> [cur|new|alt]` → `images-handmade/<image>.png`
   plus `<image>_bounds.png`, a guide layer of the same size: red tint = never drawn, red line =
   the edge of a sprite (the line pixels are inside it), cyan dots = our label boxes. Put it on a
   layer above the image (and hide or delete that layer before saving). `<image>_bounds_view.png`
   is a 4x preview in the game's colours with the guide drawn on.
2. `.venv/bin/python tools/choose.py check <image> --version mine` (or `tools/bounds.py <image>
   --file <png>`). Failures:
   - `outside`: drawn where the game never shows it.
   - `spill`: reaching into another sprite.
   - `split`: a word cut across two sprites that the game doesn't draw edge to edge at the same
     size. `tools/layouts.json` says which sprites it does draw that way.

   Notes, to look at but not failures:
   - `flat`: lettering on a sprite's edge where the original kept a margin, so its outline is cut
     flat on screen. Keep the original's 1-2 px.
   - `hidden`: a sprite more covered on screen by another part of the same picture than in the
     original.
   - `touch`: letters touching their sprite's edge.
3. Set the row's pick to `mine` and run `choose.py apply <image>`; a version that fails the check
   is refused unless `--force`.

`python3 tools/check.py` runs the same bounds check over the whole build.

## Many similar images as one sheet

`edit.py sheet start <name> <images>` writes `translation/images-handmade/sheets/<name>.png`:
original | English pairs at real size. Edit the right-hand images (magenta = transparent), then
`sheet check`, `sheet split` or `sheet approve`.
