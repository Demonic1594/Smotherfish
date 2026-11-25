"""Sacrifice census for Track B: positions where we are >= +3 (material) and
the enemy king is on an edge, from 1.6 games. Candidates: every move that
stock SF19 (MultiPV 40, depth 8) still scores >= +300 cp; "sacrifice" =
scores >= 150 cp below the best move. For each candidate, sample the real
opponent K times; after replies that fill a ring square or answer a check,
run our prover (Classic). Expected hit = share of samples into a proven
knight smother. usage: sac.py N K OPP(sf|maia) GAMES.jsonl..."""
import json, sys, random, subprocess, collections, chess
from multiprocessing import Pool
SF19 = "/tmp/claude-0/-home-user-Smotherfish/3b2e353f-b727-5683-8bd2-ac86828e52f0/scratchpad/sf19/src/stockfish"
MAIA = "/tmp/claude-0/-home-user/3b2e353f-b727-5683-8bd2-ac86828e52f0/scratchpad/maia3"
OURS = "/home/user/Smotherfish/src/stockfish"
V = {1:1,2:3,3:3,4:5,5:9,6:0}
def mat(b, c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color == c)
def holes(b, us):
    k = b.king(not us); return sum(1 for s in chess.SquareSet(chess.BB_KING_ATTACKS[k]) if not ((q := b.piece_at(s)) and q.color != us))
class Eng:
    def __init__(s, path, opts):
        s.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        for k, v in opts.items(): s.w(f"setoption name {k} value {v}")
        s.w("isready"); s.wait("readyok")
    def w(s, x): s.p.stdin.write(x + "\n")
    def wait(s, t):
        out = []
        while True:
            l = s.p.stdout.readline(); out.append(l)
            if l.startswith(t): return out
E = {}
def init(opp):
    E["eval"] = Eng(SF19, {"Threads": 1, "Hash": 32, "MultiPV": 40})
    E["opp"] = (Eng(MAIA, {"Elo": 1500, "OppoElo": 1500, "MultiPV": 1}) if opp == "maia"
                else Eng(SF19, {"Threads": 1, "Hash": 16, "UCI_LimitStrength": "true", "UCI_Elo": 1500}))
    E["kind"] = opp
    E["prove"] = Eng(OURS, {"Threads": 1, "Hash": 16, "SmotherParallel": "false", "SmotherGoal": "Full", "SmotherClassic": "true",
                            "SmotherMaxMoves": 12, "SmotherQuietMoves": 2, "SmotherNodes": 1000000})
def evals(fen):
    e = E["eval"]; e.w(f"position fen {fen}"); e.w("go depth 8"); sc = {}
    for l in e.wait("bestmove"):
        if " multipv " in l and " pv " in l and " depth 8 " in l:
            t = l.split(); mv = l.split(" pv ")[1].split()[0]
            sc[mv] = (100000 if int(t[t.index("mate") + 1]) > 0 else -100000) if "mate" in t else int(t[t.index("cp") + 1])
    return sc
def reply(fen):
    o = E["opp"]
    if E["kind"] == "maia": o.w(f"position fen {fen}"); o.w("go nodes 1")
    else: o.w("ucinewgame"); o.w(f"position fen {fen}"); o.w("go movetime 30")
    return o.wait("bestmove")[-1].split()[1]
def proven(fen):
    e = E["prove"]; e.w("ucinewgame"); e.w(f"position fen {fen}"); e.w("go depth 1")
    return any("smother mate in" in l and "proven" in l for l in e.wait("bestmove"))
def run(item):
    fen, K = item; b = chess.Board(fen); us = b.turn; sc = evals(fen)
    if not sc: return None
    best = max(sc.values()); res = {}; cache = {}
    for m, s in sc.items():
        if s < 300: continue
        b1 = b.copy(); b1.push_uci(m)
        if b1.is_game_over(): continue
        hits = 0
        for _ in range(K):
            r = reply(b1.fen())
            if r == "0000": continue
            b2 = b1.copy(); b2.push_uci(r)
            if b2.is_checkmate(): continue
            if holes(b2, us) < holes(b1, us) or b1.is_check():
                f2 = b2.fen()
                if f2 not in cache: cache[f2] = proven(f2)
                hits += cache[f2]
        res[m] = (hits / K, best - s)
    return fen, best, res
if __name__ == "__main__":
    N, K, opp = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    random.seed(17); P = []
    for f in sys.argv[4:]:
        for l in open(f):
            g = json.loads(l)
            if g.get("ours") != 1: continue
            us = g["ours_white"]; b = chess.Board(g["fen"]); mv = g["moves"].split()
            for i, u in enumerate(mv):
                b.push_uci(u)
                if b.turn != us or b.is_game_over() or mat(b, us) - mat(b, not us) < 3: continue
                k = b.king(not us)
                if (chess.square_file(k) in (0, 7) or chess.square_rank(k) in (0, 7)) and random.random() < 0.01: P.append(b.fen())
    random.shuffle(P); P = P[:N]
    with Pool(3, initializer=init, initargs=(opp,)) as pool: R = [r for r in pool.map(run, [(f, K) for f in P], chunksize=2) if r]
    n = len(R)
    def summ(name, pick):
        vals = [max([h for m, (h, c) in r.items() if pick(c)] or [0]) for _, _, r in R]
        print(f"{name:34s} mean best hit {sum(vals)/n:.4f}; positions with hit >= 0.1: {sum(v >= 0.1 for v in vals)}/{n}, >= 0.25: {sum(v >= 0.25 for v in vals)}/{n}")
    print(f"{n} positions (>= +3, king on an edge), opponent {opp}, {K} samples per move")
    summ("no sacrifice (within 150 cp of best)", lambda c: c < 150)
    summ("sacrifices (150+ cp below best)", lambda c: c >= 150)
    summ("any move still >= +3", lambda c: True)
    costs = [c for _, _, r in R for m, (h, c) in r.items() if h >= 0.25 and c >= 150]
    if costs: print("cost of the good sacrifices (cp below best): median", sorted(costs)[len(costs)//2], "max", max(costs))
    json.dump(R, open(f"diag3/sac_{opp}.json", "w"))
