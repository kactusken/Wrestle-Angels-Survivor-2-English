# Patches

What the build changes besides text and images, one section per patch: what the original code
does, what changed, why it works, the tool that makes it, limits to respect, and whether it was
*verified in game*.

The gameplay patches are groups picked with `build.py --unlocks`. `all`, the default, means every
group except `debug-*`, which change how the game starts or plays and are only applied when named.
The code behind each one is in [HIDDEN_CONTENT.md](HIDDEN_CONTENT.md).

## Gallery (`gallery`)
*From the code;* *verified in game* (2026-10-19): every page filled, and the save's own gallery
progress is unchanged without the patch. The gallery asks isSeen(i) (0x2212b0) for each CG: bit
`i` of the bitfield at 0xeac300, which the `bg` script command sets when an event shows that CG.
Only the gallery calls isSeen. The patch makes it return 1 (0x2212e8, the delay slot of its
`jr ra`: `sltu v0,zero,v0` → `li v0,1`), so all 316 slots and all 914 pictures are viewable,
including 56 variant pictures no event ever shows. Nothing is written to the save: the real
progress stays as it was and is back without the patch. Used by the "All Unlocked" releases.

## Battle cheat window (`debug-cheat`)
*From the code;* *verified in game* (2026-10-19): the window opens and its toggles change the match. START in a match opens a menu whose handler jumps
through the table at 0x4c20e0. Case 4 opens the developers' DebugCheat window, but the menu never
adds a fifth item. The patch points case 3, "Skip to end of match", at case 4's code (data word
0x4c20ec `0x0025b194` → `0x0025b1e0`), so that item opens the cheat window and skipping a match
is no longer possible. The window's labels are in translation/text/exe.csv.

## Script viewer at boot (`debug-menu`)
*From the code;* *verified in game* (2026-10-19): pick a character's script, set the variables, then
pick a scene, and it plays. The boot sequence (0x20bb50) goes logo → logo →
warning → title, and has an unused state 3 that creates the move check (WazaTest). The patch sends
the sequence to state 3 after the warning screen (0x20bc24 `li v1,2` → `li v1,3`). It also changes
state 3 to create ScnSelect, the script viewer, with the same calls the orphaned debug menu uses
at 0x20be84: object size 0x6c, vtable 0x404490, init 0x233c48 at +0x24, and no second sub-object
(7 words, 0x20bc24-0x20bc70). The sequence then moves to state 4, as after the move check;
whether leaving the viewer goes on to the title is still to be seen.

To open a sound test instead, replace the vtable word at 0x20bc60 with `0x246345e0` (BGM),
`0x246345b8` (sound effects) or `0x24634590` (voices). To open the move check, use only the
first word.

## Debug log (`--debug-log`, developer only)
*From the code; not yet verified in game.* The game's debug printf 0x2086f8 was emptied before
release (it only saves its arguments and returns), but its 483 calls remain. The flag turns its
first two instructions into `j 0x353ae8` (the real printf) + `nop`, so the messages appear in
PCSX2's EE console. `%f` output may be wrong. Never in release builds.
