"""When should construction mode take the plain mate? For our won or drawn
games (match.py records), find the first position (defender to move, not in
check, at least +8 material for us) where the defender's king has no legal
move and the defender has at most K legal moves in all. Report, per K, how
many stalemate games reach such a position before the stalemate (would be
caught) and how many knight-smother games reach one before their first
proven smother (put at risk: a cash-in there could replace the smother by a
plain mate).
Usage: python stalemate_trigger.py FILE.jsonl...
"""
import collections
import json
import sys
from multiprocessing import Pool

import chess

VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
KS = (1, 2, 3, 4, 6, 99)


def mat(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)


def analyse(line):
    g = json.loads(line)
    if g.get("ours") not in (0.5, 1):
        return None
    us = chess.WHITE if g["ours_white"] else chess.BLACK
    b = chess.Board(g["fen"])
    moves = g["moves"].split()
    first_proof = g["proofs"][0] if g.get("proofs") else 10**9
    first = {}  # K -> first ply
    for ply, u in enumerate(moves):
        if b.turn != us and not b.is_check() and mat(b, us) - mat(b, not us) >= 8:
            k = b.king(b.turn)
            legal = list(b.legal_moves)
            if legal and not any(m.from_square == k for m in legal):
                for K in KS:
                    if K not in first and len(legal) <= K:
                        first[K] = ply
        b.push_uci(u)
    if g["ours"] == 0.5:
        kind = "stalemate" if b.is_stalemate() and b.turn != us else "other draw"
    else:
        kind = "knight smother" if g.get("smother") == "classic" else "other win"
    return kind, first, first_proof, len(moves)


def main():
    lines = [l for f in sys.argv[1:] for l in open(f)]
    with Pool(4) as p:
        R = [r for r in p.map(analyse, lines, chunksize=50) if r]
    tot = collections.Counter(r[0] for r in R)
    print("games:", dict(tot))
    print(" K  | stalemates caught | knight smothers at risk (trigger before first proof) | other wins passing a trigger")
    for K in KS:
        st = sum(1 for r in R if r[0] == "stalemate" and K in r[1])
        ks = sum(1 for r in R if r[0] == "knight smother" and K in r[1] and r[1][K] < r[2])
        ow = sum(1 for r in R if r[0] == "other win" and K in r[1])
        print(f" {K:2d} | {st:4d} of {tot['stalemate']} | {ks:4d} of {tot['knight smother']} | {ow}")


if __name__ == "__main__":
    main()
