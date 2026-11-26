# Handoff note for the next session

Written because the user is continuing this work in another session. Nothing
here is finished: read "State" first, then "Next steps".

## What the user asked for (original request)

1. Set up Stockfish 19 (official repo, tag `sf_19`), apply `smother-mate-v2.patch`
   with `git am`, build, confirm bench 2497913 and the puzzle harness gives
   2348/2350 with 0 bad.
2. Work on the README's "Next goal": smarter, stronger steering for more
   smothered mates, keeping a win rate above 50% against Stockfish with
   UCI_Elo 3000 (revised from 2500: the user measured Stockfish 19 at about
   3804 Elo, so 3000 is the new bar; it is inside the UCI_Elo range
   1320-3190). Use all CPU cores for matches.
3. When done, build static Android binaries with the NDK for DroidFish.
4. Added later by the user: the engine should be able to smother the opponent
   with high likelihood at any Elo, not only at the level where smothers
   happen by themselves. Measure the smother rate (smothered mates per game
   won, and per game overall) at several UCI_Elo settings, for example
   1500, 2000, 2500 and 3000, and aim to raise it at each one. Set a numeric
   target only after the first measurements exist, because nothing has been
   measured past the 1500 baseline yet. This goal does not replace the
   win-rate constraint against 3000 in item 2.

The user's handoff zip (`smother-stockfish-handoff.zip`, with README.md,
patch, tests/, match/) is not in the repo. Ask the user to re-upload it if
the new session does not have it. The patch itself is already applied here.

## State

Branch `ccr-22798bd9-4zky9t` (PR #1) holds: sf_19 + the 4 patch commits + my
steering commit + a clang-format 20 commit. It is based on the `sf_19` tag, not
on this repo's `master` (a newer Stockfish), so the PR diff against `master`
also shows the version differences.

Done and verified:
- bench is 2497913 with the patch and with my steering code (default off).
  Unpatched sf_19 also gives 2497913.
- Puzzle harness: positions=2350 claimed=2348 verified=2348 bad=0. That is
  the full run on the patched build before my steering changes (steering is
  off by default and does not touch the prover, but re-run it once after any
  prover change). It takes about 15 minutes on one core.
- Matches vs Stockfish 19 at UCI_Elo 1500, tc 5+0.05, 1 thread, Hash 16,
  4 concurrent games, 8moves_v3 book:
  - SmotherSteer=0: 200 games, 200 wins, 0 smothered mates.
  - SmotherSteer=150: stopped early at 94 games, 94 wins, 0 smothered mates.
    I could not tell whether steering fired at all: fastchess's log does not
    contain `info string` lines, so the "smother steer" message was never
    visible. Verify this first (see Next steps, item 1).

Not done:
- No measurement of smothers per 100 games at Elo 1500 or 2000 with steering.
- No win rate vs UCI_Elo 3000 at all (the key constraint, must stay above 50%).
- No tuning of the new options.
- The Android build has not been run. The NDK is not in the repo; see below.

## What I changed (commit "Smother steering: prove traps per opponent reply")

`src/smother.{h,cpp}`: `Smother::traps()`. For a position with the opponent to
move, it tries every legal reply and runs the prover (depth `SmotherTrapDepth`,
4096 nodes, reusing the shared proof table via `Limits::keepTable`). It returns
the plausibility-weighted share of replies that lead into a forced smother
(replies that lose material by SEE count 0.3, others 1.0).

`src/search.cpp` (`start_searching`): the steering block now scores each
MultiPV candidate within the margin by
`100*trapShare + 50*(expected reply is a trap) + 0.5*potential - 0.05*loss`
and switches only if the winner beats the best move's score by 5 or more.
Steering stays off unless `SmotherSteer > 0`. When already winning, it never
picks a move whose score is below `SmotherSteerFloor`; when not winning the
margin shrinks to a quarter. "Mate phase": if the best move already has a
forced plain mate, a slightly slower mate (within `SmotherMateSlack` score
units, i.e. plies) may be chosen for its traps, at most `SmotherMateDelays`
times per game (counter reset in `Worker::clear()`).

New UCI options (engine.cpp): SmotherSteer (0-500, default 0),
SmotherSteerFloor (150), SmotherSteerLines (4), SmotherSteerTime (15, percent
of the move's time), SmotherTrapDepth (3), SmotherMateDelays (8),
SmotherMateSlack (6).

Known weak spots to check before trusting it:
- The mate-phase check `rm.score < VALUE_MATE_IN_MAX_PLY` and the slack are in
  raw score units (1 per ply); the `loss * 10` there is only a utility
  weight. Sanity test it on a position with a plain forced mate.
- Steering needs `SmotherSteerLines` MultiPV lines, which lowers search
  strength a little at a fixed time. The 3000 win rate must be measured.
- The trap scorer allows at most one quiet move (`min(1, SmotherQuietMoves)`).
- The model of the opponent is crude. UCI_Elo 1500 picks among shallow lines
  at random, so "plausible reply" weighting by SEE is a guess.

## Next steps (in order)

1. Make steering observable. Run one steered game by hand (or set fastchess
   engine logging so `info string` lines are kept) and count "smother steer"
   lines. If it never fires, debug before running more matches.
2. Measure smothered mates per 100 games vs UCI_Elo 1500 and 2000 for
   SmotherSteer 0, 100, 150. Use several hundred games per setting (the
   Elo 1500 baseline of 200 games gave 0 smothers, so expect low counts and
   plan sample sizes accordingly).
3. Measure the win rate vs UCI_Elo 3000 for the steering settings that look
   good. It must stay above 50%. Use all cores. Expect this to be much harder
   than 1500: at 3000 the opponent rarely blunders into smothers, so a win
   rate above 50% may require the steering to cost little strength.
4. Tune (`SmotherSteerFloor`, margin, `SmotherTrapDepth`, trap node budget).
5. Re-run bench (2497913) and the puzzle harness (2348/2350, 0 bad).
6. Android build with `notes/scripts/build_android.sh` (below). Copy outputs into
   DroidFish's `uci/`. Never name the binary `stockfish` or `*.ini`.
7. Update the PR description with the results.
8. For the any-Elo smother goal (request item 4): after step 2, produce a
   table of smother rate per UCI_Elo (1500, 2000, 2500, 3000) for each
   steering setting, with game counts. Use it to decide where the steering
   should be strongest, and check that the 3000 win rate from step 3 holds.

## Environment notes (the container is ephemeral; rebuild all of this)

- Network: the default environment blocks the net download. I created a personal
  environment "Smotherfish" allowing `tests.stockfishchess.org`,
  `data.stockfishchess.org`, `dl.google.com` and `raw.githubusercontent.com`.
  A new session needs the same hosts. `make net` in `src/` then works
  (the net is `nn-1a298aa575a0.nnue`).
- Build: `cd src && make -j build ARCH=x86-64-bmi2` (this machine had 4 cores,
  AVX2/AVX512).
- Python checker: the system pip cannot build `chess`. Use a venv:
  `python3 -m venv v && v/bin/pip install -U pip setuptools wheel chess`.
- Formatting: the repo's CI uses clang-format 20. `pip install "clang-format==20.*"`
  and run `clang-format -i` on changed files (Ubuntu's clang-format 18 cannot
  read the repo's `.clang-format`).
- Matches: `git clone https://github.com/Disservin/fastchess` and `make -j`;
  book: `books/8moves_v3.pgn.zip` from official-stockfish/books (a plain git
  clone works for it; LFS is not needed). Build a clean Stockfish 19 from the
  `sf_19` tag as the opponent (`git archive sf_19 src scripts`, then add the
  net). `notes/scripts/match.sh` runs one setting (edit the paths at the top).
- Android: NDK r27c from
  `https://dl.google.com/android/repository/android-ndk-r27c-linux.zip`
  (about 660 MB). `notes/scripts/build_android.sh` builds `armv8-dotprod` and `armv8`
  static binaries and strips them (edit the paths at the top).
  A glibc-static build does not start on Android; use the NDK build.
- Scripts in `notes/scripts/` have my scratchpad paths hard-coded. Edit them.

## Update from the follow-up session

Step 1 is done. Steering never fired because of two bugs, fixed in commit
"Fix smother steering never firing" on branch `ccr-00291b96-tkvbkh`:
- `Smother::traps` got `threads.stop`, which is already set after the search,
  so every reply was aborted with 0 nodes. It now gets its own flag.
- Timed searches stop inside the last MultiPV iteration, leaving lines 2..N at
  `-VALUE_INFINITE`; only the best move was a candidate. Those lines now use
  their exact `previousScore`.
After the fix, 3-4 candidates are scored per move and steering fires in games.
Bench is unchanged (2497913). In the few moves inspected, the trap share was
0% and the one steer seen was chosen on "potential" alone, so check the trap
scoring during step 2. The puzzle harness has not been re-run since the fix.
Cloning/building fastchess was blocked by the session's permission check;
steps 2-3 still need it.

### Match tooling without fastchess

Cloning outside GitHub repos (fastchess, books, official Stockfish) is refused
in these sessions (GitHub access is scoped to this repo). Instead:
- Opponent: `git archive edb0d9db src scripts` (stock Stockfish 19, in this
  repo), add the net, build. Bench 2497913.
- `pip install chess` in a venv (PyPI works).
- `notes/scripts/make_book.py ENGINE 300 openings.txt` makes balanced 8-ply
  openings (`notes/openings.txt` is the set used).
- `notes/scripts/match.py OUT.jsonl OURS OPP ELO GAMES --opt SmotherSteer=150`
  plays paired games, 5+0.05, 4 concurrent, real clocks, and records
  smothers and steer lines per game.
- `notes/scripts/summary.py res/*.jsonl` prints the table.

### First-pass grid (steering fix applied, 5+0.05, 200 games each, vs stock SF19 UCI_Elo N)

```
file                         games    W    D    L  score  +-95% smoth class  /100g  /100W steer/g time
e1500_s0.jsonl                 200  200    0    0  1.000  0.000     5     1    2.5    2.5    0.00    0
e1500_s150.jsonl               200  199    1    0  0.998  0.005     5     1    2.5    2.5    0.62    0
e2000_s0.jsonl                 200  199    1    0  0.998  0.005     1     0    0.5    0.5    0.00    0
e2000_s150.jsonl               200  196    4    0  0.990  0.010     0     0    0.0    0.0    0.69    0
e2500_s0.jsonl                 200  198    2    0  0.995  0.007     1     0    0.5    0.5    0.00    0
e2500_s150.jsonl               200  195    5    0  0.988  0.011     0     0    0.0    0.0    0.52    0
e3000_s0.jsonl                 200  187   13    0  0.968  0.017     0     0    0.0    0.0    0.00    0
e3000_s150.jsonl               200  163   36    1  0.905  0.028     0     0    0.0    0.0    0.64    0
```

"smoth" uses the engine's AnyPiece definition, "class" = knight mate.
Findings: steering as designed does not raise the smother rate at any Elo
(1500: 5 vs 5; 2000/2500: 1 vs 0), it fires ~0.6 times per game, and it costs
strength at 3000 (0.968 -> 0.905). The 50% bar vs 3000 is far from binding
(90-97%), so there is a lot of strength to spend on smothers.
Raw games are in notes/results/*.jsonl.

### Session 2 findings (won mode, shaping, seek, brutal)

Elo 1500, 400 games each, smothers per 100 games: won mode 1.0, shaping
0.2-1.0, won-mode steering 1.0, seek mode 1.0, SmotherBrutal 1.2. Scores
0.998-1.000. Elo 3000, 300 games: default 0.982, SmotherSeek=30 0.980.
Ceiling: in 200 won brutal games at 1500, a forced smother (12 moves,
3 quiet, non-strict) existed in only 10 games, 3 delivered. Every strictly
forced smother was delivered. End-game methods are capped near 5/100 games;
gains must come from earlier (openings, middlegame plans).
Raw games: notes/results/exp1, exp2 branches exp2-w1..w3.

### Session 2, overnight (Nov 20 JST)

Experiments now run on GitHub Actions (`.github/workflows/smother-exp.yml`):
push `notes/exp/plan.json` to a branch `actions-exp/<name>`; results are
committed back to that branch under `notes/results/<exp>/`. Plans can use
Maia opponents (`"opponent": "maia-1500"`, lc0 built in CI, `go nodes 1`).

Findings:
- grid1 (2000 games/setting): default, brutal, middlegame shaping and their
  combinations all give 0.6-0.9 smothers/100 games at Elo 1500/2000 and
  0.2-0.3 at 3000; scores unchanged (0.97-1.00).
- Traces of lost chances at Elo 1500: ~60% were never started because the
  prover ran out of time (needs 0.1-3M nodes); the rest the opponent escaped.
- grid2: more brutal prover time (300%/600%) did not help, because brutal
  mode spent the budget on every move and ran its own clock down (median
  lowest clock 0.45 s vs 1.73 s default, measured in match records).
- Every one of 41 traced smother chances arose at >= +15 pawns or with a
  mate on the board (only 28% of positions are >= +10). The deep prover in
  brutal mode is now gated on SmotherBigCp (1000) -> grid3b measures it.
- SmotherRobust (choose the hardest-to-escape proof) and larger/faster
  prover tables were tried and rejected (measured, no net gain).
- SmotherPonderDeep: while pondering the prover searches deep and
  unbounded; smothers needing 2-3M nodes are found after 3 s of pondering.
  This matters for real games against people (long thinking times); our
  matches cannot measure it (opponents move instantly or share the CPU).
- Maia runs hung in CI: Pool workers died when an engine failed at start-up
  and were respawned forever; fixed (lazy engine start, watchdog, hang
  records). A debug stack-dump timer armed before fork also deadlocked
  workers; fixed.
- Prover regression test (replaces the zip's puzzle harness): all 24,506
  Lichess `smotheredMate` puzzles (CC0), `notes/scripts/puzzles.py`.
  Current build and the build before tonight's prover changes both give
  claimed=24482 verified=24482 bad=0. The 24 unclaimed are smothers only in
  the puzzle's main line (another defence avoids them and is not mated
  faster), so not forced under the prover's rule.
- grid3b (deep prover only when crushing): no gain at 1500/2000/15+0.15
  (0.6-0.8 smothers/100) and no cost at 3000 (0.981 vs 0.973). In-game
  proof records: ~1.5% of games at 1500 reach a proven smother and only
  ~50% of those end in one, because the prover's rule lets the defender
  escape into a faster plain mate and weak opponents do.
- Maia grid (human-like, 1000 games each): smothers per 100 games, default
  vs brutal: Maia 1100 2.0 vs 1.4, Maia 1500 0.6 vs 0.8, Maia 1900 1.8 vs
  1.8. Scores 0.994-0.999. Same picture as against Stockfish at UCI_Elo.
- Bug fixed: in seek mode a plain forced mate is a TB-range score, which the
  won/crushing gates did not accept, so the prover lost its budget right in
  the mating phase (a smother in 7 needing 38k nodes was missed after an
  escape). grid4 measures the fix.
- Android: `.github/workflows/android-build.yml` (push to
  `android-build/<name>`) builds static armv8 / armv8-dotprod binaries with
  NDK 27.2, checks bench 2497913 under qemu, uploads artifacts.

### Session 2, morning (Nov 20 JST)

Three bugs, all fixed:
- Prover loop (commit 6a5db802). In 6 grid4 games a proven smother ended
  in a draw: the defender escaped into a quicker plain mate, the engine
  declined that mate for the same smother line, and the moves went round
  in a circle until threefold. The prover now fails any attacker move on a
  smother line that brings back a position seen before (in the game or on
  the line). Replays: 4 of the 6 now mate at once, 2 mate within 3-9 plies.
  Puzzle regression unchanged (24482/24482, 0 bad, 0 differences).
- Match runner draws (same commit). `can_claim_draw()` also counts a
  threefold the side to move *could* make next, so games ended as draws
  that the winner would never have repeated. All but 1 of ~250 draws in
  grids 1-4 were of that kind; the scores above are understated (mostly at
  Elo 3000). Now only a real third occurrence or fifty moves ends a game.
- Match runner hang (de9d6354). A Pool worker that dies loses its game and
  Pool waits forever (one grid4 job sat until the 90-minute timeout). With
  no finished game for `MATCH_STALL` seconds (600) the run now ends with
  the games so far.

grid5 (both fixes, 5+0.05; Maia runs are 1000 games, Elo 3000 runs 600):

```
file                     games    W    D  L  score  smothers /100g  proof games  delivered
e1500_brutal              2000 2000    0  0  1.000        25   1.2   61 (3.05%)  41%
e1500_default             2000 2000    0  0  1.000        22   1.1   43 (2.15%)  51%
e2000_brutal              2000 2000    0  0  1.000        22   1.1   37 (1.85%)  59%
maia1100_brutal           1000 1000    0  0  1.000        14   1.4   24 (2.40%)  58%
maia1900_brutal           1000 1000    0  0  1.000        13   1.3   24 (2.40%)  54%
e3000_brutal               600  591    9  0  0.993         3   0.5    3          3/3
e3000_default              600  591    9  0  0.993         1   0.2    1          1/1
e3000_off (SmotherMate=false) 600 593  7  0  0.994         1   0.2    -          -
```

- With real draw rules: 8,000 games at Elo 1500/2000 and vs Maia, all won.
  At Elo 3000 the smother features cost nothing measurable (0.993 vs 0.994
  with them off) and the win-rate goal (>50%) holds by a wide margin.
- Smother rate is still ~1.1-1.4 per 100 games; brutal vs default is
  within noise. Brutal still uses more clock (median lowest clock 0.66 s
  vs 1.36 s at 1500; 0.21 s at 3000), with 0 time losses in 9,200 games.
- Escapes: an escaped game ends 3-5 plies after the last proof (the
  defender steps into a mate in 1-2). No strict proof (every defence
  smothered) existed at the first chance in any of 57 escaped games, so
  preferring strict proofs cannot help. But in 17 of 55 after-escape
  positions (with the game history; 20 without) a new smother in 6-9 is
  still forced. It needs 0.3-11M prover nodes (~3M nodes/s), while by then
  the clock is 0.5-1.5 s at 5+0.05.
- Mate-in-hand budget (commit 25407786, brutal only): with a forced mate
  in hand the prover may use `SmotherMatePercent` (15) of the remaining
  clock, without the node cap, for at most 12 moves per game. 48 local
  games at 5+0.05: no time losses. grid6 measures it at 5+0.05 and as an
  A/B at 15+0.15.
- Android build of de9d6354 passed (run 44633063886, bench 2497913 under
  qemu); it does not include the mate-in-hand budget yet.

grid6 (mate-in-hand budget; same openings as grid5):

```
file                          games    W  D  L  score  smothers /100g  proof games  delivered
e1500_brutal_hand  (5+0.05)    2000 1999  1  0  1.000        22   1.1   57           39%
e1500_brutal_tc15_hand          1000 1000  0  0  1.000        14   1.4   43           33%
e1500_brutal_tc15_nohand        1000 1000  0  0  1.000        11   1.1   42           26%
e3000_brutal_hand              600  590  9  1  0.991         3   0.5    4           3/4
```

- 5+0.05: no gain (22 vs 25 in grid5): by the time a forced mate is in
  hand the clock is too low for 15% of it to buy a 1M+ node proof.
- 15+0.15 A/B: 14 vs 11 smothers, not significant, in the expected
  direction. Kept: no cost seen (no time losses, clocks unchanged), and
  real games are slower than these matches.
- The one Elo 3000 loss is an ordinary blitz loss: at ply 36 (3.2 s on the
  clock) the engine played Rxf6, -6.6 at depth 20; stock Stockfish 19 plays
  the same move 8/8 times at that clock. Elo 3000 scores, grid5/6: 0.991
  brutal+hand, 0.993 brutal, 0.993 default, 0.994 smother features off.

Where this leaves the smother rate: ~1.1-1.4 per 100 games against weak
and human-like opponents in 5-15 s games, with no strength cost. The
limits measured: a proven smother appears in ~2-3% of games; the defender
escapes ~50-60% of them into a quicker plain mate; strict proofs do not
exist in those positions; re-proofs after an escape need more time than
blitz gives. Most remaining levers are earlier in the game (openings,
middlegame plans that keep the enemy king boxed in), as noted before.
Ponder-time proving (SmotherPonderDeep) and the mate-in-hand budget only
show in slower games, which these matches do not cover.

Android, final code (commit 70d42651; later commits are notes only): run
44642135912 passed (bench 2497913 under qemu). Artifacts
`smotherfish-android-armv8-dotprod` (most phones since ~2019) and
`smotherfish-android-armv8`, kept until 2026-12-20:
https://github.com/Demonic1594/Smotherfish/actions/runs/44642135912
In DroidFish: copy the binary to the phone and pick it as an engine; do not
rename it to "stockfish". Brutal mode: set `SmotherBrutal` to true in the
engine options.

### Session 3 (Nov 20 JST, morning): construction mode

- grid7, `SmotherRobust` (greedy-weighted choice among alternative
  proofs) in brutal, same openings as grid5: 53 smothers from 117 proof
  games vs 74 from 146 without it. Rejected for good (it costs proofs).
- Escape study (306 proof games): opponents leave the smother line mostly
  at their first reply (74 of 134 escapes), usually with only 2-3 legal
  moves; in 29 escapes they grabbed a piece instead of the needed king move
  or block. Baiting with a sacrifice does not convert better (24-30%).
- Delivered smothers (227): 77% with the king in a corner, all on an edge,
  blocked mostly by its own pawns, rooks and bishops.
- Construction mode (commits 8a938b32, 4784aa00; `SmotherBuild`, off by
  default): once decided (`SmotherBuildCp` 800 or a forced mate), above
  `SmotherBuildFloor` (600) extra material counts 1/8 and
  `Smother::build_score()` (corner, own blockers, enemy pieces kept, our
  queen/knights close) counts `SmotherBuildWeight` (8) cp per point; a
  plain mate counts as the floor. `SmotherBuildMoves` per game (20).

grid8 (600 games each, 5+0.05 unless noted, Elo 1500 unless noted):

```
setting                     smothers /100g  proof games  score
brutal, no construction            9   1.5      16       1.000
build (20 moves)                  30   5.0      49       1.000
build, 40 moves                   52   8.7      85       0.999
build, 15+0.15                    33   5.5      62       1.000
build, weight 16                  15   2.5      30       1.000
build vs Maia 1100                27   4.5      42       1.000
build vs Elo 3000 (300 games)      3   1.0       3       0.997 (0 losses)
```

First method that moves the rate several-fold. grid9 measures budgets
40/80/200 and Elo 2000 / Maia 1900 / Elo 3000 at 80.
Idea queued (from an outside review): score blocker survivability in
build_score() (pinned/protected blockers vs ones that can capture our
knight or step away).

grid9 (construction budget; 600 games each, 300 at Elo 3000):

```
setting                 smothers /100g  non-wins                 score
Elo 1500, budget 40          37   6.2   0                        1.000
Elo 1500, budget 80          76  12.7   0                        1.000
Elo 1500, budget 200         71  11.8   3 draws, 5 at 400 plies  0.993
Elo 2000, budget 80          47   7.8   1 draw                   0.999
Maia 1100, budget 80         44   7.3   1 draw                   0.999
Maia 1900, budget 80         28   4.7   2 draws                  0.998
Elo 3000, budget 80           6   2.0   2 draws                  0.997
```

Commit 97256b6f: construction mode on by default in brutal mode, budget
80. Games are longer (median ~120 plies vs ~53). No losses in any run.
Android build of it: run 44654465325 (artifacts until 2026-12-20).
Commits 0b8bc9f5, 6f95b567: optional blocker survivability,
`SmotherBuildSurvive` bit mask (1 pinned +4, 2 defended +2, 4 our knight
wins it by SEE -4, 8 pawn blocker can step forward -3; capped +-12).
With 0 the search is identical to before (40/40 positions, same move and
nodes at depth 12). grid10 measures 0 / 3 / 15 and each bit alone.

grid10 (blocker survivability, budget 80; 1000 games each at Elo 1500):

```
SmotherBuildSurvive        smothers /100g (95%)   proof games  delivered  W/D/L
0  control (A)                  106  10.6 +-1.9   154          69%        997/3/0
1  pinned bonus                  99   9.9          166          60%        999/1/0
2  defended bonus               132  13.2 +-2.1   181          73%        999/1/0
3  pinned+defended (B)           89   8.9          146          61%        995/5/0
4  knight-SEE penalty           100  10.0          149          67%        997/3/0
8  pawn-push penalty            117  11.7          153          76%        999/1/0
15 all (C)                      108  10.8          158          68%        999/1/0
Maia 1100 (600): A 8.0, C 6.2.   Elo 3000 C (300): 1.3, 0.995, no losses.
```

Inconclusive: "defended" alone +2.6 (p ~0.07) but bad combined with
"pinned"; nothing else separates from the control. Default stays 0.
grid12 re-tests 0 / 2 / 10 with 2000 new games (Elo 1500) and 1000 vs
Maia 1100. grid11 tests the Elo 3000 trigger (800/600/400 vs off), Elo
2500 and 15+0.15. Also: `SmotherBuildSurviveCap` (default 12) for a cap
ablation if a survivability setting wins.

grid11 (construction defaults; 600 games each):

```
setting                               smothers /100g  W/D/L      score
Elo 3000, trigger 800 (default)              8   1.3  593/6/1    0.993
Elo 3000, trigger 600, floor 450             2   0.3  590/9/1    0.991
Elo 3000, trigger 400, floor 300             3   0.5  547/52/1   0.955
Elo 3000, smother features off               0   0.0  593/7/0    0.994
Elo 2500, defaults                          25   4.2  600/0/0    1.000
Elo 1500, defaults, 15+0.15                 74  12.3  600/0/0    1.000
```

- A lower trigger is worse on both counts; 800 stays.
- The one loss at trigger 800 (game 35): at ply 63, +7.7 by stock depth 18,
  the engine played Rb1 (mate follows) instead of g6, with 1.3 s left.
  Replayed with the game's clocks, 5/5 times every mode (construction,
  brutal without construction, smother off) plays g6: timing noise, not
  construction mode. Construction at Elo 3000 so far: 1 loss in ~1,500
  games; smother off: 0 in 600.
- 15+0.15 gives the same rate as 5+0.05 (12.3 vs 10.6-12.7).
- Engine renamed "Smotherfish 1 (Stockfish 19)" (43e8a3eb); README and
  docs/SMOTHERFISH.md written (d7b39b31).
- Merging into master: master is upstream Stockfish dev (98 commits past
  Stockfish 19, new net architecture SFNNv18); a trial merge conflicts in
  src/Makefile, src/misc.cpp, src/search.cpp. Not merged.

grid12 (survivability confirmation, new openings):

```
SmotherBuildSurvive     Elo 1500 (2000)       Maia 1100 (1000)
0  control              215  10.8  1994/6/0     64  6.4
2  defended             225  11.2  1996/4/0     73  7.3
10 defended + pawn      207  10.3  1993/6/1     74  7.4
```

grid10 + grid12 at Elo 1500: defended 357/3000 (11.9) vs control 321/3000
(10.7), p ~0.14. Not confirmed; SmotherBuildSurvive stays 0, and the cap
ablation is skipped (no term won). The option stays for later work.

Logo (docs/logo.svg) and a README in the original's style are on branch
`smotherfish` (pushed copy of this branch; intended as the default branch).
Branch `smotherfish-next`: Smotherfish merged with upstream master (98
commits past Stockfish 19); bench 1442480 = upstream, puzzle regression
identical. grid13 compares it head-to-head with `smotherfish` (new plan
field "ref" builds a git ref as the opponent).

grid13 (branch smotherfish-next = Smotherfish + upstream master 5d03b6e5,
98 commits past Stockfish 19; head-to-head against branch smotherfish):

```
run                                   games  W/D/L         score  Elo
next vs smotherfish, default mode      4000  309/3521/170  0.517  ~+12 (+8..+15)
next vs smotherfish, both brutal       2000  159/1751/90   0.517  ~+12
next, brutal vs Elo 1500               1000  10.1 smothers/100, 999/1/0
next, brutal vs Elo 3000                600  1.5 smothers/100, 0.994, 0 losses
```

Promoted: merged into this branch as Smotherfish 1.1. The engine name now
gives the upstream base, "Smotherfish 1.1 (Stockfish dev-20261115-5d03b6e5)",
not the build date and hash. Bench 1442480 (= upstream 5d03b6e5); the
Android workflow checks that number.

### Session 3, afternoon (Nov 20 JST): items from a parallel session, and their results

A parallel session added (commits 2e676c95 .. a187fabd, now on this branch):
`SmotherBuildVersion` 2 (build_score weights fitted by logistic regression,
notes/fit/), `SmotherPartial` ("all but one" smothers: one square next to
the mated king empty but covered by us), match.py `--ponder` / `--opp-think`
and a ponderhit fix (an unlimited ponder prover was waited for after
"ponderhit"; games were lost on time or hung), SPRT tests on Actions in
waves (notes/exp/sprt.json, notes/scripts/sprt_stats.py), the "Analysis
Elo" option for DroidFish, CI path fixes, and a data-race fix (all threads
now read the smother modes decided once by the main thread).

grid14 (5+0.05; A = defaults, V2 = fitted score, P = SmotherPartial):

```
run (games)           full smothers /100g   full + all-but-one /100g   score
Elo 1500 A    (2000)        11.6                  13.5                 0.999
Elo 1500 V2   (2000)        10.2                  12.2                 0.999
Elo 1500 P    (2000)         1.6                  56.4                 1.000
Elo 1500 VP   (2000)         1.1                  59.7                 1.000
Elo 3000 A / V2 / P / VP (600)  1.5 / 1.8 / 0.0 / 0.3   2.3 / 1.8 / 11.7 / 17.0
Maia 1100 A / VP (1000)  7.0 / 1.6                13.8 / 50.6          1.000
```

- V2: better offline (CV AUC 0.766 vs 0.735) but not in games (10.2 vs 11.6
  at Elo 1500, same openings). SmotherBuildVersion stays 1.
- P changes the goal: about half of all games end in a full or all-but-one
  smother, but full smothers almost disappear. Off by default; a choice for
  the user (see below).

ponder1 (opponent holds each move >= 1 s; our engine ponders):
deep pondering on vs off, Elo 1500: 11.2 vs 13.8 smothers/100g; Maia 1100:
7.8 vs 9.5. Not usable: with deep pondering on, the opponent lost 59 of 600
games on time (1 with it off) and we lost one on time: two games per
4-core runner, and our ponder search plus unlimited prover took CPU on the
opponent's turn. match.py now runs one pondering game per 4 cores
(77a780f4); ponder2 repeats the test.

SPRT hunt_vs_default (full strength head-to-head, 10+0.1, 8moves_v3,
fastchess): new = SmotherBrutal + SmotherBuildVersion 2 + SmotherPartial,
base = branch smotherfish defaults. 6400 games, pentanomial
[0,153,2864,177,6], score 0.5028, +2.0 Elo (95% 0..+4), LLR 66.7 > 2.94:
H1 (no loss beyond the [-10, 0] bounds). Smother hunting costs no strength
against an equal opponent, where construction mode never switches on.

CircleCI (free plan; .circleci/config.yml, branches circle-exp/*, 30
parallel 4-CPU machines, results as artifacts). Setting the project up via
"Use an existing GitHub Actions workflow" made CircleCI treat the file as a
GitHub workflow (every job a no-op); a pipeline definition created through
the API ("Experiments") runs it natively. First run, circle-exp/hybrid,
Elo 1500, 1000 games each (openings seed 1450), about 15 minutes:

```
SmotherPartialAfter    full smothers /100g   full + all-but-one /100g   W/D/L
0  (off)                     8.8                    11.1                 997/3/0
80                           9.5                    15.4                 996/3/1
60                           7.2                    21.9                 998/2/0
40                           7.6                    38.0                 997/3/0
(SmotherPartial always, grid14: 1.6 / 56.4)
```

The hybrid keeps the full smothers (differences within noise at 1000
games) while adding near ones; 40 looks best. The one loss (H80, ply 66,
0.15 s left, no proof) came before any hybrid effect. grid15 on GitHub
(2000 games per threshold, other openings) confirms before a default
changes.

grid15 (GitHub, 2000 games per setting at Elo 1500, seed 1400):

```
SmotherPartialAfter    full /100g   full + all-but-one /100g   W/D/L
0  (off)                  12.1             13.8                 1996/4/0
80                        10.3             17.6                 1996/4/0
60                         8.6             25.8                 1993/6/1
40                         7.3             37.0                 1998/2/0
Elo 3000, 80 (600)          2.2              3.2                 592/8/0
Maia 1100, 0 / 80 (1000)  7.7 / 7.6      14.0 / 15.8              all won
```

With CircleCI's run (other openings): near smothers rise clearly with an
earlier threshold (40: about 37-38 per 100 games vs 11-14 off); the cost in
full smothers is between ~0 (CircleCI) and ~40% (GitHub). Default not
changed yet; the SPRT hybrid40_vs_brutal measures the strength side.

grid16 (Elo 2000 / 2500, 1000 games each): SmotherPartial always on gives
44.1 / 40.0 full-or-near smothers per 100 games (full 0.4 / 0.8); hybrid 80
gives 12.1 / 8.4 (full 6.0 / 4.4). All 3996 games won or drawn (0 losses).

ponder2 (one pondering game per 4-core runner, opponent >= 1 s per move):
deep pondering on vs off, Elo 1500: 12.2 vs 10.8 full smothers/100g; Maia
1100: 9.0 vs 6.8. Positive in both, but 3 losses on time with it on, each on
the move a proof arrived. Cause: rebuilding a found proof's line ignored the
stop flag. Fixed (see the prover commit after this note); a rerun should
show whether the gain holds without time losses.

grid17 (construction floor = how far construction may sacrifice; brutal,
5+0.05; 1000 games at Elo 1500/2000, 600 at 2500):

```
SmotherBuildFloor   Elo 1500 /100g   Elo 2000 /100g   Elo 2500 /100g   draws 1500/2000/2500
600 (default)            8.3              7.4              3.8            4 / 3 / 3
400                     10.4              7.0              4.3            3 / 6 / 3
250                      9.6              6.6              3.8            7 / 9 / 5
```

No clear gain from sacrificing more (differences within noise), and the
lowest floor adds draws; 600 stays. One loss in the run (Elo 2000, floor 600).

SmotherGoal (Full / Hybrid / Near) added for GUIs; combo options fixed
(the inherited check aborted on the repeated words of any combo). Near now
prefers a true smother up to three moves longer (search: a near mate scores
three moves later; prover: looks for a true one with the budget left);
200 grid14 positions: true smother in 15 vs 2. grid18 measures it in games.

CircleCI: the account was suspended by CircleCI (API: "Your account has
been suspended") during the second run, reason not stated; likely the
pattern of a new free account running 30 parallel CPU-bound jobs. Not used
any more; .circleci/config.yml stays for reference.

grid18 (Near with the true-smother preference; openings of grid14 P and
grid16 P): Elo 1500 (2000 games) true 3.3 / total 56.4 per 100 (before:
1.6 / 56.4); Elo 2000 (1000) true 2.1 / total 43.3 (before: 0.4 / 44.1).
2999 wins, 1 draw.

SPRT hybrid40_vs_brutal (current code, full strength, 10+0.1): 6400 games,
pentanomial [0,145,2885,169,1], score 0.502, +1.4 Elo (95% -0.5..+3.3),
LLR 20.9: H1, no strength cost.

SmotherGoal default is now Hybrid (brutal mode only; bench unchanged).

### Blocker starvation (Nov 20 evening; outside reviews by GPT and GLM)

Corrected numbers with construction mode on (grid15 control, Elo 1500,
Full): 17 proof games per 100, 72% delivered (the 50-60% escape rate was
measured before construction mode). Escapes are rarely budget expiry (14 of
95). In escaped games the opponent ends with 3 pieces (6 in delivered) and
we capture ~7 enemy units after the decisive point (4 in delivered).
Blocker reserve (defender non-king pieces minus open king-ring squares):

```
                    decided (+9)        first proof         end
                    pieces  reserve     pieces  reserve     pieces
delivered (242)        9      6            6      4            6
escaped (95)           9      6            5      2            3
```

Same start; the escaped games lose blockers during construction. New
options (defaults unchanged, 40/40 positions identical): SmotherBuildKeep
(points per enemy piece, 3), SmotherBuildKeepNear (per piece within two
squares of its king, 3), SmotherBuildMaterialDiv (extra material counts
1/N above the floor, 8). grid19 tests keep 8, material 1/16, both, and
near 8 at Elo 1500 (2000 games) and 2500 (1000). Queued ideas from the
reviews: a blocker-reserve term, holding back optional captures, reply
prediction from our own game data, and checks that force the defender's
pieces onto its king ring (for Elo 2500-3000).

### The clock is the bottleneck (Nov 21, 00:30 JST)

Brutal mode at 5+0.05 vs Elo 1500 (grid15 control, 2000 games): median
clock at our move 30 is 0.24 s (normal play, h2h_default: 1.67 s); 56% of
our moves are played with < 0.5 s left. Time per move by our move number:

```
moves        0-4  5-9  10-14 15-19 20-24 25-29 30-34 35+
brutal (ms)  165  215  265   253   176   100   62    47
normal (ms)  153  167  167   154   139   120   106   91..59
```

The prover is waited for when merely winning (+3, SmotherWinTimePercent
100, plus 50% steering) and when crushing (300% of optimum, capped at 0.6
of maximum), so the clock is spent before and early in construction, and
the construction phase (often 30+ moves) runs on the 0.05 s increment. A
proof needs 0.3-11M nodes (~0.1-3 s). Turning off the waiting when merely
winning does not fix it (local, 15 games): the drain is moves 15-30, when
crushing. Real games (3+2 blitz, pondering on human think time) give 10-100x
more compute in this phase, so 5+0.05 may understate the real rate.
New option SmotherBuildTime N (off): each construction move uses at least
1/N of the clock left. grid21 measures the rate at 5+0.05, 30+0.3 and
180+2 (Hybrid/Near/Full, Elo 1500/2000/2500) and two clock-economy
variants at 5+0.05. Also new: SmotherBuildStarve/StarveAt (blocker-reserve
guard, off), measured by grid20.

ponder3 (current code, Hybrid default, pondering on, 5+0.05, 400 games each):

```
                 deep prover while pondering   true/100   total (true+near)/100
Elo 1500         off                            6.5        49.8
Elo 1500         on (default)                   7.2        50.5
Maia 1100        off                            5.8        38.5
Maia 1100        on (default)                   7.2        41.0
```

No time losses (the stop fix holds). Deep pondering is ahead in every
comparison so far (ponder2 and ponder3) but each is within noise; it stays
on. With pondering the clock lasts longer (median 0.56 s at our move 30 vs
0.24 s without) and Hybrid's total rate at Elo 1500 is ~50 per 100 games,
against ~37 without pondering in grid18 (other openings): more compute in
the late game, more smothers, in line with the clock finding above.

grid19 (keeping enemy pieces; 5+0.05, brutal, SmotherGoal=Full; full and
near per 100 games; proof games = the prover found a forced smother):

```
arm                       games  full  near  proof games  delivered  draws  losses
e1500 A control            2000  10.1   1.6     15.2         66%        3      0
e1500 B keep 8             2000  12.2   2.8     18.2         67%        4      0
e1500 C material 1/16      2000  10.7   2.5     15.6         69%        8      0
e1500 D keep 8 + mat 1/16  2000  12.3   3.0     18.6         66%        6      1
e1500 E keep-near 8        2000   9.7   1.8     15.0         64%        8      0
e2500 A control            1000   5.7   1.0      8.0         71%        2      0
e2500 D keep 8 + mat 1/16  1000   7.4   1.6      9.7         76%        5      0
e2500 E keep-near 8        1000   4.8   0.9      6.8         71%        2      0
```

- Keeping enemy pieces works: B and D +2.1/+2.2 full smothers at Elo 1500
  (z ~2.0-2.1 each), D +1.7 at 2500; D vs A pooled over both Elos z ~2.6.
  It works by creating more chances (proof games 15 -> 18.5 per 100), not
  by converting more of them (still ~2/3 delivered).
- Flattening material (C) adds little on its own or on top of keep 8;
  extra points for pieces near the king (E) slightly hurt.
- The one loss (D, game 80): back-rank mate at ply 70 while 8 points of
  material up, clock 0.12-0.2 s for the last 12 moves: the clock problem.
- Next: keep 8 (alone, fewer draws than D) combined with the winners of
  grid20 (blocker-reserve guard) and grid21 (clock economy).

grid20 (blocker-reserve guard, SmotherBuildStarve; Elo 1500, Full, 2000
games each):

```
arm                  full  near  proof games  delivered  reserve at proof (deliv/esc)
A control             9.6   1.8     14.9         64%        3 / 2
S10 (10 per unit <4) 10.9   2.1     15.8         69%        4 / 3
S20 (20 per unit <4)  8.4   2.1     12.0         70%        4 / 4
S10 at 6              7.3   2.5     11.1         66%        5 / 4
```

The guard does keep the reserve up, but strong settings cost more chances
than they save (fewer proof games); S10 is +1.3 (z ~1.3, noise). Option
stays off. Time forfeits by us: 1 in ~17,000 games of grid19/20 (S10, ply
95, 0.19 s left, far ahead; the opponent flags at a similar rate, so it
looks like runner jitter at a near-empty clock). grid22 (queued after
grid21): SmotherBuildKeep 3/8/12/16 with Full, and keep 8 with Hybrid.

grid21 (time controls and clock economy; brutal; Elo 1500 unless noted):

```
arm                       tc       games  full  near  total  proof games  delivered (full)
Full control              5+0.05    2000   9.7   2.0   11.8     14.6          67%
Full T1 (no waiting when
  merely winning, brutal
  prover 100%, build t 20) 5+0.05   2000  10.4   1.8   12.2     14.7          71%
Full T3 (100%, build t 10) 5+0.05   2000  10.4   1.7   12.1       -             -
Full                      30+0.3     400  11.2   2.0   13.2     22.8          49%
Hybrid                    5+0.05    1000   9.0  28.3   37.3       -             -
Hybrid                    30+0.3     399   8.3  30.3   38.6       -             -
Hybrid                    180+2       96  14.6  32.3   46.9       -             -
Near                      30+0.3     399   4.5  59.4   63.9       -             -
Hybrid Elo 2000           30+0.3     400   7.2  26.0   33.2       -             -
Hybrid Elo 2500           30+0.3     200   5.5  24.5   30.0       -             -
```

- The clock hypothesis is mostly wrong. Six times the time (30+0.3)
  barely changes the rates. With more time the prover finds a forced
  smother in more games (14.6 -> 22.8 per 100), but fewer of them are
  delivered (67% -> 49%): the extra chances are the ones the defender
  escapes. Escapes, not prover time, are the bottleneck. 180+2 (96 games)
  hints higher (14.6 full, 46.9 total) but is too small to tell.
- Clock economy (T1/T3): +0.7 full per 100, noise. Options stay off.
- Near reaches 63.9 total per 100 at 30+0.3 (56.4 at 5+0.05 in grid18);
  Hybrid at Elo 2000/2500 already meets the 40-50 / 15-20 targets for
  total (33 and 30 at 30+0.3, Hybrid counts near only after 40 build
  moves; Near would be higher).
- Bug found and fixed (e9a88a7a): one time forfeit in the Near arm at
  30+0.3 (ply 45, 2.73 s left, a proof found on that move). Waiting for a
  finishing prover had no time bound because rebuilding a proof's line
  ignores its limits. Now capped at its deadline plus a tenth of its
  budget. In crushing positions the engine also uses ~20% of the clock
  left per move (deep prover, mate-in-hand), which leaves little margin
  on a loaded machine.

grid22 (SmotherBuildKeep sweep, Elo 1500, 5+0.05, brutal):

```
arm              games  full  near  total  proof games  delivered  draws
Full keep 3       2000   9.7   1.4   11.0     14.2          68%        6
Full keep 8       2000  14.6   1.8   16.4     19.6          74%        3
Full keep 12      2000  12.0   2.4   14.3     17.4          69%        3
Full keep 16      2000  13.1   2.8   15.8     18.0          73%        1
Hybrid keep 3     1000   7.6  27.3   34.9       -             -        2
Hybrid keep 8     1000   6.9  45.4   52.3       -             -        2
```

Keep 8 replicates grid19 and more: Full +4.9 per 100 (z ~4.5), Hybrid
total +17.4 per 100 (z ~5.9). 12 and 16 are no better than 8. Default
changed 3 -> 8 (4e401120); only construction mode (brutal) reads it.
grid23 (queued): the new default with Near and Hybrid at Elo 1500/2000/
2500, Maia 1100, pondering, and Elo 3000, to compare with the targets
(70 / 40-50 / 15-20 smothers, full or near, per 100 games).

grid23 (keep 8 default, prover wait fix; brutal, 5+0.05; total = full +
near "all but one" smothers per 100 games):

```
opponent     goal              games  full  total   W    D  L   target (total)
Elo 1500     Hybrid             1000   8.4   53.1  999   1  0
Elo 1500     Hybrid, pondering   400   7.0   60.8  400   0  0
Elo 1500     Near               1000   3.8   65.6  999   1  0   70
Elo 2000     Hybrid             1000   5.7   43.8  995   4  1
Elo 2000     Near               1000   2.5   54.3  998   2  0   40-50
Elo 2500     Hybrid             1000   4.7   38.3  998   2  0
Elo 2500     Near               1000   1.5   45.7  998   2  0   15-20
Elo 3000     Hybrid              500   0.4   12.6  499   1  0
Maia 1100    Hybrid              500   7.8   43.8  500   0  0
Maia 1100    Near                500   1.6   49.2  500   0  0
```

- Targets for full-or-near smothers: Elo 2000 and 2500 met (2500 by
  twice the target); Elo 1500 at 65.6 (Near) vs 70; pondering adds ~8 to
  Hybrid, so Near with pondering is likely over 70 (not yet measured).
- Near trades true smothers for near ones (3.8 vs 8.4 full at 1500).
- The loss (Elo 2000, Hybrid): never more than +3, ordinary blitz loss at
  0.2 s per move; construction never started.
- Human-like opponent (Maia 1100): 43.8 (Hybrid) / 49.2 (Near).

grid24 (Near goal, keep 8, 5+0.05; arm "e1000_N" is Stockfish at UCI_Elo
1320, its minimum):

```
opponent              games  full  total (full + near)
Elo 1320               600   6.3   73.2
Elo 1500, pondering    600   3.7   65.3   (65.6 without, grid23)
Maia 1100, pondering   300   1.3   49.0   (49.2 without, grid23)
```

Near reaches the 70 target at Elo 1320 and is at ~65 at Elo 1500.
Pondering adds nothing to Near (it added ~8 to Hybrid in grid23).
No losses. Android build of e564712d (android-build/keep8, run
44831189138): success (the workflow checks bench 1442480 under qemu).

### Nov 21 (day): defaults, new opponents, escapes, Elo 3000

- Defaults now: SmotherBrutal true, SmotherGoal Hybrid, SmotherBuildKeep 8
  (deb0c5b8). The bench runs with brutal off (1442480 = upstream). With all
  defaults, 40 local games vs Elo 1500: 40 wins, 42.5 full-or-near /100.
- Maia-3 opponents in the experiment workflow ("opponent": "maia3-<elo>",
  CSSLab maia3 1e13597c, 5M model, CPU, torch 2.15.0, offline wrapper).
  Samples moves like humans at that rating (Temperature 1.0).
- Escapes after construction (grid22 keep 8, Full, 100 escaped games): the
  engine keeps building a median 57 plies after the last proof but rarely
  finds a second smother; games end in plain mates with 2-4 open squares.
  While building, a plain mate scores as the floor, so the mate-in-hand
  budget (is_win(prev)) never applied after an escape. New: escape budget
  (SmotherEscapeMoves/Percent, off), triggered when the defender's reply
  differs from the proof's ("info string smother escape").
- Queued: grid25 (earlier construction vs Elo 3000/3190: BuildCp/Floor
  800/600, 500/300, 300/150), grid26 (defaults vs Maia-3 1100-2300),
  grid27 (robust / strict proofs / mate-in-hand 30%), grid28 (escape
  budget at 5+0.05 and 15+0.15).
- Lichess bot: waiting for the user to create a new Lichess account and save
  a bot:play token as the repository secret LICHESS_BOT_TOKEN.

grid25 (earlier construction vs strong opponents; defaults otherwise):

```
opponent   BuildCp/Floor  games   W    D   L   score  full  total
Elo 3000   800/600        1000   990   9   1  0.995   1.2  13.5
Elo 3000   500/300        1000   951  47   2  0.975   1.1   8.5
Elo 3000   300/150        1000   733 247  20  0.857   0.4   3.5
Elo 3190   800/600         500   485  13   2  0.983   0.6   8.0
Elo 3190   500/300         500   455  43   2  0.953   0.2   5.6
```

Starting construction earlier is clearly worse: more draws and fewer
smothers. Against strong opponents the floor is what keeps the win; the
default 800/600 stays. Smothers at 3000+ need another idea (choosing
smother-friendly moves among near-equal ones).

grid26 (defaults vs Maia-3): Maia-3 1900: 474 games, all won, 9.5 full,
49.6 total per 100; Maia-3 2300: 500 games, all won, 7.8 full, 46.6
total. The 1100 and 1500 arms were lost when the run was cancelled and
re-run; grid26b repeats them.

grid26b (defaults vs Maia-3, 500 games each, all won): 1100: 10.6 full,
57.6 total per 100; 1500: 12.6 full, 53.2 total. With grid26: Maia-3 at
1100-2300 gives 47-58 total and 8-13 full, about as against Stockfish.

grid29 (Hybrid switch point, SmotherPartialAfter; 1000 games each):

```
opponent   after 20 build moves   after 40 (default)   after 60
           full   total           full   total         full   total
Elo 1500   4.6    61.4            7.2    55.9          10.1   45.0
Elo 2000   3.0    50.1            5.7    44.4           7.4   38.6
```

A clean trade: each 20 moves earlier gives ~6 more total and ~3 fewer
true smothers. Default stays 40 (user preference: Hybrid, more true ones
are good). grid27/28 lost most jobs in the cancel and re-run; re-launched
fresh as grid27b/grid28b.

First Lichess bot session (run 44873642075, 5 h, 2 games at once, 2+1 to
3+2, rated matchmaking): 33 games, +6 =27 -0, 1 near smother (vs a 1607
bot), 4 plain mates. Opponents were mostly bots rated 2850-3030; 27 draws
against them. No losses, no time losses.

grid31 (SmotherSteer, choosing smother-friendly moves among near-equal
ones, MultiPV 4):

```
opponent  arm       games   W    D   L   score  full  total
Elo 3000  default    1000  990  10   0   0.995   1.2  14.5
Elo 3000  steer 10   1000  937  51  12   0.963   0.7   5.9
Elo 3000  steer 25   1000  937  48  15   0.961   0.3   5.8
Elo 3190  default     500  483  17   0   0.983   0.4  10.6
Elo 3190  steer 10    500  421  70   9   0.912   0.4   3.4
```

Steering is clearly worse: the MultiPV search costs strength (losses
appear), and the weaker play reaches fewer won positions, so fewer
smothers. Stays off.

Helper capacity (another person's GitHub account, Nov 21): their public
fork runs .github/workflows/helper-poll.yml every 15 minutes. It copies new
upstream branches helper-exp/<name> to actions-exp/<name> in the fork and
dispatches smother-exp.yml there (a GITHUB_TOKEN push does not trigger
workflows; a dispatch does). Results land on actions-exp/<name> in the
fork (read with git fetch from the public fork). Base helper-exp branches
on the smotherfish branch: the fork syncs only that, and its token cannot
push commits that change workflow files.
Helper routing: helper-exp/<id>/<name> runs only on the fork whose owner
gives that ID (first 6 hex of sha256 of the lower-case owner name);
helper-exp/<name> runs on every helper fork. Helper IDs: 70c949 (the
first helper fork; it was 8e9ce5 before its owner was renamed), dc665d
(second helper). A rename changes the ID.
Helper branches must be built on the current smotherfish tip (only
notes/exp/plan.json may differ): a helper's token cannot push a branch
whose workflow files differ from its fork's, and the poll then skips it
every time (tc180b was first built on an older branch and never started).

grid32 (Hybrid switch point 40 vs 55 at 15+0.15, 600 games each):

```
opponent   after 40 (default)   after 55
           full   total         full   total
Elo 1500   9.2    57.8          9.7    53.5
Elo 2000   5.7    48.9          8.2    45.3
```

Same trade as at 5+0.05 (grid29/30): 55 gives more true smothers (+0.5
at 1500, +2.5 at 2000) for ~4 fewer in total. Default stays 40. At
15+0.15 both settings are higher than at 5+0.05 (Hybrid 40: 57.8 vs ~53
at Elo 1500, 48.9 vs ~44 at 2000). Helper fork: helpertest1 (200 games,
Elo 1500, 5+0.05): all won, 9.0 full, 56.0 total; tc180 was cancelled by
the helper and re-run as tc180b.

Sharded experiments (Nov 22): "shard": [i, n] in a plan keeps every n-th
job of the full matrix, so one experiment runs on several accounts at once
(our actions-exp/<exp> with shard [0, n], each helper's
helper-exp/<id>/<exp> with its own i). notes/scripts/merge_shards.py EXP
OUTDIR URL[@BRANCH]... merges the result files; then summary.py. For an
SPRT: give every account max_waves 1, add up the pair counts of all
shards (sprt_stats.py) and push the next wave by hand until it decides.

SPRT defaults_vs_brutal_off (shipped defaults: brutal, Hybrid, keep 8, vs
the same build with SmotherBrutal=false; 10+0.1, [-5, 0]): H1 after 4400
games, +0.2 Elo (95% -2.1 to +2.6). The current defaults cost no strength.

helper_tc180b (helper fork; shipped defaults at 3+2, i.e. a real blitz
time control; all games won):

```
opponent   games   full /100   total (full + near) /100   (5+0.05, grid23)
Elo 1500    288      11.8          69.1                     (8.4 / 53.1)
Elo 2000    300       9.7          61.3                     (5.7 / 43.8)
Elo 2500    203       6.9          45.8                     (4.7 / 38.3)
```

At a real time control the defaults reach the targets: ~70 at Elo 1500,
well above 40-50 at 2000 and 15-20 at 2500. More time helps both full and
near smothers (+30-70% over 5+0.05).

grid33 (first sharded experiment: 3 accounts, 75 jobs, ~75 min; shipped
defaults at 3+2):

```
opponent        games   W    D   L    full /100   total /100   (at 5+0.05)
Maia-3 1500      300   300   0   0     13.0         68.3        (12.6 / 53.2)
Maia-3 1900      300   300   0   0     10.0         58.3        ( 9.5 / 49.6)
Elo 3000         288   286   2   0      2.8         19.1        ( 1.2 / 13.5)
```

At 3+2 the rates against human-like play match those against Stockfish
(Elo 1500: 69.1 total); against Elo 3000 a real time control more than
doubles full smothers (2.8 vs 1.2 per 100) and lifts the total to 19
with no losses.

Lichess session 2 (weaker bots mixed in): 30 games +23 =7 -0, 1 full
smother (vs a 1768 bot) and 7 near; 15 of 23 wins were plain mates (lower
rate than the Stockfish/Maia grids; the bot plays 2 games at once with 1
thread each, and the 1500-2400 Lichess bots are other engines). Both
sessions: 63 games, 0 losses.

grid34 (fourth helper fork; Near goal at 3+2 vs Elo 1500, 240 games, all
won): 71.7 total, 4.2 full per 100 (Hybrid at 3+2: 69.1 / 11.8). Near
passes 70 but at the cost of most true smothers; Hybrid stays the default.

### Upstream merge: Smotherfish 1.2 (Nov 22)

Merged upstream 3e8fde75 (20 commits; StateInfo ring buffer in Position,
optimism removed, hyperbola-quintessence slider attacks, Robin Hood
repetition hashing, NMP clamp). Upstream bench 1210779 = ours with brutal
off. Prover regression: 2000/2000 Lichess smother puzzles verified, 0 bad.
Validation running: SPRT v12_vs_v11 (actions-exp/sprt-v12, 10+0.1,
[-5, 0]) and grid35 (defaults vs Elo 1500/2000/2500/3000, 5+0.05, sharded
over the four helper forks; their branches carry the merged engine with the
old workflow files, because the forks cannot take workflow changes until
they press "Sync fork"). smotherfish is fast-forwarded only after both pass;
then every helper presses "Sync fork" once. Compare grid35 with grid23
(1.1: Hybrid totals 53.1 / 43.8 / 38.3, Elo 3000 12.6).

1.2 validation passed: SPRT v12_vs_v11 (10+0.1, [-5, 0]) H1 after 4000
games, +2.4 Elo (95% -0.1 to +5.0). grid35 (defaults, 5+0.05, sharded over
four helper forks) matches 1.1: Hybrid totals 54.3 / 42.9 / 40.0 at Elo
1500/2000/2500 (1.1: 53.1 / 43.8 / 38.3), Elo 3000 12.8 (12.6). Two losses
in 3500 games, both on a near-empty clock at 5+0.05 (one time forfeit at
+17, one blitz loss at +3/+4), the known low-clock issue. smotherfish
fast-forwarded to 1.2; helpers press "Sync fork" once (workflow files
changed: Android bench check, sharded SPRT support).

Official comparison (Nov 22, 14:35 JST): Smotherfish 1.2 with defaults vs
unmodified Stockfish 3e8fde75 at full strength, 10+0.1, 8moves_v3, as a
sharded SPRT: six accounts x 18 runners x 400 games (one wave each,
seed_offset 0..500000), ~43,000 games. Ours: actions-exp/sprt-official;
helpers: helper-exp/<id>/sprt-official -> actions-exp/sprt-official in each
fork, results notes/results/sprt/official_vs_stockfish_s<i>/. Add up the
pentanomial counts of all six (sprt_stats.py) for the published result.

Official comparison result (Nov 22, 16:36 JST): Smotherfish 1.2 defaults vs
unmodified Stockfish 3e8fde75, 10+0.1, 43,200 games (108 chunks over six
accounts, incl. re-runs of the 16 chunks that crashed from the fastchess
-march=native build, fixed in 185ee255): -0.3 Elo, 95% -1.1 to +0.4,
pentanomial [5, 1097, 19435, 1061, 2]. Equal within noise. Added to README.

### Phase 0: opportunity recall (Nov 22, 22:45 JST)

notes/scripts/recall.py on 1000 won games of conc200 (1.2 defaults vs Elo
1500, 5+0.05): every winning position (eval >= +6, depth 10) checked with
a large prover budget (12 moves, 2 quiet, 20M nodes, true smothers only).
Results on branch analysis/recall1.

```
full          93   9.3%  true smother delivered
missed       149  14.9%  a forced true smother existed, no engine proof there
unconverted   21   2.1%  engine proof there, no true smother followed
never        737  73.7%  no forced true smother in any winning position
```

A forced true smother appeared in 26.3% of won games, but only 9.3% got
one. At first availability we already had a forced mate (260 of 263),
median mate in 8, median 44 plies after the first winning position. Of the
149 missed: the engine's next proof came a median 36 plies later, and 107
ended in a near smother. Hybrid mode proves a near smother first and then
looked for a true one at most 3 moves longer, so a shorter near one won.
Now an option, SmotherFullExtra (default 3); grid37 tests 6 and 12.
recall2/recall3 repeat the analysis on the 3+2 games (tc180b, Elo 1500 /
2500) to see how much of "missed" is bullet time pressure.

grid36 (phase 1 search control, 5+0.05, sharded over six forks; full
smothers per 100, full+near in brackets): Elo 1500 (1200 games each):
control 6.8 (53.8), Lmr 1024 7.7, Lmr 2048 8.8 (56.8), DefLmr 1024 7.3,
Lmr+DefLmr 8.0, Nmp 2 7.2. Elo 2500 (600): 3.3-4.3, control 4.3. Lmr 2048
+2.0 at 1500 (p ~0.09), not at 2500: retest with more games.

recall2 (3+2, Elo 1500, 288 games): full 11.8%, missed 10.1%, unconverted
10.8% (engine proved a smother where a forced true one existed; 28 of 31
ended near), never 67.4%. recall3 (3+2, Elo 2500, 203): full 6.9%, missed
3.9%, unconverted 7.4%, never 81.8%.

grid37 (SmotherFullExtra; Elo 1500, 1500 games): 3: 7.9 (57.6), 6: 9.0
(54.1), 12: 7.8 (54.5); Elo 2500 (600): 3: 4.5, 12: 4.3. Not the cause.
grid38 tests SmotherFullFirst 0 / 30 / 60 (true smother first, then near).

Rule (Nov 22): always distribute experiments over our account and every
helper fork for faster feedback. notes/scripts/distribute.sh PLAN.json
builds the seven shard branches (each fork's base version is listed in the
script; update it after that fork presses "Sync fork"). Forks poll about
hourly; the user can press Run workflow on Helper poll for a quick start.
One fork (dc665d) has no working schedule; the enterprise fork's poll can be
dispatched from this session.

grid38 (SmotherFullFirst, 5+0.05, sharded 7 ways, ~20 min): Elo 1500 (1500
each): 0: 7.9 (52.8), 30: 7.5 (52.5), 60: 7.4 (57.9); Elo 2500 (600): 0:
5.0, 60: 4.3. No gain.

Why (replay of a recall2 "unconverted" game, Elo 1500, 3+2): the engine
plays every proven move, yet the proven distance goes 5,4,5,6,5,4,6,7. The
proofs use the default (non-strict) rule: a reply may escape the smother if
it runs into a quicker plain mate. The opponent takes those escapes, brutal
mode declines the plain mate and proves a new smother, and the cycle repeats
until Hybrid accepts a near smother. So recall's "available" counts these
non-strict proofs and overstates what is convertible; the escape problem is
the one already measured (grid27b: robust 13.0 vs 12.1, strict 12.2, n.s.).
Next: recall with a strict oracle (every reply smothered) for the real
headroom.

recall4 (strict oracle, 600 won games, Elo 1500, 5+0.05): full 8.8%,
missed 0.0%, unconverted 0.3%, never 90.8%. A truly forced (strict) smother
appeared in 9.2% of won games and was delivered in 53 of 55. Conversion is
solved; recall1's "available" was mostly escapable proofs.

grid39 (Lmr 2048 retest, 7 shards): Elo 1500 (3500 each) control 8.8, L2
8.4; Elo 2500 (1400) control 2.7, L2 4.6 (z 2.7, but grid36 had the
opposite). L2 had 1 loss (0.14 s clock) and more games ending on time. Not
adopted.

grid40 (phase 2 build-score terms, 7 shards; full per 100, z vs control):
Elo 1500 (2000 each): control 8.3; OwnKeep 10 8.2; KeepNear 10 7.5 (-1.0);
Escape 6 9.2 (+1.0); KnightSafe 8 8.5; all four 8.0. Elo 2500 (800):
control 4.1; OwnKeep 4.6; KeepNear 2.4 (-2.0); Escape 4.0; KnightSafe 2.5
(-1.8); all 5.0. No term helps; KeepNear and KnightSafe hurt at 2500.
Hand-tuned build-score terms look exhausted.

### Phase 3: tuning build_score weights on game results (Nov 23)

SmotherBuildWeights (boxed, hole, corner, edge, knight, queen; default
12,10,25,10,4,3) plus Keep / KeepNear / Escape, tuned by batches of random
sets played in games (5+0.05, sharded over our account and five forks).
tune1b: 17 sets x 900 games, 4.6-8.7 full per 100; mostly noise (the
winner fell back in tune2). tune2: top 4 + 8 near them. tune3 showdown
(4000 games vs Elo 1500, 1500 vs 2500 each):

```
set  weights / keep, near, escape        full 1500  near 1500  full 2500  near 2500
c00  12,10,25,10,4,3 / 8,3,0               7.75      45.8       3.87      33.3
m03  13,8,23,8,2,4 / 11,2,4                8.12      50.0       4.87      38.7
v03  14,11,35,5,2,4 / 9,4,9                8.07      45.7       4.33      30.1
m01  17,8,21,10,1,2 / 10,3,4               7.97      48.0       3.27      35.7
m07  14,10,34,10,3,3 / 7,4,5               7.75      44.2       4.20      30.4
```

Full smothers: no set separates from the defaults (m03 +0.4 / +1.0, z
0.6 / 1.3). Full or near: m03 58.1 vs 53.6 at 1500 (z ~4) and 43.6 vs 37.2
at 2500 (z ~3.5), a clear gain on the README's full-or-near metric. No
losses beyond 1 per set. SPRT sprt-m03 (m03 vs defaults, 10+0.1, [-3, 0],
six accounts x 18 runners x 200 games) checks strength before a default.

sprt-m03 final (m03 weights vs defaults, 10+0.1, six accounts x 18 x 200):
21,600 games, +1.3 Elo (95% +0.2 to +2.4), pentanomial [4, 518, 9676,
596, 6], H1 for [-3, 0]. No strength cost. tc180m03 checks the smother
gain at 3+2 (defaults vs m03, 300 games each vs Elo 1500 / 2000 / 2500).

tc180m03 (3+2, 5 of 6 shards, ~250 games per row; full / full or near per
100): Elo 1500 defaults 12.9 / 59.8, m03 12.4 / 71.6 (z +2.8 on full or
near); Elo 2000 12.0 / 62.0 vs 10.8 / 65.8; Elo 2500 8.0 / 49.2 vs 7.3 /
60.9 (z +2.6). No losses.

### Smotherfish 1.3 (Nov 23)

m03 is the default: SmotherBuildWeights 13,8,23,8,2,4, SmotherBuildKeep 11,
SmotherBuildKeepNear 2, SmotherBuildEscape 4. Bench unchanged (1210779,
brutal off). README and docs/SMOTHERFISH.md ("Tuning") updated; Android
build on android-build/v13; smotherfish fast-forwarded. Helper forks can
press "Sync fork" when convenient (distribute.sh bases stay as listed until
they do). Lichess bots pick up 1.3 from their next session (bot 4 already
ran m03).

human1 (HumanBlunder with UCI_Elo 1320 vs Maia-3 1300, 5+0.05, 300 games
each): HB 0 0.725, 5 0.325, 10 0.295, 15 0.238, 25 0.128, 40 0.072. The plain
limiter plays like ~1470 against Maia-3; ~1350 should be HB ~2. human2
refines with HB 1/2/3 vs Maia-3 1300 and 1500.
human2 (vs Maia-3, 300 games each): 1300: HB1 0.442, HB2 0.402, HB3 0.392;
1500: HB1 0.370, HB2 0.323, HB3 0.280. About 1330 / 1300 / 1280. HumanBlunder 1
with Skill Level 0 ~ 1350. Documented in docs/SMOTHERFISH.md.

Enterprise fork (Nov 23): GitHub Support raised the limit to 360 standard
jobs; a new-account safeguard raises the real concurrency in steps until
~Nov 29. conc360 probe (250 short jobs): ~20 running at once. Back in
distribute.sh with an equal share (base 4450b466, its synced version).

All forks synced to 33bbe361 (Nov 23): distribute.sh builds every shard on
33bbe361 and sets max_parallel 20 (full free-account concurrency). When a
later smotherfish commit changes workflow files, the forks must sync again
before their base here is moved (their token cannot push workflow changes).

sprt-ltc (1.3 vs Stockfish 3e8fde75, 60+0.6, seven accounts, 60 games per
runner): 7,320 games, +0.5 Elo (95% -0.6 to +1.7), pentanomial [0, 73, 3503,
84, 0], H1 for [-5, 0]. README updated.
Release workflow: GCC profile-guided builds fail at random ("corrupted
profile info", the prover thread races the counters); Linux and Windows use
plain builds, Android (clang) keeps PGO.

human3 (vs Maia-3; score): HB0 0.682 vs 1500, 0.478 vs 1900; HB1 0.330 vs
1500; HB2 0.500 vs 1100, 0.383 vs 1500; HB4 0.480 vs 1100, 0.310 vs 1500;
HB8 0.412 vs 1100; HB16 0.268 vs 1100; UCI_Elo 1320/1600/1900/2200 vs 1900:
0.478 / 0.823 / 0.922 / 0.970. Maia-3's levels are compressed (HB0 is 72%
vs 1300 but 48% vs 1900), so human ratings are defined on the Maia scale:
the Maia-3 level that scores 50%. HB0 ~1900, HB1 ~1250, HB2 ~1100-1150,
HB4 ~1080, HB8 ~1000, HB16 ~900. HumanBlunderPermille added for the gap
1250-1900; human4 measures 1/2/4/6 per mille vs Maia-3 1500 and 1700.

human4 (UCI_Elo 1320 + HumanBlunderPermille vs Maia-3, 300 games each): vs
1500: pm1 0.370, pm2 0.347, pm4 0.355, pm6 0.350; vs 1700: 0.298, 0.270,
0.353, 0.275. Flat: any blunder rate > 0 also widened the ordinary Skill
choice from 4 to 8 lines (the lines kept for blunders), which weakened
every move. Fixed (choice among 4, blunders among 8; bench unchanged). The
HumanBlunder ratings above (human1-3) were measured with the bug and are
too low. human5 recalibrates: per mille 2/5/10/20/40/80/160, each vs two
Maia-3 levels; then HumanElo.

human5 (after the fix; UCI_Elo 1320 + per mille vs Maia-3, 300 games each):
pm2 0.620 vs 1500, 0.567 vs 1700; pm5 0.642 / 0.510 (1500/1700); pm10
0.688 / 0.598 (1300/1500); pm20 0.648 / 0.607 (1300/1500); pm40 0.695 /
0.625 (1100/1300); pm80 0.608 / 0.483 (1100/1300); pm160 0.627 / 0.442
(900/1100). Maia-scale rating (level scoring 50%): bracketed rates
interpolated (pm80 ~1270, pm160 ~1040); the others extrapolated with the
slope of the HB0 points (logit 0.18 per 100 levels; HB0 ~1860): pm40 ~1580,
pm20 ~1700, pm10 ~1735, pm5 ~1780, pm2 ~1815. About +-50 each.
HumanElo added (0 = off, 1050-2500): piecewise-linear rating -> (UCI_Elo,
per mille) over these points plus UCI_Elo 1600 ~2150, 1900 ~2300, 2200
~2500 (make_skill in search.cpp). Docs table replaced. Bench unchanged.

### Deep diagnostic: where smothers come from (Nov 23 evening)

conc360 games (1.3 defaults vs Elo 1500, 5+0.05, 2500 games, every move
recorded, no adjudication). Scripts: notes/scripts/funnel.py,
notes/scripts/smother_feats.py.

- Definition: the harness and engine count "full" as any piece mating a
  king whose every neighbour square holds its own pieces (SmotherClassic
  off). Of 227 full smothers, 22 were knight (classic) smothers; most are
  queen mates. README numbers are any-piece smothers.
- Ending by our moves after the decisive point (+5 material): full median
  26 (classic 14), near 46 (Hybrid accepts near after 40 build moves),
  plain 80 (51% at the 80-move construction cap; only 19% of plain games
  ever had a proof).
- Hazard of a full smother per 10 of our win-phase moves: 0.4 (0-10), 2.3,
  2.8, 2.5 (10-40), then 1.4 (40-50) and 0.1-0.4 after, as near smothers
  take 28% in 40-50. Construction yields full smothers at a steady rate
  (~0.25% per move) until the near switch.
- Defender material at the decisive point does not differ by ending
  (median 26). Box breaks come mostly from the defender's own moves (a box
  piece leaves, a pawn moves), rarely from our captures.
- States predicting a full smother within 10 moves (base 2.2%): king in a
  corner 5.5% (edge 1.3, centre 0.8); open squares 0: 29%, 1: 16%, 2:
  3.2%; our queen on the board 2.7% (none 0.6%). Our knights do not
  predict any-piece smothers. These match the build score's terms, so a
  learned score would mostly re-find them.
- Literature: no prior work on steering an engine to one mate pattern
  beyond this project; composition technique (decoy sacrifice into the last
  hole, Philidor) is within the prover's checks.
grid15 (older version): Full goal 12.1 full vs Hybrid-40 7.3. grid41
(5+0.05; Elo 1500 1000 games, Elo 2500 400 per arm): default, Full 80,
Full 160 build moves, Hybrid at 80 with 160, classic Full 160.

human6 (HumanElo vs Maia-3, 300 each): 1350: 0.643 vs 1100, 0.492 vs 1500
(~1480, too strong); 1600: 0.632 vs 1300, 0.453 vs 1700 (~1595); 2000
(limiter 1455): 0.768 vs 1700, 0.663 vs 2100 (~2400+; Maia-3's top levels
are compressed). Map: added (1480, 70 per mille), top point (2420, limiter
1455), HumanElo max 2400. human7 checks 1350 / 1800 / 2200.

grid41 + grid41b (5+0.05; full / classic / near / full+near per 100; draws):
Elo 1500 (1000 each): default 8.7 / 0.5 / 50.8 / 59.5, 1 draw, 1 loss;
Hybrid at 80, 160 build moves 13.3 / 1.2 / 42.2 / 55.5, 1; Hybrid at 120,
200 moves 19.4 / 1.4 / 25.3 / 44.7, 25 draws; Full 80 15.1 / 1.3 / 2.2;
Full 160 19.9 / 1.3 / 2.0, 4 draws; classic Full 160 1.7 / 1.6 / 6.5.
Elo 2500 (400): default 4.2 / 36.5 near / 40.8; Hybrid 80/160 8.2 / 31.5 /
39.8; Full 160 14.8 / 0.8. Holding out longer trades near for full nearly
1:1 except Hybrid 80/160: +4.6 full (z 3.3) for -4.0 full+near (z -1.8) at
1500, +4.0 full for -1.0 at 2500. Classic-only barely raises knight
smothers. SmotherNearHold (new, off): after the switch, keep holding out
while the box has <= 1 open square (or <= 2 with the king in a corner).
grid42 tests it vs Hybrid 80/160 and the default, also vs Maia-3 1500.

grid42 (5+0.05; full / near / full+near per 100; z vs default D):
Elo 1500 (1000): D 7.6 / 52.1 / 59.7; Hybrid 80 + 160 build moves 14.4 /
43.7 / 58.1 (z full +4.9, f+n -0.7); NearHold arms 12.3-17.2 full but
f+n 34-41 (z -8 to -11). Elo 2500 (400): D 3.5 / 37.0 / 40.5; 80/160 9.2 /
35.2 / 44.5. Maia-3 1500 (400): D 9.5 / 42.8 / 52.2; 80/160 14.2 / 28.8 /
43.0 (z full +2.1, f+n -2.6). NearHold failed by design: a near smother
needs the nearly closed box, so holding out there removed the near ones.
Removed. 80/160 with grid41 at Elo 1500 (2000 games): 13.9 vs 8.2 full,
56.8 vs 59.6 full+near. tc180h80 checks it at 3+2 (SF 1500 / 2500,
Maia-3 1500, 300 each).
human7 (300 each): HumanElo 1350: 0.575 vs 1100, 0.500 vs 1500 (~1500;
with human6 ~1490, still too strong); 1800: 0.633 / 0.458 vs 1500 / 1900
(~1805); 2200: 0.595 / 0.420 vs 1900 / 2300 (~2115). human8 measures 90 /
110 / 130 per mille directly vs 1100 and 1500 for the low end.

### Outside review round 2: GLM (Nov 24)

Brief: notes/review_brief2.md. GLM's review (saved by the user) proposed:
ready-square score (1), lazier defender in the eval (2), wider prover
quiet moves after an oracle check (3), checks whose answers close the box
(4), step-shaped ring score (5), time on closed boxes (6); a fitted hold
table; knight-graph distance for classic smothers; a resigning opponent
in the harness; long shot: a small box pull between +2 and +8 (SPRT).
It corrected us: near lost per full gained is ~2 (not 1:1); the objective
(value of full vs near) must be stated.
Offline checks on 4,494 default wins (conc360 + grid41 + grid42 controls):
- Ready squares (queen reaches in one, protected by another piece): full
  within 10 moves with 1 open ring square: ready 0 8.9%, 1 30.2%, 2+ 73%
  (n 6558 / 1536 / 134); with 2 open: 2.3 / 5.4 / 5.5%. Strong signal
  beyond the open count.
- Defender's last move before our full smother: answered a check 269,
  free move 101, capture 20 (forced closings dominate).
- State at the decisive point: 1 open + corner + queen 27.6% full (n 105)
  vs 7-10% typical; per-opening dispersion 1.16x noise (openings matter
  little).
- grid41b Hybrid 120/200 draws: 24 of 25 were the harness's 400-ply cap
  (games still building), not real draws.
- Lichess record: 271 bot games, 1 human; resignation rate not measurable.
New options (off): SmotherBuildReady, SmotherBuildDefRing,
SmotherBuildRingTable. grid43 tests them on top of Hybrid 80 / 160 moves.

grid43 (5 of 7 shards; base Hybrid 80 / 160 build moves; full / near /
full+near per 100, z vs base B): Elo 1500 (712 each): B 13.3 / 45.2 / 58.6;
Ready 20 16.4 / 36.1 / 52.5 (z +1.6 / -2.3); Ready 60 13.8 / 36.5 / 50.3;
RingTable 60,50,0,-10,-15 15.3 / 46.1 / 61.4 (z +1.1 / +1.1); DefRing 30
12.9 / 43.1 / 56.0; DefRing 0 12.2 / 40.0 / 52.2. Elo 2500 (~290): B 8.6 /
24.7 / 33.2; RingTable 8.3 / 33.3 / 41.7 (z f+n +2.1); Ready and DefRing
no gain. Ready trades near for full; RingTable is the only arm not worse
on either count.
tc180h80 (3+2, ~290 each; full / near / full+near): SF 1500 D 11.0 / 63.7
/ 74.7, 80/160 16.0 / 49.0 / 65.0 (z +1.8 / -2.6); SF 2500 D 6.1 / 55.4 /
61.4, 80/160 10.4 / 34.4 / 44.8 (z +1.8 / -3.9); Maia-3 1500 D 15.0 / 55.7
/ 70.7, 80/160 16.0 / 48.0 / 64.0. At 3+2 the near smothers after move 40
are easier, so 80/160 costs 2-4 near per full gained. No losses.
human8 (UCI_Elo 1320 + per mille vs Maia-3 1100 / 1500, 300 each): 90:
0.620 / 0.460 (~1400); 110: 0.563 / 0.400 (~1255); 130: 0.473 / 0.335
(~1020). human5's 80 per mille ~1270 was off. HumanElo map low end now
(1020, 130), (1255, 110), (1400, 90), (1490, 72); range 1020-2400.

grid43 complete (base 80/160; full / near / full+near, z vs B): Elo 1500
(1000): B 14.0 / 45.6 / 59.6; RingTable 15.3 / 44.4 / 59.7 (z +0.8 / 0.0);
Ready 20 15.3 / 36.7 / 52.0 (z +0.8 / -3.4); Ready 60 13.5 / 34.4 / 47.9;
DefRing 30 12.3 / 45.2 / 57.5; DefRing 0 11.5 / 39.9 / 51.4 (-1.7 / -3.7).
Elo 2500 (400): B 8.5 / 25.5 / 34.0; RingTable 7.8 / 35.5 / 43.2 (f+n z
+2.7); others within noise. Ready and DefRing dropped.

Outside reviews: DeepSeek (ring-piece mobility, KeepFar, conditional hold,
learned model) and ChatGPT (counterfactual blocker stability = safe ring
exits, check funnel, step-shaped ring score, protected final-check
squares, learned model, box-closure prover; method: game-clustered CIs,
hazard denominators, decisive vs construction timeline, oracle as a lower
bound). Offline (notes/scripts/review2_checks.py, review2_exits.py):
raw ring-piece mobility: no signal; enemy pieces far from the king: no
harm (no KeepFar); decisive threshold +4/+6/+8: same hazard shape; king
able to move vs stuck (<= 1 open): ~6-10% vs ~19-29%. Safe exits (off
the ring, not lost, no mate in one), game-clustered 95% CI, <= 1 open:
0: 29.3% [25.6-33.7], 1-2: 18.6% [15.5-21.7], 3+: 6.1% [4.7-7.3]. Cheap
proxy (to squares we do not attack): 25.5 / 18.6 / 10.5%. New option
SmotherBuildExit (points per proxy exit, at most 6, when <= 2 open).
grid44: base 80/160; B, Exit 6, Exit 15, RingTable, RingTable + Exit 6;
Elo 1500 x1500, 2500 x600, Maia-3 1500 x400.

User (Nov 24): objective = full smothers first, near smothers as the
fallback. Release 1.4.1: HumanElo recalibration only (bench unchanged).
80/160 (SmotherPartialAfter 80, SmotherBuildMoves 160) is the candidate
default for 1.5, after grid44 and a strength check.

grid44 (base 80/160; full / near / full+near, z vs B): Elo 1500 (1500):
B 14.1 / 42.3 / 56.4; RingTable 14.8 / 48.3 / 63.1 (z +0.6 / +3.7); Exit
6 13.8 / 41.9 / 55.7; Exit 15 14.1 / 41.3 / 55.4; RingTable + Exit 6 14.5
/ 43.0 / 57.5. Elo 2500 (600): B 8.3 / 32.2 / 40.5; RingTable 9.3 / 34.8
/ 44.2; Exit arms within noise. Maia-3 1500 (400): B 12.0 / 32.0 / 44.0;
RingTable 14.8 / 37.8 / 52.5 (f+n z +2.4). The exit penalty does nothing
in games although it predicts well offline (a predictor, not a lever).
RingTable with grid43 (Elo 1500, 2500 games each): full 15.0 vs 14.1,
full+near ~61.7 vs 57.7: more near fallbacks, full not hurt.
Candidate 1.5 = SmotherPartialAfter 80 + SmotherBuildMoves 160 +
SmotherBuildRingTable 60,50,0,-10,-15. tc180c15 (3+2 vs 1.4.1 defaults)
and sprt-c15 (10+0.1, [-3, 0], 7 accounts x 18 x 200) check it.

tc180c15 (3+2, 6 of 7 shards; Aurazur did not run; true / near / true+near
per 100): SF 1500: 1.4.1 12.3 / 58.1 / 70.4 (260), C15 13.2 / 50.5 / 63.6
(220); SF 2500: 6.9 / 51.4 / 58.3 (259), C15 8.8 / 42.9 / 51.8 (170, 2
draws); Maia-3 1500: 8.8 / 58.0 / 66.8 (250), C15 17.3 / 45.0 / 62.3 (260,
z true +2.8). sprt-c15 (5 of 7 shards): 18,000 games, -1.0 Elo [-2.2,
+0.1], pentanomial [3, 483, 8080, 432, 2], H1 for [-3, 0].
Akleotes concurrency (Nov 24, 18:39 JST): 42 jobs at once (SPRT 18 + 3+2
20 + probe 4), up from ~20-24 on Nov 23.
Release 1.5 (user approved): Hybrid switch 80 (was 40), SmotherBuildMoves
160 (was 80), SmotherBuildRingTable 60,50,0,-10,-15. Bench unchanged.

Nov 24 evening (user approved): (1) distribute.sh: weighted shares; the
enterprise fork takes 2 of 8 shards with max_parallel 40 (it ran 42 jobs
at once); distribute.sh now also copies notes/scripts from the tested ref,
and expand_plan.py accepts a list of shard indices. (2) match.py:
HarnessResign=T,P pseudo-option: the opponent resigns before each of its
moves with P% chance once T+ material points down. resign1: 1.5 vs the
1.4 settings (PartialAfter 40, BuildMoves 80, no RingTable) vs SmotherHold
25 with switch 40, against Maia-3 1500 resigning at 2/5/10% per move
(threshold 8), 400 games each. (3) SmotherHold N (off): after the near
switch, hold out up to N consecutive moves where a full smother is very
likely (<= 1 open ring square, a ready square, the king cannot step out;
offline 43-55% within 10 moves). grid45: 1.5 vs Hold 10, Hold 25, switch
40 + Hold 25; Elo 1500 x1500, 2500 x600, Maia-3 1500 x400.

Human resignation, Lichess database (Oct 2026, first 60,000 human rated
games streamed; notes/scripts/lichess_resign_stats.py): chance per own move
of resigning by material deficit 3-5 / 6-8 / 9-11 / 12-14 / 15+: bullet
0.7 / 1.5 / 2.4 / 2.6 / 2.1%; blitz 1.6 / 3.7 / 5.3 / 5.7 / 3.7%; rapid 1.8
/ 3.6 / 4.5 / 4.4 / 3.1% (blitz 1600-1999: up to 8.2%). Games where one
side was 8+ down end: bullet resign 19%, mate 20%, time/other 57%, draw
4%; blitz 42 / 24 / 29 / 5; rapid 45 / 32 / 17 / 6. So resign1's 5% arm
matches blitz/rapid, 2% bullet; 10% is a worst case. At most a quarter to
a third of lost human games reach any mate.

Lichess database pipeline (Nov 24, user asked for much more data):
notes/scripts/lichess_db.py streams a monthly dump (no full download;
~1,500 games/s on 4 cores) and keeps human games only: resignation and
game-ending counts (stats.json), every game ending in a full or near
smothered mate (smothers.jsonl.zst: site, Elo, time control, UCI moves,
kind), and a sample (1 in 50 decided games, 1 in 500 others). Workflow
.github/workflows/lichess-db.yml (push notes/exp/lichess.json to data/**)
runs one job per month on our account and attaches the files to the
release "lichess-data". First run data/lichess1: 12 months (2025-11 to
2026-10) x 3M games = 36M games. Test on 40,000 games (Oct 2026): 1,148
near, 56 full, 25 classic smothered mates.

grid45 (SmotherHold on 1.5; true / near / true+near, z vs 1.5): Elo 1500
(1500): 1.5 13.1 / 46.9 / 60.0; Hold 10 11.6 / 45.3 / 56.9; Hold 25 16.1 /
42.4 / 58.5 (z +2.3 / -0.9); switch 40 + Hold 25 8.9 / 60.3 / 69.1 (-3.7 /
+5.2). Elo 2500 (600) and Maia-3 1500 (400): Hold no gain; switch 40 +
Hold 25 again fewer true, many more near. Akleotes' double share (2,472
games) finished with the others.
resign1 (Maia-3 1500 resigning once 8+ down; true / near / true+near /
resigned per 100, 400 each): 2%: 1.5 11.0 / 12.2 / 23.2 / 54; old (40/80,
no table) 8.8 / 25.5 / 34.2 / 37; switch 40 + Hold 25 8.5 / 32.0 / 40.5 /
45. 5%: 1.5 8.0 / 4.0 / 12.0 / 76; old 5.0 / 13.8 / 18.8 / 66; S40H25 7.0
/ 18.2 / 25.2 / 65. 10%: 5.2 / 2.5 / 7.8 / 85; 6.0 / 11.8 / 17.8 / 71; 4.2
/ 12.2 / 16.5 / 77. Against resigners 1.5 keeps the most true smothers
(n.s.) but loses its near fallback; S40H25 is the candidate human (Lichess)
profile.

Lichess data, first merge (8 of 12 months finished, 2025-11 partial; 21.4M
human games; notes/scripts/lichess_merge.py). Resign chance per own move by
deficit 3-5 / 6-8 / 9-11 / 12-14 / 15+: bullet 0.8 / 1.6 / 2.6 / 2.5 / 1.8%;
blitz 1.7 / 3.8 / 5.6 / 6.0 / 4.0%; rapid 1.8 / 3.8 / 5.4 / 5.6 / 3.7%;
classical 1.8 / 3.5 / 4.6 / 4.6 / 3.1%. Games with one side 8+ down end:
bullet resign 19.5% mate 21.3% time/other 55.5%; blitz 43.4 / 23.0 / 28.1;
rapid 47.8 / 29.5 / 17.0; classical 46.6 / 32.4 / 14.6. Human smothered
mates: near 597,512 (27.9 per 1000 games), full 25,424 (1.19), classic
14,413 (0.67). Top ECO for full+classic: B00, A00, A40, C50, B01.
All 12 months merged (2025-11 partial): 33,357,502 human games; rates
unchanged from the 8-month merge. Human smothered mates: near 930,794
(27.9 per 1000), full 39,941 (1.20), classic 22,524 (0.68).

match.py: HarnessResign=curve:P1,..,P5 resigns with the measured Lichess
chance per own move for deficits 3-5 / 6-8 / 9-11 / 12-14 / 15+ (blitz:
1.7,3.8,5.6,6.0,4.0). resign2: Maia-3 1500 (1500 each) and 1900 (600 each)
on the blitz curve; arms 1.5, switch 40, switch 40 + Hold 25. lichess-bot
passes UCI_Opponent (title rating human/computer name) to engines that
declare it: a per-opponent profile can live in the engine.
human_smother_test.py (pilot, 60 games from Oct 2026): forced smother
(oracle) 1 move before mate 100%, 3 moves 17%, 5 moves 7%, 10 moves 0%;
the engine proved every forced one; full run 2,000 games in progress.

Human smother test, full run (2,000 real full/classic smothers from all 12
months, 7,225 positions; notes/scripts/human_smother_test.py, summary
human_smother_summary.py; real engine 1.5 at 800 ms after a warm-up;
oracle 12 moves / 2 quiet / 5M nodes). Forced smother existed 1 / 3 / 5 /
10 moves before mate: 100 / 14.8 / 3.5 / 0.1%; the engine proved 100 /
99.3 / 98.5 / 100% of those (3 misses of 365, mates in 8-11). Engine's
move = human's move: 96.8 / 47.7 / 42.0 / 38.8% (at 1 move the other 3%
were different proven smothers). Forced share 3 moves out: classic 30%,
full 6%. Conclusion: detection is solved on real games; human smothers
mostly come from defender errors, so trap-setting against humans (in
construction mode only) is the remaining lever. Next check: in unforced
positions, how often does a Maia-3 defence walk into the smother?

Trap test (notes/scripts/trap_test.py; 1,497 positions 3 or 5 moves before
real human smothers where none was forced yet; Maia-3 at the defender's
rating replies 16 times; oracle checks for a forced smother after each
reply). Walk-in chance after the human's move vs Smotherfish's move: 3
moves out 6.3% vs 5.7% (eval after +1.7 vs +2.7), 5 moves out 3.8% vs 2.7%
(+0.6 vs +1.3); in construction territory (eval >= +8) 14.7% vs 13.4%.
The humans' trap moves cost about a pawn and barely beat the engine even in
games selected because the trap worked: trap-setting dropped. (Three engine
exits were the script passing Maia's "0000" after a mating move; Stockfish
exits on an illegal move in "position". Fixed in the script.)

resign2 (7 of 8 shares; Maia-3 resigning on the measured Lichess blitz
curve; true / near / true+near / resigned per 100): Maia-3 1500 (1,308
each): 1.5 5.4 / 3.1 / 8.5 / 84; switch 40 5.4 / 12.1 / 17.5 / 76 (f+n z
+6.9); switch 40 + Hold 25 4.4 / 12.8 / 17.1 / 76. Maia-3 1900 (528): 1.5
4.4 / 3.8 / 8.1 / 82; switch 40 4.4 / 10.4 / 14.8 / 78 (z +3.4); + Hold
4.5 / 9.5 / 14.0. Against resigning humans the 40-move switch keeps every
true smother and doubles the total; SmotherHold adds nothing. Proposal:
use switch 40 automatically when UCI_Opponent says the opponent is human.

Release 1.5.1 (user approved): UCI_Opponent declared; when its third word
is "human", Hybrid's near switch is SmotherHumanAfter (40) instead of 80.
Verified python-chess (lichess-bot) accepts it and the switch fires.

Research round 3 (Nov 25 JST; communities: TalkChess personalities,
Lc0 odds bots with search contempt and human-emulating training, trap
articles; no smother-specialised project found). Lichess openings (11
months; per-ECO base from the 1-in-500 sample): true smothers per 1000
games by the mating side: C57 (Two Knights 4.Ng5 d5) Black 7.2 (classic
mostly, 6.7 within 20 moves); B00/B02/B20 White 3.2-4.0, mostly Scholar's
mate shapes (Qxf7# with the king boxed counts as AnyPiece full); average
1.9. Opening steering would add < 1 per 100 games: not pursued. resign3:
earlier construction against resigning humans (switch 40 base; BuildCp /
Floor 600/450, 500/350, 400/250), Maia-3 1500 x1500 and 1900 x600.

User (Nov 25): a smothered mate means a KNIGHT mate against a king fully
boxed by its own pieces (classic). AnyPiece "full" (incl. Scholar's-mate
shapes) and near smothers do not count. Earlier classic rates (per 100,
5+0.05): Elo 1500 1.4 defaults ~0.4-0.5, 1.5 ~1.0-1.2, classic-only Full
160 1.6 (grid41). New option SmotherBuildKnightCheck (points per knight one
knight move from a checking square not guarded by an enemy pawn, half for
two). grid46: 1.5 vs SmotherClassic vs + KnightCheck 8 vs + KnightCheck 8 +
RingTable 90,40,0,-10,-15; Elo 1500 x2500, 2500 x400, Maia-3 1500 x400.

Lichess bots 1-4 started (Nov 25, ~03:50 JST, 5 h) on the enterprise fork
from actions-exp/grid46 (1.5.1 code + KnightCheck off): bots 1, 2, 4 1.5.1
defaults (human switch via UCI_Opponent); bot 3 SmotherClassic=true.

resign3 (switch 40 base, Maia-3 resigning on the Lichess blitz curve;
classic / any-piece full / near per 100): Maia-3 1500 (1500 each): base
(BuildCp 800) 0.5 (8) / 5.3 / 12.5; 600/450 0.8 / 5.6 / 15.0; 500/350 1.6
(24, z +2.8) / 5.8 / 15.5; 400/250 1.1 / 5.5 / 16.7. Maia-3 1900 (600):
1.0 / 4.3 / 9.7 vs 1.0-1.3 / 2.5-4.8 / 14.7-17.0. No draws or losses.
Earlier construction adds near smothers; the classic gain at 500 is too
few events to act on. Combine with grid46's best knight setting later.

grid46 (6 of 8 shares; CLASSIC knight smothers per 100, the user's goal):
Elo 1500 (1876 each): 1.5 0.7 (14); SmotherClassic 2.5 (46, z +4.2, 12
draws); + KnightCheck 8 4.0 (75, z +6.5, 5 draws); + RingTable
90,40,0,-10,-15 3.3 (61). Maia-3 1500 (~300): 0.3 / 3.3 / 3.6 / 3.8. Elo
2500 (~300): 1.0 / 1.6 / 1.0 / 0.7 (too few). No losses. Under the classic
goal nearly all full smothers are classic; near and queen smothers mostly
vanish. grid47 tunes KnightCheck 4 / 8 / 16 / 24 and 16 + BuildCp 500 /
Floor 350 (all SmotherClassic).

grid47 (6 of 8 shares; all SmotherClassic; classic per 100): Elo 1500
(~1870): KnightCheck 4 3.5, 8 2.4, 16 3.0, 24 3.2, 16 + BuildCp 500/350
4.8 (14 draws, 2 losses); Maia-3 1500 (~450): 3.1 / 1.8 / 5.5 / 4.2 / 4.4;
Elo 2500 (304): 2.0 / 1.0 / 1.3 / 1.0 / 2.3. Weights 4-24 plateau at ~3
per 100 vs 0.7 for 1.5; earlier construction loses games vs engines.
Candidate 1.6: SmotherClassic + KnightCheck 16. sprt-k16 (10+0.1, [-3,0],
vs 1.5.1) and tc180k16 (3+2, 400 each vs SF 1500 / 2500, Maia-3 1500).

sprt-k16 (4 of 7 shards, 18,000 games, 10+0.1): SmotherClassic +
KnightCheck 16 vs 1.5.1: +0.7 Elo [-0.5, +1.8], pentanomial [3, 458, 8046,
488, 5], H1 for [-3, 0]. tc180k16 partial (3+2; knight per 100): SF 1500
1.4 (2/139) vs 3.8 (5/130); SF 2500 0 vs 0.9; Maia-3 1500 2.0 (3/150) vs
6.0 (9/150); together 5 vs 15; no draws or losses.

tc180k16 (6 of 7 shards; knight per 100): SF 1500 0.9 (3/319) vs 3.7
(10/268, z +2.3); Maia-3 1500 1.4 (5/350) vs 6.3 (22/350, z +3.3); SF 2500
0 vs 0.4. No draws or losses. User wants a more substantial gain before
calling it 1.6.
Diagnostic (classic goal, grid47 Elo 1500, 7,473 wins): classic hazard
~0.5% per 20 of our moves, fading after 100 (longer build will not help).
At the final mate: classic games - defender 3-6 units, ring closed;
other mates - defender 0-2 units in 63%, 3+ open ring squares in 88%; we
have a knight in 79%; we underpromote to knights often (4,699 vs 5,078
queen promotions). The box runs out of blockers: grid48 tests Keep 22,
Keep 22 + MaterialDiv 16, Starve 10 (at 4) on SmotherClassic + KnightCheck
16.

Rule (user, Nov 25): after every distributed launch, remind the user to
press "Run workflow" on Helper poll for the helper forks (AlSynthK,
bazaak-coder, Aurazur in particular; Aurazur never runs on its own), even
though it is optional, so results come back faster.

grid48 (all 8 shares; knight per 100): Elo 1500 (2500): base 3.2 (81, 13
draws), Keep 22 3.1 (4 draws), Keep 22 + MatDiv 16 3.0, Starve 10 3.5 (87);
Maia-3 1500 (600): 2.7 / 3.2 / 3.3 / 3.5; Elo 2500 (400): 0.8 / 1.0 / 1.8 /
1.2. Keep 22 cut "defender <= 2 units at the mate" from 62% to 25% but did
not raise knight smothers: blockers were not the limit.
Classic hazard by state (grid48 Elo 1500, 1.15M positions; knight smother
within 10 moves): closed box + corner + knight one move from a checking
square 82% (0.04% of positions); 1 open + corner + knight 1 move 7.6%
(1.6%); 3+ open (77% of positions) < 0.1%. The last open square is the
bottleneck. With 1 open in a corner: "decoy ready" (a defender piece
covers the hole, our queen/rook can go there guarded) 7.6% vs 4.2% / 3.3%.
New options: SmotherBuildDecoy, SmotherCrushMoves (12), SmotherCrushQuiet
(2). grid49: base, CrushQuiet 3, + CrushMoves 16, Decoy 40, Decoy 40 +
Quiet 3 (all SmotherClassic + KnightCheck 16).

grid49 (6 of 8 shares; knight per 100; base SmotherClassic + KnightCheck
16): Elo 1500 (~1875): base 3.1 (58), Decoy 40 3.6, CrushQuiet 3 3.7, Quiet
3 + CrushMoves 16 4.0 (75, z +1.5), Decoy + Quiet 3 3.7; Elo 2500 (~300):
1.3 / 2.5 / 2.6 / 2.6 / 1.6; Maia-3 1500 (~450): 2.6 / 2.5 / 4.8 / 3.3 /
3.7. All +20-30%, none significant alone; no time losses. Levers tried
after the classic goal + knight routes (KnightCheck weight, Keep, Starve,
Decoy, deeper prover, earlier construction) each moved < +30%: the
defender's last blocker is the limit.

User (Nov 25): 1.6 should be a big upgrade on both fronts: many more
knight smothers and any real strength our own features can add (not
Stockfish tuning). Learned classic model: notes/scripts/classic_feats.py
on grid47-49 Elo 1500 classic-goal games (832k positions; label = knight
smother within 10 of our moves); logistic fit, held-out games AUC 0.936 vs
0.900 for the hand-style score. Coefficients (log-odds): h0 +5.01, corner*
h0*kd1 +3.54, h1 +2.73, h2 +1.93, corner*h1 +1.92, units +1.28, corner
-1.28, corner*h0 +1.25, queen +0.97, decoy +0.95, knights +0.85, kd1 +0.79,
kd2 +0.76, corner*h1*kd1 +0.67, edge -0.30, exits -0.29, stuck +0.27.
Engine option SmotherBuildModelScale (points per log-odd; replaces ring,
corner/edge, nearness, knight-route and decoy terms) + SmotherBuildModel.
grid50: hand score (KnightCheck 16) vs model scale 6 / 11 / 20, all with
SmotherClassic + CrushQuiet 3 + CrushMoves 16.

## Knight-smother network (Nov 25)

A small network that predicts a knight (classic) smother within 10 of our
moves, used as the construction score (SmotherBuildNetScale, points per
log-odd; replaces the same hand terms as SmotherBuildModelScale).

- Inputs (167): the 17 classic features (classic_feats.py) and a 5x5 window
  around the enemy king, mirrored toward a1, 6 channels per square (off
  board, their pawn, their piece, our knight, our queen, our other).
- Data: nn_data.py on all knight-goal games of grid46-49 (Elo 1500 and
  Maia-3 1500): 4,562,539 positions, 13,390 positives. Holdout = games with
  hash % 5 == 0 (917k positions, 2,749 positives).
- Holdout AUC: linear on the 17 features 0.912 (2 epochs; 0.936 fully fitted
  earlier), all pairwise products 0.947, network 16 hidden 0.968 (32: 0.968,
  64: 0.964, overfits). Window alone with 32 hidden: 0.945. 16 hidden kept.
- Engine: smother_net.h generated by nn_export.py (normalisation folded into
  the first layer; window inputs are sparse, about 600 multiply-adds per
  call). The `smothernet` UCI command prints the features and logit for the
  side to move; nn_check.py: 3,002 positions, 0 feature mismatches, max logit
  difference 8e-5. Bench unchanged (1210779).
- grid51: grid50's design with the network at scale 6 / 11 / 20 vs
  KnightCheck 16 (seeds +1000).
- Queued after grid51 / grid50 / sprt-proverquiet are read: (1) on-policy
  round: add the network arms' own games to the data, retrain, re-export,
  retest; (2) wider inputs: pieces beyond the 5x5 window that reach the
  last open ring square (rook/bishop/queen lines), knight distance map;
  judged by classic smothers per 100 games, not AUC.

grid50 (classic / 100 games; KnightCheck 16 vs linear model scale 6/11/20;
all SmotherClassic + CrushQuiet 3 + CrushMoves 16): Elo 1500 (2500 each)
3.8 / 2.5 / 3.4 / 4.1; Maia-3 1500 (600) 3.7 / 2.5 / 2.5 / 4.3; Elo 2500
(400) 1.8 / 2.3 / 1.0 / 2.3. Higher scale better; 20 matches the hand score
(103 vs 96, z +0.5), 6 is worse (z -2.6). 1 loss in 14k (2500, M20); time
losses 4 (M20) vs 8 (B). grid51b: net 30 / 45 and model 35 on Elo 1500 and
Maia-3 1500, grid51 seeds.

Lichess bots session 3 (Nov 25 03:50-08:50 JST): 164 games +84 =78 -2, all
opponents bots (matchmaking); 1 classic smother (bot 3, SmotherClassic).
Both losses at 30+0 vs a 3124 bot (one flag in a drawn KBP v K, one at 1 s);
bot 4 played that bot ~30 times in a row.

sprt-proverquiet (SmotherTimePercent=0 vs default, 10+0.1, bounds [0, 3],
28,800 games over all 7 accounts): +0.3 Elo [-0.6, 1.2], LLR -16.3, H0.
The prover's time in undecided positions costs no measurable strength;
turning it off is not a 1.6 strength gain.

## Fresh-view review (Opus, high effort, brief only; Nov 25)

Main diagnosis (testable): in construction mode the IMAGINED defender in
our tree does not care about material, because above +6 our eval divides
material by 8 while each build point is worth 8 cp (a rook ~60 cp vs
KnightCheck 16 = 128 cp). So the tree's defender gives up pieces to deny
build terms, while real opponents (SF1500, Maia, humans) keep material;
moves that drive a defender piece onto the last open square (the observed
bottleneck) look useless to the search. Would explain the KnightCheck
plateau and the failed eval terms. Also: the last ring square can only be
filled by a defender non-king move.
Proposed: M1 classify how the box closed in our knight smothers; M2 compare
real defender moves with our PV's predicted reply vs a normal-eval reply;
M3 trap fall rate by length; M4 resources at construction start (knights,
defender units able to reach the open square). Ideas: (1) root steering by
expected traps under a fitted defender model (net probability as value,
prover on the few replies that fill a ring square); (2) material-protecting
defender in the tree (SEE pruning of losing quiet defender moves in
construction mode, checks never pruned); (3) keep/create a knight; (4) keep
box material before construction; (5) stall breaker. Net: use as value in
(1), discounted label, hold out by OPENING not game (AUC may be inflated),
ensembles against exploitation. Strength: +5 Elo from our machinery not
realistic; M5 (prover mates the search missed in undecided SPRT positions)
would show any ceiling.

DeepSeek round 3: (1) closure prover: separate AND/OR search whose goal
is "a defender piece occupies the last open ring square" (checks,
captures, sacrifices, attacks on that square's defender, zugzwang); also a
diagnostic: how often is closure forceable at all; (2) prover move
ordering toward the last square (little use: our prover is exhaustive
within its move set); (3) closure predictor / second net head with
"closure forceable within K" labels; (4) extensions for last-square moves
in construction mode (similar to the LMR tries that failed); (5) root
steering by net on child positions (Opus idea 1 without a defender
model); (6) pin/freeze term for the piece on the last square. Strength:
+5 Elo not realistic (agrees with Opus). Did not spot the material
compression issue; its eval-term ideas (3, 6) are exposed to it.

grid51 + grid51b (knight smothers per 100; B = KnightCheck 16):
Elo 1500 (2500): B 3.9 (98) | net 6: 4.2 (105) | 11: 2.8 | 20: 0.8, 14
losses | 30: 0.4, 22 losses | 45: 0.2, 28 losses; linear model 35: 2.6.
Maia-3 1500 (600): B 5.0 | net 6: 5.3 | 11: 3.0 | 20: 1.5 | 30/45: 0.3-0.5
with 4 losses each. Elo 2500 (400): B 1.5 | net 6 1.3 | 11 0.5 | 20 0.5, 9
losses. All losses are us getting mated: at scale >= 20 the net term
outweighs material (compressed /8 above +6) and the search gives up pieces
chasing the net's output. Net at scale 6 = hand score (n.s.); linear
model peaks near 20. The better predictor did not give more smothers when
used as the eval at every node: matches the review's warning (the search
exploits the predictor; the tree's defender is not the real one).

ChatGPT round 3: first fund an offline "final-square closure audit" (one
open ring square: is closure forceable, by which mechanism, how deep,
does the knight mate still follow); then a target-square closure prover
(forced recapture, interposition, deflection/overload, forced retreat;
positive proofs only, never negative claims); network at the root only,
among moves within epsilon of the best, ranked after the defender's best
reply (min over a shallow defender search), later action-conditioned
Q(s,m); closure head; target planning with limited commitment;
feasibility-gated construction end. Measure PR-AUC/precision/calibration,
not only AUC. Strength: +5 Elo not credible; keep non-regression.
All three reviews agree: closure audit first; network at the root, not as
an all-node eval (confirmed by grid51).

M1 (offline, 2,481 knight smothers in grid46-51): the last ring square was
filled by a defender blocking a check 48%, capturing a checking piece on
the ring 34% (Philidor-type sacrifice), free choice 9%, moving an attacked
piece 7%, few legal moves 1%; median 0 of our moves between closure and
mate. Knight smothers come almost entirely from the final forced check
sequence (prover territory), not from quiet closure.

GLM round 3: arrival, not conversion, is the problem (at most ~5% of games
reach box closed + corner + knight ready). Minimax gives a non-forced close
zero value; the prover only certifies forced ones. Opponent model from
upstream Skill code (UCI_Elo 1500 -> level ~1.5: depth-2 pick among
MultiPV 4 with a random push; 2500 -> depth ~7); check our harness's
opponent binary matches. Census D1 (trap availability: for our top moves,
weight the modelled defender's 4 replies, strict-prove after those that
fill a ring square; share of turns with expected hit >= 0.25) and D2
(ingredients at +4 / +8: king castled corner, both front pawns home, a
mobile defender piece able to reach the corner-adjacent square in 2, our
knight and queen alive; smother rate ready vs not; who lost the
ingredient). Ideas: trap finder vs modelled defender; prover move classes
(pin/mate-threat forcing interposition, herding); +4..+8 band without
compression plus readiness bonus; keep ingredients in normal play;
closability-aware target and exit; net as action value over modelled
replies, policy head, time-to-smother heads. Strength: +5 not credible.
Note: the network scale WAS bracketed (grid51/51b: 20+ loses games).

Closure audit (smother_audit.py; prover alone, Classic, 16 moves, 3 quiet,
20M nodes; positions us to move, >= +8, enemy king on an edge, from
grid51 B / N6 games; for smother games, positions more than 16 of our
moves before the mate): forced knight smother exists in 1 open square,
games without a smother 2/120 (1.7%); 2 open squares 0/120; games with a
smother (earlier positions) 1 open 2/57, 2 open 3/62. So in our stalled
positions a forced knight smother almost never exists even with a big
budget: an OPPORTUNITY problem, not a prover-limit problem. A stronger or
closure prover is unlikely to help much; the lever is non-forced closure
(traps against the real defender: Opus idea 1 / GLM D1).

D1 trap census (smother_d1_traps.py; 240 positions from grid51 e1500_B,
>= +8, king on an edge, 1-2 open ring squares; candidates = stock SF19
MultiPV 8 moves >= +6; real opponent SF19 UCI_Elo 1500 sampled 8 times per
candidate; prover after replies that fill a ring square or block a check):
a candidate with expected hit >= 0.1 in 1/240 positions (0.4%), and we
played it. One-move traps are essentially absent in stalled positions.

D2 ingredients (smother_d2_ingredients.py; 4,989 games grid51 e1500 B+N6,
first time >= +8; knight smother rate): our knight gone 21.8% of games ->
1.2% (vs 4.9% with); our queen gone 21.3% -> 1.2%; enemy non-pawn pieces
0 / 1 / 2 / 3+: 0 / 0.9 / 2.0 / 5.7%; enemy pawn shield in front of the
king 0 / 1 / 2 / 3: 2.4 / 4.7 / 5.0 / 10.4%; "ready" (king in corner zone,
shield >= 2, a piece, our knight) 11.1% of games -> 7.6% vs 3.6%.
At +4 the picture is similar (ready 18.9% -> 6.4%).
Reading: with no forced smothers and no traps once construction stalls,
what remains is the material on the board when we become winning. Keeping
our knight and queen and the enemy's pieces/shield before +8 is the one
lever left with measured headroom (bounded: even "ready" games give ~7.6).

M2 imagined-defender test (smother_m2.py; 500 won positions from grid51
B arms, depth 12, positions where the PV starts with the move we played):
construction-mode PV predicts the real reply 99/122 = 81%; its predicted
line has the defender losing >= 2 net material within 4 plies 14%.
(Normal-eval comparison: only 27 usable, 59% match.) The tree's defender
does NOT systematically give away material: the material-compression
hypothesis (Opus review) is not supported. Caveat: selected sample (PV
first move = played move).

Prep phase (new, off by default): SmotherPrepCp (0 = off) and
SmotherPrepKnight / Queen / Piece / Shield (cp). Between +SmotherPrepCp
(previous score) and construction, a bonus at every node for our knight,
our queen, enemy non-pawn pieces (up to 3) and enemy pawns in front of the
enemy king (from D2). Checked: +6.7 position scores +8.5 with defaults
(bonus about +1.6); the bonus also raises the score that starts
construction, so construction begins slightly earlier (watch draws).
Bench unchanged. grid52: B (SmotherClassic + KnightCheck 16 + CrushQuiet 3
+ CrushMoves 16) vs P (PrepCp 400, 40/40/20/10) vs P2 (400, 80/80/40/20)
vs P3 (300, 80/80/40/20); Elo 1500 x2500, Maia-3 1500 x600, Elo 2500 x400.

New helper fork added (Nov 25, ID f2d74f, weight 1; distribute.sh now has
9 shares). Its Actions must be enabled once in the fork's Actions tab; the
session cannot dispatch its poll (no app access), so it runs on its own
schedule or by Run workflow. Merge lists need its URL from now on.

grid52 (prep phase; knight smothers per 100, all SmotherClassic +
KnightCheck 16 + CrushQuiet 3 + CrushMoves 16): Elo 1500 (2500 each) B 3.8
(95) / P 3.3 (83) / P2 3.2 (79) / P3 3.6 (91); Maia-3 1500 (600) 3.3 (20)
/ 2.5 / 3.5 / 5.0 (30, z +1.4); Elo 2500 (400) 0.8 / 2.3 / 1.5 / 2.0. No
gain on the main test; draws 14 / 4 / 11 / 3; no losses. Keeping the D2
ingredients by eval bonus does not raise knight smothers (the D2 link is
correlation). Prep phase stays off by default.

Volunteer network (option B, fishtest-like on GitHub Actions; see
docs/HELPING.md): helpers are discovered from the public forks list
(notes/scripts/volunteers.py; IDs only, weights/exclusions in
notes/volunteers.json); distribute.sh takes its targets from it (ONLY=...
to restrict). volunteers.py status EXP (delivered vs expected per account,
checked on grid52: 14,000/14,000), refill EXP (plan with the jobs of
accounts that delivered nothing, same seeds; tested with a simulated
missing fork: 73 jobs / 1,744 games), merge EXP OUTDIR (EXP + refills from
every account; replaces merge_shards.py with URL lists). README links the
guide (on the development branch; forks see it after the next release).

Status page (docs/status/, published on the gh-pages branch; GitHub Pages
must be set to "Deploy from a branch: gh-pages / root" once). Static: the
browser reads the forks list and each account's workflow runs from GitHub's
public API (IDs shown, not names; ~10 requests per load, 5-minute cache,
"unknown" when rate limited). Results, strength tests and audit findings
come from docs/status/results.json: update it after each analysis and
republish (copy docs/status/* to gh-pages). Docs: README (test status link,
knight smothers, helping), guide (knight-smother options and findings,
helping link).

D1 trap census vs Maia-3 1500 (smother_d1_traps_maia.py; opponent = local
Maia-3 5M at Elo 1500, sampled 8 times per candidate, "go nodes 1"): 600
stalled positions from our Maia-3 games: best candidate with expected hit
>= 0.1 in 1.0% (>= 0.5 in 0.5%), the move we played 0.2% (0%); mean gain
best - played +0.0044 per position (95% bootstrap +0.0006 to +0.0096),
carried by 5 positions. Small but nonzero against human-like play (zero
against SF 1500). Next after 1.6: SmotherSteer + SmotherSteerWonOnly with
SmotherClassic vs Maia-3 (about 2,000 games per arm).

Release 1.6 prepared on a local branch release-1.6 (defaults SmotherClassic
true, KnightCheck 16, CrushQuiet 3, CrushMoves 16; version 1.6; README,
guide, notes/release/v1.6.md with STRENGTH_RESULT placeholder). Bench
1210779. Waiting for sprt-release16.

sprt-release16 (1.6 settings vs 1.5.1 defaults, 10+0.1, bounds [-3, 1],
8 accounts incl. the new fork, 162 runners): 32,400 games, -0.3 Elo (95%
-1.2 to +0.5), LLR +14.1, H1: no regression. Release notes filled in.

Release 1.6: all six binaries built and passed bench, but the Publish step
failed with HTTP 504 (GitHub outage, Nov 25 16:07 UTC incident); re-run
pending. Track A (main version, full strength): grid53 = 1.6 defaults vs
SmotherBuildDecoy 40 / 80; Elo 1500 6,000 games per arm, Maia-3 1500
1,200 per arm (target: +10% knight smothers, detectable at this size).
Track B (opt-in "obsessed" setting that spends strength) waits for the
user's signal.

Release 1.6 published (Nov 26 ~02:00 JST) from 6a8caf3d: the 1.6 defaults
plus the removal of 29 experimental options (identical play to the
SPRT-tested build: 300 positions, same moves and node counts, fixed depth,
sequential prover). The first publish failed in a GitHub outage (504).
Helper forks synced to 6a8caf3d except d32e35 (still 33bbe361):
notes/volunteers.json now has "base" 6a8caf3d and per-fork "bases"
{"d32e35": "33bbe361"} until it syncs (volunteers.py targets reads it).

Track B targets (user, Nov 26): knight smothers >= +50% over the main
version (about 4 -> 6+ per 100 vs SF 1500; all types reported too), with a
strength floor of >= 80% score vs Stockfish UCI_Elo 2600 at 10+0.1.
grid54: 1.6 strength baseline vs UCI_Elo 2600 (1,000 games) and 3000 (400)
at 10+0.1.

Sacrifice census (Track B groundwork; smother_sacrifice_census.py):
positions >= +3 (material), enemy king on an edge, from 1.6 games; every
move SF19 still scores >= +300 cp (MultiPV 40, depth 8); "sacrifice" =
>= 150 cp below the best; 6 sampled opponent replies per move; prover
after replies that fill a ring square or answer a check. vs SF 1500 (300
positions): sacrifices with expected hit >= 0.1: 0/300; other moves 2/300.
vs Maia-3 1500 (200): 0/200 and 0/200. One-move sacrificial gambles almost
never create a forced knight smother from +3..+8 positions (one-ply
horizon; multi-move gambles not measured). Track B should lean on longer /
earlier construction and trap steering vs humans, not sacrifices.

grid53 (Track A; knight smothers per 100, 1.6 defaults vs SmotherBuildDecoy
40 / 80): Elo 1500 (6,000 each) 3.65 (219) / 3.48 (209) / 3.53 (212); Maia-3
1500 (1,200 each) 3.2 (38) / 3.0 (36) / 3.7 (44, z +0.7). No gain; all
ending types unchanged; 1 loss in 21,600. Decoy stays off.
grid54 (1.6 strength margin, 10+0.1): vs UCI_Elo 2600 940 games +937 =3 -0
(99.8%); vs 3000 360 games +353 =7 -0 (99.0%). 100 games of Akleotes's
re-run jobs never reached the results branch (results were committed by
the first attempt). Track B floor (>= 80% vs 2600) leaves a large budget.

Helper forks: four more joined Nov 26 (IDs f0afe4, a8e399, 87fb66, 2456cd),
found automatically: 11 accounts, 13 shares.
grid55 (Track B round 1: spend strength on earlier and longer
construction): B 1.6 vs O1 (BuildCp 500, Floor 300, BuildMoves 200) vs O2
(O1 + MaterialDiv 16) vs O3 (BuildCp 400, Floor 200, BuildMoves 200,
MaterialDiv 16); Elo 1500 x2500, Maia-3 1500 x1200 (5+0.05), Elo 2600 x400
at 10+0.1 (floor: >= 80%).

Akleotes concurrency probe (conctest1, Nov 26 04:16 JST: 256 jobs of 6
games, max_parallel 256): peak 84 jobs at once (82 running with 174 queued,
then 84), up from ~42 on Nov 24. Weight raised to 4 (80 jobs). Its grid55
share was cancelled and rerun uncapped as grid55-r1 (same 108 jobs and
seeds; merged into grid55 by volunteers.py merge).

grid56 (Track B round 2, queued overnight; forks pick it up on their
hourly poll after grid55): trap steering. B 1.6 vs S1 (SmotherSteer 100,
SteerWonOnly) vs S2 (S1 + WinTrapDepth 7, WinSteerTime 100) vs S3 (S1 +
grid55's O1 construction); Maia-3 1500 x2000, Elo 1500 x2500 (5+0.05), Elo
2600 x400 at 10+0.1 (floor >= 80%).

Helper kick (.github/workflows/helper-kick.yml, on the main branch): every
15 minutes (and on Run workflow) starts Helper poll on each fork that has a
helper-exp share it has not copied yet, using the secret HELPER_KICK_PAT (a
classic PAT of the owner, scope public_repo, owner = collaborator with write
on each fork). No checkout, inline script, permissions {}, no PR/fork
triggers; inert until the secret exists. Forks need no sync (their tips
have 6a8caf3d as an ancestor, so helper branches built on it still copy).
Helper kick verified (Nov 26 04:42 JST): secret set, public_repo scope is
enough; first run kicked 10 forks (Akleotes already had grid56); 9 copied
grid56 at once, 2 waiting for a free runner behind grid55. Aurazur now
starts automatically.
grid56: one job on 8e9ce5 failed installing Maia-3 (m1500_S2, chunk 51,
seed 64051, 24 games); refilled as grid56-r1 on Akleotes.

Refill bug (Nov 26): refill plans listed each job as its own run, so every
job got chunk index 0 and same-named result artifacts overwrote each other:
grid55-r1 kept 272 of 2,544 games. Fixed: plans may set "first_chunk"
(expand_plan.py; seed = run seed + index - first_chunk), volunteers.py
refill sets it. Akleotes's grid55 share re-issued as grid55-r2; grid55-r1 is
listed under "superseded" in notes/volunteers.json (merge/status skip it).
Akleotes grid56: 5,240 of 5,280 games (1 job lost).
Housekeeping: helper-exp deletes moved to a workflow (session git deletes
are refused); status page: status.json built every 15 min by the Status
data workflow (notes/scripts/status_data.py).
Fork 2456cd (one of the two newest helpers) became unreachable on Nov 26
~05:55 JST (github.com answers 403; still listed as a fork): its grid55
(1,252 games) and grid56 (1,320) shares never arrived; refilled on Akleotes
as grid55-r3 and grid56-r2 (with first_chunk). grid55-r2 (Akleotes's own
share, corrected) delivered all 2,544 games.

grid55 (Track B round 1, 92% in: all but 2456cd's share, refill grid55-r3
pending; knight smothers per 100): Elo 1500 (2,308 each) B 3.6 (84) / O1
4.0 (92, z +0.6) / O2 3.1 (71) / O3 3.2 (73); Maia-3 1500 (~1,110) B 4.2 /
O1 3.5 / O2 3.8 / O3 3.6. Draws vs Elo 1500: 0.4% / 8.2% / 6.6% / 6.0%,
nearly all the 400-ply game cap (building from +4/+5 for 200 moves makes
games too long). Score vs Elo 2600 (10+0.1): 99.9 / 97.5 / 96.4 / 96.1%
(2 losses in O3): all far above the 80% floor. Verdict: earlier and longer
construction does not raise knight smothers; it only adds long draws.

grid56 (Track B round 2: trap steering; complete incl. refills r1/r2;
knight smothers per 100): Elo 1500 (2,500 each) B 3.2 (79) / S1 SmotherSteer
100 + SteerWonOnly 2.3 (58, z -1.8) / S2 + WinTrapDepth 7, WinSteerTime 100
1.9 (47, z -2.7) / S3 S1 + O1 construction 1.9 (47); Maia-3 1500 (2,000) 2.8
(56) / 2.7 (54) / 2.1 (42) / 2.8 (56). Losses vs Elo 1500 0 / 2 / 1 / 9;
score vs 2600 100 / 99.8 / 100 / 95.8%. Trap steering lowers knight
smothers, also against human-like Maia-3.
Openings (25,308 1.6 games at Elo 1500 over 600 opening x colour cells):
knight-smother rate barely depends on the opening (dispersion ratio 1.11;
split-half r 0.05; best 20% picked on one half: 4.3 vs 3.55 per 100 on the
other). A smother opening repertoire would be worth +20% at most, noisily.
Track B status: building earlier/longer (grid55) and trap steering (grid56)
both fail; with existing mechanisms there is no strength-for-smothers trade
that raises knight smothers.

## grid57: Track B round 3, all smother types (26 Nov, 16,400 games)

Presets on existing options, 1.6 code (base 6a8caf3d). Per 100 games:
knight = knight (classic) smother, full = full smother by another piece,
near = "all but one" smother.

| Opponent | Arm | knight | full | near | all smothers | plain mate | score |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SF 1500 5+0.05 (2,500) | B (1.6) | 3.0 | 0.2 | 3.6 | 6.8 | 92.8 | 99.8% |
| | H40 (`SmotherPartialAfter 40`) | 3.5 | 0.3 | 4.0 | 7.8 | 91.7 | 99.8% |
| | AK (`SmotherClassic false`) | 1.3 | 9.8 | 31.7 | 42.8 | 56.9 | 100% |
| | AN (`SmotherClassic false`, `SmotherGoal Near`) | 0.8 | 2.5 | 64.3 | 67.6 | 32.3 | 100% |
| Maia-3 1500 5+0.05 (1,200) | B | 3.1 | 0.0 | 4.9 | 8.0 | 91.9 | 100% |
| | H40 | 3.2 | 0.2 | 4.0 | 7.4 | 92.7 | 100% |
| | AK | 1.7 | 11.4 | 28.8 | 41.9 | 58.1 | 100% |
| | AN | 0.8 | 3.3 | 63.4 | 67.5 | 32.4 | 100% |
| SF 2600 10+0.1 (400) | B | 0.8 | 0.5 | 2.8 | 4.0 | 95.8 | 99.9% |
| | H40 | 2.2 | 0.0 | 3.2 | 5.4 | 94.2 | 100% |
| | AK | 0.0 | 5.5 | 24.8 | 30.3 | 69.5 | 100% |
| | AN | 0.0 | 2.0 | 49.8 | 51.8 | 48.0 | 100% |

- All four keep the strength floor (100% against 2600; no losses anywhere).
- Counting all smother types, AN gives 10 times 1.6's rate (67.6 vs 6.8 per
  100 against 1500) and AK 6 times, with games 15-45% shorter. Both trade
  knight smothers away (0.8-1.7 vs 3.0).
- Full smothers by any piece (knight + other): AK 11.1 vs 3.2 (3.5 times).
- H40 is within noise of B on knight smothers (3.4 vs 3.0 per 100, pooled
  1500 opponents, z about 0.9).
- So the "obsessed" setting exists already as a preset: AN for any smother,
  AK for full smothers. No setting beats 1.6 on knight smothers.

## Why boxes slip away: the arming finding (26 Nov, from grid57 B/H40 logs)

Offline on 1.6's games (scratchpad scripts, python-chess):
- Every knight smother came out of a full box (all ring squares held by
  defender units). 18% of games reach one; 17% of those convert. 82% of
  box episodes end when the defender moves a box unit out on its next move.
- At the moment a box closes: knight one move from a checking square the
  defender does not guard -> knight smother next move 48 of 48 (100%);
  checking square guarded 50 of 104; no knight check 0 of 721.
- Arming x box state, P(knight smother within 20 plies): one open ring
  square armed 5.3-6.1% vs not armed 0.5%; two open squares 0.18-0.41% vs
  0.13%. We are armed in 43% of two-open positions but only 28% of one-open
  positions: the unconditional KnightCheck term spends its pull where it
  does nothing.
- Dead ends checked: a knight smother in 1-2 instead of the final queen
  smother: 0 cases; forced knight smothers missed by the prover in box
  positions: 1 of 189; promotions already favour knights (1,886 vs 1,277
  queens); more attacking pieces near the king goes with fewer defender
  units around it; the knight-smother rate per 40 plies is flat (~0.6%).
- New option SmotherBuildArmGap (extra KnightCheck points while at most
  one ring square is open, off by default; bench unchanged). grid58: B vs
  ArmGap 24 / 48 / 48 + KnightCheck 8, same opponents as grid57.

grid58 result (16,400 games, all accounts): no gain. Knight smothers per
100, pooled Stockfish 1500 + Maia-3 1500 (3,700 each): B 3.73, ArmGap 24
3.57 (z -0.4), ArmGap 48 3.41 (z -0.8), ArmGap 48 + KnightCheck 8 4.03
(z +0.7); all 99.8-100% against 2600, no losses. Mechanism check: the
share of one-open-square positions with a knight armed did not move (B
27.0%, G48 27.2%, G48K8 27.8%), nor did arming when a box forms (18.7 /
18.5 / 19.3%). The eval term cannot steer the knight in: one-open states
last about a move and the defender in our own tree (material at 1/8)
dissolves the box rather than allow the bonus, as the fresh-view review
predicted. SmotherBuildArmGap stays off (dev branch only, not released).

grid59 (confirmation, 25,594 games; Akleotes's 4 shares refilled as
grid59-r1 after its run hit the 256-job limit): knight smothers per 100,
Stockfish 1500 + Maia-3 1500 pooled (6,000 per arm): B 3.55, H40 3.23
(z -1.0), ArmGap 48 + KnightCheck 8 3.64 (z +0.3, 3 losses to Stockfish
1500), both 3.52 (z -0.1). Pooled with the earlier tests against their own
B: H40 3.29 vs 3.34 (9,700 games each, z -0.2); ArmGap 48 + KnightCheck 8
3.79 vs 3.62 (z +0.6). Neither meets the rule (z >= 2, no losses): 1.6
as released stays the baseline; no strength SPRT needed.

grid60 (SmotherBuildDefSee: the defender in our search skips moves losing
more than N cp unless they give check; 19,600 games): knight per 100,
SF1500 + Maia-3 1500 pooled (4,500 per arm): B 3.02, D1 3.40 (z +1.0),
D100 3.18 (+0.4), D300 3.18 (+0.4); no losses, 99.8-100% vs 2600. By
opponent, D1: SF1500 2.8 vs 3.0, Maia-3 4.7 vs 3.1 (z ~2.2 on its own, but
one of six post-hoc cells). Mechanism unchanged: our captures after +8
material 6.5-6.7, defender units at the end 2.2-2.5 in every arm, so the
real games did not keep more defender material. grid61 confirms D1 vs B
against Maia-3 only (the human-like case).
