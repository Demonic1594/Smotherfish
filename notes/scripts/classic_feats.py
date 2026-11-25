import json, chess, sys, glob, numpy as np
from multiprocessing import Pool
V={1:1,2:3,3:3,4:5,5:9}
def mat(b,c): return sum(V[p.piece_type] for p in b.piece_map().values() if p.color==c and p.piece_type!=6)
NAMES=["corner","edge","h0","h1","h2","c_h0","c_h1","kd1","kd2","c_h1_kd1","c_h0_kd1","decoy","queen","stuck","units","exits","knights"]
def feats(b, us):
    them=not us; k=b.king(them); ring=chess.SquareSet(chess.BB_KING_ATTACKS[k])
    hl=[s for s in ring if not ((p:=b.piece_at(s)) and p.color==them)]; h=len(hl)
    f,r=chess.square_file(k),chess.square_rank(k); e=(f in(0,7))+(r in(0,7)); corner=e==2; edge=e==1
    pg=chess.SquareSet()
    for s in b.pieces(chess.PAWN,them): pg|=b.attacks(s)
    chk=[s for s in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[k]) if not ((p:=b.piece_at(s)) and p.color==us) and s not in pg]
    kd=9
    for s in b.pieces(chess.KNIGHT,us):
        one=chess.SquareSet(chess.BB_KNIGHT_ATTACKS[s])
        if any(c in one for c in chk): kd=1; break
        if any(any(c in chess.SquareSet(chess.BB_KNIGHT_ATTACKS[t]) for c in chk) for t in one): kd=min(kd,2)
    decoy=0
    if h==1 and corner:
        s=hl[0]; att=b.attackers(them,s); oa=b.attackers(us,s)
        decoy=int(any(b.piece_type_at(a)!=chess.KING for a in att) and any(b.piece_type_at(a) in (chess.QUEEN,chess.ROOK) for a in oa) and any(b.piece_type_at(a)!=chess.QUEEN for a in oa))
    stuck=int(all(b.is_attacked_by(us,s) or ((p:=b.piece_at(s)) and p.color==them) for s in ring))
    ours_att=chess.SquareSet()
    for s in chess.SquareSet(b.occupied_co[us]): ours_att|=b.attacks(s)
    ex=0
    for s in ring:
        p=b.piece_at(s)
        if p and p.color==them and p.piece_type!=chess.KING:
            for t in b.attacks(s):
                if t not in ring and t!=k and not (b.piece_at(t) and b.piece_at(t).color==them) and t not in ours_att: ex+=1
    units=len([p for p in b.piece_map().values() if p.color==them and p.piece_type!=6])
    return [corner,edge,h==0,h==1,h==2,corner and h==0,corner and h==1,kd==1,kd==2,corner and h==1 and kd==1,corner and h==0 and kd==1,decoy,
            bool(b.pieces(chess.QUEEN,us)),stuck,min(units,8)/8,min(ex,6)/6,min(len(b.pieces(chess.KNIGHT,us)),2)/2]
def game(line):
    g=json.loads(line)
    if g.get("ours")!=1: return []
    us=g["ours_white"]; b=chess.Board(g["fen"]); mv=g["moves"].split(); n=len(mv); cls=g["smother"]=="classic"; won=None; out=[]
    for i,u in enumerate(mv):
        b.push_uci(u)
        if won is None and mat(b,us)-mat(b,not us)>=5: won=i
        if won is None or b.turn!=us or b.is_game_over() or (i%4 and not cls): continue
        out.append([float(x) for x in feats(b,us)]+[float(cls and (n-1-i)<=20), float(g["game"])])
    return out
if __name__=="__main__":
    L=[l for f in sys.argv[2:] for l in open(f) if l.strip()]
    with Pool(4) as p: R=[r for rr in p.imap_unordered(game,L,chunksize=20) for r in rr]
    np.save(sys.argv[1], np.array(R,dtype=np.float32)); print(len(R),"rows")
