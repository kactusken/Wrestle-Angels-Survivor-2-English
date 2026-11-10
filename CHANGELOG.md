# Changelog

## v0.3 (beta)
Fixes from a play-test report:
- Winning a belt said "has won the タイトル!" (and "captured the タイトル!" for a successful
  challenge): the English kept a stray Japanese word. Both now say "the title!".
- The speaker tag on the vacation scenes (and other messages from the president) read "residen":
  the game strips the first and last two bytes of a tag as its 【 】 brackets, and the English had
  one-byte brackets, so it cut "P" and "t". The tag now uses the game's own brackets.
- A bug in the original game (also in the Japanese release): at the start of a game, a
  wrestler's move that came after a higher-level move she hadn't learned yet was named "ダミー技"
  ("dummy move"), e.g. Miyuki Sanada's Take the Hit in the Other card list. The move itself always
  worked. Fixed in the code; the names are kept in the save, so only games started with v0.3 show
  the right names.

## v0.2 (beta)
- Text that was still in Japanese, found through a player report and an audit of the executable:
  the rival promotions' monthly reports (scouting attempts, autograph sessions, TV ads, ad truck,
  talks with free agents), save prompts, title names ("%s Title", "%s Junior Title"), the
  Hospital status, an ejection message, match times, the venue-select header and "months since
  last show".
- The foreign promotions' countries (five of six were in Japanese).

## v0.1 (first public beta)
- All 242 story scripts translated: about 60,000 lines of dialogue.
- The executable's text: menus, match commentary, announcer lines, the roster, moves, venues,
  coaches and special skills.
- 247 text pictures lettered in English: menus, banners, status screens, finance reports, move
  cards, month banners and the ring names under all 158 portraits.
- Proportional spacing for Latin letters: the game's text-drawing code rewritten, so letters
  are spaced by their width instead of a fixed 11-pixel cell.
- Story scripts that grew are moved on the disc, and the game's file position table is updated
  to match.
- Three patches: English, English (All Unlocked) and the original Japanese (All Unlocked). The
  All Unlocked patches open the whole gallery without changing your save.
