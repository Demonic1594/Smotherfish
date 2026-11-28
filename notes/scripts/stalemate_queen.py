"""The desperado configuration: defender to move (not in check, we lead by
+8), its king has no legal move, and it has a queen off the king's ring (a
piece free to check us). How many stalemate, knight-smother and other won
games pass through it before their end, and in knight smothers, did a
defender queen help close the box (on the ring at mate)?
Usage: python stalemate_queen.py FILE.jsonl...
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
    them = not us
    b = chess.Board(g["fen"])
    hit = None
    plies = g["moves"].split()
    for i, u in enumerate(plies):
        if hit is None and b.turn == them and not b.is_check() and mat(b, us) - mat(b, them) >= 8:
            k = b.king(them)
            ring = chess.BB_KING_ATTACKS[k]
            free_q = any(not (chess.BB_SQUARES[s] & ring) for s in b.pieces(chess.QUEEN, them))
            if free_q and not any(m.from_square == k for m in b.legal_moves):
                hit = len(plies) - i  # plies before the end
        b.push_uci(u)
    if g["ours"] == 0.5:
        kind = "stalemate" if b.is_stalemate() and b.turn != us else "other draw"
    else:
        kind = "knight smother" if g.get("smother") == "classic" else "other win"
    q_ring = kind == "knight smother" and bool(b.pieces(chess.QUEEN, them) & chess.SquareSet(chess.BB_KING_ATTACKS[b.king(them)]))
    return kind, hit, q_ring


def main():
    lines = [l for f in sys.argv[1:] for l in open(f)]
    with Pool(4) as p:
        R = [r for r in p.map(analyse, lines, chunksize=50) if r]
    by = collections.defaultdict(list)
    for r in R:
        by[r[0]].append(r)
    for k, L in sorted(by.items()):
        h = [r[1] for r in L if r[1] is not None]
        med = sorted(h)[len(h) // 2] if h else 0
        extra = f"; a defender queen on the ring at mate in {sum(r[2] for r in L)}" if k == "knight smother" else ""
        print(f"{k:15s} {len(L):6d} games; pass a boxed king with a free defender queen: {len(h)} ({100*len(h)/len(L):.1f}%), median {med} plies before the end{extra}")


if __name__ == "__main__":
    main()
