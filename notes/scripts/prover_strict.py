"""Strict proofs at the first proof of each game. For every game of ours with
a proven knight smother (match.py "proofs": plies, our move), rebuild the
position of the first proof and prove it again twice with the same limits:
default rule (sanity) and SmotherStrict (every defence must be smothered).
Delivery (the game ended in a knight smother) is then split by whether a
strict proof existed there.
Usage: python prover_strict.py ENGINE NODES FILE.jsonl...
"""
import collections
import json
import subprocess
import sys
from multiprocessing import Pool

import chess

ENGINE, NODES = sys.argv[1], int(sys.argv[2])
E = {}


def init():
    p = subprocess.Popen([ENGINE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    for k, v in {"Threads": 1, "Hash": 16, "SmotherParallel": "false", "SmotherGoal": "Full", "SmotherClassic": "true",
                 "SmotherMaxMoves": 16, "SmotherQuietMoves": 3, "SmotherNodes": NODES}.items():
        p.stdin.write(f"setoption name {k} value {v}\n")
    E["p"] = p


def prove(fen, strict):
    p = E["p"]
    p.stdin.write(f"setoption name SmotherStrict value {'true' if strict else 'false'}\n"
                  f"ucinewgame\nposition fen {fen}\ngo depth 1\n")
    r = None
    while True:
        l = p.stdout.readline()
        if "smother mate in" in l and "proven" in l:
            r = int(l.split("mate in")[1].split()[0])
        if l.startswith("bestmove"):
            return r


def run(job):
    fen, delivered, src = job
    return fen, delivered, src, prove(fen, False), prove(fen, True)


def main():
    jobs = []
    for f in sys.argv[3:]:
        for l in open(f):
            g = json.loads(l)
            if g.get("ours") != 1 or not g.get("proofs"):
                continue
            b = chess.Board(g["fen"])
            for u in g["moves"].split()[: g["proofs"][0]]:
                b.push_uci(u)
            jobs.append((b.fen(), g.get("smother") == "classic", "/".join(f.split("/")[-2:])))
    with Pool(4, initializer=init) as pool:
        R = pool.map(run, jobs, chunksize=1)
    n = len(R)
    print(f"proof games {n}; re-proved with the default rule at {NODES:,} nodes: {sum(1 for r in R if r[3])}")
    for lab, L in (("strict proof exists", [r for r in R if r[4]]), ("no strict proof", [r for r in R if not r[4]])):
        d = sum(r[1] for r in L)
        print(f"  {lab:20s} {len(L):4d} games ({100*len(L)/n:4.1f}%), delivered {d} ({100*d/max(1,len(L)):.0f}%)")
    esc = [r for r in R if not r[1]]
    print(f"escaped games {len(esc)}: a strict proof existed at the first proof in {sum(1 for r in esc if r[4])}")
    L = [(r[3], r[4]) for r in R if r[3] and r[4]]
    if L:
        print("strict minus default proof length (moves): " + ", ".join(f"{k}: {v}" for k, v in sorted(collections.Counter(s - d for d, s in L).items())))
    by = collections.defaultdict(lambda: [0, 0, 0])
    for r in R:
        by[r[2]][0] += 1; by[r[2]][1] += r[1]; by[r[2]][2] += bool(r[4])
    for k, (a, d, s) in sorted(by.items()):
        print(f"  {k:28s} proof games {a:4d}  delivered {100*d/a:3.0f}%  strict available {100*s/a:3.0f}%")


if __name__ == "__main__":
    main()
