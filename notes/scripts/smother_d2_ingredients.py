"""D2 ingredients (GLM): at the first position where we are >= +T (T = 4, 8),
us to move: enemy king in a corner zone (files a,b,g,h on its back rank),
its pawn shield (pawns of theirs on the 3 squares in front of the king)
count, enemy non-pawn pieces, our knight, our queen. Knight-smother rate by
ingredient group; who removed shield pawns later."""
import json, sys, collections, chess
V = {1:1,2:3,3:3,4:5,5:9,6:0}
def mat(b, c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color == c)
def ingr(b, us):
    them = not us; k = b.king(them); f, r = chess.square_file(k), chess.square_rank(k)
    back = 7 if them == chess.BLACK else 0; step = -1 if them == chess.BLACK else 1
    corner = r == back and f in (0, 1, 6, 7)
    shield = sum(1 for df in (-1, 0, 1) if 0 <= f + df < 8 and 0 <= r + step < 8 and b.piece_at(chess.square(f + df, r + step)) == chess.Piece(chess.PAWN, them))
    pieces = sum(1 for p in b.piece_map().values() if p.color == them and p.piece_type not in (1, 6))
    return dict(corner=corner, shield=shield, pieces=min(pieces, 3), knight=bool(b.pieces(chess.KNIGHT, us)), queen=bool(b.pieces(chess.QUEEN, us)))
S = {4: collections.defaultdict(lambda: [0, 0]), 8: collections.defaultdict(lambda: [0, 0])}; N = 0; T = 0
for fn in sys.argv[1:]:
    for l in open(fn):
        g = json.loads(l)
        if g.get("ours") != 1: continue
        N += 1; us = g["ours_white"]; ok = g["smother"] == "classic"; T += ok
        b = chess.Board(g["fen"]); done = set()
        for u in g["moves"].split():
            b.push_uci(u)
            if b.turn != us: continue
            d = mat(b, us) - mat(b, not us)
            for t in (4, 8):
                if t not in done and d >= t:
                    done.add(t); x = ingr(b, us)
                    ready = x["corner"] and x["shield"] >= 2 and x["pieces"] >= 1 and x["knight"]
                    for key in [("all",), ("ready", ready), ("corner", x["corner"]), ("shield", x["shield"]), ("knight", x["knight"]), ("queen", x["queen"]), ("pieces", x["pieces"])]:
                        S[t][key][0] += 1; S[t][key][1] += ok
print(N, "games,", T, "knight smothers")
for t in (4, 8):
    print(f"-- first time >= +{t}:")
    for key, (n, k) in sorted(S[t].items(), key=lambda kv: str(kv[0])):
        print(f"   {str(key):22s} {n:5d} games ({100*n/N:5.1f}%)  knight smother {100*k/max(n,1):5.1f}%")
