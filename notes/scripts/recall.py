#!/usr/bin/env python3
"""Opportunity recall: where are true smothers lost? (notes/plan_ideas.md, phase 0)

usage: recall.py ENGINE GAMES.jsonl OUT.jsonl [--games N] [--skip K] [--workers W]
                 [--depth D] [--win CP] [--nodes N] [--moves M] [--quiet Q] [--every E]
                 [--shard i/n]

For every game our engine won: replay it; at each of our moves, evaluate the
position with the engine at fixed depth (smother features off). From the
first move whose eval is at least --win centipawns (or a mate for us), run
the prover with a large node budget ("oracle", true smothers only) on our
positions, every --every-th one, until it finds a forced smother.

Each game gets one class (written per game to OUT.jsonl, summary on stdout):
  full      the game ended in a true smother;
  missed    a forced true smother existed (oracle) at ply p, but the engine
            did not claim a proof at p in the game (detection);
  unconverted  the engine claimed a proof at p, yet no true smother followed
            (conversion: a near proof, or the line was left);
  never     no forced true smother in any winning position checked (supply).
For full games, "avail" is the first ply the oracle finds one, so
delivered - avail shows how early chances appear.
"""
import argparse, json, subprocess, sys, time
from multiprocessing import Pool
import chess

ap = argparse.ArgumentParser()
ap.add_argument("engine"); ap.add_argument("games"); ap.add_argument("out")
ap.add_argument("--games", type=int, default=0, dest="ngames")
ap.add_argument("--skip", type=int, default=0)
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--depth", type=int, default=10)
ap.add_argument("--win", type=int, default=600)
ap.add_argument("--nodes", type=int, default=20000000)
ap.add_argument("--moves", type=int, default=12)
ap.add_argument("--quiet", type=int, default=2)
ap.add_argument("--every", type=int, default=1)
ap.add_argument("--shard", default="0/1", help="i/n: every n-th won game from i")
ap.add_argument("--strict", action="store_true",
                help="oracle counts only strict proofs (every defence smothered)")
A = ap.parse_args()

E = {}


class Eng:
    def __init__(self, opts):
        self.p = subprocess.Popen([A.engine], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, bufsize=1)
        for k, v in opts.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        while self.p.stdout.readline().strip() != "readyok":
            pass

    def send(self, s):
        self.p.stdin.write(s + "\n")

    def go(self, fen, moves, cmd):
        self.send(f"position fen {fen}" + (" moves " + " ".join(moves) if moves else ""))
        self.send(cmd)
        lines = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError("engine died")
            lines.append(l)
            if l.startswith("bestmove"):
                return lines


def init():
    off = {"SmotherMate": "false", "SmotherBrutal": "false", "SmotherBuild": "false"}
    E["eval"] = Eng({"Threads": 1, "Hash": 64, **off})
    # The prover's limits in a game when not yet crushing (defaults 8 / 1 / 5M).
    E["small"] = Eng({"Threads": 1, "Hash": 16, "SmotherParallel": "false",
                      "SmotherGoal": "Full", "SmotherMaxMoves": 8, "SmotherQuietMoves": 1,
                      "SmotherNodes": 5000000,
                      "SmotherStrict": "true" if A.strict else "false"})
    E["oracle"] = Eng({"Threads": 1, "Hash": 16, "SmotherParallel": "false",
                       "SmotherGoal": "Full", "SmotherMaxMoves": A.moves,
                       "SmotherQuietMoves": A.quiet, "SmotherNodes": A.nodes,
                       "SmotherStrict": "true" if A.strict else "false"})


def score_us(lines):
    """Last reported score, from the side to move's view: cp, or +-100000 for mates."""
    s = None
    for l in lines:
        t = l.split()
        if "score" in t:
            i = t.index("score")
            if t[i + 1] == "cp":
                s = int(t[i + 2])
            elif t[i + 1] == "mate":
                m = int(t[i + 2]); s = 100000 if m > 0 else -100000
    return s


def oracle(fen, moves, which="oracle"):
    for l in E[which].go(fen, moves, "go depth 1"):
        if "smother mate in" in l and "proven" in l:
            return int(l.split("mate in")[1].split()[0])
    return None


def run(g):
    t0 = time.time()
    b = chess.Board(g["fen"]); mv = g["moves"].split()
    ours = chess.WHITE if g["ours_white"] else chess.BLACK
    rec = {"game": g["game"], "plies": g["plies"], "smother": g["smother"], "open": g["open"],
           "proofs": g["proofs"]}
    first_win = None; checked = 0; avail = None; mate_in = None; seen = 0
    for i in range(len(mv)):
        if b.turn == ours and not b.is_game_over():
            s = score_us(E["eval"].go(g["fen"], mv[:i], f"go depth {A.depth}"))
            if s is not None and s >= A.win:
                if first_win is None:
                    first_win = i
                    rec["pieces_at_win"] = chess.popcount(b.occupied_co[not ours]) - 1
                seen += 1
                if (seen - 1) % A.every == 0:
                    checked += 1
                    n = oracle(g["fen"], mv[:i])
                    if n:
                        avail, mate_in = i, n
                        rec["eval_at_avail"] = s
                        # Would the prover's normal (not crushing) limits find it?
                        rec["small_finds"] = oracle(g["fen"], mv[:i], "small") is not None
                        break
        b.push_uci(mv[i])
    rec.update({"first_win": first_win, "checked": checked, "avail": avail, "mate_in": mate_in,
                "secs": round(time.time() - t0, 1)})
    if g["smother"] is not None:
        rec["cls"] = "full"
    elif avail is None:
        rec["cls"] = "never"
    elif avail in g["proofs"]:
        rec["cls"] = "unconverted"
    else:
        rec["cls"] = "missed"
    return rec


if __name__ == "__main__":
    G = [json.loads(l) for l in open(A.games)]
    G = [g for g in G if g.get("ours") == 1.0][A.skip:]
    si, sn = map(int, A.shard.split("/"))
    G = G[si::sn]
    if A.ngames:
        G = G[:A.ngames]
    C = {}
    with Pool(A.workers, initializer=init) as pool, open(A.out, "w") as f:
        for k, r in enumerate(pool.imap_unordered(run, G), 1):
            f.write(json.dumps(r) + "\n"); f.flush()
            C[r["cls"]] = C.get(r["cls"], 0) + 1
            if k % 10 == 0:
                print(k, C, file=sys.stderr, flush=True)
    n = sum(C.values())
    print(f"{n} won games")
    for c in ("full", "missed", "unconverted", "never"):
        print(f"  {c:12s} {C.get(c, 0):5d}  {100 * C.get(c, 0) / max(n, 1):5.1f}%")
