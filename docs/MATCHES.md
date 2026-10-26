# Matches: cards, exchanges, damage and finishes

How a match works in Wrestle Angels Survivor 2: the controls, the cards, how the game decides
who wins an exchange, damage, pins and submissions, tag and six-woman matches, the skills that act
in matches, the CPU, and matches you don't watch. The [player's guide](https://kactusken.github.io/Wrestle-Angels-Survivor-2-English/guide/#match-basics)
explains the same rules for players, with an exchange calculator; this page has the exact rules
and addresses.

**Nothing on this page has been checked in the game yet.** Marks:
- *code* - read from the executable `SLPM_550.56`; RAM address given (RAM = file offset + 0x1ff000).
  Many formulas are confirmed by the developers' debug `printf` strings next to them (quoted in
  Japanese where useful).
- *text* - on-screen text; English labels are the patch's (translation/text/exe.csv, moves.csv,
  skills.csv, translation/letters/*.json).
- *fans* - Japanese 5ch strategy threads 2008-2014, often quoting the official guide book
  (sources at the end). Not checked against the code unless said so.
- *inferred* / *(unverified)* - a reading or guess that still needs checking.

Every rule was read from WAS2's own code; nothing was carried over from the first game's study
(the Wrestle Angels Survivor translation's docs/MATCHES.md). Where WAS2 differs from WAS1 it says so (and
§15 lists all the differences).

Skill names: the patch's English (skills.csv), with the 1-based id the code uses
(id k = skill table entry k-1 at 0x50e000; entry 44 is a second, unused カット).

## Contents
- [In plain words](#in-plain-words)
- [1. Before the match](#1-before-the-match) · [2. Controls and the screen](#2-controls-and-the-screen)
- [3. The cards](#3-the-cards) · [4. Who wins an exchange](#4-who-wins-an-exchange)
- [5. Reversals](#5-reversals) · [6. Which move happens](#6-which-move-happens)
- [7. Damage, health and the ring](#7-damage-health-and-the-ring)
- [8. Pins, cradles and submissions](#8-pins-cradles-and-submissions)
- [9. Tag and six-woman matches](#9-tag-and-six-woman-matches)
- [10. How matches end](#10-how-matches-end) · [11. Skills in matches](#11-skills-in-matches)
- [12. The CPU](#12-the-cpu) · [13. Skipped and unwatched matches](#13-skipped-and-unwatched-matches)
- [14. Strategy](#14-strategy) · [15. Differences from WAS1](#15-differences-from-was1)
- [16. Possible bugs](#16-possible-bugs) · [17. Open questions and emulator checks](#17-open-questions-and-emulator-checks)
- [Reference: match state](#reference-match-state) · [Sources](#sources)

---

## In plain words

A match is a card game played one **exchange** at a time.

- **You hold 5 cards.** Each card is a move type - **Throw, Hold, Power, Strike, Aerial**, or
  the rarer **Finisher, Double** (team matches) and **Other** - with a number from 1 to 10 (10 shows
  as **A**). Each exchange both corners play one card; the winner's move happens, the loser's
  doesn't.
- **Score = card number + your attack in that type − her defence in that type**, plus small
  bonuses. The Atk/Def letters on the match screen are these ratings. There is no dice roll in
  the score; the luck is in the cards and in what happens after (reversals, pins, cuts).
- **Big moves cost points on a fresh opponent.** If the move's level is higher than the tenths of
  health she has *lost*, the whole level comes off your score. Small moves early, big moves late.
- **Losing builds a comeback:** after 3, 4, 5, 6, 7+ lost exchanges in a row your card gets
  +1, +3, +5, +7, +9. **Ties** go to whoever lost the previous exchange.
- **A Finisher card always wins** the exchange and can't be reversed; it adds +40 damage. Two
  finishers: the previous loser wins. Finisher cards come more often the more hurt you are and
  the more grit and popularity you have.
- **New: Take the Hit (受け).** Some wrestlers have this Other-card move: you lose the exchange on
  purpose, take 15% less damage per level of it, and get +level on your next exchange.
- **The loser may reverse** about 54 big moves (a German suplex into a sunset flip, a moonsault
  into raised knees). Dexterity, a low card from the attacker, and - unlike WAS1 - being *hurt*
  make reversals likelier. Judgment rolls twice; Focus on the attacker makes it harder.
- **Damage** = the move's damage at its level + the attacker's Strength (plus size, skills,
  bleeding, criticals). Health is 50 + 30 × Stamina + 10 × Strength (in hundreds of points), so
  50 to 530.
- **To win: pin her, make her give up, or knock her out.** Pins almost never work while she
  has any health left; at 0 health it comes down to grit. **Cradles** steal wins below 40% health.
  In a hold she chooses each round to crawl to the ropes or try to break free. **New: KO** - a
  critical hit (Killer S / Killer G skills) that empties her health can end it at once (15%).
- **No count-out, no disqualification.** Running out of exchanges is a **draw**.
- **Partners** can break up pins and holds, by rules of distance, health, speed, size and
  friendship.
- **Difficulty (LEVEL 1-3) changes nothing in matches.** The CPU follows fixed rules, plays a
  Finisher card the moment it has one, and draws slightly *worse* card numbers than you.
- **Matches you skip** aren't played: ratings, grit and best attack grade decide the odds.

---

## 1. Before the match
- **Watch / Skip** per match (labels *text*: "Start Match", "Skip", "Watch" on BATTLE/BT_LIST;
  help 0x4c3598 "Choose whether to watch matches and change the match control mode.").
  Skip decides the match without playing it (§13).
- **Control mode per wrestler** (*text*: plates COM, AUTO, S-AUTO, MANUAL and L1/R1 tab glyphs on
  BT_LIST). How the pre-match screen assigns them was not traced; WAS1 used L1/R1 on the wrestler
  (*inferred* the same here).
- The modes (*code*, value at 0x59e7f8 + side×4, set per team member at battle +0x78):

  | Mode | Value | Card | Move |
  |---|---|---|---|
  | **COM** | −2 | CPU | CPU |
  | **Auto** | −1 | CPU | CPU - the same routine as COM; your wrestler plays herself |
  | **Semi-Auto** | 1 | you | the game picks it (CPU routine) and shows "move NN%" |
  | **Manual** | 0 | you | you, from a list |

  COM and Auto differ only in the deal: COM draws from a slightly worse number table and can't get
  a repeat Finisher card within 10 exchanges (§3). (*code* 0x2539c0, 0x244384, 0x244574)
- Each wrestler keeps her own mode and controller port; a tag swaps them in (0x250570), so tag
  partners can be on different pads or modes (*code*).
- The new-game difficulty LEVEL.1/2/3 (0x59e8b8) only sets the starting money (5000/4000/3000 AP);
  no match code reads it (*code*, 0x21c1d8).

## 2. Controls and the screen
*Code* (pad bits at 0x306fa0; card input 0x253a94-0x254100) unless marked.

| Where | Button | What it does |
|---|---|---|
| Your cards | LEFT / RIGHT | browse the hand |
| | ○ | play the card (Manual: then pick the move; a Double card: pick the partner first) |
| | □ | command list: **Pin / Cancel Pin** (in the ring) or **Return / Cancel Return** (outside), plus **Tag / Cancel Tag** in team matches; Tag asks which partner |
| | △ | wrestler details *(inferred: opens the shared details screen)* |
| | × | slide the cards and gauges off the screen to watch the ring; × again brings them back *(inferred)* |
| | START | battle menu: "**&lt;name&gt;'s Control Mode**" (switch to the other two of Manual / Semi-Auto / Auto), **Options**, **Skip to End of Match** (confirm "Skip to the end of the match. Is that OK?") |
| Move list (Manual) | UP / DOWN, ○ | the moves of that type usable from the current position, shown with their level |
| Partner list (Double) | UP / DOWN, ○ | partner name and her health % |
| Caught in a hold | UP / DOWN, ○ | **Break Free** or **Reach the Ropes** (§8.3) |
| CPU vs CPU / Auto | START or R1 on pad 1 | opens the battle menu at the next CPU turn, to take over or skip (0x253444) |

- **Commands only take effect if your card wins the exchange** (*code*): the loser's Pin request
  is cleared at the judgement (0x2544f4), her Return and Tag requests after the reversal check
  (0x2546a8). A card whose move can't pin (pin type 0, e.g. any hold) cancels Pin (0x248e0c).
- A card with no move usable from the current position can't be played (error sound,
  0x253cc8).
- **Semi-Auto readout** "move name   NN%" (0x2596c8). The % (0x250ec0) is: Finisher 99; otherwise
  (score − mn − 1) × 100 / (mx − mn + 9), clamped 1-99, where mx / mn are the opponent's best and
  worst (attack − your defence) over the five types. It assumes every card the opponent could
  play is equally likely and ignores her bonuses, the level cost on her side, Take the Hit and the
  tie rule - **a rough guide only**. Manual shows no %.
- **Screen** (*text*, BATTLE/MATCH images): each wrestler's health bar with arm and leg meters,
  both wrestlers' **Atk / Def** for Throw, Hold, Power, Strike, Aerial (grades 0-9, then A-E =
  10-14, S = 15), the cards played, the ring position, and Return / Tag / Pin bubbles.
- Card type names (*text*, BATTLE_MATCH_2): Throw, Hold, Power, Strike, Aerial, Finisher,
  Double, Other.

## 3. The cards
*Code* (deal 0x243fb8; hand at 0x101ba88 + side × 0x24) unless marked.

| Type (code) | Score uses | Notes |
|---|---|---|
| 1 **Throw**, 2 **Hold**, 3 **Power**, 4 **Strike**, 5 **Aerial** | your attack − her defence in that type | the normal cards |
| 8 **Other** | your Speed grade − her Speed grade | weapons, dirty tricks, cradles, Body Throw, **Take the Hit** (each wrestler's own Other moves) |
| 6 **Finisher** | number only; always wins | number always 10; plays one of her (up to two) designated finishers |
| 7 **Double** | number + 2 + streak term | team matches, in the ring only |

- **Hand: 5 cards.** At the start each side is dealt 5 (one every 4 frames, 0x2537ac; the
  opening deal never gives a Finisher card). After every exchange each side draws one
  (0x25388c).
- **Random numbers**: the C library `rand()` (0x34b7d8), shared with the rest of the game. WAS1 had
  a separate match generator.

### 3.1 The draw, in order (0x243fb8)
1. **Finisher card** (not if one is already in hand):
   - chance % = **grit + 7 − 2 × her own health in tenths + popularity / 100 + 3 if Big-Match**
     (debug "特カード抽選 (%d+2-%d*2+5)+%d+%d"). The +3 also comes from **Challenger** when she is
     the blue corner in a title match with less than 30% health (0x244e08; title match = match
     kind 2, *inferred*).
   - **grit** = wrestler +0x6d0 (根性; from the roster, or 5-9 at random for generated wrestlers;
     fans list values 4-10). Popularity from 0x23b640.
   - Example: grit 7, popularity 600 → 0% at full health, 6% at 70%, 10% at 50%, 20% at 0.
   - After her first Finisher card she can get more only while she is **5+ tenths of health
     behind** the opponent. No other cap (WAS1: two per match, the second at 6+ behind).
   - **COM only**: no repeat Finisher card within 10 exchanges of the last ("特カード前回から
     10ターンは出現率０％（COMのみ）", 0x2443c4).
   - The card must be playable from the current position, else she gets a normal draw.
2. **Double card** (team matches, not if one is in hand; only while the **opponent is below 80%**
   and **she has lost some health**): **21% / 18% / 15% / 10%** by her best relationship with a
   partner - roster list +0x110 / lists +0x118, +0x124 / none / list +0x130 (0x2440a4). The fans'
   "best / better / bad partner" lists (*fans*) are presumably these (*inferred*). WAS1: flat 1 in 6.
3. **Ordinary card**:
   - **Type** by her five attack stats ranked best to worst: **25 / 21 / 17 / 15 / 14 %**, Other
     **8%** (*fans* quote the same from guide book p.123). Ties in rank go by a roster value, then by
     defence (0x257248; fans: "defence, then list order").
   - **Ring General**, or **Presence** as red corner in a title match below 30% health: best type
     **30%**, fifth **9%** (0x2441b0, 0x244e98).
   - **At most one Other card in hand** (with one, the roll is out of 92).
   - **Number** - an independent roll each time; **no deck** (WAS1 dealt from a 180-card deck):

     | Number | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 (A) | average |
     |---|---|---|---|---|---|---|---|---|---|---|---|
     | You (Manual / Semi-Auto / Auto) % | 5.5 | 5.5 | 5.5 | 5.5 | 11 | 11 | 17 | 17 | 11 | 11 | 6.40 |
     | COM % | 7 | 7 | 8 | 8 | 10 | 10 | 15 | 15 | 10 | 10 | 6.02 |

     (0x2444bc / 0x244574.) Fans: "67% chance of a 6 or higher" (guide p.123) - that matches the
     player's table exactly (*fans*, agrees with *code*). The CPU's table is *worse* - the old fan
     suspicion that the CPU draws better cards is wrong.
   - **Stuck-hand protection**: if the new card would leave a full hand with nothing playable from
     the current position, it becomes a Throw card of the same number (0x2446d0).
- Debug cheat 0x101bbb4 ("Cards: Normal->Priority") deals Finishers, then Doubles, then Hold/Strike.

### 3.2 Display
The number glyph comes from the strip "0123456789ABCDES" (BATTLE/MATCH.GSL), so **10 shows as A**
(*code* 0x252fd4 + image; texture identity *inferred*).

## 4. Who wins an exchange
*Code*: judge 0x244f20, score 0x2449d8, base 0x244750.

### 4.1 The score
```
score = card number
      + attack(type) − her defence(type)                      Throw..Aerial cards
          +1 attack if you have that type's attack skill (Throw Atk .. Aerial Atk)
          +1 defence for her if she has that type's defence skill (Throw Def .. Aerial Def)
        (Other: your Speed grade − her Speed grade; Finisher: nothing; Double: +2)
      − the move's level, if level > 10 − her health in tenths              "level cost"
      + comeback: you lost the last 3/4/5/6/7+ exchanges → +1/+3/+5/+7/+9    (not Double cards)
      | Double card instead: +2 × her losing streak − 2 × yours (yours at most −6), at most +8
      + tag request: if your chosen partner has more health than you, the gap in tenths
        (doubled when it is 5 or more)
      + the move's own modifier against a standing / downed opponent (move +0xe0 / +0xe4)
      + 1 for the red corner in a title match ("チャンピオン補正", match kind 2, side 0)
      + 1 if the venue is in her home prefecture ("地元補正")
      + 1 with Clutch when she is below 50% and 5+ tenths behind ("NS25逆境補正")
      + the level of the Take the Hit she used last exchange ("前回「受け」補正", §4.3)
```
- **Ratings** (0x257248, at the start and after tags): attack and defence grades 0-15 of the raw
  stats (thresholds 100, 200 ... 800, 950, 1100, 1250, 1400, 1550, 1750, 1950; table 0x4c0d38),
  plus skill modifiers (0x101bad0 +0x50/+0x54):
  - **Explosive**: +1 attack in her best of Throw / Strike / Aerial;
  - **Fighting Spirit**: +1 attack and defence in her best type if the opponent's rating is at least
    1.25 × hers;
  - an opposing partner with **Trash Talk** (on the apron, not the legal wrestler): −1 attack and
    defence in her worst type. Singles: never.
- **The level cost**: at full health every move pays its level; at 90% level 1 is free; at 70%
  levels 1-3; at 50% levels 1-5; below 20% everything (*fans* agree: "Lv9 free only below 19%").
  The difficulty term WAS1's SNES ancestor had is gone; **no difficulty and no random term**.
- Down/standing modifiers per move (move +0xe0 / +0xe4): fans' summary "+3/+4 for most moves on a
  downed opponent, +5 for double-teams and some aerials, +6 for dirty moves; −1 for some holds and
  aerials on a standing one; Dragon Screw +1 on a standing one" (*fans*; values in the table are
  −1..+6, *code*).

### 4.2 The judgement (0x244f20)
1. **Take the Hit loses to anything.** If both play it, go on to step 2.
2. **A Finisher card beats any other card.** Two Finishers: the side that **lost the previous
   exchange** wins.
3. Otherwise **higher score wins; a tie goes to the side that lost the previous exchange.** The
   very first tie is a coin flip (0x243d38).
- The winner's streak resets and the loser's grows (0x2493a8, after the reversal check, so a
  reversal counts as the reverser's win - fans tested this, thread 03 #961-964).
- Debug cheat words: 0x101bbac "always red's turn".

### 4.3 Take the Hit (受け, move 173, an Other move) - new in WAS2
- Played as an Other card. It **always loses the exchange** (0x244fa8), so the opponent's move hits.
- That hit does **15% less damage per level** of her Take the Hit (+1 level with **Iron Wall**),
  never below 0 (0x24d014; set at 0x245078 and used the same exchange).
- **Next exchange her score gets +its level** (0x244d30; cleared after that judgement).
- Since she lost, her own losing streak grows (so the comeback bonus grows too) and the
  opponent's resets.
- Fans quote the guide book: "damage cut by level × 15%", "helps the next exchange"; Iron Wall
  "less damage when taking the hit"; "it can even cancel a finisher's damage" (*fans*, agrees with
  *code*). Example: level 6 cuts 90%.

### 4.4 Finisher cards
- Win the exchange outright (unless both play one) and **can't be reversed** (0x248f98).
- The move is one of the wrestler's designated finishers (up to two, wrestler +0x678/+0x67c; you
  can change them in management, "Change the wrestler's finisher").
- **+40 damage** to health - or, for a hold that targets an arm or leg, **+15 to that limb
  meter instead** of the +40 (0x24d17c-0x24d1a8). The Strength term is not added for Finisher
  cards (0x24ccdc). This is probably the fans' "joint finisher bug" (§16).
- Ignores the level cost (no level term is scored for Finisher cards). Can also be a critical hit.

## 5. Reversals
*Code* 0x248f50 ("返し技判定 %d < %d+%d+%d+%d+%d").
- 54 moves have a reversal (move +0x58, second option +0x5c), e.g. German / Tiger / Dragon
  Suplex → Sunset Flip, Backdrop → Body Press, Powerbomb / Liger Bomb → Reverse Huracanrana,
  Lariat → Fujiwara Armbar or a Lariat back, Moonsault / Shooting Star Press → Knee Counter or
  Self-Destruct, Missile Kick → Self-Destruct, Chair Shot → Chair Shot. Finisher cards can't be
  reversed.
- **Chance %**, rolled by the loser (the would-be victim):
  ```
  (move level + 3) + (10 − loser's health in tenths) + 2 × loser's Dexterity grade
  + the move's down/standing modifier (by whether the loser is down)
  + (10 − winner's card number)
  ```
  - **A hurt wrestler reverses more** (WAS1 subtracted the same term). A fan's 100-throw test
    (63 reversed) only fitted the guide book's formula with this term added (*fans*, thread
    S2-02 #552) - so the code and the test agree; the book's printed sign is wrong.
  - Low cards and big moves get reversed more.
  - **Judgment** (loser): two rolls, either succeeds. **Focus** (winner): the roll is doubled
    (chance about halved); Focus vs Judgment: one plain roll.
  - Debug cheat 0x101bba8 "Counter: Normal->Always".
- **Which reversal** when there are two options: Lariat-type (option 2 = Lariat, move 190) -
  Lariat back if the loser's Power attack ≥ the winner's Hold attack, else the armbar (looks like
  a slip, §16). Flying presses - Self-Destruct (she crashed) if the loser's Speed + 2 × (4 − size)
  is higher than the winner's, else Knee Counter.
- The reversal must be usable at the current position, else nothing happens ("返し技不発").
- A reversal makes the reverser the exchange winner: her move (level = the reversal's minimum
  level) is done, and the original attacker's Pin / Return / Tag requests are cancelled.

## 6. Which move happens
- **Manual**: you choose from her moves of the card's type that can be used at the current
  position (move +0xf4: in the ring only / anywhere / outside only / at the ropes only, 0x243910).
- **Semi-Auto, Auto and COM** (0x250820): from the usable moves, minus the wrestler's two
  "COM doesn't use" moves (roster +0x7b0/+0x7b4) when there are alternatives:
  - normally: among moves with level ≤ 10 − her health in tenths (no level cost), the best one
    40%, second 30%, third 30% (two: 50/50; none affordable: the lowest level);
  - when 2+ tenths healthier than the opponent, or asking to tag, and the card is strong
    (base score minus the advantage in a stored type ≥ 16 / 11-15): 50% the highest-level move /
    the second-highest regardless of the level cost.
- Finisher cards: one of her finishers usable here. Double cards: the six double-team moves (§9).
- Each move's level is the wrestler's own (learned level, MANAGEMENT §8.7).

## 7. Damage, health and the ring
*Code* (apply 0x24d0c8, calculation 0x24c8f8).

### 7.1 Health and limb meters
- **Max health = 50 + 30 × (Stamina / 100) + 10 × (Strength / 100)** on the raw 0-1200 stats,
  integer division (0x23b550) - up to 530. WAS1 used the 1-15 grades.
- **Arm and leg meters** (HP struct +4 arm, +8 leg) start at half max health; moves with a limb
  target (move +0x8c: 1 arm, 2 leg) damage them. They never recover in a match. Unlike WAS1 they
  are also damaged in team matches.
- Starting health comes from the match record (normally full; whether any format carries damage
  over was not traced).

### 7.2 Damage, in this order
1. **Finisher card**: +40 health, or +15 limb for a limb-targeting hold (§4.4).
2. **Critical hit** (new): move level ≥ 6, the attacker has **Killer S** and the move is a Killer S
   move (strikes like High Kick, Superkick, Elbow, Palm Strike, Backfist, Capture Suplex, SSD,
   Northern Lights Bomb...) or **Killer G** and a Killer G move (Dragon Screw, Achilles Hold, Flying
   Armbar, Kneebar, Chickenwing holds, Ankle Hold, Choke Sleeper...): **6%** ("Critical!!"). Adds
   another +40 health / +15 limb. Fans quote the guide book: "level 6+, 6%" (*fans*, agrees).
3. **Base damage** from the move table at the card's level (body and limb, 9 levels; e.g. Arm Drag
   15 → 70, Tiger Suplex 23 → 95).
4. Attack skill of the type (+2 health / +1 limb); the defender's defence skill (−2 / −1).
5. **Strength term** (not for Finisher cards), added in full to health damage, half to limb:
   Strength grade + 4 **Brute Strength** + 4 **Outside Fighter** while outside + (size − 2)
   + (10 − attacker's health in tenths) **if the attacker is bleeding**.
6. **Brutal** (attacker): +10%.
7. **Sturdy** (defender): +10% from Hold cards, −10% from all others. **Flexible**: ×0.8 from
   Hold cards.
8. **Berserker** while bleeding: +10% dealt, +10% taken.
9. **Take the Hit**: −15% per level (§4.3).
- Size (roster +0xc4, 0-4, 2 = average; fans: SS/S/M/L/LL): −2..+2 damage, and changes knockdowns,
  cuts and some reversal choices. Fans: "±1 damage per size rank" (*fans*; code says ±1 per rank
  from M too, since the term is size − 2).
- Damage can't take health below 0.

### 7.3 KO and referee stoppage (new)
Only on a **critical hit whose damage is more than her remaining health**, in the ring: **15%**,
and the match ends at once (0x24d298-0x24d32c). Killer G moves: "Oh! The referee has stopped it!" /
"Referee stoppage!"; others: "Incredible, it's a KO!!" (*text*). Fans quote the same 6% / 15% from
the guide book (*fans*). Debug cheat 0x101bbb8 "Sub/KO: Normal->Always".

### 7.4 Knockdowns
After each damaging move both wrestlers stand up, then the defender goes down with chance
**(damage − 40 + 2 × (attacker's size − 2)) / 80** (0x24d444). **Balanced** (defender): a second
roll must also succeed. Being down matters for the next exchange's move modifiers (§4.1) and
reversal chances. WAS1: (damage − 40) / 80.

### 7.5 Ring position and going outside
- Position (0x59e7d8): −2..+2 in the ring (±2 at the ropes), ±3 both outside. Red pushes toward
  −2, blue toward +2. Each move (move +0xf0) pushes 1 or 2, pulls 1, swaps sides (aerials,
  Moonsault), or returns to the centre (To Center Ring).
- **Pushed at the ropes → maybe outside**, by the alignments of attacker and defender: Face-Face
  5%, Face-Normal 10, Face-Heel 15, Normal-Face 15, Normal-Normal 20, Normal-Heel 25, Heel-Face 25,
  Heel-Normal 30, Heel-Heel 35% (0x24d820). **Escape Artist** on either: a second roll. **Keep
  Distance** (Other move) always takes both outside ("And she heads outside to lure her opponent
  out!!").
- Going outside cancels the attacker's Pin and Tag. Outside: holds break at once, no pins (a
  cradle "means nothing on the floor"), outside-only moves (topes, Chair Shot, Ring Post Attack,
  Poison Mist, Wooden Sword) become usable.
- **Return** (□ outside): if the winner asked, both go back in at the ropes (±2), at the end of the
  exchange (0x2556a0, 0x256c98). **No count-out.** The CPU returns after more exchanges outside
  than its alignment number: Face 1, Normal 2, Heel 3.

### 7.6 Bleeding
- After a hit, if she isn't already bleeding: chance = the move's bleed % (most moves 0; strikes,
  kicks, dives 1-10%; weapons, chair, ring post, wooden sword 20%), doubled by **Razor** (0x24d68c).
  "《相手名》 is bleeding!" (*text*).
- Lasts the match: **halves her recovery**; her own attacks get + (10 − her health tenths);
  Berserker +10% / +10%.
- WAS1 gave the bonus to the attacker *against* a bleeding victim; WAS2 gives it to the bleeding
  wrestler's *own* attacks (§16).

### 7.7 Recovery each exchange (0x24dab8)
- Base = **Recovery grade** (0-15) HP, times:
  - **singles**: by her own health tenths - ×0.25 at full, 0.4, 0.55, 0.7, 0.85, 1.0 (50%), 1.1,
    1.2, 1.3, 1.4, ×1.5 at 0;
  - **tag** (legal wrestler): ×¾ at the ropes, ×½ elsewhere, 0 outside;
  - **six-woman** (legal wrestler): ×½ at the ropes, 0 elsewhere.
- +20% with **Stamina**, +20% if a partner on the apron has **Supportive**; halved when bleeding.
- **Kick-out burst** (replaces her normal recovery once, 0x24e7d8): Recovery grade × ½ / 1 / 1.5 /
  2 / 3 for a kick-out at 1 / 2 / 2.5 / 2.8 / 2.9, × 1 for a rope break (same skill bonuses,
  halved when bleeding). A 2.9 kick-out at 0 health also heals 3 × grade at once.
- **Partners on the apron** below 50% heal 2 × Recovery grade per exchange, up to 50%.
- WAS1: flat Recovery in singles, half in tag, none in six-woman.

## 8. Pins, cradles and submissions
*Code* (pin flow 0x254ab0-0x254c48; count 0x24e048, 0x24e1d0; holds 0x24e898).

### 8.1 When she covers
- Each move has a **pin type** (move +0xe8): **never** (all holds; cancels Pin), **only with Pin**,
  **automatic** (big suplexes, bombs, drivers, Power Slam, Frankensteiner, presses, Moonsault,
  Shooting Star, Sunset Flip...), or **cradle** (Roll-Up, Inverted Cradle, Small Package Hold,
  Rolling Cradle (Hold), La Magistral...).
- If the winner's move pins automatically, or she asked to **Pin** and the move allows it, and they
  aren't outside: **she always covers** - no cover roll (WAS1 rolled 100/90/40/20/10/5/2/1% by
  health). Pins at the ropes are allowed (rope break below).

### 8.2 The count
1. **Count 1**: kicks out if rand%10 < health tenths − 1. **Count 2**: if rand%10 < health tenths.
   So at 20%+ health she's out by 2; at 10-19% she reaches 2 with 90%.
2. Partner cut-in chance here (team matches, §9.2).
3. **Rope break** at the ropes: rand%100 < Strength grade + grit + her health tenths - *the code
   reads the pinner's Strength and grit* (§16).
4. **Cradles** (pin type cradle, or the pinner has **Pinfall** and the victim has health left):
   - at 40%+ health she always kicks out (at 2.5);
   - else three count with **(level / (tenths + 1)) × 10 %**, integer division first: level 5 →
     50 / 20 / 10 / 10% at 0-9 / 10-19 / 20-29 / 30-39%. With Pinfall on a non-cradle move a second
     25% roll is needed too.
   - Grit doesn't matter (fans say the same).
5. **Normal pin at 0 health**: kick-out % = **grit × 2 (singles) / × 1.4 (tag) / × 1 (six-woman)
   × 10 / c + 30 with Indomitable** (or Presence as red corner in a title match at 30%+) - *as
   coded these are the pinner's grit and skills* (§16). c = the level correction (§8.4). Kick-out
   at 2.9 ("So close!").
6. **Normal pin with any health left**: first, if the move's level is below half the pinner's
   attack in that type ("small move from a strong wrestler"), she kicks out with 98/98/90/70/55/30%
   for levels 1/2/3/4/5/6+. Then she kicks out if rand%100 < (100 − (60 − HP) / 10) × 10 / c,
   HP in **raw points**: the three-count chance is **5% at 1-10 HP, 4, 3, 2, 1% up to 50 HP, then
   0** - and 0 with any level correction.
- Messages (*text*): "kicks out at 1!", "at 2!", "at 2.5!", "just kicks out at 2.8!", "kicks out at
  2.9! So close!", "gets the three count!!"; rope break "just barely reaches the ropes! Rope break!".

### 8.3 Submissions
- A hold lasts **(level + 1) / 2 rounds** (Dragon Screw, Tarantula, Choke Sleeper: 1). The first
  round's damage is the move's normal hit. Outside, a hold breaks at once.
- **One-round holds (levels 1-2 and those three) end at once with no give-up check** - they can't
  win by submission.
- **Each round the held wrestler chooses** (Manual: menu; CPU 0x251c88):
  - **Reach the Ropes**: one step toward the ropes, still taking the round's damage; choosing it
    *at* the ropes breaks the hold. Not offered away from the ropes for holds that pin both in
    place (move +0xf0 = 6; fans name Romero Special, Stretch Muffler, Dragon Cavernaria).
  - **Break Free**: health tenths + Dexterity / 2 + 2d6 + 2 × round ≥ holder's Hold attack + 2d6
    → escapes with no damage.
- After each continuing round's damage, **give-up checks** (0x24edf4-0x24efdc), with
  X = ((holder's Hold attack − victim's Hold defence + level) / 2) × c / 10:
  - body: rand%100 < (3 − health tenths) × 2 + X;
  - arm/leg holds: rand%100 < (3 − health tenths) × 4 + X (the limb meter is computed but not used,
    §16);
  - at 0 health, or the attacked limb meter at 0: rand%100 < (holder's grit − victim's grit + 20)
    × c / 10 (fans quote the guide book: "(grit difference + 20) × level" - *fans*);
  - **Endurance** (or Challenger as blue corner in a title match at 30%+): resists a successful
    roll 40% of the time.
- Messages (*text*): "She taps, she taps! ... gets the submission!", "fights her way out on her own!",
  "It's no use! The ropes are still too far!".

### 8.4 Level correction (new)
Each wrestler's highest pin / hold level used so far in the match is remembered (0x24df10). A pin
or hold of 1 / 2 / 3 / 4 / 5+ levels **lower** works at **90 / 80 / 60 / 40 / 20 %** (divides the
0-health kick-out and the HP>0 pin, multiplies give-up). Pins and holds share it. Fans: "after a
failed pin or submission at one level, lower levels work worse; roll-ups aren't affected" (*fans*;
in the code cradles don't use c either).

## 9. Tag and six-woman matches

### 9.1 Basics
- One legal wrestler per side holds the side's hand; tags swap the legal wrestler, her health, her
  control mode and pad (0x250570). Ratings are recomputed (0x255990).
- **Tag** (□ → Tag, pick a partner) happens at the end of the exchange **only if your card won**,
  and adds the health gap to your score (§4.1). The CPU tags out to a fresher partner (§12).
- **Double cards**: in the ring only; Manual picks the partner (shown with health %) and a
  double-team move. Six moves exist: Taiko Drum Barrage (always offered) and Double Dropkick
  (always), Double Lariat, Double Piledriver, Double Powerbomb, Double Impact - each needs the pair's
  morale gap ≤ a limit and their combined rating ≥ a minimum, depending on their relationship
  (e.g. no special relationship: Lariat gap ≤ 600 & sum ≥ 900; Piledriver ≤ 400 & 1200; Powerbomb
  ≤ 300 & 1600; Impact ≤ 150 & 2000; best partners get looser limits, the "bad" list tighter;
  0x251028). Semi-Auto / Auto / COM pick among all six without this check (§16).
- Partners on the apron recover (§7.7). Trash Talk and Supportive work from the apron.

### 9.2 Breaking up pins and holds (new detail)
- **Will the partner come in?** (0x24f1d0, no randomness): she comes when the victim's health
  tenths (or the attacked limb meter, if lower) is below 6 at her own corner's ropes, 5 one step
  out, 4 in the centre, 2 one step from the far ropes, and only at 0 at the far ropes. Then she
  can't come again for 2-3 exchanges. In six-woman the healthier partner (by %) comes (*fans* say
  the same).
- **Does it work?** (0x24f360) The other side's partner tries to block. Save fails if rand%10 >
  victim's health tenths × 2 + 10/7/4/1/−2 (by distance from her corner) + relationship (+2 best,
  +1 friend, −1 bad) + (cutter's Speed − (size − 2)) − (blocker's Speed − (size − 2)) + 2 with
  **Cut Play**. If the pinning/holding side's card was a **Double**, the save always gets through
  (0x24f360 returns the clean-save result; odd, *check in game*). Messages: "breaks it up!",
  "blocks the save!".
- Fans' summary (guide book): thresholds "≤59% at your corner ... ≤9% at the far ropes", lighter
  and faster cutters better, Cut skill helps (*fans*, agrees with *code*).

## 10. How matches end
- **Pinfall, submission, KO / referee stoppage** (§7.3, §8).
- **No count-out, no disqualification** (*code*: the outside counter, battle +0x178, is only read by
  the CPU's Return rule). "%s is ejected!!!" belongs to the Survival format between bouts
  (*inferred*).
- **Time limit** = a number of **exchanges** (0x24f670, table 0x4dd8d0):

  | Bout | Singles | Tag | Six-woman |
  |---|---|---|---|
  | Ordinary / title match | 40 | 50 | 66 |
  | Main event | 48 | 60 | 80 |
  | Two match categories (tournament / league?, *uncertain*) | none | none | none |

  **Time up is always a draw** ("And that's time! This match is a time-limit draw!"). A title match
  drawn on time: "Time-limit draw, so the title will be held by %s." (*text*; who %s is: *inferred*
  the promotion).

## 11. Skills in matches
*Code* (call sites listed); "help" quotes are the game's skill descriptions or fans' list (*fans*).

| Skill (id) | Effect in a match (*code*) | Where |
|---|---|---|
| Throw/Hold/Power/Strike/Aerial **Atk** (55/57/59/61/63) | +1 attack in the score; +2 health / +1 limb damage | 0x244848, 0x24caa8 |
| Throw/Hold/Power/Strike/Aerial **Def** (56/58/60/62/64) | +1 defence; −2 / −1 damage taken | same |
| **Clutch** (25) | +1 score below 50% health and 5+ tenths behind | 0x244cc4 |
| **Explosive** (23) | +1 attack in best of Throw / Strike / Aerial | 0x25744c |
| **Fighting Spirit** (42) | +1 attack and defence in best type vs an opponent rated ≥1.25× | 0x2574e0 |
| **Trash Talk** (43) | from the apron: opponent −1 attack/defence in her worst type | 0x257570 |
| **Ring General** (40) | best card type 30% (fifth 9%) | 0x2441b0 |
| **Big-Match** (41) | +3% Finisher card chance | 0x24430c |
| **Challenger** (47) | blue corner, title match: below 30% +3% Finisher cards; at 30%+ resists give-up 40% | 0x244e08 |
| **Presence** (48) | red corner, title match: below 30% Ring General's card odds; at 30%+ the +30 at-0 kick-out (applied as the *pinner's*, §16) | 0x244e98 |
| **Judgment** (8) | reversal: two rolls | 0x249100 |
| **Focus** (51) | opponent's reversal roll doubled (about half the chance); cancelled by Judgment | 0x2490d4 |
| **Killer S** (14) / **Killer G** (66) | 6% critical (+40) with matching level 6+ moves; KO / referee stop 15% | 0x24d1d4 |
| **Brute Strength** (13) | +4 Strength term | 0x24c8c0 |
| **Outside Fighter** (17) | +4 Strength term outside | 0x24cd08 |
| **Brutal** (12) | +10% damage dealt | 0x24cdac |
| **Sturdy** (5) | −10% damage taken, but +10% from Hold cards | 0x24cdf4 |
| **Flexible** (6) | ×0.8 damage from Hold cards | 0x24ce90 |
| **Berserker** (15) | while bleeding: +10% dealt and +10% taken | 0x24cf0c |
| **Iron Wall** (54) | Take the Hit counts 1 level higher | 0x24d024 |
| **Razor** (53) | doubles the bleeding chance | 0x24d66c |
| **Balanced** (46) | knockdown needs two rolls | 0x24d474 |
| **Escape Artist** (49) | second roll for going outside | 0x24d898 |
| **Stamina** (24) | +20% recovery and kick-out bursts | 0x252114 |
| **Supportive** (44) | from the apron: +20% partner's recovery | 0x2520c8 |
| **Endurance** (7) | resists a give-up 40% | 0x244dc0 |
| **Indomitable** (9) | +30% kick-out at 0 health (applied as the *pinner's*, §16) | 0x24e534 |
| **Pinfall** (65) | every pin uses the cradle rule (needs below 40%, then a 25% roll) | 0x24e378 |
| **Cut Play** (16) | +2 save score | 0x24f528 |
- **No match effect found**: Brawler (22), Ring Smarts (50), Madness (52) - no check with these ids
  anywhere in the executable (*code*, searched all skill-test calls with constant ids). Fans list
  Ring Smarts as "cancels" something and Madness as a match skill (*fans*, unverified).
- **Durable, Control, Brutal**: also change post-match injury odds (MANAGEMENT §8.6).
- **President skills**: none read by the match code (*code*); Bodywork only lowers post-match
  injuries (MANAGEMENT §8.6).
- Also new: **home prefecture +1**, **title-match red corner +1** (§4.1).

## 12. The CPU
*Code* (cards 0x251348, moves 0x250820, holds 0x251c88). Same for COM and Auto.
- **Each turn, in order**: outside → Return after 1 / 2 / 3 exchanges (Face / Normal / Heel); in the
  ring → ask to **Pin** with 100 / 80 / 50 / 20 / 5 / 2 / 1% when the opponent is at 0-6 tenths
  (WAS1: always at 70% or less); **Tag** to the first partner with 2+ tenths more health (when she
  is at 40%+, unless the opponent is below 20%), or with any more health (below 40%, unless she
  leads by 3+ tenths or the opponent is at 0).
- **Card**: highest value, **no randomness**: number + attack − defence (Other: Speed; Double
  number + 2); **Finisher 99 - played the moment it has one** (WAS1 rolled 20-100%). Each
  wrestler's "card strategy" (roster +0x100) *replaces* the value with fixed priorities: 35 for her
  favourite big type (Power / Aerial / Hold) at 5+, 10 for her secondary (Strike / Strike / Throw)
  at 3+. Types she must leave to a stronger partner, or whose only move is "COM doesn't use", get
  −100; unusable here −999.
- **Move**: §6.
- **Holds**: Reach the Ropes if (her health tenths + Dexterity) − holder's Hold attack < −1 in the
  centre, < 1 one step from the ropes, always at the ropes; Break Free otherwise.
- **Difficulty**: none in matches (§1). Fans' complaints that the CPU gets better cards: the code
  gives the COM *worse* numbers (§3.1); fans' observation "the CPU plays its best card first" is
  right (*fans*, agrees with *code*).

## 13. Skipped and unwatched matches

### 13.1 Unwatched (Skip on the match screen; CPU promotions' shows)
*Code* 0x269728 → 0x268a18. Nothing is simulated.
- Each wrestler's power = **rating + 5 × grit + 10 × her best attack grade**; teams add their
  members' powers, and each member who is above every opponent gets +20, and each who is below every
  opponent also +20 (§16).
- Red's win % from the power gap (singles): 50 even, 55 at +1-50, 62 at +51-100, 77 at +101-150,
  89 at +151-200, **certain at +201** (and mirrored: 45, 38, 20, 10, 1, then 0 at −250 or worse).
  Tag and six-woman tables are a little flatter (tag certain at +251, six-woman 95% at +251-300).
- Scaled by the two sides' starting health % when health carries over.
- **Draw** only when the bout has a time limit and the average ratings are within 100: 1%
  (WAS1: never).
- No champion bonus on this path (WAS1 had +50). The finish, time and health left are made up
  afterwards.
- Fans: "rating + grit + style + champion bonus, each 30-100" and "skipping wins even 30 points
  down" (*fans*, partly agrees).

### 13.2 Skip to End of Match (START menu; 0x24f838)
- With 1-6 exchanges left in a timed match: draw with 80 / 70 / 60 / 50 / 40 / 30%.
- Otherwise the unwatched odds pick a winner; then, if that side has no more health *and* a lower
  rating than the other, the result flips with a chance growing with the health gap (up to 90-99%).
- Tag matches: the decider ignores ratings (50/50 before the health correction) - §16.

## 14. Strategy
From the rules above; fans' tips marked.
1. **Play small moves early, big moves late.** The level cost takes the whole level off at full
   health. Semi-Auto/CPU already pick affordable moves; in Manual, check the opponent's health
   tenths against the level.
2. **Dump weak cards early** while the opponent lands small moves: the damage is small, and three
   or more losses in a row add +1/+3/+5... Then rush with your best cards. "Ideal: win two, lose
   one" (*fans*).
3. **Ties go to the previous loser** - after a loss, a card that only matches her score wins.
4. **Save the Finisher card for a big move** - it ignores the level cost and adds +40. But a
   **limb-targeting hold as finisher only adds +15 to the limb** - pick a throw/bomb as finisher.
   Against a Finisher card, the previous loser wins a finisher-vs-finisher; fans "take a hit just
   before" (*fans*).
5. **Take the Hit** when you have a bad hand or see a Finisher coming: it can wipe out most of the
   damage (level 6 cuts 90%) and adds its level next exchange.
6. **Avoid reversal-prone moves on a hurt, dexterous opponent**, especially with low cards. Big
   suplexes and bombs are the usual victims; moves with no reversal are safer (fans keep lists).
   Focus protects you; Judgment opponents reverse twice as often.
7. **Pins need her near 0.** Above ~50 raw HP a normal pin can't win at all; even at 0 her grit
   decides. **Cradles** win below 40% (best around 0-9%). Don't drop to a lower-level pin or hold
   than one you already used (§8.4).
8. **Submissions**: holds of level 3+ only (levels 1-2 can't make her give up), high Hold attack vs
   her Hold defence, and in the centre so she can't reach the ropes. A hold below 30% health or on a
   worn limb at 0 gets dangerous. Holds are rarely the best way to win (*fans*).
9. **KO**: a Killer S / Killer G wrestler with level 6+ matching moves has a 6% critical each time;
   if it empties the health bar, 15% KO.
10. **Ring position**: Heels go outside a lot (up to 35%); Outside Fighter +4 there. Return
    happens only if you win the exchange.
11. **Tag**: tag in a fresher partner (score bonus = health gap); keep a partner near your corner
    for saves; best-partner pairs get more Double cards and easier double-teams.
12. **Skipping** is safe when your side's power is 200+ higher; close matches are coin flips.
13. **Growth** (MANAGEMENT §8.6): wins over stronger opponents teach the most.

## 15. Differences from WAS1
All from the code of both games unless marked.
| | WAS1 | WAS2 |
|---|---|---|
| Card numbers | shuffled 180-card deck, same for both | independent rolls; COM slightly worse table |
| Finisher cards | grit + 7 − 2 × health, max 2, second at 6+ behind | + popularity/100, +3 Big-Match/Challenger; no cap, repeats at 5+ behind; COM 10-exchange cooldown |
| Double cards | 1 in 6 | 10-21% by partner relationship |
| Other cards | 8%, no limit | 8%, at most one in hand; include Take the Hit |
| Score extras | comeback, tag, position bonuses | + type skills, Clutch, champion +1, home +1, Take the Hit bonus, Explosive/Fighting Spirit/Trash Talk |
| Take the Hit | - | new |
| Reversal chance | − (10 − loser's health tenths) | **+** (hurt wrestlers reverse more); Judgment, Focus |
| Max health | 50 + 10 Str + 30 Sta (grades) | same shape on raw stats / 100 (to 530) |
| Damage outside | Strength counts twice | only Outside Fighter +4 |
| Bleeding bonus | attacker vs a bleeding victim | the bleeding wrestler's own attacks |
| Criticals, KO | none | Killer S / G 6% critical, 15% KO |
| Knockdown | (dmg − 40)/80 | + size, Balanced |
| Recovery | flat; half in tag; none in six-woman | scaled by own health; position rules in teams; Stamina/Supportive |
| Limb meters | not damaged in team matches | damaged in all |
| Cover attempt | roll by health (100-1%) | always covers |
| Count 1/2 | - | rolls on health tenths |
| Level correction | - | 90-20% for a lower pin/hold than used before |
| Pin skills | - | Pinfall, Indomitable, Presence |
| Give-up | (Hold atk − def + level)/2, more below 30% | same core + level correction, grit contest at 0, Endurance/Challenger, 1-round holds can't win |
| Partner saves | partners break up pins | detailed rules (distance, speed, size, relationship, Cut Play) |
| Time limit | 40/48, 50/60, 66/80; tournaments none | same numbers |
| Controls | COM, S-AUTO, MANUAL | COM, AUTO, S-AUTO, MANUAL; switch and skip mid-match (START) |
| CPU finisher | 20-100% by exchange | always at once |
| CPU pin | whenever ≤70% | 100-1% by health tenths |
| Unwatched | rating + 10 × best style advantage + 5 × grit (+50 champion); never drawn | rating + 10 × best attack grade + 5 × grit; 1% draw when close |
| Difficulty | none in matches | none in matches |

## 16. Possible bugs
*Code* readings; none checked in the game yet.
1. **Pin rolls use the pinner's numbers** (0x24e208: s7 = the winner's wrestler). The rope break
   (Strength grade + grit) and the at-0 kick-out (grit, Indomitable, Presence) read the *pinner*,
   while health and the recovery burst use the pinned wrestler. The give-up code gets the sides
   right. As coded, a high-grit or Indomitable wrestler's *own* pins get kicked out more, and her grit
   does nothing for her when she is pinned. Fans' "Indomitable doesn't work" rumour fits (*fans*,
   thread 04 #16-18). Check: breakpoint 0x24e4f4.
2. **Limb give-up ignores the limb meter** (0x24eedc uses health tenths; the limb tenths are only
   printed).
3. **Limb-hold finishers get +15 limb instead of +40 health** (0x24d184): likely the fans' "joint
   finisher bug" (Wikipedia mentions it); the fans' description ("only the +40, no move damage")
   doesn't match the code exactly - check in game.
4. **Lariat reversal choice** compares the loser's Power attack with the *winner's* Hold attack
   (0x2491a0) - probably meant the loser's own Hold. (WAS1 has the same slip.)
5. **One-round holds** (levels 1-2, Dragon Screw, Tarantula, Choke Sleeper) never get a give-up
   check.
6. **Bleeding bonus on the bleeder's own attacks** (0x24cd54) - maybe intended ("bleeding fury"),
   maybe the victim was meant (as in WAS1).
7. **Heavy-move injury counter** (0x24d710): the rating thresholds fall through, so every victim
   rated 599+ counts moves of level 5+.
8. **Tag "Skip to End of Match"** (0x270f58): each member's power becomes `power + flag ? 50 : 0`
   - a precedence slip; ratings are ignored (50/50).
9. **Unwatched team odds** give +20 to both the strongest and the weakest member (same as WAS1).
10. **Double-team checks** (morale/rating) apply only in Manual; the CPU, Auto and Semi-Auto can use
    any of the six.
11. CPU card strategy *lowers* a strong off-favourite card to 10.
12. The CPU's "4+ unusable cards → tag" rule doesn't check that a partner exists.

## 17. Open questions and emulator checks
- Pre-match screen: how COM / AUTO / S-AUTO / MANUAL and pads are assigned (L1/R1?).
- △ (details) and × (hide the panels) - confirm in game.
- Title matches: is the champion always the red corner (champion +1, Presence/Challenger rules)?
- Which match categories have no time limit (tournaments, leagues?).
- "the title will be held by %s" - who?
- Starting health below full in any format (one-night tournaments?).
- Roster relationship lists (+0x110, +0x118/+0x124, +0x130): best partner / friends / bad pair?
- Fans say Hold Atk adds hold rounds (guide p.113); the code's round count (0x30dda8) was not
  checked for skills.
- Brawler, Ring Smarts, Madness: no match effect found.
- Move fields +0x88, +0x100, +0x104 and position effects 5/6.
- Emulator checks: (1) pin bug - breakpoint 0x24e4f4, compare s7 with each side; (2) a limb-hold
  finisher's damage; (3) Take the Hit damage cut; (4) the debug log (docs/HIDDEN_CONTENT.md) prints
  every score, reversal, damage, pin and give-up formula - the fastest way to verify this page.

---

## Reference: match state
*Code.*
- **Battle object 0x101b8d0**: +0/+4 legal member slot per side; +8 exchange counter; +0xc + side×4
  consecutive losses; +0x14 winner of the current/previous exchange (0 red, 1 blue); played cards at
  +0x18 + side×0x18 {+0 type, +4 move id, +8 level, +0xc number, +0x10 move index, +0x14 move
  record}; +0x48 bleeding flags; +0x60 highest pin/hold level per member; +0x78 / +0x90 control mode
  / pad per member; +0xa8 heavy moves taken; +0xc0 / +0xd8 Finisher cards dealt / last turn; +0xf0
  COM-unusable types; +0x168 reversal flag; +0x16c / +0x170 hold rounds / round; +0x174 hold choice;
  +0x178 exchanges outside; +0x17c kick-out burst; +0x180 + side×4 Take the Hit bonus; +0x188 cut
  cooldown; +0x18c pending event bits.
- **Health**: legal wrestlers 0x101ba60 + side×0x14, team members 0x101b830 + side×0x3c + slot×0x14
  {+0 health, +4 arm, +8 leg, +0xc max} (tenths 0x258128, % 0x258150).
- **Hands** 0x101ba88 + side×0x24: five 4-byte slots {type, number, state, anim} at +4, played card
  +0x18, cursor +0x20.
- **Ratings** 0x101bad0 + side×0x28 + type×8 {attack, defence}, modifiers +0x50/+0x54; type ranking
  0x101bb70 + side×0x14.
- **Globals**: ring position 0x59e7d8; down bits 0x59e7dc; Pin / Return / Tag requests 0x59e7e0 /
  0x59e7e8 / 0x59e7f0; control mode 0x59e7f8; pad 0x59e800; tag partner 0x59e808 / 0x59e810.
- **Debug cheat words** 0x101bba8-0x101bbb8 (reversals, red's turn, cuts, card priority, give-up/KO).
- **Moves** 0x4ff880 + id × 0x108 (id 0 dummy, 223 moves): +0x54 type, +0x58/+0x5c reversals, +0x8c
  limb, +0x90/+0x94 level range, +0x98 damage per level, +0xe0/+0xe4 standing/down modifier, +0xe8
  pin type, +0xec bleed %, +0xf0 position effect, +0xf4 where usable, +0xf8/+0xfc Killer G/S.
  Ids 163-185 are system moves (Keep Distance, To Center Ring, cradles, weapons, Take the Hit,
  double-teams, pins); 186-223 reversals. moves.csv rows don't follow the ids - match by Japanese name.
- **Main flow** 0x253410 (56 states, table 0x4c1e20): deal → choose → judge 0x244f20 → reversal
  0x248f50 → move and damage 0x24d0c8 → pin / hold → saves → recovery 0x24dab8 → time check
  0x24f670 → Return → Tag.

## Sources
Fans (Japanese; untrusted, often quoting the 2008 guide book pages 113/123/124/127):
- 5ch "サバイバー2 攻略スレ 01": https://kako.5ch.io/test/read.cgi/gameover/1225871868/
- 5ch "攻略スレ 01 (実質02)": https://kako.5ch.io/test/read.cgi/gameover/1227400225/
- 5ch Survivor threads 03 / 04 / 05: https://kako.5ch.io/test/read.cgi/gameover/1162085655/ ,
  https://kako.5ch.io/test/read.cgi/gameover/1293977102/ , https://kako.5ch.io/test/read.cgi/gameover/1340727241/
- Japanese Wikipedia, レッスルエンジェルス (Survivor 2 section).
- The fan wiki wasv.sakura.ne.jp (has a "試合のコツ" page) was offline and the Wayback Machine was
  unreachable during the study.
