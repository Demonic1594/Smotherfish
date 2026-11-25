"""Training rows for the knight-smother network: 17 hand features + a 5x5
window around the enemy king (mirrored so the king is nearest a1), 7 states
per square (empty/off-board, their pawn, their piece, our knight, our queen,
our other, their king-centre unused). Label: knight smother within 10 of
our moves. usage: nn_data.py OUT.npz GAMES.jsonl..."""
import json, sys, numpy as np, chess
from multiprocessing import Pool
sys.path.insert(0, __import__("os").path.dirname(__file__))
from classic_feats import feats, mat
def window(b, us):
    them = not us; k = b.king(them); kf, kr = chess.square_file(k), chess.square_rank(k)
    fx = -1 if kf > 3 else 1; ry = -1 if kr > 3 else 1   # mirror toward a1
    w = np.zeros((25, 6), np.uint8)
    for i in range(5):
        for j in range(5):
            f, r = kf + fx * (i - 2), kr + ry * (j - 2); idx = i * 5 + j
            if not (0 <= f < 8 and 0 <= r < 8):
                w[idx, 0] = 1; continue
            p = b.piece_at(chess.square(f, r))
            if p is None: continue
            if p.color == them:
                if p.piece_type == chess.PAWN: w[idx, 1] = 1
                elif p.piece_type != chess.KING: w[idx, 2] = 1
            else:
                if p.piece_type == chess.KNIGHT: w[idx, 3] = 1
                elif p.piece_type == chess.QUEEN: w[idx, 4] = 1
                else: w[idx, 5] = 1
    return w.reshape(-1)
def game(line):
    g = json.loads(line)
    if g.get("ours") != 1: return []
    us = g["ours_white"]; b = chess.Board(g["fen"]); mv = g["moves"].split(); n = len(mv)
    cls = g["smother"] == "classic"; won = None; out = []
    for i, u in enumerate(mv):
        b.push_uci(u)
        if won is None and mat(b, us) - mat(b, not us) >= 5: won = i
        if won is None or b.turn != us or b.is_game_over(): continue
        out.append((np.array(feats(b, us), np.float32), window(b, us), float(cls and (n - 1 - i) <= 20), hash(g["fen"] + g["moves"][:40]) & 0xffff))
    return out
if __name__ == "__main__":
    L = [l for f in sys.argv[2:] for l in open(f) if l.strip()]
    F, W, Y, G = [], [], [], []
    with Pool(4) as p:
        for rows in p.imap_unordered(game, L, chunksize=20):
            for f, w, y, gi in rows: F.append(f); W.append(w); Y.append(y); G.append(gi)
    np.savez_compressed(sys.argv[1], F=np.array(F), W=np.array(W), Y=np.array(Y, np.float32), G=np.array(G))
    print(len(Y), "rows,", int(sum(Y)), "positives")
