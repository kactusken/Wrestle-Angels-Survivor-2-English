# Hidden content

Unlockables, debug features, button codes and unused content, each marked *verified in game* or
*from the code*. Check The Cutting Room Floor and existing guides first.

**Prior art (2026-10-18).** No TCRF or Data Crystal page exists for any Wrestle Angels game, and
the Japanese strategy wikis are mostly gone. Fan summaries say the game has "no particular hidden
elements or tricks". The full reference was the official guide book (2008). Raw cheat codes for
SLPM-55056 are on PSX Data Center; two of them are gallery codes that agree with the code below.

Checked in the game so far (2026-10-19): the gallery unlock, the battle cheat window and the
script viewer. Everything else here is from the code. Build groups `gallery`, `debug-cheat` and
`debug-menu` and the flag `--debug-log` switch some of it on (docs/PATCHES.md). The suggested checks are under
[Emulator checks](#emulator-checks).

## Contents
- [Gallery](#gallery) · [Wrestlers](#wrestlers) · [Debug menus](#debug-menus) ·
  [Battle cheat window](#battle-cheat-window) · [Debug log](#debug-log)
- [Button codes and secret names](#button-codes-and-secret-names) · [Unused files](#unused-files) ·
  [Unused moves](#unused-moves) · [Scripts](#scripts) · [Music](#music) ·
  [Emulator checks](#emulator-checks)

## Gallery
*From the code;* *verified in game* (2026-10-19) with the `gallery` patch. The title menu's Gallery (class `Gallery`, vtable 0x406750, created at 0x209620
as top-level mode 7) has 36 pages of 9 thumbnails. Slots at 0x13c (316) and above are skipped
(0x29c2b8), so there are 316 slots.

- **What each slot shows** (0x29c148): `n = page*9 + pos`. Wrestler `(n % 158) / 2`, plus 100 for
  slots 158 and up (the other persona), and event `(n & 1) + 1`. The CG name is
  `char%03d_ev%02d`. The first variant (`a`, `b`, ...) of that name that has been seen is shown,
  and the viewer pages through the other seen variants.
- **CG index:** 914 entries of 12 bytes at 0x392390 (`charNNN_evMMx`, sector offset into
  `/SYS/EV.BIN`, 141 sectors each). Thumbnails are `TH01-36.GSL` (page + 1); UI art `GALETC.BIN`.
- **Flags:** a bitfield at 0xeac300, bit `i` = CG index entry `i`. isSeen 0x2212b0 (only caller
  the gallery, 0x29c1d0); setSeen 0x2212f8 (only caller 0x229210).
- **How a CG unlocks:** the script command `bg NAME` looks NAME up in the background table
  (0x391fb8) and then in the CG index. A CG name is marked seen and shown. Each wrestler has two
  slots: `ev01` is the vacation scene (script segment 105) and `ev02` the daily events (106/107).
  Scripts 001-079 fill slots 0-157 and 101-179 fill slots 158-315. Foreign wrestlers have no
  gallery. Every slot has at least one script that unlocks it.
- **Never-shown variants:** 56 CG index entries are named by no script (e.g. `char005_ev02e/f`,
  `char016_ev01f-h`, `char068_ev01a/c`, `char073_ev02a/d/e`, `char077_ev01b/c` and their 1xx
  twins). Their slots still open through other variants, so these are variant pictures you can never
  page to.
- **Save data:** the save header holds the options (+0x08, 9 bytes) and a copy of the bitfield
  (+0x14, 0x80 bytes). Saving ORs RAM into the copy, and the first load ORs the copy into RAM
  (0x2216c8). Gallery progress is shared by all three save slots and only grows. No other
  persistent unlock flags exist: no clear flag, play counter, mode or wrestler unlock.
- **Patch idea (unlock all):** 0x2212e8 `0002102b` (`sltu v0,zero,v0`, the delay slot of isSeen's
  `jr ra`) → `24020001` (`li v0,1`). Every CG counts as seen, the 56 never-shown variants included,
  and nothing is written to the save. The PSX Data Center code instead writes 0xFF over each tested
  byte (0x2212dc `00831804` → `240200ff`, 0x2212e0 `00431024` → `a0a20000`). That way the unlocks
  are saved and stay after the patch is removed.

## Wrestlers
*From the data and code.* There are no unlock-gated hidden wrestlers. Wrestlers appear on a
schedule (year and month per start era) through tryouts and scouting; second personas appear
some years later.

- **The secretary (roster 242, id 999) is a complete wrestler** with her own stats and 26 moves.
  Every roster loop stops at 241 (`slti 0xf2` at 0x2092a4, 0x2308d8, 0x27cb80). She has a
  separate runtime struct at 0x101ae18 and no portrait (GM_CHR.BIN has 158 chains, indices 0-157).
- The last u32 of each roster record is its script number. All 84 foreign records have scripts:
  42 wrestlers in two eras.
- 18 foreign records are named `？？？` but have ring names (masked wrestlers - by design).
- Oddities not yet decoded: record 110 +0x104 is 10 (all other personas -1); rare values at
  +0x7c0, +0x118 and +0x130. +0x7e4 looks like a debut year.

## Debug menus
*From the code.* The RTTI names (source `wres2/src/demo.cc`) include DebugSelect, BgmTest,
SeTest, VoiceTest, VoiceMenu, MaskTest, ScriptSelect, DebugFlagWindow, VarSelect, ScnSelect,
WazaTest and ChrCheck. The executable was compiled on Jul 30 2008 ("Compiled at %s", 0x46b628).

- **DebugSelect**: its update function 0x20bcb8 survives (8-way jump table 0x469950), but its
  vtable, constructor and every reference to it are gone. Its items (labels still in the
  executable, unreferenced):

  | # | Label | Opens |
  |---|---|---|
  | 0 | 技チェック (move check) | WazaTest, vtable 0x405ac8 |
  | 1 | 立ち絵チェック (portrait check) | ChrCheck, 0x405aa0 |
  | 2-4 | ＢＧＭ / ボイス / ＳＥ | BgmTest 0x4045e0 (all 38 tracks), VoiceTest 0x404590, SeTest 0x4045b8 |
  | 5 | スクリプト (script) | ScnSelect 0x404490 |
  | 6, 7 | エンディング / エンディング(ノーマル) | the ending (0x22e828, modes 2 and 1) |

- **Script viewer** (complete, *verified in game* (2026-10-19) with the `debug-menu` patch: character, variables, scene): ScnSelect (init 0x20b8e8) lists the 242 script files, then
  VarSelect (0x20b750) and DebugFlagWindow (0x20b420) set 11 script variables (KOUI, AITE, HOMERU,
  SHIKARU, HAGEMASU, IKON, CHUSAI, SCOUT, ISEKI, OFFICE, GYM; names 0x38cf60, values 0x59ea35+i;
  □ sets all to 0). ScriptSelect (0x20b208) then plays a chosen scene.
- **MaskTest**: only its name remains.
- **Boot sequence back door**: Demo (update 0x20bb50, jump table 0x4698e0) runs logo → logo
  → warning. Its state 3 creates WazaTest, but nothing sets state 3.
  - Patch: 0x20bc24 `24030002` → `24030003` opens the move check after the warning screen.
  - To open the script viewer instead, also patch (the same calls DebugSelect makes at
    0x20be84): 0x20bc48 `24040110` → `2404006c`, 0x20bc5c `26040028` → `26040024`,
    0x20bc60 `24635ac8` → `24634490`, 0x20bc64 `0c0c15fe` → `0c08cf12`,
    0x20bc6c `0c0c15fe` → `00000000`, 0x20bc70 `26040090` → `00000000`.
  - For a sound test, use `246345e0` (BGM), `246345b8` (SE) or `24634590` (voice) at 0x20bc60.
  - Scenes may expect game data that isn't loaded this early.
- **Top-level states**: SubControl (update 0x208740, jump table 0x4684e0) has 33 states. State 32
  (Office mode 15, 0x208c34) is never set in SubControl - a weak lead.
- An unreferenced screenshot path `host0:Capture/screen%03d.tm2` remains.

## Battle cheat window
*verified in game* (2026-10-19). *From the code* (source `battle/battle_main.cc`). START in a match opens BattleSkip (vtable
0x404d88): P1/P2 control mode, Options, Skip to end of match. Its jump table at 0x4c20e0 has a 5th
case (0x25b1e0) that opens **DebugCheat** (init 0x25b4d8, update 0x25b890), but no item for it is
ever added.

DebugCheat toggles five words at 0x101bba8-0x101bbb8, which the battle code reads (0x24410c,
0x244f90, 0x24e054, 0x24d228): reversals always/normal, always red's turn / attack checks red
only, cut checks always/priority, card dealing priority, give-up/KO always.

Patch: data word 0x4c20ec `0025b194` → `0025b1e0` - "Skip to end of match" opens the cheat window
instead.

## Debug log
*From the code.* 0x2086f8 is an emptied printf with 483 call sites, all with format strings
("Adventure::Init(%d,%d)", "Music::Play(%d) [%s]", "label not found ! %s", ...). The real printf
is 0x353ae8. Patch: 0x2086f8 `27bdff80` → `080d4eba` (`j 0x353ae8`), 0x2086fc `ffa50048` →
`00000000`. The messages should then show in PCSX2's EE log (`%f` may print wrong).

## Button codes and secret names
*From the code.* None found. Pad reads go through press/held/repeat wrappers (0x21f488, 0x21f5b8,
0x21f6e8; state 0x1095c08). Every check is "any of these bits". The only multi-bit masks are
skip-type (0x62 at 0x288170; Start or □ to skip a CPU match, 0x253480). Logo and title screens
check only Start. Name entry (InputName, 0x2aa180-0x2abd00) compares only against the full-width
blank; no string compare anywhere takes a Japanese literal.

## Unused files
*From the code.* The executable finds files through the table at 0x38cfa0 (12-byte entries
`{name, LBA, sectors}`; code points at an entry, or at a series' first entry + index x 12).

- **No table entry (never loaded):**
  - `/SYS/SUCCESS.GSL`: an earlier boot logo (the class is still `LogoSuccess`; it loads
    TRYFIST.GSL).
  - `/SYS/MAP.GSL`: an all-in-one mock-up of the territory map (the game builds it from `/MAP/`).
  - `/SYS/COMBACK.GSL`: an empty teal window frame.
  - `/SYS/COMSE.HBS`: a sound bank (sequence, bank, samples).
  - `/BATTLE/ACC00.GSL`: a red "Accsident!!" (sic) stamp in the style of the attendance stamps,
    probably a cut injury result.
  - `/BATTLE/WIN00-02.GSL`: WINNER, ベルト奪取 (title won), ベルト防衛 (title defended) banners.
  - `/BATTLE/TL01.GSL`: a gold FINAL SERIES logo.
- **In the table but never referenced:** `SYSTITLE`, `MODE`, `OMA_BG00` and `CGMODE1-8.GSL`.
  These are the title, mode select and gallery screens of an unrelated 2004 visual novel (New
  game / Continue / Extras; CG, SCENE, MUSIC), carried over from an earlier project. `CGMODE4/5`
  are 0 bytes; `CGMODE8` repeats two `CGMODE1` pictures.
- **Gallery page 36** (`TH36.GSL`): all nine pictures are identical - placeholder art (the page
  has only one real slot).
- **Masks:** only scripts load masks (0x229dac), and they use 001, 002, 004, 020, 029, 038 and 042.
  45 of the 52 transition masks are unused, including the special shapes 101-104 (crescent wipe,
  ink splatter).

## Unused moves
*From the data.* No wrestler has W012 ＪＯサイクロン, W014 ＳＳＤ, W212 スプラッシュマウンテン,
W259 ＳＳＤ (a duplicate in the signature block), W312 コンビネーションキック or W412 シューティングＳプレス.
W208 and W266 are missing from the numbering; W266 is inside the signature block (W251-271), so a
finisher was probably cut. W7xx-W9xx are moves the engine picks (double teams, counters).

## Scripts
*From the data and code.*

- **Unused commands:** add, alarm, bglc, bto, cgmv, cgmvas, cglc, cglcas, cga, cgbc, call, ddm,
  down, er, ercg, let, mto, nop, pt, return, site, sel, sub, ts, up, use, wait, wto (names .sdata
  0x599848-0x5999b8). add/sub/up/down/let and cgmv still have handlers ("parameter error"
  messages), so a variable and subroutine system was apparently cut. The variables ISEKI, OFFICE
  and GYM are used by no script.
- **Conversation scenes twice:** segment `_072` holds scenes 073-102 inline, and the same scenes
  also exist as separate segments `_073`-`_102` with their labels commented out. 1,080 of 4,740
  lines differ. One copy is probably dead.
- **Hikawa / SA-KI (046/146):** scenes 053 and 068-070 exist only as `_1` and `_2` variants.
  The Climax tournament win/loss code (0x270094, 0x2700c4) asks for plain `char046_069`/`_070`,
  which don't exist - a possible original bug.
- **Lines that never show:** in 076:105 and 176:105 two of the President's thoughts are in
  half-width brackets, so the engine reads them as labels.
- **Developer comments:** about 830 distinct `//` notes, e.g. 019:107 "★セリフ追加 ダメならはずす"
  (lines added - remove if not OK), 020:105 "★テスト", 035:71 "★ファイル名が仕様と違う" (file
  name differs from the spec), 073:108 "対象のキャラクターが指定されていません" (no target
  character given), commented-out CG flicker sequences in 002:106 and 020:107.

## Music
*From the code and data.* Scripts play bgm03, 04, 07, 09-18, 20 and 31-48. The code plays BGM06-08
in battle and BGM19 in the ending. **BGM01, 02 and 05** are played only by the dead BGM test,
unless the title or menus play them by a path not yet found - check by ear.

## Emulator checks
1. Battle cheat window: 0x4c20ec → `0025b1e0`, then START in a match → last item.
2. Move check at boot: 0x20bc24 → `24030003`.
3. Gallery unlock: 0x2212e8 → `24020001`; all 36 pages filled, page 36 a single thumbnail.
4. Script viewer and sound tests (the boot patch set above).
5. Debug log (EE console).
6. Talk to a wrestler with a breakpoint on 0x2008a0: which copy of the conversation scenes runs.
7. Hikawa Saki in a Climax tournament: watch for "File not Found" (breakpoint 0x200978).
8. Title and menu music: BGM01/02/05.

Working notes, tables and scripts: build/work/hidden/ (gallery/unlock_table.txt lists slot → CG →
scene).
