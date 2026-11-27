"""Knight supply in won games: do we still have a knight when the game is
decided (+8 material), do we lose it afterwards (and how), do we make a new
one by promotion, and how does the knight-smother rate depend on it.
Usage: python knight_supply.py FILE.jsonl...
"""
import collections
import json
import sys
from multiprocessing import Pool

import chess

VAL = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}


def mat(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)


def analyse(line):
    g = json.loads(line)
    if g.get("ours") != 1:
        return None
    us = chess.WHITE if g["ours_white"] else chess.BLACK
    them = not us
    b = chess.Board(g["fen"])
    mv = g["moves"].split()
    dec = None
    kn_at_dec = None
    lost_by = collections.Counter()  # how our knights disappeared after decided
    promo = collections.Counter()
    positions = 0
    no_knight_pos = 0
    pawn_lead_no_knight = 0  # positions without a knight but with a pawn of ours
    for i, u in enumerate(mv):
        m = chess.Move.from_uci(u)
        if dec is None and b.turn == us and mat(b, us) - mat(b, them) >= 8:
            dec = i
            kn_at_dec = len(b.pieces(chess.KNIGHT, us))
        if dec is not None and b.turn == us:
            positions += 1
            if not b.pieces(chess.KNIGHT, us):
                no_knight_pos += 1
                if b.pieces(chess.PAWN, us):
                    pawn_lead_no_knight += 1
        if dec is not None:
            if b.turn == them and b.piece_type_at(m.to_square) == chess.KNIGHT and b.color_at(m.to_square) == us:
                # the defender takes our knight: was it defended (a trade) or not?
                defended = bool(b.attackers(us, m.to_square))
                lost_by["traded" if defended else "hung"] += 1
            if b.turn == us and m.promotion:
                promo[chess.piece_symbol(m.promotion)] += 1
        b.push(m)
    return dict(smother=g["smother"], dec=dec is not None, kn=kn_at_dec, lost=lost_by,
                promo=promo, pos=positions, nk=no_knight_pos, pk=pawn_lead_no_knight,
                kn_end=len(b.pieces(chess.KNIGHT, us)))


def main():
    lines = [l for f in sys.argv[1:] for l in open(f)]
    with Pool(4) as p:
        R = [r for r in p.map(analyse, lines, chunksize=20) if r and r["dec"]]
    n = len(R)
    ks = sum(r["smother"] == "classic" for r in R)
    print(f"decided won games {n}, knight smothers {ks} ({100*ks/n:.2f} per 100)")
    print("\nknights of ours when decided (+8): games / knight smothers / per 100")
    for k in (0, 1, 2):
        L = [r for r in R if min(r["kn"], 2) == k]
        s = sum(r["smother"] == "classic" for r in L)
        print(f"  {k}{'+' if k == 2 else ' '}  {len(L):5d}  {s:4d}  {100*s/max(1,len(L)):5.2f}")
    P = sum(r["pos"] for r in R); NK = sum(r["nk"] for r in R); PK = sum(r["pk"] for r in R)
    print(f"\nour positions after decided: {P}; with no knight of ours {NK} ({100*NK/P:.1f}%), "
          f"of those with a pawn of ours left {PK} ({100*PK/max(1,NK):.1f}%)")
    lost = collections.Counter(); promo = collections.Counter()
    for r in R:
        lost += r["lost"]; promo += r["promo"]
    print(f"our knights taken by the defender after decided: {dict(lost)}")
    print(f"our promotions after decided: {dict(promo)}")
    # games that had a knight at decided but none at the end (non-smother games)
    gone = [r for r in R if r["kn"] and not r["kn_end"] and r["smother"] != "classic"]
    print(f"games with a knight at +8 and none at the end (no knight smother): {len(gone)} ({100*len(gone)/n:.1f}%)")
    # share of each game's construction spent without a knight, by outcome
    for lab, L in (("knight smother", [r for r in R if r["smother"] == "classic"]),
                   ("other", [r for r in R if r["smother"] != "classic"])):
        a = sum(r["nk"] for r in L); b_ = sum(r["pos"] for r in L)
        print(f"  {lab:15s}: positions without a knight {100*a/max(1,b_):.1f}% of {b_}")


if __name__ == "__main__":
    main()
