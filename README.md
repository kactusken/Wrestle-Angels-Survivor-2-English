# Wrestle Angels: Survivor 2 — English Translation

An English translation patch for **Wrestle Angels: Survivor 2** (2008, PlayStation 2, released
only in Japan).

The patch translates all 242 story scripts (about 60,000 lines of dialogue), the game's menus,
match commentary and announcer lines, the roster, 189 moves, venues, coaches and special skills,
and 247 text pictures: menus, banners, status screens, finance reports, move cards and the ring
names under all 158 portraits. The game only had a full-width Japanese font, so the English runs
on a new proportional font with a hook in the game's text drawing code.

**[See screenshots](docs/SCREENSHOTS.md)** of the patched game.

> **Status: first public beta (v0.1).** All dialogue, menus and text pictures are translated and
> the game has been played in English, but not every story path, event or late-game screen has
> been seen yet. Please report anything cut off, overlapping or still in Japanese
> ([how to report](#reporting-problems)). [CHANGELOG.md](CHANGELOG.md) lists what's in each
> release.

## Downloads

Get the latest zip from the [Releases](../../releases) page. It contains 3 patches. Pick one:

| Patch | What you get |
|---|---|
| **Wrestle Angels - Survivor 2 (English)** | The translation, with the game otherwise unchanged. |
| **Wrestle Angels - Survivor 2 (English) (All Unlocked)** | The translation, with every gallery picture viewable. Your save's own gallery progress is kept and comes back without this patch. |
| **Wrestle Angels - Survivor 2 (Japan) (All Unlocked)** | The original Japanese game, with every gallery picture viewable. |

## How to patch

You need your own copy of the original Japanese disc. Disc images are not provided here.

- Game: *Wrestle Angels: Survivor 2* (Japan), serial SLPM-55056.
- The image must match: `Wrestle Angels Survivor 2 (Japan).iso`, 4074340352 bytes, CRC32 `275d9e6f`,
  SHA-1 `ea5d4f86102205b885e15a09b5e4d4318d839136`.

Then:

1. Apply the `.xdelta` patch with an xdelta tool:
   - [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/) runs in your web browser
     (CD images; it may not cope with a multi-GB DVD image).
   - Delta Patcher is a desktop app for Windows, macOS and Linux.
   - On the command line: `xdelta3 -d -s "Wrestle Angels Survivor 2 (Japan).iso" "patch.xdelta" "patched.iso"`
2. Open the patched image in your emulator. Tested in PCSX2.

### Emulation notes

PCSX2 shows some visual glitches early in the game. Switching to the software renderer
(Settings → Graphics → Renderer: *Software*) fixes most of them, but the intro screens then look
half cut off. This isn't caused by the patch: the original Japanese game runs the same way in
PCSX2.

## Notes for players

- **Names.** Full names are in Western order (given name first). Honorifics are dropped, except
  *senpai*. The portraits keep their Japanese name tags, with the English ring name added at the
  bottom of the character.
- **What's still in Japanese.** The title logo, the staff credits and voice cast, counter words
  after some numbers (名, 日目), the kanji grid on the name-entry screen, and the voices.
- **Saves.** Saves from the original Japanese game work with the patch.
- **Hidden content.** See [docs/HIDDEN_CONTENT.md](docs/HIDDEN_CONTENT.md).
- **Event timeline.** The [interactive timeline](https://kactusken.github.io/Wrestle-Angels-Survivor-2-English/timeline/) shows what can happen each month
  and what unlocks it.

## Reporting problems

Open an [issue](../../issues) with:

- a screenshot,
- which patch you used,
- where you were: the mode and menu, or roughly what had just happened.

Text that is cut off, overlaps, or still shows Japanese is especially helpful.

## For ROM hackers and contributors

Everything needed to rebuild the patches from the original disc is in this repository: the
translated text, the patching code (Python 3, no dependencies for the build) and documentation of
the game's formats.

| Document | What's in it |
|---|---|
| [docs/BUILDING.md](docs/BUILDING.md) | Setting up, building, making patches, and the checking tools |
| [docs/TRANSLATION.md](docs/TRANSLATION.md) | Text file formats, scope, style guide, glossary, and naming decisions |
| [docs/EDITING.md](docs/EDITING.md) | Editing the in-game text graphics |
| [docs/PATCHES.md](docs/PATCHES.md) | How each code patch works |
| [docs/TECHNICAL.md](docs/TECHNICAL.md) | The game's disc layout, archives, compression, data formats, and memory map |
| [docs/PLATFORM.md](docs/PLATFORM.md) | PS2 pitfalls for this kind of work |
| [docs/HIDDEN_CONTENT.md](docs/HIDDEN_CONTENT.md) | Unlockables, debug features, and unused and cut content |
| [docs/MANAGEMENT.md](docs/MANAGEMENT.md) | How management mode works: money, shows, recruitment, training, events |
| [Event timeline](https://kactusken.github.io/Wrestle-Angels-Survivor-2-English/timeline/) | Interactive event timeline: what can happen each month and what unlocks it (source: [docs/timeline/](docs/timeline/)) |
| [tools/README.md](tools/README.md) | Every tool, what it's for and how to run it |

Quick start:

```sh
python3 tools/extract.py                 # unpack the disc in rom/ into extracted/
python3 build.py                         # -> build/Wrestle Angels - Survivor 2 (English).iso
python3 make_patches.py --version v0.1   # -> release/*.xdelta and a zip (needs xdelta3)
```

## Legal

This is a non-commercial fan translation, not affiliated with or endorsed by the game's developers
or publishers. It contains no copyrighted game data that would let
anyone play without owning the game. The patches only work on your own copy of the disc.
Wrestle Angels: Survivor 2 and its contents belong to their respective owners. The Japanese text in this
repository is included for translation and reference.

The code in this repository is released under the [MIT License](LICENSE).
