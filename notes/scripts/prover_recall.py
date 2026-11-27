"""Per-game recall of a prover variant at an in-game node budget.
For each sampled won game, walk our positions after +8 material where the
enemy king has at most MAXOPEN open ring squares, and run the prover (knight
smothers only, 16 moves, 3 quiet) with NODES nodes until the first proof.
Report, per variant, the share of games without a knight smother in which a
forced one was proven at some point, and (for knight-smother games) how many
of our moves before the real mate the first proof came.
Usage: python prover_recall.py ENGINE GAMES NODES MAXOPEN FILE.jsonl...
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
    "current": {"SmotherProverZugzwang": 0, "SmotherProverThreatQuiet": "false"},
    "zugzwang4": {"SmotherProverZugzwang": 4, "SmotherProverThreatQuiet": "false"},
    "both": {"SmotherProverZugzwang": 4, "SmotherProverThreatQuiet": "true"},
}
ENGINE, NGAMES, NODES, MAXOPEN = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
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


def prove(fen):
    p = E["p"]
    p.stdin.write(f"ucinewgame\nposition fen {fen}\ngo depth 1\n")
    r = None
    while True:
        l = p.stdout.readline()
        if "smother mate in" in l and "proven" in l:
            r = int(l.split("mate in")[1].split()[0])
        if l.startswith("bestmove"):
            return r


def run(job):
    g, var = job
    p = E["p"]
    for k, v in VARIANTS[var].items():
        p.stdin.write(f"setoption name {k} value {v}\n")
    us = g["ours_white"]
    b = chess.Board(g["fen"]); mv = g["moves"].split()
    n_our = sum(1 for i in range(len(mv)) if (i % 2 == 0) == (b.turn == us))
    tried = 0
    ours_left = None
    for i, u in enumerate(mv):
        if b.turn == us and not b.is_game_over() and mat(b, us) - mat(b, not us) >= 8 \
                and holes(b, us) <= MAXOPEN and b.pieces(chess.KNIGHT, us):
            tried += 1
            r = prove(b.fen())
            if r:
                ours_left = sum(1 for j in range(i, len(mv)) if (j - i) % 2 == 0)
                return g["game"], g["_f"], var, True, ours_left, tried, b.fen()
        b.push_uci(u)
    return g["game"], g["_f"], var, False, None, tried, None


def main():
    random.seed(11)
    G = []
    for f in sys.argv[5:]:
        for l in open(f):
            g = json.loads(l)
            if g.get("ours") == 1:
                g["_f"] = f
                G.append(g)
    random.shuffle(G)
    sm = [g for g in G if g["smother"] == "classic"][: NGAMES // 4]
    no = [g for g in G if g["smother"] != "classic"][: NGAMES - len(sm)]
    jobs = [(g, v) for g in sm + no for v in VARIANTS]
    with Pool(4, initializer=init) as pool:
        R = list(pool.imap_unordered(run, jobs, chunksize=1))
    print(f"node budget {NODES:,}; positions: >= +8, <= {MAXOPEN} open ring squares, we have a knight")
    for v in VARIANTS:
        Rv = [r for r in R if r[2] == v]
        key = {(r[0], r[1]): r for r in Rv}
        fn = [key[(g["game"], g["_f"])] for g in no]
        fs = [key[(g["game"], g["_f"])] for g in sm]
        found_no = sum(r[3] for r in fn)
        lead = sorted(r[4] for r in fs if r[3])
        print(f"{v:10s}: games without a knight smother: proof found in {found_no}/{len(fn)} ({100*found_no/len(fn):.1f}%); "
              f"knight-smother games: found in {sum(r[3] for r in fs)}/{len(fs)}, median {lead[len(lead)//2] if lead else '-'} of our moves before the real mate; "
              f"positions proved per game {sum(r[5] for r in Rv)/len(Rv):.1f}")
    json.dump(R, open(f"recall_{NODES}_{MAXOPEN}.json", "w"))


if __name__ == "__main__":
    main()
