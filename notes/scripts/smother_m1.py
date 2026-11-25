"""M1: for each knight smother in our games, classify the defender move that
filled the last ring square of the final king square."""
import json, sys, glob, collections, chess
V = {1:1,2:3,3:3,4:5,5:9,6:0}
def cls_game(g):
    us = g["ours_white"]; them = not us
    b = chess.Board(g["fen"]); mv = [chess.Move.from_uci(u) for u in g["moves"].split()]
    boards = []
    for m in mv: boards.append(b.copy()); b.push(m)
    k = b.king(them); ring = chess.SquareSet(chess.BB_KING_ATTACKS[k])
    # walk back: find last position (before a defender move) where ring of k was NOT full of their pieces
    def full(bb): return bb.king(them) == k and all((p := bb.piece_at(s)) and p.color == them for s in ring)
    n = len(mv)
    for i in range(n - 1, -1, -1):
        pre = boards[i]
        if pre.turn != them: continue
        post = pre.copy(); post.push(mv[i])
        if full(post) and not full(pre):
            m = mv[i]; dist = (n - 1 - i) // 2  # our moves after closure (incl. mate)
            if pre.piece_type_at(m.from_square) == chess.KING: kind = "king walked in"
            elif pre.is_check(): kind = "blocked a check" + (" (capture)" if pre.is_capture(m) else "")
            elif pre.is_capture(m) and m.to_square in ring: kind = "captured our piece on the ring"
            else:
                # was the moved piece attacked and insufficiently defended before?
                fs = m.from_square; pv = V[pre.piece_type_at(fs)]
                att = pre.attackers(us, fs); dfd = pre.attackers(them, fs)
                hang = att and (not dfd or min(V[pre.piece_type_at(a)] for a in att) < pv)
                # does the move defend another attacked piece of theirs?
                threat_before = sum(1 for s in chess.SquareSet(pre.occupied_co[them]) if pre.piece_type_at(s) != 6 and pre.attackers(us, s) and not pre.attackers(them, s))
                threat_after = sum(1 for s in chess.SquareSet(post.occupied_co[them]) if post.piece_type_at(s) != 6 and post.attackers(us, s) and not post.attackers(them, s))
                if hang: kind = "moved an attacked piece away"
                elif threat_after < threat_before: kind = "defended a hanging piece"
                elif pre.legal_moves.count() <= 3: kind = "few legal moves (zugzwang-like)"
                else: kind = "free choice"
            return kind, dist, pre.piece_type_at(m.from_square)
    return "closed before tracking", None, None
C = collections.Counter(); D = collections.defaultdict(list); P = collections.Counter()
seen = 0
for f in sys.argv[1:]:
    for l in open(f):
        g = json.loads(l)
        if g.get("smother") != "classic" or g.get("ours") != 1: continue
        seen += 1; k, d, pt = cls_game(g); C[k] += 1
        if d is not None: D[k].append(d); P[chess.piece_name(pt)] += 1
print(seen, "knight smothers")
for k, c in C.most_common():
    ds = sorted(D[k]); med = ds[len(ds)//2] if ds else None
    print(f"  {k:34s} {c:5d} {100*c/seen:5.1f}%  median our-moves to mate after closing: {med}")
print("piece that closed:", dict(P))
