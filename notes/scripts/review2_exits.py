import json, chess, sys, random, collections as C
V={1:1,2:3,3:3,4:5,5:9}
def mat(b,c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color==c and p.piece_type!=6)
def mate_in_one(b):
    for m in list(b.legal_moves):
        b.push(m); ok=b.is_checkmate(); b.pop()
        if ok: return True
    return False
G=[json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip()]
G=[g for g in G if g.get("ours")==1]
recs=[]  # (game, key, y)
for gi,g in enumerate(G):
    us=g["ours_white"]; them=not us; b=chess.Board(g["fen"]); mv=g["moves"].split(); n=len(mv); full=bool(g["smother"]); won=None
    for i,u in enumerate(mv):
        b.push_uci(u)
        if won is None and mat(b,us)-mat(b,them)>=5: won=i
        if won is None or b.turn!=us or b.is_game_over() or (i-won)//2>=40: continue
        k=b.king(them); ring=chess.SquareSet(chess.BB_KING_ATTACKS[k])
        opn=sum(1 for s in ring if not ((p:=b.piece_at(s)) and p.color==them))
        if opn>1: continue
        y=full and (n-1-i)<=20
        # ready squares
        rd=0
        for s in ring:
            p=b.piece_at(s)
            if p and p.color==us: continue
            if any(s in b.attacks(q) for q in b.pieces(chess.QUEEN,us)) and [a for a in b.attackers(us,s) if b.piece_type_at(a)!=chess.QUEEN]: rd+=1
        # safe exits: defender ring-piece moves off the ring, landing on a square we don't attack
        # (or defended at least as many times), and after which we have no mate in one
        bb=b.copy(stack=False); bb.turn=them; safe=0
        if not bb.is_check():
            for m in list(bb.legal_moves):
                if m.from_square in ring and m.from_square!=k and m.to_square not in ring:
                    to=m.to_square
                    if len(bb.attackers(us,to))>len(bb.attackers(them,to)): continue
                    bb.push(m); mi=mate_in_one(bb); bb.pop()
                    if not mi: safe+=1
        km=sum(1 for m in bb.legal_moves if m.from_square==k)
        key=(opn, "ready" if rd else "no ready", "king stuck" if km==0 else "king can move", "safe exits 0" if safe==0 else "safe exits 1-2" if safe<=2 else "safe exits 3+")
        recs.append((gi,key,y))
# game-clustered bootstrap
by=C.defaultdict(lambda: C.defaultdict(lambda:[0,0]))
for gi,k,y in recs: by[k][gi][0]+=1; by[k][gi][1]+=y
rng=random.Random(1)
def ci(d):
    games=list(d.values()); n=sum(a for a,b in games); y=sum(b for a,b in games)
    bs=[]
    for _ in range(400):
        s=[games[rng.randrange(len(games))] for _ in games]; N=sum(a for a,b in s); bs.append(sum(b for a,b in s)/N if N else 0)
    bs.sort(); return 100*y/n, 100*bs[10], 100*bs[389], n, len(games)
print("Boxes with <=1 open ring square: full smother within 10 moves (95% CI clustered by game)")
for k in sorted(by):
    r,lo,hi,n,ng=ci(by[k])
    if n>=60: print(f"  open {k[0]} | {k[1]:8s} | {k[2]:13s} | {k[3]:14s}: {r:5.1f}% [{lo:4.1f}-{hi:4.1f}]  n {n} positions, {ng} games")
# marginal: safe exits only
m=C.defaultdict(lambda: C.defaultdict(lambda:[0,0]))
for gi,k,y in recs: m[k[3]][gi][0]+=1; m[k[3]][gi][1]+=y
print("\nSafe exits alone:")
for k in sorted(m):
    r,lo,hi,n,ng=ci(m[k]); print(f"  {k:14s}: {r:5.1f}% [{lo:4.1f}-{hi:4.1f}]  n {n}, {ng} games")
