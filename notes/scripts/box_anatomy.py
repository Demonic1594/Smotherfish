"""Box-closure anatomy on Smotherfish game records (jsonl from match.py).

A "box" = every square next to the enemy king holds an enemy piece (0 open).
For every box closure (us to move, box closed, previous us-to-move position
not closed) record: what closed it (the defender's reply to our check: block
or capture; the defender's free move; a king step), whether a knight mate in
one exists ("armed"), our nearest knight's distance (knight moves) to a
knight-check square, and what happened next.
Usage: python box_anatomy.py FILE.jsonl...
"""
import collections
import json
import sys
from multiprocessing import Pool

import chess

VAL = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}


def mat(b, c):
    return sum(VAL[p.piece_type] for p in b.piece_map().values() if p.color == c)


def open_sq(b, them):
    k = b.king(them)
    return [s for s in chess.SquareSet(chess.BB_KING_ATTACKS[k])
            if not ((p := b.piece_at(s)) and p.color == them)]


def knight_dist(b, us, them):
    """Fewest knight moves for any knight of ours to reach a square that
    attacks the enemy king (board ignored apart from our own pieces on the
    target). 0 = no knight."""
    k = b.king(them)
    targets = {s for s in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[k])
               if not ((p := b.piece_at(s)) and p.color == us)}
    best = 99
    for n in b.pieces(chess.KNIGHT, us):
        seen = {n}; front = {n}; d = 0
        while front and d < 6:
            d += 1
            nxt = set()
            for s in front:
                for t in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[s]):
                    if t not in seen:
                        seen.add(t); nxt.add(t)
            if nxt & targets:
                best = min(best, d); break
            front = nxt
    return 0 if best == 99 else best


def knight_mate_now(b):
    for m in b.legal_moves:
        pt = b.piece_type_at(m.from_square)
        if (pt == chess.KNIGHT or m.promotion == chess.KNIGHT) and b.gives_check(m):
            b.push(m); ok = b.is_checkmate(); b.pop()
            if ok:
                return m
    return None


def analyse(line):
    g = json.loads(line)
    if g.get("ours") != 1:
        return None
    us = chess.WHITE if g["ours_white"] else chess.BLACK
    them = not us
    b = chess.Board(g["fen"])
    mv = g["moves"].split()
    events = []
    prev_open = None
    decided_ply = None
    for i, u in enumerate(mv):
        # position before move i
        if b.turn == us:
            if decided_ply is None and mat(b, us) - mat(b, them) >= 8:
                decided_ply = i
            o = open_sq(b, them)
            if decided_ply is not None and not o and prev_open:
                # closure: how did the defender's last move do it?
                last = b.peek()
                b.pop()
                was_check = b.is_check()
                cap = b.is_capture(last)
                king = b.piece_type_at(last.from_square) == chess.KING
                kd_before = knight_dist(b, us, them) if b.move_stack else 0
                b.push(last)
                cause = ("king step" if king else
                         ("check: capture" if cap else "check: block") if was_check else
                         ("free: capture" if cap else "free move"))
                km = knight_mate_now(b)
                kd = knight_dist(b, us, them)
                # what we played
                played = mv[i]
                smother_now = (km is not None and played == km.uci())
                # did our previous move give the check, and what was the knight
                # distance when we chose it (two plies back)?
                pre = None
                if was_check and len(b.move_stack) >= 2:
                    a = b.pop(); c = b.pop()
                    pre = knight_dist(b, us, them)
                    b.push(c); b.push(a)
                # outcome of the episode
                next_mv = mv[i + 1] if i + 1 < len(mv) else None
                events.append(dict(cause=cause, armed=km is not None, kd=kd, pre_kd=pre,
                                   smother_now=smother_now, units=len(b.pieces(chess.PAWN, them)) +
                                   sum(len(b.pieces(t, them)) for t in (2, 3, 4, 5)),
                                   knights=len(b.pieces(chess.KNIGHT, us)),
                                   end=g["smother"], since=(i - decided_ply) // 2))
            prev_open = len(o)
        b.push_uci(u)
    return dict(smother=g["smother"], events=events, decided=decided_ply is not None)


def main():
    lines = [l for f in sys.argv[1:] for l in open(f)]
    with Pool(4) as p:
        R = [r for r in p.map(analyse, lines, chunksize=20) if r]
    n = len(R)
    games_box = sum(1 for r in R if r["events"])
    print(f"won games {n}, decided {sum(r['decided'] for r in R)}, knight smothers "
          f"{sum(r['smother']=='classic' for r in R)} ({100*sum(r['smother']=='classic' for r in R)/n:.2f} per 100)")
    print(f"games with >= 1 box closure after +8: {games_box} ({100*games_box/n:.1f}%)")
    E = [e for r in R for e in r["events"]]
    print(f"closures {len(E)}; armed (knight mate in 1) {sum(e['armed'] for e in E)}; "
          f"armed and played {sum(e['smother_now'] for e in E)}")
    print("\nby cause: closures / armed / knight dist 1 / 2 / 3+ / no knight")
    by = collections.defaultdict(list)
    for e in E:
        by[e["cause"]].append(e)
    for c, L in sorted(by.items(), key=lambda x: -len(x[1])):
        kd = collections.Counter(min(e["kd"], 3) for e in L)
        print(f"  {c:15s} {len(L):5d}  armed {sum(e['armed'] for e in L):4d}  "
              f"kd1 {kd[1]:4d}  kd2 {kd[2]:4d}  kd3+ {kd[3]:4d}  none {kd[0]:4d}")
    U = [e for e in E if not e["armed"]]
    print(f"\nunarmed closures {len(U)}: knight dist "
          + ", ".join(f"{k}: {v}" for k, v in sorted(collections.Counter(min(e['kd'], 4) for e in U).items())))
    C = [e for e in U if e["cause"].startswith("check") and e["pre_kd"] is not None]
    print(f"unarmed closures we forced with a check: {len(C)}; our knight distance when we gave the check: "
          + ", ".join(f"{k}: {v}" for k, v in sorted(collections.Counter(min(e['pre_kd'], 4) for e in C).items())))
    print(f"defender units at unarmed closures: median {sorted(e['units'] for e in U)[len(U)//2] if U else '-'}; "
          f"closures with no knight of ours: {sum(e['knights']==0 for e in U)}")
    # per game: did the game have a closure where our knight was at distance 2?
    g2 = sum(1 for r in R if any((not e['armed']) and e['kd'] == 2 for e in r['events']))
    print(f"games with an unarmed closure, knight 2 moves from a check square: {g2} ({100*g2/n:.1f}%), "
          f"of which knight smother later: {sum(1 for r in R if r['smother']=='classic' and any((not e['armed']) and e['kd']==2 for e in r['events']))}")


if __name__ == "__main__":
    main()
