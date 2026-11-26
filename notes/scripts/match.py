#!/usr/bin/env python3
"""Minimal paired-game match runner (stand-in for fastchess, which we cannot fetch here).

usage: match.py OUT.jsonl OURS OPP ELO GAMES [--steer N] [--opt Name=Value ...]
        [--tc 5+0.05] [--conc 4] [--book openings.txt]

Each opening is played twice with colours swapped. Clocks are real: a side
whose move takes longer than its remaining time (+ 100 ms grace) loses.
Smothered mate = checkmate where every square next to the mated king is
held by its own pieces or off the board; "classic" if the checker is a knight.
Each won mate also records "open": how many squares next to the mated king
are neither its own pieces nor the checker's square (0 = smother, 1 = "all
but one", the SmotherPartial rule).

--ponder: our engine ponders on the opponent's time (go ponder, then
ponderhit or stop), as in a real game. Games then use two CPU cores each, so
the number of concurrent games is halved.
--opp-think SEC: the opponent's move is held back until SEC seconds have
passed, like a person thinking; that wait is not charged to its clock. With
--ponder it is time our engine can use. Maia ("go nodes 1") answers at once
without it.
"""
import argparse, faulthandler, json, os, random, subprocess, sys, threading, time
from multiprocessing import Pool, TimeoutError
import chess

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("ours"); ap.add_argument("opp")
ap.add_argument("elo", type=int); ap.add_argument("games", type=int)
ap.add_argument("--opt", action="append", default=[])
ap.add_argument("--tc", default="5+0.05"); ap.add_argument("--conc", type=int, default=4)
ap.add_argument("--book", default=os.path.join(os.path.dirname(__file__), "openings.txt"))
ap.add_argument("--seed", type=int, default=1)
# Custom opponent (e.g. Maia on lc0): its own UCI options, and a fixed "go"
# command instead of a clock (Maia plays like a human with "go nodes 1").
# With --opp-opt given, the UCI_Elo limit is not applied to the opponent.
ap.add_argument("--opp-opt", action="append", default=[])
ap.add_argument("--opp-go", default="")
ap.add_argument("--ponder", action="store_true")
ap.add_argument("--opp-think", type=float, default=0.0)
A = ap.parse_args()
BASE, INC = (float(x) for x in A.tc.split("+"))


HANG = float(os.environ.get("MATCH_HANG", 60))  # seconds of silence = hung engine


class Hang(Exception):
    pass


class Eng:
    def __init__(self, path, opts, log=None):
        self.path, self.opts, self.log = path, opts, log
        err = open(log, "a") if log else subprocess.DEVNULL
        self.p = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=err, text=True, bufsize=1)
        self.send("uci"); self.wait("uciok")
        for k, v in opts.items():
            self.send(f"setoption name {k} value {v}")
        self.ready()

    def readline(self):
        # Watchdog: kill the engine if it says nothing for HANG seconds.
        t = threading.Timer(HANG, self.p.kill)
        t.start()
        try:
            l = self.p.stdout.readline()
        finally:
            t.cancel()
        if not l:
            raise Hang(f"{os.path.basename(self.path)} stopped answering")
        return l

    def restart(self):
        try: self.p.kill()
        except Exception: pass
        self.__init__(self.path, self.opts, self.log)

    def send(self, s): self.p.stdin.write(s + "\n")
    def wait(self, tok):
        while True:
            l = self.readline()
            if l.startswith(tok): return l
    def ready(self): self.send("isready"); self.wait("readyok")

    def go(self, fen, moves, wt, bt, fixed=""):
        self.send(f"position fen {fen} moves {' '.join(moves)}" if moves else f"position fen {fen}")
        self.send(f"go {fixed}" if fixed else
                  f"go wtime {int(wt*1000)} btime {int(bt*1000)} winc {int(INC*1000)} binc {int(INC*1000)}")
        t0 = time.monotonic(); infos = []
        while True:
            l = self.readline()
            if l.startswith("info string"): infos.append(l.strip())
            elif l.startswith("bestmove"):
                self.last_bestmove = l
                return l.split()[1], time.monotonic() - t0, infos

    def go_ponder(self, fen, moves, wt, bt):
        # Start pondering on `moves` (which end with the expected reply).
        self.send(f"position fen {fen} moves {' '.join(moves)}")
        self.send(f"go ponder wtime {int(wt*1000)} btime {int(bt*1000)} "
                  f"winc {int(INC*1000)} binc {int(INC*1000)}")

    def ponderhit(self):
        # The opponent played the expected move: the search goes on as a
        # normal one, timed from now.
        self.send("ponderhit")
        t0 = time.monotonic(); infos = []
        while True:
            l = self.readline()
            if l.startswith("info string"): infos.append(l.strip())
            elif l.startswith("bestmove"):
                self.last_bestmove = l
                return l.split()[1], time.monotonic() - t0, infos, l

    def stop_ponder(self):
        # Wrong guess: stop and throw the pondering result away.
        self.send("stop")
        while True:
            if self.readline().startswith("bestmove"):
                return

    def quit(self):
        try: self.send("quit"); self.p.wait(2)
        except Exception: self.p.kill()


def smother_kind(b):
    """Called on a checkmated board (side to move is mated)."""
    # Matches the engine's AnyPiece style: every square next to the king holds
    # one of its own pieces, except the checking piece's own square.
    k = b.king(b.turn)
    checkers = b.checkers()
    for sq in chess.SquareSet(chess.BB_KING_ATTACKS[k]):
        if sq in checkers:
            continue
        pc = b.piece_at(sq)
        if not pc or pc.color != b.turn:
            return None
    if any(b.piece_type_at(s) == chess.KNIGHT for s in checkers):
        return "classic"
    return "any"


def open_squares(b):
    """Squares next to the mated king that are neither its own pieces nor the
    checker's square (0 = smother, 1 = 'all but one')."""
    k = b.king(b.turn)
    checkers = b.checkers()
    n = 0
    for sq in chess.SquareSet(chess.BB_KING_ATTACKS[k]):
        if sq in checkers:
            continue
        pc = b.piece_at(sq)
        if not pc or pc.color != b.turn:
            n += 1
    return n


ENGS = {}
CFG = {}


def debug_dumps():
    # MATCH_DEBUG=<seconds>: print every thread's stack to stderr at that
    # interval, so a stuck job shows where it is in the CI log.
    sec = int(os.environ.get("MATCH_DEBUG", "0") or 0)
    if sec > 0:
        faulthandler.dump_traceback_later(sec, repeat=True)


def worker_init(opts_ours, opts_opp):
    # Engines start lazily in play(): a failure there is reported as a result
    # instead of killing the worker (a Pool would respawn it forever).
    CFG["ours"], CFG["opp"] = opts_ours, opts_opp
    debug_dumps()


def ensure_engines():
    log = f"{A.out}.opp-{os.getpid()}.log" if A.opp_opt else None
    for name, path in (("ours", A.ours), ("opp", A.opp)):
        e = ENGS.get(name)
        if e is not None and e.p.poll() is None:
            continue
        for attempt in range(3):
            try:
                ENGS[name] = Eng(path, CFG[name], log if name == "opp" else None)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)


def drop_engines():
    for e in list(ENGS.values()):
        try:
            e.p.kill()
        except Exception:
            pass
    ENGS.clear()


def play(job):
    # Any engine failure (hang, crash, start-up error) is reported as a hang
    # record with the position, not scored; engines restart for the next game.
    PLAYED["moves"] = []
    try:
        ensure_engines()
        return play_game(job)
    except Exception as ex:
        drop_engines()
        gi, fen0, ours_white = job
        return {"game": gi, "fen": fen0, "ours_white": ours_white,
                "hang": f"{type(ex).__name__}: {ex}",
                "moves": " ".join(PLAYED.get("moves", []))}


PLAYED = {}
RESIGN = {}
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def material(b, c):
    return sum(VAL.get(p.piece_type, 0) for p in b.piece_map().values() if p.color == c)


# Trap prototype (HarnessTrap=P): in decided positions where the enemy king
# has at most one open square around it, play the move whose defender
# replies walk into a forced knight smother (within 2 of our moves, checks
# only) with the highest Maia-3 probability for the opponent's rating, if
# that is at least P and our engine says the move keeps us winning. Measures
# the ceiling of opponent-model steering; its thinking is not on our clock.
TRAP = {}


def _ks(b):
    if not b.is_checkmate():
        return False
    t = b.turn; K = b.king(t); c = list(b.checkers())
    return (len(c) == 1 and b.piece_type_at(c[0]) == chess.KNIGHT
            and all((p := b.piece_at(s)) and p.color == t for s in chess.SquareSet(chess.BB_KING_ATTACKS[K])))


def _forced(b, n):
    for m in list(b.legal_moves):
        if not b.gives_check(m):
            continue
        b.push(m)
        if b.is_checkmate():
            ok = _ks(b)
        elif n == 1:
            ok = False
        else:
            ok = True
            for r in list(b.legal_moves):
                b.push(r); ok = _forced(b, n - 1); b.pop()
                if not ok:
                    break
        b.pop()
        if ok:
            return True
    return False


def _maia(board):
    m = ENGS.get("maia")
    if m is None or m.poll() is not None:
        m = subprocess.Popen([os.path.expanduser("~/maia3env/bin/python"),
                              os.path.join(os.path.dirname(os.path.abspath(__file__)), "maia_policy.py")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, bufsize=1, env={**os.environ, "HF_HUB_OFFLINE": "1"})
        while not m.stdout.readline().startswith("ready"):
            pass
        ENGS["maia"] = m
    m.stdin.write(f"{A.elo} {board.fen()}\n"); m.stdin.flush()
    return json.loads(m.stdout.readline())


def _score_after(e, fen0, moves, mv):
    # Our engine's score for playing mv (searchmoves), side to move = us.
    e.send(f"position fen {fen0} moves {' '.join(moves)}" if moves else f"position fen {fen0}")
    e.send(f"go nodes {TRAP['nodes']} searchmoves {mv}")
    sc = None
    while True:
        l = e.readline()
        if l.startswith("info") and " score " in l:
            t = l.split(" score ")[1].split()
            sc = 100000 if (t[0] == "mate" and int(t[1]) > 0) else -100000 if t[0] == "mate" else int(t[1])
        elif l.startswith("bestmove"):
            return sc


def trap_move(b, ours, fen0, moves):
    us = b.turn; them = not us
    K = b.king(them)
    if sum(1 for s in chess.SquareSet(chess.BB_KING_ATTACKS[K]) if not ((p := b.piece_at(s)) and p.color == them)) > 1:
        return None
    if material(b, us) - material(b, them) < 5:
        return None
    best = None
    for m in list(b.legal_moves):
        b.push(m)
        hits = []
        for r in list(b.legal_moves):
            b.push(r); h = _forced(b, 2); b.pop()
            if h:
                hits.append(r.uci())
        if hits:
            pr = _maia(b); mass = sum(pr.get(h, 0) for h in hits)
            if best is None or mass > best[1]:
                best = (m.uci(), mass)
        b.pop()
    if best is None or best[1] < TRAP["p"]:
        return None
    sc = _score_after(ours, fen0, moves, best[0])
    return best if sc is not None and sc >= 400 else None


def play_game(job):
    gi, fen0, ours_white = job
    ours, opp = ENGS["ours"], ENGS["opp"]
    for e in (ours, opp):
        e.send("ucinewgame"); e.ready()
    b = chess.Board(fen0)
    moves, clock = [], {chess.WHITE: BASE, chess.BLACK: BASE}
    PLAYED["moves"] = moves
    steers = 0; steer_plies = []; result = None; reason = ""
    traps = []  # [ply, Maia probability] of each trap move the prototype played
    our_clock = []; proofs = []  # our clock after each of our moves; plies with a proven smother
    pondering = None  # the opponent move our engine is pondering on
    ponder_hits = ponder_total = 0
    resign_rng = random.Random(A.seed * 1000003 + gi)
    while result is None:
        stm = b.turn
        is_ours = (stm == chess.WHITE) == ours_white
        deficit = material(b, not stm) - material(b, stm) if RESIGN and not is_ours else 0
        if (not is_ours and RESIGN and deficit >= RESIGN["threshold"]
                and resign_rng.random() * 100 < (RESIGN["curve"][min(deficit, 15) // 3 - 1]
                                                 if "curve" in RESIGN else RESIGN["pct"])):
            result = "0-1" if stm == chess.WHITE else "1-0"; reason = "resign"; break
        e = ours if is_ours else opp
        fixed = "" if is_ours else A.opp_go
        tm = trap_move(b, ours, fen0, moves) if (is_ours and TRAP) else None
        if tm is not None:
            if pondering is not None:
                ours.stop_ponder(); pondering = None
            mv, dt, infos = tm[0], 0.0, []
            traps.append([len(moves), round(tm[1], 3)])
        elif is_ours and pondering is not None:
            ponder_total += 1
            if moves and moves[-1] == pondering:
                ponder_hits += 1
                mv, dt, infos, _ = ours.ponderhit()
            else:
                ours.stop_ponder()
                mv, dt, infos = e.go(fen0, moves, clock[chess.WHITE], clock[chess.BLACK], fixed)
            pondering = None
        else:
            t_start = time.monotonic()
            mv, dt, infos = e.go(fen0, moves, clock[chess.WHITE], clock[chess.BLACK], fixed)
            if not is_ours and A.opp_think > 0:
                # A thinking person: hold the move back; not charged to the clock.
                rest = A.opp_think - (time.monotonic() - t_start)
                if rest > 0:
                    time.sleep(rest)
        if fixed:
            dt = 0  # a fixed-node opponent plays without a clock
        if is_ours:
            for i in infos:
                if "smother steer" in i:
                    steers += 1; steer_plies.append(len(moves))
                if "smother mate in" in i and "proven" in i:
                    proofs.append(len(moves))
        clock[stm] -= dt
        if clock[stm] < -0.1:
            result = "0-1" if stm == chess.WHITE else "1-0"; reason = "time"; break
        clock[stm] += INC
        if is_ours:
            our_clock.append(round(clock[stm], 2))
        try:
            m = chess.Move.from_uci(mv)
            if m not in b.legal_moves: raise ValueError
        except Exception:
            result = "0-1" if stm == chess.WHITE else "1-0"; reason = f"illegal {mv}"; break
        b.push(m); moves.append(mv)
        if is_ours and A.ponder and not b.is_game_over():
            # Ponder on the reply our engine expects, if it gave a legal one.
            parts = getattr(ours, "last_bestmove", "").split()
            if len(parts) >= 4 and parts[2] == "ponder":
                try:
                    pm = chess.Move.from_uci(parts[3])
                except ValueError:
                    pm = None
                if pm is not None and pm in b.legal_moves:
                    ours.go_ponder(fen0, moves + [parts[3]], clock[chess.WHITE], clock[chess.BLACK])
                    pondering = parts[3]
        if b.is_checkmate():
            result = "1-0" if b.turn == chess.BLACK else "0-1"; reason = "mate"
        # Draw only when it has happened: a third occurrence, fifty moves.
        # can_claim_draw() also counts a repetition the side to move could
        # make next, which ended winning games the winner would not repeat.
        elif (b.is_stalemate() or b.is_insufficient_material()
              or b.is_repetition(3) or b.is_fifty_moves()):
            result = "1/2-1/2"; reason = "draw"
        elif len(moves) >= 400:
            result = "1/2-1/2"; reason = "cap"
    if pondering is not None:
        ours.stop_ponder()
    sm = smother_kind(b) if reason == "mate" else None
    nopen = open_squares(b) if reason == "mate" else None
    ours_score = {"1-0": 1.0, "0-1": 0.0}.get(result, 0.5)
    if not ours_white: ours_score = 1.0 - ours_score
    ours_mated_them = reason == "mate" and ours_score == 1.0
    return {"game": gi, "fen": fen0, "ours_white": ours_white, "result": result,
            "reason": reason, "ours": ours_score, "plies": len(moves),
            "smother": sm if ours_mated_them else None,
            "smothered_us": sm if (reason == "mate" and ours_score == 0.0) else None,
            "steers": steers, "steer_plies": steer_plies, "moves": " ".join(moves),
            "our_clock": our_clock, "proofs": proofs,
            "open": nopen if ours_mated_them else None,
            "ponder_hits": ponder_hits, "ponder_total": ponder_total, "traps": traps}


def parse_opts(lst):
    d = {}
    for s in lst:
        k, v = s.split("=", 1); d[k] = v
    return d


if __name__ == "__main__":
    book = [l.strip() for l in open(A.book) if l.strip()]
    rnd = random.Random(A.seed); rnd.shuffle(book)
    jobs = []
    for r in range(A.games // 2):
        fen = book[r % len(book)]
        jobs += [(2 * r, fen, True), (2 * r + 1, fen, False)]
    ours_opts = {"Threads": 1, "Hash": 16, **parse_opts(A.opt)}
    # Harness settings passed as pseudo-options (the workflow only forwards
    # --opt): HarnessResign=T,P makes the opponent resign before each of its
    # moves with P percent chance once it is T or more points of material
    # down (1/3/3/5/9), like a human who gives up a lost game.
    for k in [k for k in ours_opts if k.startswith("Harness")]:
        v = ours_opts.pop(k)
        if k == "HarnessTrap":
            TRAP.update(p=float(v), nodes=200000)
        elif k == "HarnessResign":
            if v.startswith("curve:"):
                # Percent per own move for deficits 3-5, 6-8, 9-11, 12-14,
                # 15+ (measured on Lichess, notes/scripts/lichess_merge.py;
                # blitz: curve:1.7,3.8,5.6,6.0,4.0).
                RESIGN.update(threshold=3, curve=[float(x) for x in v[6:].split(",")])
            else:
                t, pct = v.split(",")
                RESIGN.update(threshold=int(t), pct=float(pct))
    if A.ponder:
        ours_opts["Ponder"] = "true"
        # While pondering, our engine runs two threads (search and smother
        # prover) on the opponent's time, on top of the opponent's own: one
        # game per 4 cores. With two, ponder1 had the opponent lose 59 of
        # 600 games on time from CPU contention, which skewed the result.
        A.conc = max(1, A.conc // 4)
    opp_opts = ({"Threads": 1, **parse_opts(A.opp_opt)} if A.opp_opt else
                {"Threads": 1, "Hash": 16, "UCI_LimitStrength": "true", "UCI_Elo": A.elo})
    # (No debug_dumps() here: a faulthandler timer armed in the parent is
    # inherited by forked workers and deadlocks them when they re-arm it.)
    W = D = L = SM = SMC = ST = 0
    with Pool(A.conc, worker_init, (ours_opts, opp_opts)) as pool, open(A.out, "a") as f:
        H = 0
        # A worker that dies loses its game and Pool then waits forever (one
        # grid4 job sat 90 minutes like that). No result for STALL seconds,
        # far longer than any game, ends the run with the games so far.
        it = pool.imap_unordered(play, jobs)
        stall = float(os.environ.get("MATCH_STALL", 600))
        def results():
            while True:
                try:
                    yield it.next(timeout=stall)
                except StopIteration:
                    return
                except TimeoutError:
                    print(f"STALL: no game finished in {stall:.0f} s; stopping", flush=True)
                    pool.terminate()
                    return
        for n, g in enumerate(results(), 1):
            if "hang" in g:  # not scored; kept separately for debugging
                H += 1
                with open(A.out + ".hangs", "a") as hf:
                    hf.write(json.dumps(g) + "\n")
                print(f"HANG game {g['game']}: {g['hang']} after {len(g['moves'].split())} plies",
                      flush=True)
                continue
            f.write(json.dumps(g) + "\n"); f.flush()
            W += g["ours"] == 1; D += g["ours"] == 0.5; L += g["ours"] == 0
            SM += g["smother"] is not None; SMC += g["smother"] == "classic"; ST += g["steers"]
            if n % 20 == 0 or n == len(jobs):
                print(f"{n}/{len(jobs)} W{W} D{D} L{L} score {(W+D/2)/n:.3f} "
                      f"smothers {SM} (classic {SMC}) steers {ST}" + (f" hangs {H}" if H else ""),
                      flush=True)
