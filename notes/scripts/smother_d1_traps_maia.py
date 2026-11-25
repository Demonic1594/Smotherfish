"""D1 trap census (GLM): in our won positions (>= +8, enemy king on an edge,
1-2 open ring squares, us to move), for each candidate move that keeps the
position won (stock SF19 MultiPV 8, score >= +6), sample the real opponent
(stock SF19, UCI_Elo 1500) K times; after every sampled reply that fills a
ring square, run our prover (Classic). Expected hit = share of samples that
lead to a proven knight smother. Compare best candidate with the move we
actually played."""
import json, sys, random, subprocess, collections, chess
from multiprocessing import Pool
SF19 = "/tmp/claude-0/-home-user-Smotherfish/3b2e353f-b727-5683-8bd2-ac86828e52f0/scratchpad/sf19/src/stockfish"
OURS = "/home/user/Smotherfish/src/stockfish"
V = {1:1,2:3,3:3,4:5,5:9,6:0}
def mat(b, c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color == c)
def holes(b, us):
    k = b.king(not us); return sum(1 for s in chess.SquareSet(chess.BB_KING_ATTACKS[k]) if not ((q := b.piece_at(s)) and q.color != us))
class Eng:
    def __init__(s, path, opts):
        s.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        for k, v in opts.items(): s.w(f"setoption name {k} value {v}")
        s.w("isready"); s.wait("readyok")
    def w(s, x): s.p.stdin.write(x + "\n")
    def wait(s, t):
        out = []
        while True:
            l = s.p.stdout.readline(); out.append(l)
            if l.startswith(t): return out
E = {}
def init():
    E["eval"] = Eng(SF19, {"Threads": 1, "Hash": 32, "MultiPV": 8})
    E["opp"] = Eng("/tmp/claude-0/-home-user/3b2e353f-b727-5683-8bd2-ac86828e52f0/scratchpad/maia3", {"Elo": 1500, "OppoElo": 1500, "MultiPV": 1})
    E["prove"] = Eng(OURS, {"Threads": 1, "Hash": 16, "SmotherParallel": "false", "SmotherGoal": "Full", "SmotherClassic": "true",
                            "SmotherMaxMoves": 12, "SmotherQuietMoves": 2, "SmotherNodes": 1000000})
def candidates(fen):
    e = E["eval"]; e.w(f"position fen {fen}"); e.w("go depth 10"); best = {}
    for l in e.wait("bestmove"):
        if " multipv " in l and " pv " in l:
            t = l.split(); mv = l.split(" pv ")[1].split()[0]
            if "mate" in t: sc = 100000 if int(t[t.index("mate") + 1]) > 0 else -100000
            else: sc = int(t[t.index("cp") + 1])
            best[mv] = sc
    return [m for m, s in best.items() if s >= 600]
def proven(fen):
    e = E["prove"]; e.w("ucinewgame"); e.w(f"position fen {fen}"); e.w("go depth 1")
    return any("smother mate in" in l and "proven" in l for l in e.wait("bestmove"))
def run(item):
    fen, played, K = item; b = chess.Board(fen); us = b.turn; h0 = holes(b, us)
    res = {}; cache = {}
    for m in set(candidates(fen)) | {played}:
        b1 = b.copy(); b1.push_uci(m)
        if b1.is_game_over(): continue
        hits = 0
        for _ in range(K):
            o = E["opp"]; o.w(f"position fen {b1.fen()}"); o.w("go nodes 1")
            r = o.wait("bestmove")[-1].split()[1]
            b2 = b1.copy(); b2.push_uci(r)
            if b2.is_checkmate(): continue
            if holes(b2, us) < holes(b1, us) or b2.is_check():
                f2 = b2.fen()
                if f2 not in cache: cache[f2] = proven(f2)
                hits += cache[f2]
        res[m] = hits / K
    return fen, played, res
if __name__ == "__main__":
    random.seed(int(__import__("os").environ.get("SEED", "9"))); P = []
    for f in sys.argv[3:]:
        for l in open(f):
            g = json.loads(l)
            if g.get("ours") != 1: continue
            us = g["ours_white"]; b = chess.Board(g["fen"]); mv = g["moves"].split()
            for i in range(len(mv) - 1):
                b.push_uci(mv[i])
                if b.turn != us or b.is_game_over() or mat(b, us) - mat(b, not us) < 8: continue
                k = b.king(not us)
                if 1 <= holes(b, us) <= 2 and (chess.square_file(k) in (0, 7) or chess.square_rank(k) in (0, 7)) and random.random() < 0.02:
                    P.append((b.fen(), mv[i + 1], g["smother"] == "classic"))
    random.shuffle(P); P = P[:int(sys.argv[1])]; K = int(sys.argv[2])
    with Pool(3, initializer=init) as pool: R = pool.map(run, [(f, p, K) for f, p, _ in P], chunksize=2)
    n = len(R); best = [max(r.values()) if r else 0 for _, _, r in R]; pl = [r.get(p, 0) for _, p, r in R]
    for t in (0.1, 0.25, 0.5):
        print(f"best candidate expected hit >= {t}: {sum(x >= t for x in best)}/{n} = {100*sum(x>=t for x in best)/n:.1f}%;  move we played >= {t}: {100*sum(x>=t for x in pl)/n:.1f}%")
    print(f"mean expected hit: best candidate {sum(best)/n:.3f}, move played {sum(pl)/n:.3f}; candidates per position {sum(len(r) for _,_,r in R)/n:.1f}")
    json.dump(R, open("diag3/d1m.json", "w"))
