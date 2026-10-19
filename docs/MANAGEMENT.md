# Management mode

How the management game works: the monthly turn, money, popularity, shows, recruitment, training,
and the events and story. The numbers are from the executable's code and data. Where the
developers' debug `printf` strings sit next to a calculation, they name each quantity, so the
formulas are reliable labels, not guesses.

**Nothing on this page has been checked in the game yet.** Findings are marked *from the code*
(with the address), *from text* (an on-screen string, exe.csv id) or *inferred*. Integer
division truncates throughout, which matters for training (§8.3). Checks worth doing in an
emulator are under [Open questions](#open-questions).

A month-by-month timeline of every event and what unlocks it, with a year-by-year track and when
each wrestler is available in each era, is the interactive page [timeline](timeline/)
(open it on the GitHub Pages site; GitHub shows only its source).

## Contents
- [Short answers](#short-answers) · [1. The month](#1-the-month) · [2. Money](#2-money)
- [3. Share and popularity](#3-share-and-popularity) · [4. Shows](#4-shows)
- [5. Rating, TV, belts and facilities](#5-rating-tv-belts-and-facilities)
- [6. Recruitment](#6-recruitment) · [7. Keeping wrestlers](#7-keeping-wrestlers)
- [8. Training and growth](#8-training-and-growth) · [9. Story and events](#9-story-and-events)
- [10. Rival promotions](#10-rival-promotions) · [11. President skills](#11-president-skills)
- [12. Strategy summary](#12-strategy-summary) · [Open questions](#open-questions)

## Short answers

**How do decisions affect the game?** Almost everything runs through two numbers: your
**share** in each prefecture and your wrestlers' **popularity**. Popularity is mostly a
wrestler's ability rating (§3.3), so training is what eventually fills arenas. Share and
popularity set attendance, attendance sets ticket money, and the top three wrestlers'
popularity sets the TV contract. Venue choice decides whether a show makes or loses money,
because rent is charged on capacity, not on the crowd.

**How much should I spend on recruitment?** (§6)
- **Tryout (1-99 AP):** spend **1 AP**, or **99 AP** when your roster is small and you have two
  free dorm places. Up to `50 + 5 × (roster − 6)` AP the first candidate is exactly the same as
  with 1 AP; middle amounts are wasted.
- **Rookie scouting (fixed 50 AP):** better rookies than any tryout. With the president skill
  Network every find is in the top three grades.
- **Transfers:** the minimum cost is fixed; each added AP is +1 % success (+1.5 % with
  Eloquence), no diminishing returns, until success is certain - spend exactly what reaches
  certainty, not more. Failed attempts make the next one easier, so chase a star with 99 AP
  month after month.
- **Contract renewals:** offer **111 %** of her demand; never below 96 %.

**Is there a story?** No fixed plot. The code picks every scene from the calendar, stats, flags
and random rolls; the scripts only show it. The one story thread is the **Final Series**, and
the endings depend on how you do in it (§9).

---

## 1. The month

### 1.1 Turn order
*From the code* (0x219c60) *and text* (0x4fd878, 0x4db870). **One turn is one month.**
1. Office work: any number of commands, as AP allows (menus in §1.3).
2. "End this month's office work" → book the month's shows: 0-8 show days.
3. The shows, then the monthly financial report.
4. Month change: events and news for the next month (§9.4).

The year counter goes up in April (the Japanese fiscal year) and wraps around, so **the game has
no last year** (*from the code* 0x219ca4).

### 1.2 Calendar
| When | What | Source |
|---|---|---|
| April | The year counter goes up; the game starts in April of Year 1 | *code* 0x219c8c, 0x21affc |
| January | Pro Wrestling Awards, then contract renewals | *code* 0x27f124, 0x2efb80 |
| February / March | Valentine's Day / White Day | *code* 0x239e68, 0x239f38 |
| March of a Final Series year | Final Series | *code* 0x21ad34 |
| May | First-pitch offers | *code* 0x23a740 |
| October | School festival offers | *code* 0x23a830 |
| December | EX League invitation (rating ≥ 2500, 2+ non-junior wrestlers) | *code* 0x215c10 |
| December | CPU promotions never invade | *code* 0x214318 |

### 1.3 Office menus
*From text* (help strings; the menu labels themselves are images).

| Menu | Commands and costs |
|---|---|
| Wrestlers | personnel, coaching staff, **tryout** (1-99 AP), **rookie scouting** (50 AP), **transfer talks**, guest booking, release, urge retirement, overseas tour (5 AP per wrestler per month), vacate title, hire coach (100 AP), dismiss coach |
| Management | overseas partnership and ending it, expand/sell facilities, create belt, advertising, events (autograph session 50 AP, concert 100 AP), invade, vacation (30 AP per eligible wrestler) |
| Info | promotion data, history, rankings, belts, share map, other promotions (free) |
| Gym | training schedules, coach assignment, talk (10 AP, once a month), special training (20 AP), practice match |
| System | save/load, options, years until the Final Series, how CPU shows are shown |

Other costs: a present on a wrestler's 20th birthday 10 AP, returning White Day gifts 10 AP
each (*text* 0x4f65c8, 0x4f0be0).

### 1.4 The Final Series - the goal
*From the code* (0x21ad34, 0x20a770-0x20a8c0, 0x25e598) *and text* (0x4f8c60-0x4f9468).
- Held in **March**. You choose the years until the first one at New Game (default 5) and can
  change it in System until that year; afterwards it comes back **every 4 years**.
- Three divisions (openweight singles, openweight tag, junior singles), one wrestler per
  division, four days: three league days, then the finals. Points are summed per promotion.
- Accepting the early invitation pays **300 AP**; you cannot hold your own shows that month.
  Each division entered pays **50 AP**, plus a bonus for finalists.
- 1st / 2nd / 3rd: share **+5 / +2 / +1 %** in every prefecture, +100 / +50 / +25 AP, and
  +150 / +75 / +30 popularity per wrestler.
- **Staying out costs 10 % of your share in every prefecture**, and any show of your own that
  month draws ×0.7.

### 1.5 Endings
*From the code* (0x20a618, 0x22e828, 0x22eb48).
- **Best ending:** your promotion wins the Final Series. **Normal ending:** you took part but
  didn't win. **None:** you didn't take part. Each is shown once (flags 0x800 / 0x40).
- The staff roll shows up to 10 of your wrestlers with **trust ≥ 500 and affection ≥ 800**, by
  rating. The top one plays her personal ending: scene 136 (fond) if her affection is above 800,
  else 135. With nobody qualifying there is no personal ending.
- Play continues afterwards (*inferred*: the next Final Series is set 4 years later and the
  secretary says "revenge in 4 years").

### 1.6 Bankruptcy
*From the code* (0x2f3984, 0x2103c0-0x2106e4).
- Each month that starts with **AP below 0** counts; a month at 0 or above resets the count.
  The secretary warns after the first and second; **the third month in a row is bankruptcy**.
- It is not game over: the promotion restarts. Every wrestler, guest, coach, belt and
  partnership is gone, facilities return to level 0, the TV deal ends, **share is halved in
  every prefecture**, and AP goes back to the starting amount. The founding share boost is
  applied again (10 random prefectures instead of 20).
- Selling facilities refunds 70 % (§5.4): do it before the third month.

---

## 2. Money

### 2.1 AP
**AP is the only currency. 1 AP = ¥100,000** (*from the code* 0x2888cc, 0x301c68). The books are
kept in yen; at month end `AP += (income − expenses) / 100,000`. AP is clamped to ±999,999.

Starting AP: **5000 / 4000 / 3000** at difficulty 1 / 2 / 3, **+1500** with the president skill
Assets (*from the code* 0x2106e8, 0x210760).

### 2.2 Income
*From the code* (0x288c60-0x289258, 0x2f1360-0x2f14d0, 0x20ffe8-0x2100bc).

| Source | Amount |
|---|---|
| Tickets | **¥4,000 per spectator** (1 AP per 25 people) |
| TV rights, monthly | cable or local 10 AP, national late-night 25, prime time 50, golden time 100 |
| Merch shop / restaurant, monthly per prefecture | 1-9 AP by your share there (table below); in a "fever" month merch ×10, restaurant ×15 |
| Sponsors (up to 4) | each **(popularity − 600) / 5 AP** a month; a Connected wrestler counts +300 popularity |
| Showbiz work | movies, CMs, photo books, CDs (§9.4) |
| Concerts | top wrestler's popularity × 3 dice / 100 AP (§3.2) |
| Awards | MVP 300, rookie 150, best singles bout 150, best tag 100, best junior 100 AP |
| President skill Wealth | +50 AP a month |

| Your share in the prefecture | < 8 % | 8 | 15 | 22 | 29 | 36 | 43 | 50 | ≥ 57 % |
|---|---|---|---|---|---|---|---|---|---|
| Shop income, AP / month | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |

Fever months (*from the code* 0x212910, 0x212bb0): a goods boom comes 4 % a month and a restaurant
on TV 5 %, each announced 2 months after its roll. **The goods boom is bugged:** it pays each merch
shop a flat token amount (about 0 AP) instead of ×10. Food poisoning (1 %) closes one restaurant.

### 2.3 Expenses
*From the code* (0x2892b0-0x28987c, 0x288e70-0x288f84).

| Cost | Amount |
|---|---|
| **Venue rent, per show day** | capacity × ¥4,000 × rate %, **whether or not it fills** (§4.1) |
| Salaries | annual salary / 12 each month |
| **Running cost** | promotion rating / 100 AP a month (rating 3000 → 30 AP) |
| Coaches | about 3 AP each a month |
| Overseas tours | 5 AP per touring wrestler |
| Guest and foreign wrestlers | 1-50 AP per appearance, by popularity |

The president skill Management cuts venue rent, running cost and tour cost by 10 %.

---

## 3. Share and popularity

### 3.1 Share
*From the code* (0x20e498, 0x20f268-0x20f888, 0x289920-0x289ab4).
- Each of the **48 areas** (the 47 prefectures, Hokkaido split East/West) has 100 % of share
  split among the promotions; the rest is unclaimed. A gain comes from the unclaimed part first,
  then **from rivals, the biggest first**. Share is zero-sum.

| Event | Share change |
|---|---|
| Founding show | home prefecture **+5 %**, the rest of its region +1 %, 20 random prefectures +1 % |
| Each show day | **+1 %** there, **+2 % more** if sold out, +1 % more at 95 % full |
| No show in a prefecture | **−1 % every 6 months** |
| TV | national slots +1 % everywhere every 3 months; cable every 6 months; local +1 % in its region every 3 months |
| Autograph session (50 AP) | +1 to +3 % in one prefecture |
| Concert (100 AP) | +1 to +4 % in one prefecture |
| Final Series 1st/2nd/3rd | +5 / +2 / +1 % everywhere |

**Advertising** adds share **for the current month only** (it is added when attendance is
worked out, then cleared):

| Ad | Cost | Effect this month |
|---|---|---|
| TV commercial | 200 AP | +10 % in every prefecture |
| Print | 100 AP | +5 % in every prefecture |
| Radio | 50 AP | +2 % in every prefecture (in the code; the player's menu text lists only the other three) |
| Ad truck | 50 AP | +5 % in one prefecture |

### 3.2 Autograph sessions and concerts
*From the code* (0x2fe5c0, 0x2fe880).
- **Autograph session** (50 AP, up to 3 wrestlers): each gains about +20 popularity; the
  prefecture gains share = their total popularity / 100, clamped to 1-3 %.
- **Concert** (100 AP, up to 3, takes a schedule slot): about +30 popularity each; share
  +1 to +4 %; income = top wrestler's popularity × (three dice) / 100 AP. The dice are 1-6, one
  side more per Singer, one less per Tone-Deaf (5-7). A 1000-popularity singer averages about
  105 AP, so a concert roughly pays for itself and the share is the profit.

### 3.3 Wrestler popularity
*From the code* (0x23b640, 0x238860, 0x23cc40).
- **Popularity = rating** (×1.2 with Popular, ×0.8 with Plain) **+ a variable bonus + a fixed
  bonus** (each up to 2000).
- **Rating** = the average of the 15 stats + 10 per learned move.
- The variable bonus comes from events: media work (+120 to −10 by result), autograph +20,
  concert +30, awards (+100, MVP +200), Final Series placings. It **decays 10 % every month** (*from the code* 0x23cc40). A
  scandal halves popularity.
- **Winning or losing ordinary matches does not change popularity** (no such code was found).
  Matches give experience (§8.6) and feed the year-end awards.

---

## 4. Shows

### 4.1 Venues and rent
*From the code* (venue table 0x4e02e0, 0x50 bytes each; rent 0x288e70).
- **384 venues, 8 per prefecture.** Capacity 500-55,000; most prefectures top out at
  4,000-5,500. The big ones: Fukuoka 55,000; Tokyo 50,000; Osaka 50,000; West Hokkaido 50,000;
  Aichi 45,000; Saitama 40,000 and 30,000; Hiroshima 30,000 (outdoor). 79 venues are outdoor.
- **Rent = rate % of a sell-out's takings, charged on capacity.** The rate is therefore the
  **break-even attendance**:

| Capacity | ≤ 1,000 | 1,001-2,000 | 2,001-3,000 | 3,001-5,000 | 5,001-7,000 | 7,001-10,000 | 10,001-29,999 | ≥ 30,000 |
|---|---|---|---|---|---|---|---|---|
| Indoor | 30 % | 33 % | 41 % | 54 % | 62 % | 71 % | 76 % | 85 % |
| Outdoor | 25 % | 26 % | 34 % | 43 % | 56 % | 62 % | 72 % | 85 % |

A dome must be 85 % full to break even; a small hall makes money at 30 %. Outdoor venues are
cheaper but weather hits their crowds (§4.3).

### 4.2 Show formats
*From text* (0x4edb08-0x4ede38).
- **Tour:** one venue a day, any prefectures. **Single venue:** every day at one venue.
- Match formats: normal card, league (3+ days), tournament (2+ days), special matches, team
  matches, one-night tournaments, open leagues.
- **A show needs six available wrestlers**; one that drops below six is cancelled.
- Manual, semi-auto or auto matches, watched or skipped. **The box-office code never reads how a
  match was played**: only the result and the card matter.

### 4.3 Attendance
*From the code* (0x26ce90 = 0x26bc48 + 0x26c318, then 0x26c8f8). A crowd is a **walk-up part**
plus a **core part**, then modifiers.

**The card's draw.** Each wrestler's popularity is lowered by 200 if she is foreign and by 100
if she belongs to another promotion. A **star** is a wrestler at 1100 or more. With the top four
p1 ≥ p2 ≥ p3 ≥ p4, the card's draw is `E = p1 + p2/2 + p3/4 + p4/4`, times a star bonus: 4
stars ×1.1, 5-6 ×1.2, 7 ×1.3, 8 ×1.4, any other count ×1.5.
That last case includes 0-3 stars, which looks like a **bug**: the CPU's version of the same
table gives ×1.0 for 0-3 stars (*from the code* 0x26b6b8 vs table 0x4dcb68).

**Walk-up crowd** (0x26bc48):
```
walk-up = (share% / 4 + 2) × K × E / 10 × rest × weather   (+10 % with a hometown wrestler)
          + 100, at most half the capacity
```
- **share:** on tour, your share in that prefecture; in a single-venue run, 60 % that
  prefecture + 40 % its region.
- **K:** 1.0 with up to 2 active promotions, 1.1 / 1.2 / 1.3 with 3 / 4 / 5+.
- **rest (tour):** months since your last show in that prefecture: **1 → 25 %, 2 → 50 %,
  3 → 75 %, 4+ → 100 %**.
- **rest (single venue):** by the number of days and the venue size:

| Days | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| ≥ 30,000 | 100 | 70 | 50 | 30 | 10 | 10 | 10 | 10 |
| 10,000-29,999 | 100 | 80 | 70 | 60 | 50 | 40 | 30 | 20 |
| 3,000-9,999 | 100 | 80 | 70 | 60 | 50 | 50 | 40 | 40 |
| 1,000-2,999 | 100 | 90 | 80 | 70 | 70 | 60 | 50 | 50 |
| < 1,000 | 100 | 90 | 90 | 80 | 80 | 70 | 70 | 60 |

- **weather** (rolled each day by season): indoors 50-100 %, outdoors 20-100 %. Winter is worst
  (snow and blizzards: outdoor 40 % / 20 %); June and summer have the most storms.

**Core crowd** (0x26c318):
```
core = (total card popularity / 50 + fans) × matches × main event × repeat × rest × quality
```
- **fans:** for each top-four wrestler at **800+ popularity**, `(popularity − 750)² / 200`
  (capped at 1500): 800 → 12, 1000 → 312, 1200 → 1012, 1500 → 2812. Below 800 she brings no
  fans. **This term dominates once you have stars.**
- **matches on the card:** 0-1 → 50 %, 2 → 70 %, 3-4 → 100 %, 5-6 → 120 %, **7+ → 140 %**
  (counting stops at the first empty slot).
- **main event:** the last match's average popularity against the top four's average: below
  40 % → 60 %, rising 10 points per 10 % of the ratio, up to **140 % above 110 %**. A singles
  main event between your two most popular wrestlers scores highest.
- **repeat:** the same main event on other days this month: 0-1 → 100 %, 2 → 90 %, 3 → 80 %,
  4+ → 70 %.
- **quality:** each wrestler on the card scores by rating: < 400 → 1, < 600 → 1.5,
  < 900 → 2, < 1100 → 2.5, < 1300 → 3, < 1500 → 4, else 5; quality = 1 + Σ(score − 1) / 10.
  Ten wrestlers rated 900-1099 give ×2.5.

**Modifiers** (0x26c8f8):
```
crowd = (walk-up + core) × title × random(85-115 %)
        × 0.7 if you sat out the Final Series this month   × 1.05 with Publicity
        × (0.4 + share% / 200 × K)   + 200,   at most 105 % of capacity
```
- **title:** with any belt on the line at least ×1.05; with two, (prestige₁ / 1000) ×
  (prestige₂ / 1000), e.g. 1200 and 1100 → ×1.32.
- **share factor:** 0.40 at 0 % share, 0.65 at 50 %, 0.90 at 100 %.
- Labels: at capacity "sold out", 95 % "packed", 90 % "full". Only a sell-out and 95 % add
  share (§3.1).

---

## 5. Rating, TV, belts and facilities

### 5.1 Promotion rating
*From the code* (0x2109f8; some weights *inferred*).
```
rating = Σ roster popularity (at least 100 each; the top wrestler ×1.5 if 800+)
       + half the prestige of each held title   + half each overseas partner's value
       + HQ level × 3000   + gym and dorm levels × 300
       + 5 per merch shop  + 15 per restaurant
```
Rating sets the **running cost** (rating / 100 AP a month) and gates TV (3000) and belts.

### 5.2 TV
*From the code* (0x212f60, 0x2132b0-0x213a70).
- **Offer:** rating ≥ 3000 and a wrestler at 600+ popularity. If 19 of your last 20 shows were in
  your home region, the offer is a local station, otherwise cable. "No downside to accepting":
  it is money and share.
- Contracts run **6 months**. Renewal score = **(sum of the top three popularities) / 10 +
  random 0-99**:

| Current slot | Cancelled | Downgraded | Renewed | Upgraded |
|---|---|---|---|---|
| Cable / local | < 201 | - | 201-280 | ≥ 281 → late-night |
| Late-night | < 201 | 201-280 → local | 281-340 | ≥ 341 → prime (after one "nearly" renewal) |
| Prime | < 251 | 251-320 → late-night | 321-380 | ≥ 381 → golden (after one "nearly" renewal) |
| Golden | < 251 | 251-380 → prime | ≥ 381 | - |

- Golden time needs the top three at about 1100+ each. A national deal also ends if the rating
  falls below 3000 or no wrestler is at 600+. A scandal pulls the show for 2 months.

### 5.3 Belts
*From the code* (table 0x4fe718; requirement columns *inferred* from text 0x4fde98).

| Belt | Cost | Rating | Wrestlers |
|---|---|---|---|
| 1st | 1000 AP | 2000 | 6 |
| 2nd | 3000 AP | 3000 | 8 |
| 3rd | 5000 AP | 4000 | 10 |

New belts start at prestige 0; how prestige grows was not found. A belt not defended for 5
months brings a warning, and at 6 months it is stripped (*text* 0x4f7db0). Partner promotions'
belts have prestige 500-1100.

### 5.4 Facilities
*From the code* (cost table 0x4dd488, effects 0x4dd500). **Selling a level refunds 70 %.**

| Facility | Cost of each level | Effect at level 0, 1, 2, ... |
|---|---|---|
| HQ building (max 3) | 5000, 10000, 30000 | rating +0 / +3000 / +6000 / +9000 |
| Dorm (max 5) | 500, 1000, 3000, 5000, 10000 | wrestler limit 6 / 8 / 10 / 12 / 14 / 16 |
| Gym (max 4) | 500, 1000, 1500, 2000 | coach limit 1-5; 2 special trainings a month from level 2 |
| Tour bus (max 4) | 500, 1000, 1500, 2000 | trust +0 to +4 a month; injuries −5 % per level |
| Merch shop (one per prefecture) | 500 | income by share (§2.2) |
| Restaurant (one per prefecture) | 700 | same table; fever ×15 |

The HQ's +3000 rating also adds 30 AP a month of running cost: buy it when you need the rating.

**Overseas partnerships** send foreign wrestlers and add to the rating. Cost 600-1100 AP by
promotion, ×1.5 if it already has a partner, ×0.8 with Worldly (*from the code* 0x2cf410).

---

## 6. Recruitment

### 6.1 Talent grades
*From the code* (roster record +0xdc). Every wrestler has a **talent grade 0-5, 0 best**: the
series' stars are grade 0. Talent scales all training (130 % for grade 0 down to 80 % for
grade 5, §8.2). Rookies appear by debut year and can be found until 2 years past their starting
age (and under 20). After that they probably stay free agents until 27 (*inferred*).

### 6.2 Tryout (1-99 AP)
*From the code* (0x2e1d98; debug 0x4f2ff8). Once a month; needs a free dorm place. The AP is
paid up front. There is no signing roll: you choose whether to hire.
```
score = AP − 30 + 5 × (6 − roster size) − random(1-100)
```
The score picks a row of grade odds; the game then takes a rookie of that grade, or a worse one
if none is left (never a better one).

| Score | ≥ 80 | 70-79 | 60-69 | 50-59 | 40-49 | 20-39 | < 20 |
|---|---|---|---|---|---|---|---|
| Chance of grade 0-2 | 30 % | **38 %** | 33 % | 28 % | 23 % | 18 % | 13 % |

The top row is worse than 70-79: probably a typo in the data.

- **Up to `50 + 5 × (roster − 6)` AP the score is always below 20**, so the first candidate is
  the same as with 1 AP. Above that, each AP shifts the odds by 1 %.
- **A second candidate** needs 2+ free dorm places and a second roll of the same formula ≥ 0;
  each AP adds 1 % to the chance of one.
- Chance of a grade 0-1 rookie as the first candidate:

| Roster | 1-30 AP | 50 AP | 70 AP | 90 AP | 99 AP | 2nd candidate at 99 AP |
|---|---|---|---|---|---|---|
| 1 | 3.0 % | 3.9 % | 5.6 % | 8.3 % | 9.4 % | 94 % |
| 6 | 3.0 % | 3.0 % | 3.6 % | 5.0 % | 6.1 % | 69 % |
| 10 | 3.0 % | 3.0 % | 3.0 % | 3.6 % | 4.1 % | 49 % |

**Spend 1 AP or 99 AP.** 99 is worth it with a small roster and 2+ free dorm places (two
candidates most of the time). With a big roster a tryout is a lottery whatever you pay.

### 6.3 Rookie scouting (50 AP)
*From the code* (0x2e2f40, 0x2e34f8). Once a month, in one region; each further region costs
another 50 AP. Three rolls, each finding the best available rookie of the rolled grade or worse,
**born in that region**:

| | Grade 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Normal | 15 % | 20 % | 25 % | 20 % | 10 % | 11 % |
| With Network | 30 % | 40 % | 31 % | - | - | - |

**Visit:** success 60 % (70 % on a return visit), ×0.7 Shy, ×1.4 Friendly, ×1.5 Eloquence. A
signing probably also costs 10 AP per year of her age (*inferred* from the report text
0x4f4db0). Kanto has the most rookies (16 of the 79), Hokkaido the fewest (4). Foreign
wrestlers are never scouted.

**Scouting beats any tryout for quality:** 35 % a roll for grade 0-1, against at most 9 % for a
99 AP tryout.

### 6.4 Transfers (rival wrestlers and free agents)
*From the code* (0x2e4400; debug 0x4f3390-0x4f3448). Once a month.
- **Minimum cost** = `clamp(popularity, 350-1500) + clamp(rating, 350-1500) / 2 − 400`
  (125-1850 AP). It does not change the odds.
- **Added AP** (1-99) is what counts:
```
target = rating/20 + trust'/10 + popularity/30 + 2 × your roster size
         + 30 / 20 / 10 if she is her promotion's #1 / #2 / #3 by rating
   trust' = her trust in her promotion ×1.5 Loyal, ×0.7 Wanderer, ×1.5 Shy, ×0.7 Friendly
roll   = (added AP + random(1-100) + a quarter of the AP added last time you failed with her)
         × 1.5 with Eloquence
success if target < roll
```
- **Automatic failure:** she holds a belt, is entered in the EX League or the Final Series, or is
  touring abroad. If her promotion's president has Charisma, 30 % of successes are cancelled.
- **A failure lowers her trust in her promotion** by `(1050 − trust) / 4 + added AP`, so each
  later attempt is easier.
- After signing, her trust in you is `1150 − her old trust`: wrestlers unhappy at a rival love
  their new home.
- **Cost:** the success message shows minimum + added AP. The CPU, using the same code, pays only
  the added AP when it fails. The player very likely pays the same way (*inferred*: the
  player's deduction was not found).

| Example target | Target | +50 AP | +99 AP | +99 with Eloquence |
|---|---|---|---|---|
| Weak free agent (rating 450, trust 500, pop 300; your roster 8) | 98 | 52 % | 100 % | 100 % |
| Mid free agent (700 / 500 / 600; roster 10) | 125 | 25 % | 74 % | 100 % |
| A rival's #3 (800 / 600 / 700; roster 10) | 153 | 0 % | 46 % | 97 % |
| A rival's ace (1200 / 800 / 1200; roster 12) | 234 | 0 % | 0 % | 43 % |

The same ace with 99 AP every month: 0 % → 6 % → 26 % → 51 % → 69 % (with Eloquence 43 % →
78 % → 92 % → 100 %).

**How much to add:** each AP is +1 % (+1.5 % with Eloquence) until success is certain at about
`target` AP; more is wasted. Prefer targets with low trust, Wanderer or Friendly, outside their
promotion's top three, and keep your own roster small while poaching.

### 6.5 Guests, partners and coaches
*From the code* (0x2c4908, 0x2c4a10) *and text* (0x4ee600, 0x4ee748).
- **Guest booking** of a freelancer for N months: `2 × ((popularity + rating/4 − 400) / 12) × N`
  AP, paid when you accept. The booking ends if she signs elsewhere.
- **Overseas partnership** (foreign wrestlers): see §5.4.
- **Coaches:** 100 AP to hire, limited by the gym level (§8.5).

---

## 7. Keeping wrestlers

### 7.1 Salaries and renewals
*From the code* (0x3013b0, 0x302740-0x302b68).
```
demand = (max(rating, 400) × max(popularity, 300) + previous × 3/100) / 10 × (100 + greed %)
         at least 90 % of the previous salary, at least 12 AP a year
```
Greed is a per-wrestler value from −50 % to +50 %. You can make up to 3 offers:

| Offer | Result |
|---|---|
| ≥ 111 % of the demand | satisfied: **trust +200, affection +100** |
| 96-110 % | normal |
| 70-95 % | unhappy: **her trust is capped at 850 for good** |
| < 70 % | very unhappy; after the third such offer she probably leaves (*inferred*) |

### 7.2 Trust, affection and morale
*From the code* (0x23f4d8-0x23f5f8). Each wrestler has **trust** (in the promotion), **affection**
(for the president) and **morale**, each 0-1050. Trust matters most:
- **Below 100:** 50 % a month she refuses practice (§8.4).
- **40 or less:** a "thinking of leaving" warning. **Below 6:** 10 % a month she leaves.
- Low trust makes her a target for CPU poaching (§10).
- **800+ with affection 800+:** private events and the ending (§9).

Trust rises with good renewals, vacations, a tour bus and successful talks; it falls with
failed special training, firing coaches and unhappy contracts.

**Talk** (Gym, 10 AP, once a month): praise, scold or encourage, each succeeding 70 % (84 %
with Eloquence); **mediate** clears a grudge 20 % (40 %). The amounts by which trust, affection
and morale change are **per wrestler** (from her roster record), so the same verb works
differently on different wrestlers; Mysterious wrestlers react randomly (*from the code*
0x2083c4-0x2083a0, 0x280e78, 0x23b430).

### 7.3 Retirement
*From the code* (0x23ac60, 0x23af88, 0x235fa8).
- **Age:** at 30 or older she always retires. Under 30, only in decline, holding no belt, and with
  her rating below 80 % of her best (*from the code* 0x23ac60).
- **Injury:** an injury of level 5 ends her career after hospital (§8.6).
- **Urging retirement** (only past her peak): she accepts if her current stat total is below
  1.4 × her potential total: certainly when 3000+ below, otherwise with chance (difference) / 30 %.
  A wrestler who grew well past her potential refuses.
- A retired wrestler may offer to become a coach.

---

## 8. Training and growth

### 8.1 Stats
*From the code* (0x236eb8-0x237740, 0x2379a8, 0x238860).

| # | Attack / defence (cap 2000 each, attack + defence ≤ 3199) | # | Basic (cap 1200 each, total ≤ 4699) |
|---|---|---|---|
| 0 / 1 | Throws | 10 | Strength |
| 2 / 3 | Holds | 11 | Dexterity |
| 4 / 5 | Power | 12 | Stamina |
| 6 / 7 | Strikes | 13 | Recovery (lowers injuries) |
| 8 / 9 | Aerial | 14 | Speed |

Grades 0-15 are thresholds at 100, 200 ... 800, 950, 1100, 1250, 1400, 1550, 1750, 1950.
**Rating = average of the 15 stats + 10 per learned move**, and popularity follows rating (§3.3).

### 8.2 Age phases
*From the code* (0x23c1a0, tables 0x4bf7a0-0x4bf830). Years since a wrestler's starting age put
her in a phase; her growth type and length (per wrestler) set how long each lasts. Growth
always lasts **4 years** (phases 0 + 1); the type decides how much of that is phase 0, the
length how long the peak and decline last.

| Phase | 0 fast growth | 1 growth | 2 peak | 3 decline | 4 late decline |
|---|---|---|---|---|---|
| Stat cap | potential +200 | +200 | +0 | −300 | −600 |
| Natural growth per month (per 300 below the cap) | +6 | +4 | 0 | −4 per 300 above | −6 per 300 above |
| Training bonus | +80 | +40 | 0 | −40 | −80 |
| Match EXP bonus | +3 | +2 | +1 | +1 | 0 |

The cap is **not a hard limit**: training adds on top of it. Near the cap, only natural growth
stops. In decline, only stats 300+ above the lowered cap shrink.

### 8.3 Training power
*From the code* (0x236608). Each wrestler has one training value per month, and **each of the 4
schedule slots spends all of it**:
```
time  = 3 × (30 − matches this month) × coach (1.0 none, 1.3-1.5 hired, 1.4 president)
        × 2 if special training succeeded, × 0.5 if it failed     × 1.1 Hard Worker
power = (match EXP + time + phase bonus) × talent (130 / 120 / 110 / 100 / 90 / 80 % for grade 0-5)
        × injury (100 / 80 / 50 % at level 0 / 1 / 2)   ÷ 2 in a slump
per slot = (power + 2) / 4
```
Hospitalised wrestlers don't train.

| Situation (talent 100 %, no matches) | Per slot |
|---|---|
| Phase 0, no coach | 43 |
| Phase 0, best coach | 54 |
| Phase 0, best coach, special training success | 88 |
| Phase 2, best coach | 34 |
| Phase 4, best coach | 14 |

### 8.4 Schedules
*From the code* (0x236a4c-0x2377ac; pointer table 0x3cb9d8). Four slots a month.

| Option | Where the points go |
|---|---|
| Individuality (default), Coach growth | spread over every group by fixed small percentages |
| One basic stat | 60 % to it, 10 % to each other basic |
| All basics | Strength, Dexterity and Stamina only (Recovery and Speed get nothing, as coded) |
| Attack / Defence | 80 % over the five attack (defence) stats, 4 % to each basic |
| A style (Throws / Holds / Power / Strikes / Aerial) | that style's attack and defence + one basic (Strength / Dexterity / Stamina / Recovery / Speed) |
| Weakness | the lowest stats in each group |
| Rest | nothing; helps injuries heal |
| New move / Move level | move EXP instead (§8.7) |

**Every share is rounded down separately**, so options that split points many ways lose them.
Points gained from one slot:

| Power per slot | Individuality / Coach | All basics | One basic | Attack | Defence | Weakness | A style |
|---|---|---|---|---|---|---|---|
| 20 | 9 | 20 | 20 | 16 | 14 | 18 | 20 |
| 33 | 15 | 32 | 31 | 29 | 28 | 24 | 32 |
| 50 | 47 | 49 | 50 | 50 | 47 | 45 | 49 |
| 80 | 68 | 80 | 80 | 79 | 78 | 78 | 80 |

**The default Individuality wastes about half the points below 40 per slot.** Use a style or a
single stat.

**Refusal:** a wrestler with trust below 100 refuses practice 50 % of months (taking 2 slots).
Keep trust at 100+ and it never happens.

### 8.5 Coaches and special training
*From the code* (0x2363a0, 0x236608, 0x282ef0, 0x2120e0; coach table 0x466cd0).
- A coach **multiplies training time** by 1.3-1.5 and **raises the trainee's caps** to the
  coach's own stats +100 (in phases 0-1). A specialist coach lets a low-potential wrestler grow
  well past her potential.
- A wrestler can coach: ×1.0-1.4 by her best rating, ×1.5 with Mentor; her stats set the caps.
  The president coaches at ×1.4.
- **Special training** (20 AP): needs an assigned coach; **1 a month, 2 with gym level 2+.**
  Success **65 + (coach ability − 600) / 50 %** (79-83 %) doubles that month's time term;
  failure halves it. Do it before starting practice.
- Risks next month: 5 % slump (half training, no special training); after a failure, with trust
  800 or less, 15 % she goes missing from practice.

### 8.6 Matches and injuries
*From the code* (0x23e308, table 0x4c0738; 0x23e668).
- **Match EXP** by result and the opponent's rating minus hers:

| Rating difference | ≥ 201 | 151-200 | 101-150 | 51-100 | −49 to 50 | −99 to −50 | −149 to −100 | −199 to −150 | ≤ −200 |
|---|---|---|---|---|---|---|---|---|---|
| Win | 16 | 8 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
| Draw | 8 | 6 | 4 | 3 | 2 | 1 | 0 | 0 | 0 |
| Loss | 3 | 3 | 3 | 2 | 1 | 0 | 0 | 0 | 0 |

  Honest wrestlers gain more from wins (up to 20) and can lose EXP on losses; Rebels gain more
  from losses. Each match also costs 3 × coach of training time, so **a win over a stronger
  opponent pays off; many matches against weaker ones slow growth.**
- **Injury chance per match** = 0.2 % × (heavy moves taken − (Recovery grade − matches this
  month)), at most 3 %. ×0.5 Durable or an opponent with Control; ×2 an opponent with Brutal;
  −5 % per tour bus level; ×0.8 Bodywork. Severity +1 (88 %), +2 (10 %), +3 (2 %).
- **Injury levels:** 1-2 she plays hurt (training ×0.8 / ×0.5); 3 hospital for 1 month; 4-5
  hospital for 3 months; level 5 ends her career. Levels 1-2 heal with chance
  15 × (2 × rest slots + matches) % a month. A jump of 2+ levels in a month costs 100 on 1-2
  stats and some trust, morale and affection.

### 8.7 Moves and skills
*From the code* (0x2377c0-0x237e18; tables 0x4c0cc0, 0x4c0ce8).
- Each move-practice slot adds the full training power as move EXP. A new move of level 1-9
  needs 15, 30, 45, 65, 85, 105, 130, 155, 180 EXP; Studious wrestlers need 80 %. Changing the
  practiced move discards the EXP. Each learned move adds 10 to the rating.
- **Skills (Popular, Hard Worker, Durable ...) are innate.** Nothing in the code writes them;
  they cannot be learned or lost.

---

## 9. Story and events

### 9.1 No fixed plot
*From the code* (0x2009a0, 0x230af8) *and the scripts* (all 242). Each wrestler has about 108
short scenes (scouting, joining, training, media, injuries, retirement, endings ...), always
the president alone with her. **The code decides when each scene plays.** The scripts contain
no logic: they only branch on a result the code computed (did the scouting succeed?) and they
cannot change stats, flags or the roster. What happens after a scene is applied by the code.

- **Fixed:** the opening, the calendar events (§1.2), the Final Series and the endings.
- **Random:** nearly every personal event, as a percentage roll once stat thresholds are met
  (§9.4).
- **Your choices:** who you sign, train, talk to, send on vacation, release or urge to retire,
  and yes/no answers to the secretary's offers.

Each game event always plays the same scene number; only a few have random variants (entrance
2, victory 3, award 2, tournament win 2).

### 9.2 The opening
The secretary, **Kiriko Inoue**, explains that the promotion has no wrestlers, a show needs six,
and a late founding show hurts the business. That is the whole set-up; after it she only reads
the monthly news.

### 9.3 New game settings
*From text* (0x46ba28-0x46be80). Players and number of promotions, years until the Final
Series, difficulty, **era** (Dawn of Joshi Pro: few domestic talents and help from abroad; a
warring-states era of rising and falling promotions; Dawn of a New Era: a mature scene around
New Japan Joshi Pro), two president skills (§11), name, logo and home prefecture.

### 9.4 Monthly events
*From the code* (0x2f3aac and the checks it calls; debug strings 0x4bfaf8-0x4c0430). Checked
each month for each of your wrestlers.

| Event | Conditions | Chance a month |
|---|---|---|
| Fan club formed | popularity ≥ 600 | 30 % |
| Fan club grows / shrinks | by club size and popularity | 6 % (9 % Popular, 3 % Plain) / 15 % |
| Sponsor | popularity ≥ 1200 (≥ 900 with Connected), no sponsor; only the most popular qualifier | 10 / 5 / 2 / 1 % with 0 / 1 / 2 / 3 sponsors |
| CM or movie offer | popularity ≥ 1000 (a movie takes the whole month) | 5 %; +3 % each for Singer, Actor, Connected, Salesmanship; +5 % with a sponsor; −3 % for Plain, Tone-Deaf, Bad Actor (1-15 %) |
| Photo book / CD | popularity ≥ 800 | 5 % (+5 Alluring / Singer) |
| One-day police chief | morale and popularity ≥ 600; highest affection | 5 % |
| First pitch (May) | popularity ≥ 1100 | 10 % (15 % Salesmanship) |
| School festival (October) | popularity ≥ 700 | 10 % |
| 20th birthday (gift 10 AP) | trust and affection ≥ 800 | certain |
| Valentine's Day (February) | trust and affection ≥ 850; top 3 by affection | certain |
| **Private event 1** | age ≥ 18, trust and affection ≥ 800; highest affection | 10 % |
| **Private event 2** | after event 1, age ≥ 20, trust and affection ≥ 850 | 10 % |
| Slump | special training last month | 5 % |
| Refuses practice | trust < 100 | 50 % |
| Goes missing from practice | failed special training, trust ≤ 800 | 15 % |
| Leaves | trust < 6 | 10 % |
| Grudge | 5 % per match against that opponent (Leader halves it, Egotist ×1.5) | next month |

Media results: popularity / 100 + random 0-99 (+10 Actor / Alluring / Singer, −10 Bad Actor,
−20 Tone-Deaf for CDs) gives flop / so-so / hit / big hit / super hit, with popularity +120 to
−10 and up to 600 AP.

Promotion news: shop fever, restaurant on TV or food poisoning, deficit warnings and
bankruptcy, TV upgrades and cancellations, scandals, the EX League, belt rules, overseas
defences, alliances, invasions and the Final Series.

### 9.5 Romance and the event pictures
*From the code and scripts.* Each wrestler has two event pictures (the gallery's "Event Art"):
one in the **vacation** scene and one in the **private events**. Both private events need high
trust and affection (§9.4), so raise them with good renewals, talks and vacations. The same
wrestlers then appear in the ending's staff roll (§1.5).

### 9.6 Relationships
- **Grudges** start in matches (§9.4) and play a scene the next month. Mediation in a talk clears
  them (20 %, 40 % with Eloquence). The rival can be anyone she was booked against.
- **Factions are cut content.** The scripts have Revolution and Rebel faction scenes, but no code
  ever starts them (*from the code*: no creation site for office sequences 50-64).
- **Partner scenes** for specific pairs (Ishikawa with Ryuko, the Murakami twins, Muto with Yuki,
  ...) exist in the scripts, but no code plays them: they look unused (*from the code*).

---

## 10. Rival promotions

*From the code* (0x28f0c0, 0x28f178, 0x214318, 0x2e7cb8) *and text* (0x46a130).
- The CPU promotions include New Japan Joshi Pro (the big one: its TV deal is never cut) and
  smaller ones, each with a style.
- **Shows:** a CPU holds 3-8 show days a month (by type), tours only prefectures it hasn't
  visited for 4+ months, prefers its strongest prefectures, and books the venue nearest its own
  crowd estimate.
- **Invasions:** never in December. New Japan Joshi needs 12+ wrestlers and targets promotions
  rated 2000+ (5 % each); others need 10+. **If you invade a CPU, it retaliates: 70 % the next
  month, certainly the month after.** What an invasion changes was not traced.
- **Poaching:** a CPU with 1000+ AP and dorm space tries (25-80 % a month, more with a small
  roster). 90 % of the time it goes for a free agent; otherwise it picks among the **10
  lowest-trust** wrestlers of a promotion with 7+ wrestlers, adding 90 AP to the formula in
  §6.4. High trust, Loyal or Shy wrestlers, and your top three are the hardest to take.
  Whether your promotion can be targeted was not confirmed.
- CPU promotions can go bankrupt and restart.

---

## 11. President skills

You pick two at New Game (*from the code*, names 0x599298).

| Skill | Effect |
|---|---|
| **Eloquence** | scouting visits, transfer rolls and talks ×1.5 (talks 84 %, mediation 40 %) |
| Management | venue rent, running cost and tours −10 % |
| Bodywork | injuries ×0.8 |
| Coaching (Basics, Throws, Holds, Power, Strikes, Aerial) | the president can coach that style |
| Publicity | attendance ×1.05 |
| Salesmanship | more showbiz offers |
| Charisma | 30 % of rivals' successful transfers of your wrestlers are cancelled (if it covers your promotion; see Open questions) |
| Assets | +1500 starting AP |
| **Wealth** | +50 AP a month (beats Assets after 30 months) |
| **Network** | rookie scouting finds only grades 0-2 |
| Worldly | overseas partnerships ×0.8 |

For recruiting, take Eloquence and Network. For money, Wealth or Management.

---

## 12. Strategy summary

1. **Debut early** with six wrestlers: scouting (50 AP) for quality, 1 AP tryouts to fill gaps.
2. **Train with focus:** a style or a single stat, not Individuality. Put the best coaches and
   special training on young (phase 0-1), high-talent wrestlers.
3. **Stars are everything:** popularity follows rating; fans grow with the square of
   (popularity − 750); the top three set TV. Concentrate on a few stars rather than raising
   everyone a little.
4. **Book venues you can fill.** The rent rate is the break-even occupancy: a dome needs 85 %,
   a small hall 30 %. A sell-out adds +3 % share instead of +1 %. Avoid outdoor venues in winter
   and the rainy season.
5. **Rotate prefectures:** 4 months between visits for a full walk-up crowd. Visit everywhere you
   hold share at least every 6 months.
6. **Build long cards:** 7+ matches, your top two in a singles main event, a title on the line,
   and don't repeat the main event.
7. **Grow share** with shows, autograph sessions and concerts; ads only in big months; shops only
   in prefectures where you already have high share (a 500 AP shop at < 8 % share takes 500
   months to pay back).
8. **Take TV** as soon as the rating reaches 3000; keep a 600+ wrestler.
9. **Keep trust high:** offer 111 % at renewal, buy a tour bus, send wrestlers on vacation. Low
   trust means refusals, poaching and departures.
10. **Poach patiently:** add exactly what reaches certainty, or 99 AP a month for stars.
11. **Always enter the Final Series**, and win it for the best ending. Have a high-affection
    wrestler ready for the personal ending.
12. **Watch the books:** three negative months is bankruptcy. Sell facilities (70 % back) first.

---

## Open questions
- **Gym timing:** the month change resets match EXP and the match count. If training happens
  before the month's shows, match EXP never counts. Check: compare growth after a busy month and
  an idle one.
- **Star bonus bug** (§4.3): break at 0x26b6b8 with a card of 0-3 stars.
- **Tryout cost:** a 1 AP and a 50 AP tryout with six wrestlers should give the same first
  candidate quality.
- The player's transfer deduction; whether CPUs can poach from you; your promotion's index for
  Charisma.
- Belt prestige growth; what an invasion changes; whether play continues after the ending.
- The month-by-month timeline is [timeline](timeline/); its research notes are in
  build/work/mgmt/timeline_*.md (not in git).
