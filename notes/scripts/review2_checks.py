import json, chess, sys, math, collections as C
V={1:1,2:3,3:3,4:5,5:9}
def mat(b,c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color==c and p.piece_type!=6)
def ring(b,them): return chess.SquareSet(chess.BB_KING_ATTACKS[b.king(them)])
def opn(b,them): return sum(1 for s in ring(b,them) if not ((p:=b.piece_at(s)) and p.color==them))
def zone(k):
    f,r=chess.square_file(k),chess.square_rank(k); return ("centre","edge","corner")[(f in(0,7))+(r in(0,7))]
def ready(b,us,them):
    q=b.pieces(chess.QUEEN,us); n=0
    for s in ring(b,them):
        p=b.piece_at(s)
        if p and p.color==us: continue
        if not any(s in b.attacks(x) for x in q): continue
        prot=[a for a in b.attackers(us,s) if b.piece_type_at(a)!=chess.QUEEN]
        if prot: n+=1
    return n
G=[json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip()]
G=[g for g in G if g.get("ours")==1]
H=C.Counter(); Y=C.Counter(); close=C.Counter(); entry=C.defaultdict(lambda:[0,0]); byopen=C.defaultdict(lambda:[0,0])
for g in G:
    us=g["ours_white"]; them=not us; b=chess.Board(g["fen"]); mv=g["moves"].split(); n=len(mv); won=None
    full=bool(g["smother"])
    byopen[g["fen"]][0]+=1; byopen[g["fen"]][1]+=full
    for i,u in enumerate(mv):
        if full and i==n-2:   # the defender's last move before our mate
            m=chess.Move.from_uci(u); inchk=b.is_check(); cap=b.is_capture(m)
            prev=chess.Move.from_uci(mv[i-1]) if i else None
            lands_ring = m.to_square in ring(b,them) or b.piece_type_at(m.from_square)==chess.KING
            why="answered check" if inchk else ("recapture" if cap and prev and prev.to_square==m.to_square else ("capture" if cap else "free move"))
            close[why]+=1
        b.push_uci(u)
        if won is None and mat(b,us)-mat(b,them)>=5:
            won=i; e=(min(opn(b,them),4), zone(b.king(them)), bool(b.pieces(chess.QUEEN,us)))
            entry[e][0]+=1; entry[e][1]+=full
        if won is None or b.turn!=us or b.is_game_over(): continue
        if (i-won)//2>=40: continue
        o=opn(b,them)
        if o>3: continue
        r=min(ready(b,us,them),2); y=full and (n-1-i)<=20
        H[(o,r)]+=1; Y[(o,r)]+=y
print(len(G),"won games;", sum(bool(g["smother"]) for g in G),"full")
print("\nIdea 1 check: full within 10 moves by (open ring squares, 'ready' squares)")
for o in range(4):
    print(f"  open {o}: "+"  ".join(f"ready {r}{'+' if r==2 else ''}: {100*Y[(o,r)]/H[(o,r)]:.1f}% (n{H[(o,r)]})" for r in range(3) if H[(o,r)]))
print("\nIdea 4 check: defender's last move before our full smother:", dict(close))
print("\nLong-shot check: state at the decisive point -> full rate")
for k,(n,f) in sorted(entry.items(), key=lambda x:-x[1][0])[:12]:
    print(f"  open {k[0]}{'+' if k[0]==4 else ''} {k[1]:6s} queen {str(k[2]):5s}: n {n:5d} full {100*f/n:5.1f}%")
# per-opening dispersion
rates=[f/n for n,f in byopen.values() if n>=8]; N=[n for n,f in byopen.values() if n>=8]
p=sum(f for n,f in byopen.values())/sum(n for n,f in byopen.values())
chi=sum((f-n*p)**2/(n*p*(1-p)) for n,f in byopen.values() if n>=8)
print(f"\nPer-opening full rate: {len(N)} openings with >=8 won games, overall {100*p:.1f}%, chi2 {chi:.0f} on {len(N)-1} df (1.0x = pure noise: {chi/(len(N)-1):.2f}x)")
