"""Do the defender's promotions cause our stalemates? For our won and drawn
games (match.py records), after we first lead by +8 material: did the
defender promote a pawn, and (stalemates) was the piece we captured last a
promoted one? Compared with knight-smother games and other wins.
Usage: python stalemate_promotions.py FILE.jsonl...
"""
import collections
import json
import sys
from multiprocessing import Pool

import chess

VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def mat(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)


def analyse(line):
    g = json.loads(line)
    if g.get("ours") not in (0.5, 1):
        return None
    us = chess.WHITE if g["ours_white"] else chess.BLACK
    b = chess.Board(g["fen"])
    won = False
    promos = 0
    promoted_sq = set()
    last_capture_promoted = False
    for u in g["moves"].split():
        m = chess.Move.from_uci(u)
        if not won and mat(b, us) - mat(b, not us) >= 8:
            won = True
        if b.turn != us:
            if won and m.promotion:
                promos += 1
                promoted_sq.add(m.to_square)
            elif m.from_square in promoted_sq:
                promoted_sq.discard(m.from_square)
                promoted_sq.add(m.to_square)
        else:
            last_capture_promoted = b.is_capture(m) and m.to_square in promoted_sq
            promoted_sq.discard(m.to_square)
        b.push(m)
    if g["ours"] == 0.5:
        kind = "stalemate" if b.is_stalemate() and b.turn != us else "other draw"
    else:
        kind = "knight smother" if g.get("smother") == "classic" else "other win"
    return kind, won, promos, last_capture_promoted


def main():
    lines = [l for f in sys.argv[1:] for l in open(f)]
    with Pool(4) as p:
        R = [r for r in p.map(analyse, lines, chunksize=50) if r and r[1]]
    by = collections.defaultdict(list)
    for r in R:
        by[r[0]].append(r)
    for k, L in sorted(by.items()):
        n = len(L); pr = sum(1 for r in L if r[2] > 0)
        line = f"{k:15s} {n:6d} games reaching +8; defender promoted after +8 in {pr} ({100*pr/n:.1f}%)"
        if k == "stalemate":
            line += f"; our stalemating capture took a promoted piece in {sum(r[3] for r in L)}"
        print(line)


if __name__ == "__main__":
    main()
