#!/usr/bin/env python3
"""Human smother test set: positions from real Lichess games that ended in a
full or classic smothered mate (lichess_db.py output), K attacker moves
before the mate. For each position:
  real   - Smotherfish with its defaults, a short warm-up search then
           "go movetime MS" (so brutal mode has a previous score, as in a
           game): did it report a proven smother, and is its move the one
           the human played?
  oracle - a large prover budget (SmotherMaxMoves 12, 2 quiet, NODES):
           does a forced smother exist at all (else the human defender
           simply erred into it)?
usage: human_smother_test.py ENGINE OUT.jsonl SMOTHERS.jsonl.zst... [--games N]
       [--ks 1,3,5,10] [--ms 800] [--nodes 5000000] [--workers 4] [--seed 1]"""
import argparse, io, json, random, subprocess, sys
from multiprocessing import Pool
import chess, zstandard

ap = argparse.ArgumentParser()
ap.add_argument("engine"); ap.add_argument("out"); ap.add_argument("files", nargs="+")
ap.add_argument("--games", type=int, default=200); ap.add_argument("--ks", default="1,3,5,10")
ap.add_argument("--ms", type=int, default=800); ap.add_argument("--nodes", type=int, default=5000000)
ap.add_argument("--workers", type=int, default=4); ap.add_argument("--seed", type=int, default=1)
A = ap.parse_args()
E = {}


class Eng:
    def __init__(self, opts):
        self.p = subprocess.Popen([A.engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        for k, v in opts.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        while self.p.stdout.readline().strip() != "readyok":
            pass

    def send(self, s):
        self.p.stdin.write(s + "\n")

    def go(self, moves, cmd):
        self.send("position startpos" + (" moves " + " ".join(moves) if moves else ""))
        self.send(cmd); lines = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError("engine died")
            lines.append(l)
            if l.startswith("bestmove"):
                return lines


def init():
    E["real"] = Eng({"Threads": 1, "Hash": 16})
    E["oracle"] = Eng({"Threads": 1, "Hash": 16, "SmotherParallel": "false", "SmotherGoal": "Full",
                       "SmotherMaxMoves": 12, "SmotherQuietMoves": 2, "SmotherNodes": A.nodes})


def proven(lines):
    for l in lines:
        if "smother mate in" in l and "proven" in l:
            return int(l.split("mate in")[1].split()[0])
    return None


def run(item):
    g, k = item
    mv = g["moves"].split(); p = len(mv) - (2 * k - 1)
    if p < 0:
        return None
    pre = mv[:p]
    E["real"].send("ucinewgame")
    E["real"].go(pre, "go movetime 200")  # warm-up: a previous score, as in a game
    lines = E["real"].go(pre, f"go movetime {A.ms}")
    best = lines[-1].split()[1]
    return {"site": g["site"], "elo": g["elo"], "speed": g["speed"], "kind": g["smother"], "k": k,
            "real_proof": proven(lines), "same_move": best == mv[p],
            "oracle": proven(E["oracle"].go(pre, "go depth 1"))}


if __name__ == "__main__":
    G = []
    for f in A.files:
        for l in io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(open(f, "rb"))):
            g = json.loads(l)
            if g["smother"] in ("full", "classic"):
                G.append(g)
    random.Random(A.seed).shuffle(G); G = G[:A.games]
    ks = [int(x) for x in A.ks.split(",")]
    items = [(g, k) for g in G for k in ks]
    with Pool(A.workers, initializer=init) as pool, open(A.out, "w") as f:
        for i, r in enumerate(pool.imap_unordered(run, items), 1):
            if r:
                f.write(json.dumps(r) + "\n"); f.flush()
            if i % 100 == 0:
                print(i, "of", len(items), file=sys.stderr, flush=True)
