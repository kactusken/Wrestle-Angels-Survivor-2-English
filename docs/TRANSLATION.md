# Translation

## Where the text is

| File | Holds | Checked by |
|---|---|---|
| `translation/script/NNN.txt` | event scripts `/SCR/NNN.BIN`: one file per wrestler (0xx), her other persona (1xx), foreign wrestlers (2xx) and their other persona (3xx) | `tools/scr.py check`, `tools/lint.py` |
| `translation/text/speakers.csv` | every name shown in 【】 (speaker box, inline) | `tools/lint.py` |
| `translation/text/choices.csv` | the four choice labels (`item "..."`) | `tools/lint.py` |
| `translation/text/exe.csv` | the executable's own text: menus, messages, match commentary, announcer lines | `tools/exetext.py` |
| `translation/text/roster.csv`, `moves.csv`, `venues.csv`, `coaches.csv`, `skills.csv`, `foreign.csv`, `symbols.csv` | data tables: wrestlers, moves, venues, coaches, special skills, foreign promotions' countries, digits and symbols | `tools/lint.py` |
| `translation/graphics.csv` | images with text | `tools/check.py` |

## File formats

Message blocks: `@ id`, source lines (`JP `), translation lines (`EN `); no `EN` lines = original
kept. In `translation/script/` each block is one message (one script line); its `JP` lines are the
lines on screen and each `EN` line is one line on screen. Comments give the speaker and the scene.
Block ids are `segment.line` in the script and are not for editing.

Working on a whole script: `python3 tools/scr.py dump NNN` prints one line per block (id,
speaker, Japanese joined with ` / `); write `id<TAB>English` lines to a file and
`python3 tools/scr.py import NNN FILE` stores them, word-wrapped to the box (`|` forces a line
break), and checks them.

Control codes in the English:
- `%chr` - a wrestler's name, filled in by the game (`%chr選手と…` → `...with %chr...`)
- `\c()` - speaker change inside a message (rare; keep where the source has it)
- the end-of-message code `\b` and the `\n` line breaks are written by the build.

## Limits

- Message box: 3 lines of 440 pixels. The font is proportional (tools/font.py): lower case is
  about 10 px, `i l . , '` 4-6 px, space 5 px - roughly 44-48 characters a line.
  `tools/scr.py check` measures every line; `import` and `wrap` break lines automatically.
- At most 96 bytes a line (the window's cap, raised from 40 - tools/font.py MESSAGE_BOX).
- Characters: printable ASCII except `\` (shown as ¥) and `~` (written as the full-width ～, a
  22 px glyph - use sparingly). `♪ ★ ☆ ・` and other Shift-JIS symbols work but are 22 px wide.
  Curly quotes, `…` and `—` are converted to ASCII by the build. No `//` (starts a comment).
- Speaker names: no limit found yet (drawn at the window's top left); keep them short.

## Style guide

*Decided by Claude during the overnight setup (2026-10-18) - to be reviewed by the project lead.*

- **The player** is 社長, the (male) president of the promotion. Speaker label: `President`.
  When wrestlers address him: `Boss` (`President` in formal scenes - contracts, ceremonies,
  outsiders). His own narration in parentheses is first person: `(I offered her a contract.)`
- **Names**: Western order for full names (`Suzumi Ishikawa`); characters who use a surname
  keep the surname (`Ishikawa`). Ring names as in `translation/text/speakers.csv`. The table is
  the reference for every name in dialogue too.
- **Honorifics**: dropped (`石川さん` → `Ishikawa`, `ちゃん` → first name) except `senpai`, which
  carries the seniority that matters in joshi wrestling (`Senpai!`).
- **Thoughts and narration** in （） stay in parentheses: `(She seems tougher than she looks.)`
- **Quotes** 「」『』 → double quotes. Ellipses `…`/`……` → `...`. Stammers `そ、そうか` → `S-sure.`
  Drawn-out `～` at the end of a line: usually drop it or use `!`; keep `~` only for a sing-song
  voice where it carries character.
- **Voice**: wrestlers have strong personalities (tough, cute, haughty, sleepy, theatrical...).
  Keep each one's register and verbal tics (`うきゅ` → `Ukyu`), and keep catchphrases consistent
  within a character's file. The President is polite but plain-spoken.
- **Wrestling terms**: natural English pro-wrestling vocabulary (glossary).

## Glossary

`translation/glossary.csv` (`japanese, english, notes`): lint warns when a source line contains a
term and the English doesn't use its translation (several accepted forms: `A | B`). Prefer
established community names (existing English guides) over new coinages.

## Decisions

| Decision | Who / why |
|---|---|
| English drawn with the game's own half-width glyphs, made proportional | Claude, overnight setup: keeps the game's look; no new font art |
| Style guide above (President/Boss, no honorifics but senpai, Western name order) | Claude, overnight setup - confirmed by the user, 2026-10-18 |
| Scope: event scripts first; executable text next | Claude, overnight setup |
| Image lettering: Barlow Condensed / Semi Condensed Bold (SIL OFL, tools/fonts/) in the original's own fill, outline and glow colours (tools/letter.py) | Claude, 2026-10-18, after the user OK'd starting the images |
| Labels stay inside the original label's box. The highlight copies were confirmed in-game to show whole words at that size | Claude, 2026-10-18 |
| Main menu: Staff / Business / Info / Gym / End Month (mock-up A of three); style A (mixed case, condensed, original colours) for all menu images | the user, 2026-10-18, after seeing it in the game |
| Months on the month banners: JAN ... DEC (3 letters fill the big art like 10月) | Claude, 2026-10-18 |
| COM in menus and text = "CPU" (CPU promotions, Watch CPU, CPU Thinking...); the original English art's COM tags stay | Claude, 2026-10-18 |
| Team order 先次中副大 = Lead / 2nd / Mid / Vice / Capt | Claude, 2026-10-18 - confirmed by the user, 2026-10-18 |
| Portrait name tags: Japanese tag kept, small English ring name at the bottom of the character | the user, 2026-10-18 |
| Office header: "1 Yr  4 Mo" (the numbers are sprites drawn before each label) | Claude, 2026-10-18 - confirmed by the user, 2026-10-18 |

## What stays untranslated

- Staff credits and voice cast: kept in Japanese (the user, 2026-10-18).
- Counter words after numbers (名, 日目, 選手): kept (the user, 2026-10-18).
- Debug strings, the name-entry kanji grid, the special-skill descriptions (designer notes, not
  shown), unreferenced duplicate name lists.
- The title logo.
