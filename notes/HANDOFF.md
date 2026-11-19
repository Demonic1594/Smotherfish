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
