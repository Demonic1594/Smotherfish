#!/usr/bin/env python3
"""Expand an experiment plan into a GitHub Actions matrix.

plan.json:
  {"exp": "exp4", "tc": "5+0.05", "chunk": 100,
   "runs": [{"name": "base_e1500", "elo": 1500, "games": 400, "seed": 10,
             "opts": ["SmotherShape=32", "SmotherShapeAlways=true"]}]}

Each run is split into chunks of `chunk` games (even), one matrix job per
chunk, with seed = run seed + chunk index so chunks use different openings. Jobs are ordered slowest
first; give slow runs (high Elo, brutal) a smaller "chunk" in the plan.
A run may set "opponent": "maia-<rating>" (1100-1900) to play Maia on lc0
(human-like, "go nodes 1") instead of Stockfish at UCI_Elo, or "opponent":
"ref" to play the engine built from the plan's "ref" (a git ref) at full
strength, with the run's "opp_opts".
A run may set "ponder": true (our engine ponders on the opponent's time;
one game per 4 cores) and "opp_think": SEC (the opponent's move is held back
to at least SEC seconds, like a person thinking).
Prints `exp=...`, `maia=...` and `matrix=...` lines for $GITHUB_OUTPUT.
"""
import json, sys

plan = json.load(open(sys.argv[1]))
default_chunk = int(plan.get("chunk", 100))
tc = plan.get("tc", "5+0.05")
jobs = []
for run in plan["runs"]:
    chunk = int(run.get("chunk", default_chunk))
    chunk -= chunk % 2
    games, i = int(run["games"]), 0
    while games > 0:
        g = min(chunk, games)
        g -= g % 2
        if g <= 0:
            break
        jobs.append({"name": run["name"], "elo": int(run["elo"]), "games": g,
                     "seed": int(run.get("seed", 1)) + i, "chunk": i,
                     "opts": " ".join(run.get("opts", [])), "tc": run.get("tc", tc),
                     "opp": run.get("opponent", ""),
                     "oppopts": " ".join(run.get("opp_opts", [])),
                     "ponder": bool(run.get("ponder", False)),
                     "runner": run.get("runner", plan.get("runner", "")),
                     "think": float(run.get("opp_think", 0))})
        games -= g
        i += 1
# Slowest jobs first, so the run does not wait on a long tail at the end:
# stronger opponents mean longer games, and brutal mode waits for the prover.
# Rough time per game relative to Elo 1500 (games get much longer at 3000).
ELO_COST = [(1500, 1.0), (2000, 1.5), (2500, 3.0), (3000, 6.0)]

def elo_cost(e):
    if e <= ELO_COST[0][0]:
        return ELO_COST[0][1]
    for (e0, c0), (e1, c1) in zip(ELO_COST, ELO_COST[1:]):
        if e <= e1:
            return c0 + (c1 - c0) * (e - e0) / (e1 - e0)
    return ELO_COST[-1][1]

def cost(j):
    base = float(j["tc"].split("+")[0]) / 5.0  # relative to 5+0.05
    c = j["games"] * elo_cost(j["elo"]) * base
    if "SmotherBrutal=true" in j["opts"]:
        c *= 2
    if j["ponder"]:
        c *= 4  # a quarter as many games at a time
    c *= 1 + j["think"]  # the opponent's thinking time dominates
    return -c
# Sharding: "shard": [i, n] keeps every n-th job of the full matrix
# (starting at i), so one experiment can be split over several accounts
# (ours and helper forks); the shards' results are merged afterwards
# (notes/scripts/merge_shards.py). Seeds come from the chunk index, so the
# shards never repeat a game.
if "shard" in plan:
    # i may be a list: an account with more capacity takes several shards.
    i, n = plan["shard"]
    mine = set(i) if isinstance(i, list) else {i}
    jobs.sort(key=lambda j: (j["name"], j["chunk"]))
    jobs = [j for k, j in enumerate(jobs) if k % n in mine]
jobs.sort(key=cost)
if len(jobs) > 256:
    sys.exit("matrix too large (max 256 jobs)")
# Maia opponents ("opponent": "maia-1500") need lc0 and those networks.
maia = sorted({j["opp"].split("-")[1] for j in jobs if j["opp"].startswith("maia-")})
print("exp=" + plan["exp"])
print("maxpar=" + str(int(plan.get("max_parallel", 18))))
print("maia=" + " ".join(maia))
# Maia-3 opponents ("opponent": "maia3-1500"): the CSSLab maia3 package (5M
# model on CPU, PyTorch), installed by each match job that needs it.
# "ref": a git ref built as an extra engine; runs with "opponent": "ref"
# play it at full strength (head-to-head), with "opp_opts" as its options.
print("ref=" + plan.get("ref", ""))
print("matrix=" + json.dumps(jobs))
