<div align="center">

  <img src="docs/smotherfish-icon.png" alt="Smotherfish" width="128">

  <h3>Smotherfish</h3>

  A Stockfish-strength UCI chess engine that plays for the smothered mate.
  <br>
  <strong>[Download][release-link]</strong>
  &middot;
  <strong>[Guide][guide-link]</strong>
  &middot;
  <strong>[Test status][status-link]</strong>
  <br>
  <br>
  [Report a bug][smf-issue-link]
  &middot;
  [Help test][helping-link]
  &middot;
  [Changelog][changelog-link]
  &middot;
  [Development log][handoff-link]
  &middot;
  [Upstream Stockfish][upstream-link]

  [![Release][release-badge]][release-link]
  [![License][smf-license-badge]][smf-license-link]
  [![Based on][based-badge]][upstream-link]
  [![Protocol][uci-badge]][uci-link]
  <br>
  [![Last commit][commit-badge]][smf-commits-link]
  [![Status page][status-badge]][status-link]

</div>

## Overview

Smotherfish is a free UCI chess engine built on [Stockfish][upstream-link]
(development version of 22 November 2026, upstream commit `3e8fde75`). It keeps
Stockfish's full playing strength and adds one ambition of its own: to end the
game with a **smothered mate**, the textbook pattern in which a knight mates a
king that its own pieces box in on every side.

A smothered mate cannot be forced from most positions, because it needs the
defender's own pieces packed around its king. Smotherfish therefore combines
three mechanisms:

1. **A dedicated prover** finds forced smothered mates (checks, sacrifices and a
   few quiet moves) and plays them, even over a faster ordinary mate.
2. **Brutal mode** values every ordinary mate below a smothered one, so the
   search prefers any smother it can see.
3. **Construction mode** takes over once a game is decided: instead of mating at
   once, the engine spends moves building the position a smother needs (the
   enemy king cornered, its pieces kept close, a knight brought within reach),
   without ever giving back the win.

Against an opponent who defends well, the game never becomes decided and
Smotherfish plays exactly like Stockfish. Every change is verified to cost no
measurable strength before it becomes a default.

## Version 1.6 at a glance

Version 1.6 plays for the textbook (knight) smothered mate.

| | 1.5.1 | **1.6** |
| --- | ---: | ---: |
| Knight smothers per 100 games vs Stockfish (`UCI_Elo` 1500), 5+0.05 | 0.7 | **3.8** |
| Knight smothers per 100 games vs Maia-3 1500 (human-like), 5+0.05 | 0.3 | **3.3** |
| Knight smothers per 100 games vs Stockfish 1500, 3+2 | 0.9 | **3.7** |
| Knight smothers per 100 games vs Maia-3 1500, 3+2 | 1.4 | **6.3** |
| Strength against 1.5.1, 10+0.1, 32,400 games | | **-0.3 Elo** (95%: -1.2 to +0.5) |

1.6 trades other kinds of smothered mates (a queen against a boxed king, or a
box with one covered gap) for knight smothers. `SmotherClassic false` restores
1.5.1's aim. The [test status page][status-link] shows how games end, version by
version.

## Download

Prebuilt binaries are on the [Releases page][release-link].

| File | For |
| ---- | --- |
| `smotherfish-1.6-android-arm64-dotprod` | Android phones from about 2019 on (try this first) |
| `smotherfish-1.6-android-arm64` | Older Android phones, or if the first does not start |
| `smotherfish-1.6-windows-x86-64-avx2.exe` | Windows PCs from about 2015 on |
| `smotherfish-1.6-windows-x86-64.exe` | Older Windows PCs |
| `smotherfish-1.6-linux-x86-64-avx2` | Linux, CPUs from about 2015 on |
| `smotherfish-1.6-linux-x86-64` | Linux, older CPUs |

Every binary is checked against the bench signature before release. Keep the
file name: DroidFish treats an engine named `stockfish` specially.

## Using Smotherfish

Like Stockfish, Smotherfish has no graphical interface. Add it as a UCI engine
in any chess GUI, for example DroidFish (Android), Arena, Cute Chess, En Croissant
or ChessBase, or run it as a Lichess bot through
[lichess-bot](https://github.com/lichess-bot-devs/lichess-bot). It identifies
itself as `Smotherfish 1.6 (Stockfish dev-20261122-3e8fde75)`.

No settings are needed: smother hunting is on by default. Common profiles:

| Goal | Settings |
| ---- | -------- |
| Knight smothered mates (default) | none |
| Any smothered mate, as often as possible (about two thirds of games against 1500-rated opponents; mostly near smothers) | `SmotherClassic false`, `SmotherGoal Near` |
| Ordinary Stockfish play, smothers only when proven | `SmotherBrutal false` |
| Play like a human of a given rating | `HumanElo` 1020-2400 (calibrated against Maia-3) |
| Weaker analysis on a phone | `Analysis Elo` N |

Against human opponents (when the GUI sends `UCI_Opponent`, as lichess-bot
does), Smotherfish shortens its smother building, because people resign lost
positions long before a long build ends. Every option is documented in the
[guide][guide-link].

## How it works

| Component | Where | What it does |
| --------- | ----- | ------------ |
| Prover | `src/smother.cpp` | AND/OR proof search on a helper thread. The defence that resists longest must end in a smothered mate; every other defence must lose to a faster ordinary mate. Verified on all 24,506 Lichess `smotheredMate` puzzles. |
| Brutal mode | `src/search.cpp` | Ordinary mates count below smothered ones; the prover searches deeper (16 moves, 3 quiet) when the engine is crushing. |
| Construction mode | `src/search.cpp`, `src/smother.cpp` | From +8 pawns (or a forced mate): extra material counts 1/8, a construction score rewards a boxed, cornered king, kept enemy pieces and a knight on its way to a checking square. Never drops below +6; up to 160 moves per game. |
| Goal | `SmotherGoal`, `SmotherClassic` | Knight smothers first; "all but one" smothers are also accepted after 80 construction moves (40 against people). |

The [guide][guide-link] explains each part in detail, with the measurements
behind every default.

## Testing and results

Smotherfish is developed by measurement. Each idea is played out over thousands
of games against Stockfish limited by `UCI_Elo` and against the human-like
Maia-3 network, and each default change must pass a strength test (SPRT) against
the previous version at full strength, the method Stockfish's own Fishtest uses.

- **Strength.** 1.2 against unmodified Stockfish: -0.3 Elo over 43,200 games
  (95%: -1.1 to +0.4); 1.3 at 60+0.6: +0.5 Elo over 7,320 games. Later versions
  are each within noise of their predecessor (1.6: -0.3 Elo over 32,400 games).
- **Research.** The guide's "Findings" section summarises what limits smothered
  mates and which ideas did not work (learned networks, trap steering, keeping
  material, deeper proving), so they are not repeated.
- **Live status.** The [test status page][status-link] shows running tests,
  the helpers and every recent result.

## Help test Smotherfish

Tests run on GitHub Actions, spread over volunteers' forks of this repository.
Anyone with a GitHub account can lend their Actions minutes: fork the
repository, enable its workflows and run the "Helper poll" workflow once. Your
fork then plays its share of every test; nothing runs on your computer. See
[Helping test Smotherfish][helping-link].

## Building from source

Building works exactly as for Stockfish:

```
cd src
make -j profile-build
```

`./stockfish bench` must report **1210779** nodes, the same as the upstream
commit: the bench runs with smother hunting off, and the smother features do
not change Stockfish's normal search.

## Repository layout

| Path | Contents |
| ---- | -------- |
| `src/smother.h`, `src/smother.cpp` | The smother prover, the construction score and the learned model and network |
| `src/search.cpp` | How the prover, brutal mode and construction mode are wired into the search (search for "Smother") |
| `docs/SMOTHERFISH.md` | The guide: concepts, every option, methodology and results |
| `docs/HELPING.md` | How to lend GitHub Actions minutes to the tests |
| `docs/CHANGELOG.md` | Release history |
| `docs/status/` | Source of the test status page (published from the `gh-pages` branch) |
| `notes/HANDOFF.md` | The full development log, experiment by experiment |
| `notes/scripts/` | Match runner, test distribution, analysis and training tools |
| `notes/exp/`, `notes/release/` | Experiment plans and release notes |
| `.github/workflows/` | Experiments, strength tests, helper polling, releases and the Lichess bot |

## License and credits

Smotherfish is free software under the
[GNU General Public License version 3][smf-license-link], like Stockfish. All
credit for the engine itself goes to the Stockfish developers (see
[AUTHORS](AUTHORS)). If you distribute Smotherfish, you must include the license
and the full source code, including the changes in this fork.

## About Stockfish (upstream)

[Stockfish][website-link] is a free and strong UCI chess engine derived from
Glaurung 2.1 that analyzes chess positions and computes the optimal moves. It
does not include a graphical user interface; see the Stockfish
[documentation][wiki-usage-link] for usage, [compiling][wiki-compile-link] and
the supported [UCI commands][wiki-uci-link]. Stockfish is improved through
massive testing on [Fishtest][fishtest-link]; you can donate hardware by running
the [Fishtest Worker][worker-link]. Discussion about Stockfish takes place mainly
on the Stockfish [Discord server][discord-link]; contribution rules are in the
[Contributing Guide](CONTRIBUTING.md).

### Terms of use

Stockfish is free and distributed under the
[**GNU General Public License version 3**][license-link] (GPL v3). Essentially,
this means you are free to do almost exactly what you want with the program,
including distributing it among your friends, making it available for download
from your website, selling it (either by itself or as part of some bigger
software package), or using it as the starting point for a software project of
your own.

The only real limitation is that whenever you distribute Stockfish in some way,
you MUST always include the license and the full source code (or a pointer to
where the source code can be found) to generate the exact binary you are
distributing. If you make any changes to the source code, these changes must
also be made available under GPL v3.

### Acknowledgements

Stockfish uses neural networks trained on [data provided by the Leela Chess Zero
project][lc0-data-link], which is made available under the [Open Database License][odbl-link] (ODbL).


[discord-link]:       https://discord.gg/GWDRS3kU6R
[fishtest-link]:      https://tests.stockfishchess.org/tests
[license-link]:       https://github.com/official-stockfish/Stockfish/blob/master/Copying.txt
[uci-link]:           https://backscattering.de/chess/uci/
[website-link]:       https://stockfishchess.org
[wiki-compile-link]:  https://github.com/official-stockfish/Stockfish/wiki/Compiling-from-source
[wiki-uci-link]:      https://github.com/official-stockfish/Stockfish/wiki/UCI-&-Commands
[wiki-usage-link]:    https://github.com/official-stockfish/Stockfish/wiki/Download-and-usage
[worker-link]:        https://github.com/official-stockfish/fishtest/wiki/Running-the-worker
[lc0-data-link]:      https://storage.lczero.org/files/training_data
[odbl-link]:          https://opendatacommons.org/licenses/odbl/odbl-10.txt

[guide-link]:        docs/SMOTHERFISH.md
[changelog-link]:    docs/CHANGELOG.md
[helping-link]:      docs/HELPING.md
[handoff-link]:      notes/HANDOFF.md
[status-link]:       https://demonic1594.github.io/Smotherfish/
[release-link]:      https://github.com/Demonic1594/Smotherfish/releases/latest
[upstream-link]:     https://github.com/official-stockfish/Stockfish
[smf-issue-link]:    https://github.com/Demonic1594/Smotherfish/issues/new
[smf-license-link]:  Copying.txt
[smf-commits-link]:  https://github.com/Demonic1594/Smotherfish/commits/smotherfish
[release-badge]:     https://img.shields.io/github/v/release/Demonic1594/Smotherfish?style=for-the-badge&color=3d6fd0
[based-badge]:       https://img.shields.io/badge/based%20on-Stockfish%20dev%202026--11--22-152867?style=for-the-badge
[uci-badge]:         https://img.shields.io/badge/protocol-UCI-informational?style=for-the-badge
[commit-badge]:      https://img.shields.io/github/last-commit/Demonic1594/Smotherfish/smotherfish?style=for-the-badge
[status-badge]:      https://img.shields.io/badge/test%20status-live-e5392f?style=for-the-badge
[smf-license-badge]: https://img.shields.io/badge/license-GPL--3.0-success?style=for-the-badge
