import json, chess, sys, collections as C
V={1:1,2:3,3:3,4:5,5:9}
def mat(b,c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color==c and p.piece_type!=6)
def zone(k):
    f,r=chess.square_file(k),chess.square_rank(k); e=(f in(0,7))+(r in(0,7))
    return ("centre","edge","corner")[e]
def rows(files, window=40, horizon=10):
    for f in files:
        for l in open(f):
            g=json.loads(l)
            if g.get("ours")!=1: continue
            us=g["ours_white"]; them=not us
            b=chess.Board(g["fen"]); mv=g["moves"].split(); won=None
            n=len(mv); full=bool(g["smother"])
            for i,u in enumerate(mv):
                b.push_uci(u)
                if won is None and mat(b,us)-mat(b,them)>=5: won=i
                if won is None or b.turn!=us or b.is_game_over(): continue
                t=(i-won)//2
                if t>=window: break
                k=b.king(them); ring=chess.SquareSet(chess.BB_KING_ATTACKS[k])
                own=sum(1 for s in ring if (p:=b.piece_at(s)) and p.color==them)
                kn=b.pieces(chess.KNIGHT,us)
                kd=min([chess.square_distance(s,k) for s in kn] or [9])
                y=full and (n-1-i)<=2*horizon
                yield dict(dm=mat(b,them), zone=zone(k), holes=len(ring)-own, boxed=own,
                           knights=len(kn), kd=kd, queen=bool(b.pieces(chess.QUEEN,us)),
                           dpieces=len(b.pieces(chess.PAWN,them))+sum(len(b.pieces(t,them)) for t in (2,3,4,5)),
                           y=y, game=(f,g["game"]))
if __name__=="__main__":
    R=list(rows(sys.argv[1:]))
    base=sum(r["y"] for r in R)/len(R)
    print(len(R),"states; base rate (full smother within 10 of our moves):",f"{100*base:.2f}%")
    for key,fn in [("zone",lambda r:r["zone"]),("holes",lambda r:min(r["holes"],5)),
                   ("knights",lambda r:min(r["knights"],2)),("knight dist",lambda r:min(r["kd"],5)),
                   ("queen",lambda r:r["queen"]),("def material",lambda r:min(r["dm"]//5*5,30)),
                   ("def units",lambda r:min(r["dpieces"],10))]:
        c=C.Counter(); y=C.Counter()
        for r in R: v=fn(r); c[v]+=1; y[v]+=r["y"]
        print(f"{key:13s}", "  ".join(f"{v}:{100*y[v]/c[v]:.1f}%(n{c[v]})" for v in sorted(c)))
