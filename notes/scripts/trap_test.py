#!/usr/bin/env python3
"""Trap test on real human smothers (human_smother_test.py output + the
smother games). For positions K moves before a human smother where no forced
smother existed (oracle), compare the human attacker's move with
Smotherfish's move: after each, sample SAMPLES replies from Maia-3 at the
defender's rating and check (oracle) whether a forced smother now exists.
Also the engine's evaluation after each move (depth DEPTH), to see what a
trap move costs.
usage: trap_test.py ENGINE MAIA HST.jsonl OUT.jsonl SMOTHERS.jsonl.zst... [--n 300]
       [--samples 16] [--nodes 2000000] [--depth 12] [--workers 4] [--ks 3,5]"""
import argparse, io, json, random, subprocess, sys, collections as C
from multiprocessing import Pool
import zstandard

ap = argparse.ArgumentParser()
ap.add_argument("engine"); ap.add_argument("maia"); ap.add_argument("hst"); ap.add_argument("out")
ap.add_argument("files", nargs="+"); ap.add_argument("--n", type=int, default=300)
ap.add_argument("--samples", type=int, default=16); ap.add_argument("--nodes", type=int, default=2000000)
ap.add_argument("--depth", type=int, default=12); ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--ks", default="3,5"); ap.add_argument("--seed", type=int, default=3)
A = ap.parse_args()
E = {}


class Eng:
    def __init__(self, cmd, opts, name=""):
        self.name = name
        self.p = subprocess.Popen([cmd], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.send("uci")
        for k, v in opts.items():
            self.send(f"setoption name {k} value {v}")
        self.send("isready")
        while self.p.stdout.readline().strip() != "readyok":
            pass

    def send(self, s):
        self.p.stdin.write(s + "\n")

    def go(self, moves, cmd):
        self.last = "position startpos" + (" moves " + " ".join(moves) if moves else "") + " | " + cmd
        self.send("position startpos" + (" moves " + " ".join(moves) if moves else ""))
        self.send(cmd); lines = []
        while True:
            l = self.p.stdout.readline()
            if not l:
                raise RuntimeError(f"{self.name} died at: {self.last}")
            lines.append(l)
            if l.startswith("bestmove"):
                return lines


def init():
    for e in E.values():
        try:
            e.p.kill()
        except Exception:
            pass
    E["real"] = Eng(A.engine, {"Threads": 1, "Hash": 16}, "real")
    E["eval"] = Eng(A.engine, {"Threads": 1, "Hash": 16, "SmotherBrutal": "false", "SmotherMate": "false"}, "eval")
    E["oracle"] = Eng(A.engine, {"Threads": 1, "Hash": 16, "SmotherParallel": "false", "SmotherGoal": "Full",
                                 "SmotherMaxMoves": 12, "SmotherQuietMoves": 2, "SmotherNodes": A.nodes}, "oracle")
    E["maia"] = Eng(A.maia, {"MultiPV": 1}, "maia")


def proven(lines):
    return any("smother mate in" in l and "proven" in l for l in lines)


def score(lines):
    s = None
    for l in lines:
        t = l.split()
        if "score" in t:
            i = t.index("score")
            s = int(t[i + 2]) if t[i + 1] == "cp" else (100000 if int(t[i + 2]) > 0 else -100000)
    return s


def trap_rate(moves, def_elo):
    E["maia"].send(f"setoption name Elo value {def_elo}")
    E["maia"].send(f"setoption name OppoElo value {def_elo}")
    replies = C.Counter(E["maia"].go(moves, "go nodes 1")[-1].split()[1] for _ in range(A.samples))
    hit = 0
    for r, c in replies.items():
        if r in ("0000", "(none)"):  # our move already mated: no reply
            continue
        if proven(E["oracle"].go(moves + [r], "go depth 1")):
            hit += c
    return hit / A.samples, len(replies)


def run(item):
    try:
        return run1(item)
    except RuntimeError as ex:
        init()
        return {"site": item[0]["site"], "k": item[1], "error": str(ex)}


def run1(item):
    g, k = item
    mv = g["moves"].split(); p = len(mv) - (2 * k - 1); pre = mv[:p]
    attacker_white = p % 2 == 0
    def_elo = int(g["belo"] if attacker_white else g["welo"])
    E["real"].send("ucinewgame")
    E["real"].go(pre, "go movetime 200")
    eng = E["real"].go(pre, "go movetime 800")[-1].split()[1]
    out = {"site": g["site"], "k": k, "def_elo": def_elo, "human_move": mv[p], "engine_move": eng}
    for tag, m in (("human", mv[p]), ("engine", eng)):
        rate, nrep = trap_rate(pre + [m], def_elo)
        ev = score(E["eval"].go(pre + [m], f"go depth {A.depth}"))
        out[tag] = {"trap": rate, "replies": nrep, "eval_after": -ev if ev is not None else None}
    return out


if __name__ == "__main__":
    want = {}
    for l in open(A.hst):
        r = json.loads(l)
        if r["k"] in [int(x) for x in A.ks.split(",")] and not r["oracle"]:
            want.setdefault(r["site"], []).append(r["k"])
    G = {}
    for f in A.files:
        for l in io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(open(f, "rb"))):
            g = json.loads(l)
            if g["site"] in want:
                G[g["site"]] = g
    items = [(G[s], k) for s in want if s in G for k in want[s]]
    random.Random(A.seed).shuffle(items); items = items[:A.n]
    with Pool(A.workers, initializer=init) as pool, open(A.out, "w") as f:
        for i, r in enumerate(pool.imap_unordered(run, items), 1):
            f.write(json.dumps(r) + "\n"); f.flush()
            if i % 25 == 0:
                print(i, "of", len(items), file=sys.stderr, flush=True)
