"""Prover blind-spot audit. Positions as in notes/scripts/smother_audit.py
(us to move, >= +8 material, enemy king on an edge, H open ring squares),
from 1.6 games without a knight smother, and from games with one (more than
16 of our moves before the mate). Each position is proved by several prover
variants with the same node budget; does a forced knight smother exist?
Usage: python prover_audit.py ENGINE N NODES FILE.jsonl...
"""
import collections
import json
import random
import subprocess
import sys
from multiprocessing import Pool

import chess

VAL = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}
VARIANTS = {
    "current": {},
    "zugzwang4": {"SmotherProverZugzwang": 4},
    "threat+1quiet": {"SmotherProverThreatQuiet": "true"},
    "both": {"SmotherProverZugzwang": 4, "SmotherProverThreatQuiet": "true"},
}
ENGINE = sys.argv[1]
NODES = int(sys.argv[3])
E = {}


def mat(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)


def holes(b, us):
    k = b.king(not us)
    return sum(1 for s in chess.SquareSet(chess.BB_KING_ATTACKS[k]) if not ((q := b.piece_at(s)) and q.color != us))


def init():
    p = subprocess.Popen([ENGINE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    base = {"Threads": 1, "Hash": 16, "SmotherParallel": "false", "SmotherGoal": "Full", "SmotherClassic": "true",
            "SmotherMaxMoves": 16, "SmotherQuietMoves": 3, "SmotherNodes": NODES}
    for k, v in base.items():
        p.stdin.write(f"setoption name {k} value {v}\n")
    E["p"] = p


def run(job):
    fen, var = job
    p = E["p"]
    opts = {"SmotherProverZugzwang": 0, "SmotherProverThreatQuiet": "false", **VARIANTS[var]}
    for k, v in opts.items():
        p.stdin.write(f"setoption name {k} value {v}\n")
    p.stdin.write(f"ucinewgame\nposition fen {fen}\ngo depth 1\n")
    r = None; nodes = None; first = None
    while True:
        l = p.stdout.readline()
        if "smother mate in" in l and "proven" in l:
            r = int(l.split("mate in")[1].split()[0]); nodes = int(l.split("proven,")[1].split()[0])
        if l.startswith("bestmove"):
            first = l.split()[1]
            return fen, var, r, nodes, first


def main():
    random.seed(5)
    S = collections.defaultdict(list)
    for f in sys.argv[4:]:
        for l in open(f):
            g = json.loads(l)
            if g.get("ours") != 1:
                continue
            us = g["ours_white"]; won = g["smother"] == "classic"
            b = chess.Board(g["fen"]); mv = g["moves"].split()
            for i, u in enumerate(mv):
                b.push_uci(u)
                if b.turn != us or b.is_game_over() or mat(b, us) - mat(b, not us) < 8:
                    continue
                h = holes(b, us); k = b.king(not us)
                if 1 <= h <= 2 and (chess.square_file(k) in (0, 7) or chess.square_rank(k) in (0, 7)) and random.random() < 0.03:
                    if won and (len(mv) - 1 - i) <= 32:
                        continue
                    S[(won, h, bool(b.pieces(chess.KNIGHT, us)))].append(b.fen())
    N = int(sys.argv[2])
    pos = []
    for key, L in sorted(S.items()):
        random.shuffle(L)
        pos += [(key, f) for f in L[:N]]
    jobs = [(f, v) for _, f in pos for v in VARIANTS]
    with Pool(4, initializer=init) as pool:
        res = {(f, v): (r, n, m) for f, v, r, n, m in pool.imap_unordered(run, jobs, chunksize=2)}
    print(f"node budget {NODES:,} per position; positions per cell up to {N}")
    print(f"{'cell':44s} " + "  ".join(f"{v:>15s}" for v in VARIANTS))
    cells = collections.defaultdict(list)
    for key, f in pos:
        cells[key].append(f)
    for key in sorted(cells):
        won, h, kn = key
        L = cells[key]
        row = []
        for v in VARIANTS:
            k = sum(1 for f in L if res[(f, v)][0])
            row.append(f"{k:3d}/{len(L):3d} {100*k/len(L):5.1f}%")
        print(f"{('smother game' if won else 'no smother'):12s} open {h}  {'knight' if kn else 'no knight':10s}      " + "  ".join(f"{x:>15s}" for x in row))
    new = [(f, v, res[(f, v)]) for _, f in pos for v in VARIANTS if v != "current" and res[(f, v)][0] and not res[(f, "current")][0]]
    print(f"\nproofs found only by a relaxed variant: {len(new)}")
    for f, v, (r, n, m) in new[:25]:
        print(f"  {v:14s} mate in {r:2d}  {n:>10,} nodes  first {m}  {f}")
    json.dump({f"{f}|{v}": r for (f, v), r in res.items()}, open("prover_audit.json", "w"))


if __name__ == "__main__":
    main()
