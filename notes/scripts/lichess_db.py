#!/usr/bin/env python3
"""Process a Lichess monthly database stream into compact research data.

usage: curl -s https://database.lichess.org/standard/lichess_db_standard_rated_YYYY-MM.pgn.zst \
         | python3 -I lichess_db.py N_GAMES OUTDIR [--workers W]

Human games only (no BOT titles). Writes to OUTDIR:
  stats.json          resignation counts per own move by speed, rating band and
                      material deficit (1/3/3/5/9), and how games end once one
                      side was 8+ points down;
  smothers.jsonl.zst  every game that ends in a full or near ("all but one")
                      smothered mate: headers, UCI moves, kind;
  sample.jsonl.zst    1 in 50 games where one side was 8+ down, 1 in 500 others.
"""
import argparse, io, json, os, re, sys, zlib, collections as C
from multiprocessing import Pool
import chess, zstandard

V = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
HDR = re.compile(r'^\[(\w+) "(.*)"\]$')
MOVE = re.compile(r"(?:\d+\.(?:\.\.)?\s*)?([NBRQKa-hO][^\s{}()]*)")


def mat(b, c):
    return sum(V.get(p.piece_type, 0) for p in b.piece_map().values() if p.color == c)


def games(stream):
    """Yield (headers dict, movetext) from a PGN text stream."""
    h, mv = {}, []
    for line in stream:
        line = line.rstrip("\n")
        if line.startswith("["):
            if mv:
                yield h, " ".join(mv); h, mv = {}, []
            m = HDR.match(line)
            if m:
                h[m.group(1)] = m.group(2)
        elif line:
            mv.append(line)
    if mv:
        yield h, " ".join(mv)


def speed_of(tc):
    base, inc = map(int, tc.split("+")); est = base + 40 * inc
    return "bullet" if est < 180 else "blitz" if est < 480 else "rapid" if est < 1500 else "classical"


def band_of(elo):
    return "<1200" if elo < 1200 else "1200-1599" if elo < 1600 else "1600-1999" if elo < 2000 else "2000+"


def smother_kind(b):
    k = b.king(b.turn); chk = b.checkers(); opn = 0
    for sq in chess.SquareSet(chess.BB_KING_ATTACKS[k]):
        if sq in chk:
            continue
        p = b.piece_at(sq)
        if not p or p.color != b.turn:
            opn += 1
    if opn == 0:
        return "classic" if any(b.piece_type_at(s) == chess.KNIGHT for s in chk) else "full"
    return "near" if opn == 1 else None


def work(item):
    h, mt = item
    tc = h.get("TimeControl", "-")
    if tc == "-" or "+" not in tc or "BOT" in (h.get("WhiteTitle", ""), h.get("BlackTitle", "")):
        return None
    try:
        elo = (int(h["WhiteElo"]) + int(h["BlackElo"])) // 2
    except (KeyError, ValueError):
        return None
    sp, band = speed_of(tc), band_of(elo)
    mt = re.sub(r"\{[^}]*\}", " ", mt)
    b = chess.Board(); uci = []; at = C.Counter(); maxdef = 0
    for san in MOVE.findall(mt):
        if san in ("1-0", "0-1", "1/2-1/2", "*"):
            break
        try:
            m = b.push_san(san.rstrip("!?"))
        except ValueError:
            return None
        uci.append(m.uci())
        stm = b.turn; d = mat(b, not stm) - mat(b, stm)
        if d >= 3:
            at[(sp, band, min(d, 15) // 3 * 3)] += 1
        maxdef = max(maxdef, abs(d))
    res, term = h.get("Result"), h.get("Termination", "")
    stm = b.turn; d = mat(b, not stm) - mat(b, stm)
    lost = (res == "1-0" and stm == chess.BLACK) or (res == "0-1" and stm == chess.WHITE)
    kind = "mate" if b.is_checkmate() else ("resign" if term == "Normal" and lost else
           "draw" if res == "1/2-1/2" else "time/other")
    out = {"at": at, "res": C.Counter(), "end": C.Counter()}
    if kind == "resign" and d >= 3:
        out["res"][(sp, band, min(d, 15) // 3 * 3)] += 1
    if maxdef >= 8:
        out["end"][(sp, kind)] += 1
    rec = {"site": h.get("Site", ""), "elo": elo, "welo": h.get("WhiteElo"), "belo": h.get("BlackElo"),
           "tc": tc, "speed": sp, "result": res, "end": kind, "opening": h.get("ECO", ""),
           "moves": " ".join(uci)}
    if kind == "mate":
        sk = smother_kind(b)
        if sk:
            out["smother"] = dict(rec, smother=sk)
    key = zlib.crc32(h.get("Site", "").encode())
    if (maxdef >= 8 and key % 50 == 0) or key % 500 == 0:
        out["sample"] = dict(rec, maxdef=maxdef)
    out["n"] = 1
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int); ap.add_argument("out")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    A = ap.parse_args()
    os.makedirs(A.out, exist_ok=True)
    txt = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(sys.stdin.buffer),
                           encoding="utf-8", errors="replace")
    tot = {"at": C.Counter(), "res": C.Counter(), "end": C.Counter()}
    n = seen = nsm = nsa = 0
    cctx = zstandard.ZstdCompressor(level=10)
    with open(os.path.join(A.out, "smothers.jsonl.zst"), "wb") as fs, \
         open(os.path.join(A.out, "sample.jsonl.zst"), "wb") as fa, Pool(A.workers) as pool:
        ws, wa = cctx.stream_writer(fs), zstandard.ZstdCompressor(level=10).stream_writer(fa)
        def gen():
            global seen
            for g in games(txt):
                if seen >= A.n:
                    break
                seen += 1
                yield g
        for r in pool.imap_unordered(work, gen(), chunksize=200):
            if not r:
                continue
            n += 1
            for k in ("at", "res", "end"):
                tot[k].update(r[k])
            if "smother" in r:
                ws.write((json.dumps(r["smother"]) + "\n").encode()); nsm += 1
            if "sample" in r:
                wa.write((json.dumps(r["sample"]) + "\n").encode()); nsa += 1
            if n % 200000 == 0:
                print(n, "human games,", nsm, "smothers", file=sys.stderr, flush=True)
        ws.close(); wa.close()
    json.dump({"games_read": seen, "human_games": n, "smothers": nsm, "sampled": nsa,
               **{k: [[list(kk), v] for kk, v in tot[k].items()] for k in tot}},
              open(os.path.join(A.out, "stats.json"), "w"))
    print(f"{seen} games read, {n} human, {nsm} smothers, {nsa} sampled")
