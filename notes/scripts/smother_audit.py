"""Closure audit: positions (us to move, >= +8, enemy king with exactly H
open ring squares) from games WITHOUT a knight smother and WITH one; does a
forced knight smother exist for a large prover budget?"""
import json, sys, random, subprocess, collections, chess
from multiprocessing import Pool
V = {1:1,2:3,3:3,4:5,5:9,6:0}
def mat(b, c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color == c)
E = {}
def init():
    p = subprocess.Popen(["/home/user/Smotherfish/src/stockfish"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    for k, v in {"Threads": 1, "Hash": 16, "SmotherParallel": "false", "SmotherGoal": "Full", "SmotherClassic": "true",
                 "SmotherMaxMoves": 16, "SmotherQuietMoves": 3, "SmotherNodes": 20000000}.items():
        p.stdin.write(f"setoption name {k} value {v}\n")
    E["p"] = p
def run(fen):
    p = E["p"]; p.stdin.write(f"ucinewgame\nposition fen {fen}\ngo depth 1\n"); r = None
    while True:
        l = p.stdout.readline()
        if "smother mate in" in l and "proven" in l: r = int(l.split("mate in")[1].split()[0])
        if l.startswith("bestmove"): return fen, r
def holes(b, us):
    k = b.king(not us); return sum(1 for s in chess.SquareSet(chess.BB_KING_ATTACKS[k]) if not ((q := b.piece_at(s)) and q.color != us))
random.seed(5); S = collections.defaultdict(list)
for f in sys.argv[2:]:
    for l in open(f):
        g = json.loads(l)
        if g.get("ours") != 1: continue
        us = g["ours_white"]; won = g["smother"] == "classic"; b = chess.Board(g["fen"]); mv = g["moves"].split()
        for i, u in enumerate(mv):
            b.push_uci(u)
            if b.turn != us or b.is_game_over() or mat(b, us) - mat(b, not us) < 8: continue
            h = holes(b, us); k = b.king(not us); kf, kr = chess.square_file(k), chess.square_rank(k)
            if h <= 2 and (kf in (0, 7) or kr in (0, 7)) and random.random() < 0.03:
                # skip positions within 16 of our moves before the actual smother (already found in game)
                if won and (len(mv) - 1 - i) <= 32: continue
                S[(won, h)].append(b.fen())
N = int(sys.argv[1]); jobs = []
for key, L in S.items():
    random.shuffle(L); jobs += [(key, f) for f in L[:N]]
with Pool(3, initializer=init) as pool:
    res = dict(pool.map(run, [f for _, f in jobs], chunksize=4))
out = collections.defaultdict(lambda: [0, 0, []])
for key, f in jobs:
    o = out[key]; o[0] += 1; r = res[f]
    if r: o[1] += 1; o[2].append(r)
for (won, h), (n, k, ls) in sorted(out.items()):
    print(f"game {'with' if won else 'without'} knight smother, {h} open ring squares: {k}/{n} = {100*k/n:.1f}% have a forced knight smother (median length {sorted(ls)[len(ls)//2] if ls else '-'})")
