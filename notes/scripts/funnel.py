"""Funnel diagnostic: replay games, track the defender king's box, our knights,
material, and what breaks near-complete boxes. usage: funnel.py GAMES.jsonl..."""
import json, sys, collections as C
import chess

V = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}

def mat(b, c):
    return sum(V[p.piece_type] for p in b.piece_map().values() if p.color == c and p.piece_type != chess.KING)

def box(b, them):
    k = b.king(them)
    n = [s for s in chess.SQUARES if chess.square_distance(s, k) == 1]
    own = sum(1 for s in n if (p := b.piece_at(s)) and p.color == them)
    return k, len(n), len(n) - own   # king sq, neighbours, missing blockers

def zone(k):
    f, r = chess.square_file(k), chess.square_rank(k)
    e = (f in (0, 7)) + (r in (0, 7))
    return "corner" if e == 2 else "edge" if e == 1 else "centre"

G = [json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip()]
G = [g for g in G if "result" in g]
cls = C.Counter(); stats = C.defaultdict(list); breaks = C.Counter(); brk_by = C.defaultdict(C.Counter)
endz = C.defaultdict(C.Counter); knight_end = C.defaultdict(C.Counter); promo = C.Counter()
lostN = C.Counter(); minmiss = C.defaultdict(C.Counter); tight_plies = C.defaultdict(list)
for g in G:
    us = chess.WHITE if g["ours_white"] else chess.BLACK; them = not us
    if g["ours"] == 1.0:
        k = "full" if g["smother"] else ("near" if g.get("open") == 1 else "plain")
    else:
        k = "draw" if g["ours"] == 0.5 else "loss"
    cls[k] += 1
    if g["ours"] != 1.0:
        continue
    b = chess.Board(g["fen"]); mv = g["moves"].split()
    won_at = None; prev = None; mm = 9; tight = 0; had_knight_in_win = False
    for i, u in enumerate(mv):
        m = chess.Move.from_uci(u)
        mover = b.turn
        cap = b.piece_at(m.to_square) if not b.is_en_passant(m) else chess.Piece(chess.PAWN, them)
        if mover == us and m.promotion:
            promo[(k, chess.piece_name(m.promotion))] += 1
        if mover == us and b.piece_type_at(m.from_square) == chess.KNIGHT and False:
            pass
        nk_before = len(b.pieces(chess.KNIGHT, us))
        b.push(m)
        if won_at is None and mat(b, us) - mat(b, them) >= 5:
            won_at = i
        if won_at is None:
            continue
        if len(b.pieces(chess.KNIGHT, us)) > 0:
            had_knight_in_win = True
        if len(b.pieces(chess.KNIGHT, us)) < nk_before:
            lostN[(k, "captured" if mover == them else "self")] += 1
        ks, nn, miss = box(b, them)
        z = zone(ks)
        mm = min(mm, miss)
        cur = (z != "centre" and miss <= 1 and len(b.pieces(chess.KNIGHT, us)) > 0)
        if cur:
            tight += 1
        # what ended a tight box (missing <= 1, corner/edge, we have a knight)
        if prev and not cur and not b.is_checkmate():
            if len(b.pieces(chess.KNIGHT, us)) == 0:
                why = "our knight gone"
            elif zone(ks) == "centre" or (prev_k != ks):
                why = "king moved"
            elif mover == us and cap is not None and cap.color == them:
                why = "we captured a box piece"
            elif mover == them and b.piece_at(m.to_square) and b.piece_type_at(m.to_square) == chess.PAWN:
                why = "defender pawn move"
            elif mover == them:
                why = "defender piece left"
            else:
                why = "other (our move)"
            breaks[why] += 1; brk_by[k][why] += 1
        prev = cur; prev_k = ks
    if won_at is not None:
        stats[k].append((len(mv) - won_at, len(b.pieces(chess.KNIGHT, us)), mat(b, them), len(b.piece_map()) ))
        endz[k][zone(b.king(them))] += 1
        knight_end[k]["knight at end" if b.pieces(chess.KNIGHT, us) else "no knight at end"] += 1
        knight_end[k]["had knight in win phase" if had_knight_in_win else "never knight in win phase"] += 1
        minmiss[k][min(mm, 3)] += 1
        tight_plies[k].append(tight)
n = len(G)
print(f"{n} games:", dict(cls))
med = lambda v: sorted(v)[len(v)//2] if v else None
for k in ("full", "near", "plain"):
    s = stats[k]; w = len(s)
    if not w: continue
    print(f"\n== {k} ({w}) ==")
    print("  plies from decisive (+5 material) to end: median", med([x[0] for x in s]),
          "| defender material at end: median", med([x[2] for x in s]))
    print("  king zone at end:", dict(endz[k]))
    print("  knights:", dict(knight_end[k]))
    print("  fewest missing blockers in win phase (3 = 3+):", dict(sorted(minmiss[k].items())))
    tp = tight_plies[k]
    print("  plies with a tight box (<=1 missing, corner/edge, knight): median", med(tp),
          "| games with none:", sum(t == 0 for t in tp))
    print("  tight box ended by:", dict(brk_by[k].most_common()))
print("\npromotions (class, piece):", dict(promo))
print("our knight losses in win phase (class, how):", dict(lostN))
