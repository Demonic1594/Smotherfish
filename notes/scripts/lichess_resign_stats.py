"""Human resignation behaviour from a Lichess database stream.
usage: curl -s https://database.lichess.org/standard/lichess_db_standard_rated_YYYY-MM.pgn.zst | python3 -I lichess_resign_stats.py N_GAMES OUT.json
Per move of the side that is behind in material (1/3/3/5/9), counts how often
it resigns right there, by deficit, rating band and speed."""
import sys, io, json, collections as C
import zstandard, chess.pgn
V={1:1,2:3,3:3,4:5,5:9}
def mat(b,c): return sum(V.get(p.piece_type,0) for p in b.piece_map().values() if p.color==c)
N=int(sys.argv[1])
txt=io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(sys.stdin.buffer), encoding="utf-8", errors="replace")
at=C.Counter(); res=C.Counter(); end=C.Counter(); n=0
while n<N:
    g=chess.pgn.read_game(txt)
    if g is None: break
    h=g.headers
    tc=h.get("TimeControl","-")
    if tc=="-" or "+" not in tc: continue
    base,inc=map(int,tc.split("+")); est=base+40*inc
    speed="bullet" if est<180 else "blitz" if est<480 else "rapid" if est<1500 else "classical"
    try: elo=(int(h["WhiteElo"])+int(h["BlackElo"]))//2
    except: continue
    band="<1200" if elo<1200 else "1200-1599" if elo<1600 else "1600-1999" if elo<2000 else "2000+"
    if "BOT" in (h.get("WhiteTitle",""),h.get("BlackTitle","")): continue
    n+=1
    b=g.board(); maxdef=0; result=h.get("Result"); term=h.get("Termination","")
    moves=list(g.mainline_moves())
    for m in moves:
        b.push(m)
        stm=b.turn; d=mat(b,not stm)-mat(b,stm)   # side to move is behind by d
        if d>=3:
            key=(speed,band,min(d,15)//3*3)
            at[key]+=1
        maxdef=max(maxdef,d)
    # the game ended with the side to move at the end: resignation if Normal, no mate, and it lost
    stm=b.turn; d=mat(b,not stm)-mat(b,stm)
    lost = (result=="1-0" and stm==chess.BLACK) or (result=="0-1" and stm==chess.WHITE)
    kind = "mate" if b.is_checkmate() else ("resign" if term=="Normal" and lost else term or "?")
    if kind=="resign" and d>=3: res[(speed,band,min(d,15)//3*3)]+=1
    if maxdef>=8: end[(speed,kind if kind in("mate","resign") else "time/other" if result!="1/2-1/2" else "draw")]+=1
json.dump({"games":n,"at":[[list(k),v] for k,v in at.items()],"res":[[list(k),v] for k,v in res.items()],"end":[[list(k),v] for k,v in end.items()]},open(sys.argv[2],"w"))
print(n,"games")
