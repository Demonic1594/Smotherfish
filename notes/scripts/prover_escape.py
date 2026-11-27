"""After an escape: does a forced knight smother still exist? For every game
whose first proof episode ended without a knight smother following it
(match.py "proofs"), take our first three positions after the escape
(2, 4 and 6 plies after the episode's last proven move) and prove them with
a large budget. A hit means a bigger prover budget right after an escape
could have found a new smother.
Usage: python prover_escape.py ENGINE NODES FILE.jsonl...
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


def prove(fen):
    p = E["p"]
    p.stdin.write(f"ucinewgame\nposition fen {fen}\ngo depth 1\n")
    r = n = None
    while True:
        l = p.stdout.readline()
        if "smother mate in" in l and "proven" in l:
            r = int(l.split("mate in")[1].split()[0]); n = int(l.split("proven,")[1].split()[0])
        if l.startswith("bestmove"):
            return r, n


def first_episode_end(pl):
    end = pl[0]
    for x in pl[1:]:
        if x - end > 2:
            break
        end = x
    return end


def run(job):
    key, fens = job
    return key, [prove(f) for f in fens]


def main():
    jobs = []
    for f in sys.argv[3:]:
        for i, l in enumerate(open(f)):
            g = json.loads(l)
            if g.get("ours") != 1 or not g.get("proofs"):
                continue
            end = first_episode_end(g["proofs"])
            mv = g["moves"].split()
            # escaped: no knight smother within the episode (the game went on past it)
            if g.get("smother") == "classic" and len(mv) <= end + 2:
                continue
            b = chess.Board(g["fen"]); fens = []
            for j, u in enumerate(mv):
                if j in (end + 2, end + 4, end + 6) and not b.is_game_over():
                    fens.append(b.fen())
                b.push_uci(u)
            if fens:
                jobs.append(((f.split("/")[-2], i, g.get("smother") == "classic"), fens))
    with Pool(4, initializer=init) as pool:
        R = pool.map(run, jobs, chunksize=1)
    n = len(R)
    hit = [r for r in R if any(x[0] for x in r[1])]
    by_k = collections.Counter(next(k for k, x in enumerate(r[1]) if x[0]) for r in hit)
    print(f"escapes {n} (each: our first 3 positions after the escape, {NODES:,} nodes): forced knight smother in {len(hit)} ({100*len(hit)/n:.0f}%)")
    print("  first found at our move after the escape: " + ", ".join(f"{k + 1}: {v}" for k, v in sorted(by_k.items())))
    nodes = sorted(x[1] for r in hit for x in r[1] if x[0])
    if nodes:
        print(f"  nodes needed: median {nodes[len(nodes)//2]:,}, 75th pct {nodes[3*len(nodes)//4]:,}, max {nodes[-1]:,}")
    print(f"  of these, the game still ended in a knight smother later: {sum(1 for r in hit if r[0][2])}")


if __name__ == "__main__":
    main()
