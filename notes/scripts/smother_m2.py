"""M2: in won (construction) positions, compare the defender reply our
engine's PV predicts (construction mode on) and a normal-eval PV predicts
with the reply actually played, and how often the predicted reply gives
up material."""
import json, sys, random, subprocess, chess, glob, collections
V = {1:1,2:3,3:3,4:5,5:9,6:0}
def mat(b, c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color == c)
class E:
    def __init__(s, opts):
        s.p = subprocess.Popen(["/home/user/Smotherfish/src/stockfish"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        for k, v in opts.items(): s.w(f"setoption name {k} value {v}")
        s.w("isready"); s.wait("readyok")
    def w(s, x): s.p.stdin.write(x + "\n")
    def wait(s, t):
        while True:
            l = s.p.stdout.readline()
            if l.startswith(t): return l
    def pv(s, fen, depth):
        s.w("ucinewgame"); s.w(f"position fen {fen}"); pv = None
        for _ in range(2):  # second search sees the first's score (construction decision)
            s.w(f"go depth {depth}")
            while True:
                l = s.p.stdout.readline()
                if " pv " in l: pv = l.split(" pv ")[1].split()
                if l.startswith("bestmove"): break
        return pv
random.seed(3); rows = []
for f in sys.argv[2:]:
    for l in open(f):
        g = json.loads(l)
        if g.get("ours") != 1: continue
        us = g["ours_white"]; b = chess.Board(g["fen"]); mv = g["moves"].split()
        for i in range(len(mv) - 1):
            b.push_uci(mv[i])
            if b.turn == us and mat(b, us) - mat(b, not us) >= 8 and random.random() < 0.02:
                rows.append((b.fen(), mv[i + 1], mv[i + 2] if i + 2 < len(mv) else None))
random.shuffle(rows); rows = rows[:int(sys.argv[1])]
common = {"Threads": 1, "Hash": 64}
cons = E({**common, "SmotherClassic": "true", "SmotherBuildKnightCheck": 16, "SmotherCrushQuiet": 3, "SmotherCrushMoves": 16})
norm = E({**common, "SmotherBrutal": "false"})
st = collections.Counter()
for fen, ours, reply in rows:
    if reply is None: continue
    b = chess.Board(fen); b.push_uci(ours); fen2 = b.fen()
    # PVs from the position after our actual move, defender to move: compare first move
    # but construction mode is decided for OUR side; so search from our position and use PV[1] only when PV[0]==ours
    for name, e in (("cons", cons), ("norm", norm)):
        pv = e.pv(fen, 12)
        if not pv or len(pv) < 2 or pv[0] != ours: st[name + "_skip"] += 1; continue
        st[name + "_n"] += 1; st[name + "_match"] += pv[1] == reply
        # material the defender gives up in the predicted line over the next 4 plies
        bb = chess.Board(fen); them = not bb.turn; m0 = mat(bb, them) - mat(bb, not them)
        for u in pv[:4]: bb.push_uci(u)
        st[name + "_drop2"] += (m0 - (mat(bb, them) - mat(bb, not them))) >= 2
    rb = chess.Board(fen2); m0 = mat(rb, rb.turn) - mat(rb, not rb.turn)
    for u in [reply] + ([] ):
        rb.push_uci(u)
print(dict(st))
for n in ("cons", "norm"):
    if st[n + "_n"]: print(f"{n}: PV reply matches real reply {st[n+'_match']}/{st[n+'_n']} = {100*st[n+'_match']/st[n+'_n']:.1f}%; predicted line has defender losing >=2 net in 4 plies: {100*st[n+'_drop2']/st[n+'_n']:.1f}%")
