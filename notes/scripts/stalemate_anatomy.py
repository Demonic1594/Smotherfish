"""Anatomy of the stalemates we give in won games. For every drawn game of
ours (match.py records) that ends in stalemate with the defender to move:
- box close: the last of our moves after which the defender's king had no
  legal move and kept none until the end;
- at that moment: material, the defender's legal moves and which pieces make
  them (the "loose" pieces), and whether we had a move that left the king a
  square;
- the end: plies from box close to stalemate, and how many of the defender's
  moves in between were checks (a rampant piece forcing the draw).
Usage: python stalemate_anatomy.py FILE.jsonl...
"""
import collections
import json
import sys

import chess

VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def mat(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)


def king_moves(b):
    k = b.king(b.turn)
    return sum(1 for m in b.legal_moves if m.from_square == k)


def analyse(g, src):
    us = chess.WHITE if g["ours_white"] else chess.BLACK
    b = chess.Board(g["fen"])
    boards = [b.copy()]
    for u in g["moves"].split():
        b.push_uci(u)
        boards.append(b.copy())
    if not b.is_stalemate() or b.turn == us:
        return None
    # box close: walk back over positions with the defender to move and no king move
    i = len(boards) - 1
    close = i
    while i >= 1:
        p = boards[i]
        if p.turn != us:
            if king_moves(p) > 0:
                break
            close = i
        i -= 1
    pos = boards[close]          # defender to move, king boxed
    before = boards[close - 1]   # our move that closed the box
    movers = collections.Counter(pos.piece_at(m.from_square).piece_type for m in pos.legal_moves)
    # could we have left the king a square instead?
    alt = 0
    for m in before.legal_moves:
        before.push(m)
        if not before.is_game_over() and king_moves(before) > 0:
            alt += 1
        before.pop()
    checks = sum(1 for j in range(close, len(boards) - 1) if boards[j].turn != us and boards[j + 1].is_check())
    them = not us
    loose = sorted({chess.piece_name(pt) for pt in movers if pt != chess.PAWN})
    return {
        "src": src,
        "plies": len(boards) - 1 - close,
        "def_checks": checks,
        "def_moves": pos.legal_moves.count(),
        "pawn_moves": movers.get(chess.PAWN, 0),
        "loose": "+".join(loose) or "none",
        "mat_diff": mat(pos, us) - mat(pos, them),
        "their_pieces": sum(1 for p in pos.piece_map().values() if p.color == them and p.piece_type not in (chess.PAWN, chess.KING)),
        "alt_moves": alt,
        "close_in_check": before.is_check(),
        "fen_close": before.fen(),
    }


def main():
    R = []
    for f in sys.argv[1:]:
        src = "/".join(f.split("/")[-2:])
        for l in open(f):
            g = json.loads(l)
            if g.get("ours") == 0.5:
                r = analyse(g, src)
                if r:
                    R.append(r)
    n = len(R)
    print(f"stalemates by us: {n}")
    if not n:
        return
    med = lambda k: sorted(r[k] for r in R)[n // 2]
    print(f"median material lead at box close {med('mat_diff')}, median plies box close -> stalemate {med('plies')}")
    print("loose pieces at box close:", collections.Counter(r["loose"] for r in R).most_common())
    print("defender legal moves at box close:", sorted(collections.Counter(min(r["def_moves"], 10) for r in R).items()))
    print(f"defender had a pawn move at box close: {sum(r['pawn_moves'] > 0 for r in R)}")
    print(f"defender pieces (not pawns) at box close:", sorted(collections.Counter(r["their_pieces"] for r in R).items()))
    print(f"we had a move leaving the king a square: {sum(r['alt_moves'] > 0 for r in R)} of {n} (median {med('alt_moves')} such moves)")
    print(f"we were in check when closing the box: {sum(r['close_in_check'] for r in R)}")
    print("defender checks between box close and stalemate:", sorted(collections.Counter(min(r['def_checks'], 6) for r in R).items()))
    print("by source:", sorted(collections.Counter(r["src"] for r in R).items()))
    json.dump(R, open("stalemates.json", "w"), indent=0)


if __name__ == "__main__":
    main()
