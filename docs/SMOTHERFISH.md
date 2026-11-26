# Smotherfish guide

Smotherfish 1.6 is Stockfish (development version of 22 November 2026,
upstream commit `3e8fde75`) with one additional goal: to end the game with a
smothered mate. This guide explains the concepts, how the engine pursues them,
every option, how Smotherfish is tested and what was measured. The release
history is in [CHANGELOG.md](CHANGELOG.md); the day-by-day development log,
with every experiment, is in `notes/HANDOFF.md`.

## Contents

1. [Concepts](#1-concepts)
2. [How the engine works](#2-how-the-engine-works)
3. [Options reference](#3-options-reference)
4. [Recommended configurations](#4-recommended-configurations)
5. [Human mode (HumanElo)](#5-human-mode-humanelo)
6. [How Smotherfish is tested](#6-how-smotherfish-is-tested)
7. [Results](#7-results)
8. [Findings: what limits smothered mates](#8-findings-what-limits-smothered-mates)
9. [Testing your own changes](#9-testing-your-own-changes)

## 1. Concepts

### 1.1 Kinds of smothered mate

At checkmate, look at the squares next to the mated king.

| Kind | Definition | Counted by 1.6 |
| ---- | ---------- | -------------- |
| **Knight (classic) smother** | Every neighbour square holds one of the mated side's own pieces. Only a knight (or a pawn promoting to one) can give this mate. This is the textbook smothered mate. | Yes, the main goal |
| **Full smother, other piece** | Every neighbour square holds one of the mated side's own pieces except the square of the checking piece itself, for example a protected queen giving check from an adjacent square. | Only with `SmotherClassic false` |
| **Near ("all but one") smother** | As a full smother, but exactly one more neighbour square is empty or holds an attacking piece (it is covered, since the position is mate). | After the goal switch (section 2.4) |
| **Plain mate** | Any other checkmate. | No |

### 1.2 Why a smothered mate is hard to force

A smothered mate needs the defender's own pieces on every square around its
king. A defender who sees it coming can almost always avoid that arrangement,
so in most positions a smother cannot be forced at all. In 33 million human
Lichess games, knight smothers occur in about 0.07% of games, nearly all of
them after an unforced mistake.

Smotherfish therefore does three things:

1. It **proves** forced smothered mates when they exist and plays them, even
   over a quicker ordinary mate.
2. In **brutal mode** it values every ordinary mate below a smothered one, so
   the search prefers any smother it can see.
3. In **construction mode**, once the game is decided, it spends moves
   building the position a smother needs instead of mating at once, without
   ever giving back the win.

Against an opponent who plays well the game never becomes decided, and the
engine plays ordinary Stockfish.

## 2. How the engine works

### 2.1 The smother prover (`src/smother.cpp`)

An AND/OR proof search, separate from Stockfish's normal search:

- The attacking side may play checks (including sacrifices) plus a limited
  number of quiet moves that threaten a smother (`SmotherQuietMoves`, or
  `SmotherCrushQuiet` when crushing).
- A proof must hold against every defence. The defence that resists longest
  must end in a smothered mate; every other defence must lose to a strictly
  faster ordinary mate. A defender who avoids the smother is therefore mated
  sooner (with `SmotherStrict`, every defence must be smothered).
- Iterative deepening up to `SmotherMaxMoves` attacker moves (8; 16 when
  crushing), with its own proof table and node and time limits.
- A line that repeats a position already seen in the game or on the line is
  not a proof, so a defender cannot escape into a draw by repetition.
- By default it runs on a helper thread next to the search
  (`SmotherParallel`); when it proves a smother, its line replaces the search's
  move.

**Verification.** All 24,506 Lichess puzzles with the `smotheredMate` theme
(`notes/scripts/puzzles.py`): 24,482 are proved, every proof is checked move by
move, and none is wrong. The other 24 are smothers only in the puzzle's main
line, not forced under the rule above. On real human games, the prover finds
99% of the forced smothers that occurred.

### 2.2 Winning and brutal mode

- **Winning.** Once the previous search scored at least `SmotherWinCp` (+3
  pawns), the prover gets a larger share of the move's time
  (`SmotherWinTimePercent`).
- **Brutal mode** (`SmotherBrutal`, on by default). In the search, an ordinary
  mate counts as a certain win but below any smothered mate, so the engine
  prefers any smother it can see. When the engine is crushing (`SmotherBigCp`,
  +10 pawns, or a forced mate) the prover searches 16 moves deep with 3 quiet
  moves and more time (`SmotherBrutalTimePercent`, capped at 60% of the maximum
  time). With a forced mate in hand it may use `SmotherMatePercent` of the
  remaining clock.

### 2.3 Construction mode

Construction mode (`SmotherBuild`, on with brutal mode) starts once the
previous search scored at least `SmotherBuildCp` (+8 pawns) or found a forced
mate, and continues while the score stays at or above `SmotherBuildFloor` (+6
pawns), for at most `SmotherBuildMoves` (160) moves per game.

While it is on, the static evaluation at every node of the search is changed,
from our side's point of view, as

```
u' = floor + (u - floor) / 8 + construction_score * 8 cp      (for u >= floor)
```

so extra material above the floor counts only one eighth
(`SmotherBuildMaterialDiv`) and each construction-score point is worth 8
centipawns (`SmotherBuildWeight`). Below the floor the normal evaluation
applies, so the engine never gives back more than that. An ordinary mate
counts no more than the floor; a smothered mate keeps its real mate score.

The **construction score** (`src/smother.cpp`, `build_score`) rewards:

- the enemy king's box: points by the number of open squares next to it
  (`SmotherBuildRingTable`, 60 / 50 / 0 / -10 / -15 for 0 / 1 / 2 / 3 / 4+);
- the king in a corner or on an edge (`SmotherBuildWeights`);
- enemy pieces kept on the board, the possible blockers (`SmotherBuildKeep`,
  `SmotherBuildKeepNear`);
- a penalty per open square next to the king that we do not attack
  (`SmotherBuildEscape`);
- our queen and knights near the king, and, for knight smothers, a knight one
  knight move from a safe checking square (`SmotherBuildKnightCheck`, half for
  two moves).

Construction switches off before the 50-move rule (`SmotherSeekRule50`) and
when the budget is used up; the engine then mates normally.

### 2.4 The goal: which smothers count

- With `SmotherClassic true` (the 1.6 default) only knight smothers count as
  full smothers.
- `SmotherGoal` decides when near smothers count as well:
  - **Hybrid** (default): only full smothers for the first 80 construction
    moves, then near smothers too (`SmotherPartialAfter`). A full smother up to
    `SmotherFullExtra` (3) moves longer is still preferred to a near one.
  - **Full**: only full smothers.
  - **Near**: near smothers count from the start.

### 2.5 Human opponents

Human players resign lost games: on Lichess (33 million human games, November
2025 to October 2026), a blitz player 9-14 points down resigns on about 6% of
their moves, and only 23% of blitz games with an 8-point deficit end in mate.
When the GUI reports a human opponent (`UCI_Opponent`, for example "GM 2500
human Name", sent by lichess-bot), Hybrid therefore switches to near smothers
after `SmotherHumanAfter` (40) construction moves instead of 80. Against an
opponent resigning on the measured curve this kept every true smother and
doubled the total.

### 2.6 Pondering

While thinking on the opponent's time, the prover searches deep and without
limits (`SmotherPonderDeep`). At Elo 1500 with an opponent thinking at least
one second per move, this raised true smothers from 10.8 to 12.2 per 100 games.

## 3. Options reference

All options are standard UCI options; the defaults are what was measured best.

### 3.1 Main switches

| Option | Default | Meaning |
| ------ | ------- | ------- |
| `SmotherMate` | true | Run the smother prover at all. |
| `SmotherBrutal` | true | Brutal mode (section 2.2), the main switch for smother hunting. |
| `SmotherBuild` | true | Construction mode (section 2.3); only with `SmotherBrutal`. |
| `SmotherClassic` | true | Count only knight smothers as full smothers. `false` = any piece (1.5.1's aim). |
| `SmotherGoal` | Hybrid | Hybrid, Full or Near (section 2.4). |
| `SmotherStrict` | false | Require a smother against every defence (no faster-mate escapes). Finds far fewer proofs. |

### 3.2 Prover

| Option | Default | Meaning |
| ------ | ------- | ------- |
| `SmotherMaxMoves` | 8 | Longest proof in attacker moves outside crushing positions. |
| `SmotherQuietMoves` | 1 | Quiet attacker moves per proof line outside crushing positions. |
| `SmotherCrushMoves` | 16 | Longest proof when crushing (12 before 1.6). |
| `SmotherCrushQuiet` | 3 | Quiet attacker moves per line when crushing (2 before 1.6). |
| `SmotherTimePercent` | 25 | Prover time, percent of the move's planned time. |
| `SmotherNodes` | 5000000 | Node limit per proof (lifted with a forced mate in hand in brutal mode). |
| `SmotherParallel` | true | Prove on a helper thread next to the search. |
| `SmotherPonderDeep` | true | Unlimited proving while pondering. |

### 3.3 Winning and brutal mode

| Option | Default | Meaning |
| ------ | ------- | ------- |
| `SmotherWinCp` | 300 | Advantage (centipawns) from which the prover gets more time. |
| `SmotherWinTimePercent` | 100 | Prover time when winning, percent of the planned time. |
| `SmotherBigCp` | 1000 | Advantage from which the deep (crushing) prover runs. |
| `SmotherBrutalTimePercent` | 300 | Deep prover time, percent of the planned time (capped at 60% of the maximum). |
| `SmotherMatePercent` | 15 | With a forced mate in hand: share of the remaining clock per move. |
| `SmotherSeekRule50` | 60 | No seeking or construction once the 50-move counter reaches this (half-moves). |

### 3.4 Construction mode

| Option | Default | Meaning |
| ------ | ------- | ------- |
| `SmotherBuildCp` | 800 | Advantage (centipawns) at which construction starts. |
| `SmotherBuildFloor` | 600 | Advantage it never gives up while building. |
| `SmotherBuildMoves` | 160 | Most moves per game spent building (80 before 1.5). |
| `SmotherBuildWeight` | 8 | Centipawns per construction-score point. |
| `SmotherBuildMaterialDiv` | 8 | Extra material above the floor counts 1/N. |
| `SmotherBuildWeights` | 13,8,23,8,2,4 | Boxed, hole, corner, edge, knight-near and queen-near weights (tuned on game results in 1.3). |
| `SmotherBuildRingTable` | 60,50,0,-10,-15 | Points by open squares next to the enemy king (0 .. 4+), replacing the linear boxed and hole terms. Empty = linear. |
| `SmotherBuildKeep` | 11 | Points per enemy piece kept on the board. |
| `SmotherBuildKeepNear` | 2 | Extra points per enemy piece within two squares of its king. |
| `SmotherBuildEscape` | 4 | Points lost per open square next to the enemy king that we do not attack. |
| `SmotherBuildKnightCheck` | 16 | Points per knight one knight move from a safe checking square (half for two). 0 = 1.5.1. |
| `SmotherFullExtra` | 3 | After a near proof, how many moves longer a full smother may be and still be preferred. |
| `SmotherPartialAfter` | 0 | Near smothers count after this many construction moves (0 = as `SmotherGoal` decides; Hybrid uses 80). |
| `SmotherHumanAfter` | 40 | The same, against a human opponent (`UCI_Opponent`); 0 = as against computers. |
| `UCI_Opponent` | (empty) | Standard UCI opponent information from the GUI; only "human" or "computer" is used. |

### 3.5 Experimental (off by default)

| Option | Default | Meaning |
| ------ | ------- | ------- |
| `SmotherBuildDecoy` | 0 | Points when the one open square next to a cornered king is covered by a defender piece and our queen or rook can go there, guarded (Philidor's sacrifice). Under test (grid53). |
| `SmotherBuildModelScale`, `SmotherBuildModel` | 0, 17 coefficients | A learned linear model (log-odds of a knight smother within 10 of our moves) as the construction score, in points per log-odd. Peaks near 20, equal to the hand score. |
| `SmotherBuildNetScale` | 0 | A small learned network (`src/smother_net.h`: the 17 features and the 5x5 squares around the enemy king, 16 hidden units) as the construction score. 6 equals the hand score; 20 and more lose games. The UCI command `smothernet` prints its inputs and output. |
| `SmotherSteer`, `SmotherSteerFloor`, `SmotherSteerLines`, `SmotherSteerTime`, `SmotherSteerWonOnly`, `SmotherTrapDepth` | 0 / various | Trap steering: among near-equal moves, prefer the one that sets a smother trap. Did not raise the rate when used at all times and cost strength against strong opponents; kept for a planned test against human-like opponents. |
| `SmotherWinMargin`, `SmotherWinLines`, `SmotherWinTrapDepth`, `SmotherWinTrapNodes`, `SmotherWinSteerTime`, `SmotherMateDelays`, `SmotherMateSlack` | various | Trap-steering parameters in won positions and while a forced mate is in hand. |

### 3.6 Other

| Option | Default | Meaning |
| ------ | ------- | ------- |
| `HumanElo` | 0 | Play like a human of this rating (section 5). |
| `HumanBlunder`, `HumanBlunderPermille` | 0 | Real mistakes on top of `UCI_Elo` / `Skill Level` (percent / per mille of moves). |
| `Analysis Elo` | 0 | For "go infinite" analysis (for example DroidFish): above 0, limits analysis depth to what the `UCI_Elo` limiter uses at that rating. |

### 3.7 Removed options

1.6 removed 29 options from experiments that never beat the defaults; the
engine behaves exactly as with their old defaults (verified move for move on
300 positions): `SmotherShape*`, `SmotherPrep*`, `SmotherRobust`,
`SmotherEscapeMoves`, `SmotherEscapePercent`, `SmotherBuildVersion`,
`SmotherHold`, `SmotherFullFirst`, `SmotherBuildSurvive`,
`SmotherBuildSurviveCap`, `SmotherBuildStarve`, `SmotherBuildStarveAt`,
`SmotherBuildTime`, `SmotherBuildLmr`, `SmotherBuildDefLmr`, `SmotherBuildNmp`,
`SmotherBuildOwnKeep`, `SmotherBuildKnightSafe`, `SmotherBuildReady`,
`SmotherBuildDefRing`, `SmotherBuildExit`, `SmotherPartial` (use
`SmotherGoal Near`) and `SmotherSeek` (brutal mode seeks for up to 200 moves).
Their measurements are in `notes/HANDOFF.md`.

## 4. Recommended configurations

| Purpose | Settings | Notes |
| ------- | -------- | ----- |
| Knight smothered mates (default) | none | About 4 per 100 games against Stockfish 1500, 5 against Maia-3 1500. |
| As many smothered mates of any kind as possible | `SmotherClassic false`, `SmotherGoal Near` | 1.6 at 5+0.05: 67.6 of 100 games against Stockfish 1500 and 67.5 against Maia-3 1500 end in a smother (mostly near smothers), 51.8 against Stockfish 2600; defaults give 6.8. Knight smothers fall to 0.8. No losses, 100% against 2600 (grid57). |
| Full smothers by any piece | `SmotherClassic false` | 1.6 at 5+0.05 against Stockfish 1500: 42.8 of 100 games end in a smother, 11.1 of them full (3.5 times the defaults); knight smothers 1.3. No losses (grid57). |
| True smothers of any piece only | `SmotherClassic false`, `SmotherGoal Full` | The most full smothers, few near ones. |
| Ordinary Stockfish play | `SmotherBrutal false` | Smothers only when the prover finds a forced one. |
| Quick games against people | defaults (with `UCI_Opponent` from the GUI) | Builds for a shorter time, since people resign. |
| A human-like sparring partner | `HumanElo` N | Section 5. |

## 5. Human mode (HumanElo)

`HumanElo` N (default 0 = off, 1020 to 2400) makes the engine play like a human
of rating N. It sets the strength limit itself: below about 1860, the lowest
`UCI_Elo` limiter plus real mistakes (a share of moves picked at random from
the 8 best candidates, while the limiter alone never loses more than about a
pawn per move); above it, the `UCI_Elo` limiter alone. No other option is
needed; `UCI_LimitStrength`, `UCI_Elo` and `Skill Level` are ignored while it
is on.

Ratings are on the scale of the human-like Maia-3 network: N is the Maia-3
level the engine scores 50% against. Maia-3's levels are compressed (a setting
that scores 72% against level 1300 still scores 48% against 1900), so the
levels in between are fitted, to about +-50 (+-100 near the ends). Measured at
5+0.05:

| HumanElo | Limiter | Mistakes | Measured (300 games each) |
| -------- | ------- | -------- | ------------------------- |
| 1020 | 1320 | 13% | 47.3% vs 1100, 33.5% vs 1500 |
| 1255 | 1320 | 11% | 56.3% vs 1100, 40.0% vs 1500 |
| 1400 | 1320 | 9% | 62.0% vs 1100, 46.0% vs 1500 |
| 1490 | 1320 | 7.2% | 60.9% vs 1100, 49.6% vs 1500 (600 each) |
| 1580 | 1320 | 4% | 69.5% vs 1100, 62.5% vs 1300 |
| 1600 | (interpolated) | | 63.2% vs 1300, 45.3% vs 1700 |
| 1735 | 1320 | 1% | 68.8% vs 1300, 59.8% vs 1500 |
| 1800 | (interpolated) | | 63.3% vs 1500, 45.8% vs 1900 |
| 1880 | 1320 | 0 | 68.2% vs 1500, 47.8% vs 1900 |
| 2200 | (interpolated) | | 59.5% vs 1900, 42.0% vs 2300 (plays about 2115) |
| 2420 | 1455 | 0 | 76.8% vs 1700, 66.3% vs 2100 |

For a club player of about 1350, use `HumanElo 1350`. `HumanBlunder` N
(percent) or `HumanBlunderPermille` N (per mille) add the mistakes to whatever
`UCI_Elo` or `Skill Level` is set; `HumanBlunder 1` plays at about 1735.
Proven smothered mates are still played in full.

## 6. How Smotherfish is tested

### 6.1 Smother experiments

- **Harness.** `notes/scripts/match.py` (python-chess) with real clocks. Games
  are played to checkmate, stalemate, insufficient material, threefold
  repetition, the 50-move rule or a 400-ply cap: no adjudication and no
  resignation (an optional resignation curve measured on Lichess is available
  for tests against "human" opponents).
- **Openings.** 300 balanced positions about 4-5 moves deep
  (`notes/openings.txt`), each played with both colours.
- **Opponents.** Stockfish 19 limited by `UCI_LimitStrength` / `UCI_Elo`
  (1500 to 3000), and the human-like Maia-3 network (moves sampled at its rating).
- **Time controls.** Mostly 5 seconds + 0.05 per move (one thread per engine),
  checked at 3 minutes + 2 seconds.
- **Size.** 2,500 to 6,000 games per setting against Stockfish 1500, 600 to
  1,200 against Maia-3, 400 against Stockfish 2500. A difference is treated as
  real when z >= 2 (counts compared as Poisson rates); at about 4 knight smothers
  per 100 games, detecting a +25% change needs about 7,000 games per setting.

### 6.2 Strength tests

Every default change passes a sequential probability ratio test (SPRT) against
the previous version at full strength: paired games at 10 seconds + 0.1 per
move, one thread, played with fastchess from Stockfish's `8moves_v3` opening
book with both colours per opening, using the statistics Fishtest uses
(`notes/scripts/sprt_stats.py`). Typical bounds are [-3, +1] Elo (no
regression).

### 6.3 Where the tests run

Tests run on GitHub Actions, spread over the main repository and volunteers'
forks ([HELPING.md](HELPING.md)): about 160 jobs and 640 games at a time.
`notes/scripts/distribute.sh` splits a plan into shares,
`notes/scripts/volunteers.py` tracks and merges them, and the
[test status page](https://demonic1594.github.io/Smotherfish/) shows them live.
Raw games are on each account's `actions-exp/<name>` branch under
`notes/results/`.

## 7. Results

### 7.1 Version 1.6

How games end (share of games, 5+0.05):

| Opponent | Version | Knight smother | Full, other piece | Near | Plain mate | Draw |
| -------- | ------- | -------------: | ----------------: | ---: | ---------: | ---: |
| Stockfish 1500 | 1.5.1 | 0.7 | 13.7 | 45.0 | 40.2 | 0.2 |
| | **1.6** | **3.8** | 0.2 | 3.8 | 91.4 | 0.6 |
| Maia-3 1500 | 1.5.1 | 0.3 | 7.9 | 38.5 | 53.3 | 0.0 |
| | **1.6** | **3.3** | 0.0 | 5.0 | 91.7 | 0.0 |
| Stockfish 2500 | 1.5.1 | 1.0 | 6.6 | 30.9 | 61.5 | 0.0 |
| | **1.6** | **0.8** | 0.2 | 2.0 | 96.2 | 0.8 |

(1,876 / 2,500, 304 / 600 and 288 / 400 games; no losses.) Across the
development grids 1.6 averaged 3.8-4.3 knight smothers per 100 games against
Stockfish 1500 and 1.3-1.8 against Stockfish 2500. At 3+2: 3.7 against
Stockfish 1500 and 6.3 against Maia-3 (1.5.1: 0.9 and 1.4).

### 7.2 Strength record

| Version | Test | Games | Elo | 95% range |
| ------- | ---- | ----: | --: | --------- |
| 1.1 | against 1.0 | 4,000 | +12 | |
| 1.2 | against unmodified Stockfish (10+0.1) | 43,200 | -0.3 | -1.1 to +0.4 |
| 1.3 | against 1.2 | 21,600 | +1.3 | +0.2 to +2.4 |
| 1.3 | against unmodified Stockfish (60+0.6) | 7,320 | +0.5 | -0.6 to +1.7 |
| 1.5 | against 1.4.1 | 18,000 | -1.0 | -2.2 to +0.1 |
| 1.6 | against 1.5.1 | 32,400 | -0.3 | -1.2 to +0.5 |
| 1.6 | prover time in undecided positions off vs on | 28,800 | +0.3 | -0.6 to +1.2 |

Smother hunting costs no measurable strength against an equal opponent.

### 7.3 Earlier measurements (any-piece smothers, 1.0-1.5.1)

Before 1.6, a smother by any piece counted. Smothers per 100 games, 5+0.05:

| Setting | Elo 1500 | Elo 2000 | Elo 2500 | Elo 3000 | Maia 1100 | Maia 1900 |
| ------- | -------- | -------- | -------- | -------- | --------- | --------- |
| Brutal mode off | 1.1 | - | - | 0.2 | - | - |
| Brutal, no construction | 1.2-1.5 | 1.1 | - | 0.5 | 1.4 | 1.3 |
| Brutal, construction (20 moves) | 5.0 | - | - | 1.0 | 4.5 | - |
| Brutal, construction (40 moves) | 6.2-8.7 | - | - | - | - | - |
| Brutal, construction (80 moves) | 10.6-12.7 | 7.8 | 4.2 | 1.3-2.0 | 7.3-8.0 | 4.7 |
| Brutal, construction (200 moves) | 11.8 | - | - | - | - | - |

By goal (`SmotherBuildKeep` 8; true / true + near per 100 games):

| `SmotherGoal` | Elo 1500 | Elo 2000 | Elo 2500 |
| ------------- | -------- | -------- | -------- |
| Full | 14.6 / 16.4 | about 8-9 | about 5-7 |
| Hybrid | 8.4 / 53.1 (60.8 with pondering) | - / 43.8 | - / 38.3 |
| Near | 3.8 / 65.6 | 2.5 / 54.3 | - / 45.7 |

Tuning in 1.3 (full / full or near per 100 games):

| Test | Old defaults | 1.3 |
| ---- | ------------ | --- |
| 5+0.05, Elo 1500, 4,000 games | 7.8 / 53.6 | 8.1 / 58.1 |
| 5+0.05, Elo 2500, 1,500 games | 3.9 / 37.2 | 4.9 / 43.6 |
| 3+2, Elo 1500, 250 games | 12.9 / 59.8 | 12.4 / 71.6 |
| 3+2, Elo 2000, 250 games | 12.0 / 62.0 | 10.8 / 65.8 |
| 3+2, Elo 2500, 250 games | 8.0 / 49.2 | 7.3 / 60.9 |

1.5 against 1.4.1 at 3+2 (true / true or near): Stockfish 1500 13.2 / 63.6
(12.3 / 70.4), Stockfish 2500 8.8 / 51.8 (6.9 / 58.3), Maia-3 1500 17.3 / 62.3
(8.8 / 66.8). At 5+0.05, true smothers roughly doubled against Stockfish
1500-2500.

## 8. Findings: what limits smothered mates

Offline analyses of tens of thousands of games (`notes/scripts/smother_*.py`)
and outside reviews explain why the knight-smother rate is hard to raise
further.

| Question | Measurement | Answer |
| -------- | ----------- | ------ |
| How does the box close? | 2,481 knight smothers | 83% close with the defender's forced reply to a check in the final sequence: 48% a block, 34% a capture of a sacrificed checking piece (Philidor's pattern). Free choices: 9%. |
| Does the prover miss forced smothers? | 240 stalled won positions, prover with 16 moves, 3 quiet moves and 20M nodes | A forced knight smother existed in 2 of 120 positions with one open square and 0 of 120 with two: the lines do not exist. |
| Are there traps the opponent would fall into? | 240 positions against Stockfish 1500, 600 against Maia-3 1500, 8 sampled replies per move | Against Stockfish: 1 in 240 positions. Against human-like Maia-3: 1% of positions, about 0.004 per move above the move played. |
| Does the engine model the defender realistically? | 500 won positions | Its expected reply matched the real one 81% of the time; its lines rarely drop material. |
| Does keeping the right pieces help? | 4,989 games | Games that still have our knight and queen, enemy pieces and king-side pawns at +8 smother about twice as often, but rewarding the engine for keeping them (the prep phase) did not raise the rate. |
| Does a better predictor help? | 4.5 million positions, AUC 0.936 (linear) and 0.968 (network) | Used as the construction score, both only tie the hand score; at high weights the search gives up material and loses games. |

What did not help (each measured over thousands of games): more prover time,
steering towards traps at all times, a shaping bonus, robust or strict proofs,
earlier construction (more draws), a lower floor, blocker-survivability terms,
search-control changes in construction mode, keeping our own mating pieces,
knight safety, ready squares, a safe-exit penalty, starving and holding
variants, and the prep phase.

## 9. Testing your own changes

- `./stockfish bench` must still report **1210779** nodes (the bench of the
  upstream base commit; it runs with brutal mode off).
- `notes/scripts/puzzles.py ENGINE smothered.csv N SEED` re-runs the prover
  regression test (the Lichess puzzle database filtered on `smotheredMate`).
- **Experiments.** Write a plan (`notes/exp/<name>.json`, see
  `notes/scripts/expand_plan.py`) and spread it over all accounts with
  `notes/scripts/distribute.sh notes/exp/<name>.json`; follow it with
  `notes/scripts/volunteers.py status <name>` and collect it with
  `volunteers.py merge <name> OUTDIR`, then `notes/scripts/summary.py`.
- **Strength tests.** Push `notes/exp/sprt.json` to an `actions-exp/<name>`
  branch; `sprt.yml` plays games until the result is clear; combine shards with
  `notes/scripts/sprt_stats.py ELO0 ELO1 0.05 0.05`.
- **Helping.** To lend your GitHub Actions minutes, see [HELPING.md](HELPING.md).
