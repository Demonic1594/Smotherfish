"""Merge lichess_db.py outputs (lichess-<month>-stats.json / -smothers.jsonl.zst
from the release lichess-data) in the current directory and print the tables."""
import json, glob, io, sys, collections as C
import zstandard
at=C.Counter(); res=C.Counter(); end=C.Counter(); tot=0
for f in sorted(glob.glob("lichess-*-stats.json")):
    d=json.load(open(f)); tot+=d["human_games"]
    for k,v in d["at"]: at[tuple(k)]+=v
    for k,v in d["res"]: res[tuple(k)]+=v
    for k,v in d["end"]: end[tuple(k)]+=v
print(f"{tot:,} human games")
print("\nResign chance per own move by material deficit:")
for sp in ("bullet","blitz","rapid","classical"):
    row=[]
    for dd in (3,6,9,12,15):
        a=sum(v for k,v in at.items() if k[0]==sp and k[2]==dd); r=sum(v for k,v in res.items() if k[0]==sp and k[2]==dd)
        row.append(f"{100*r/a:4.1f}%" if a else "  -  ")
    print(f"  {sp:9s} "+"  ".join(row))
print("\nBlitz, by rating:")
for b in ("<1200","1200-1599","1600-1999","2000+"):
    print(f"  {b:10s} "+"  ".join(f"{100*res.get(('blitz',b,dd),0)/at[('blitz',b,dd)]:4.1f}%" for dd in (3,6,9,12,15)))
print("\nGames where one side was 8+ down end by:")
for sp in ("bullet","blitz","rapid","classical"):
    t=sum(v for k,v in end.items() if k[0]==sp)
    if t: print(f"  {sp:9s} n {t:8,d}: "+"  ".join(f"{kind} {100*end.get((sp,kind),0)/t:4.1f}%" for kind in ("resign","mate","time/other","draw")))
# smothers
S=C.Counter(); bysp=C.Counter(); byband=C.Counter(); eco=C.Counter()
for f in sorted(glob.glob("lichess-*-smothers.jsonl.zst")):
    r=io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(open(f,"rb")))
    for l in r:
        g=json.loads(l); k=g["smother"]; S[k]+=1; bysp[(g["speed"],k)]+=1
        e=g["elo"]; b="<1200" if e<1200 else "1200-1599" if e<1600 else "1600-1999" if e<2000 else "2000+"
        byband[(b,k)]+=1
        if k!="near": eco[g["opening"]]+=1
print(f"\nSmothered mates: near {S['near']:,}  full {S['full']:,}  classic (knight) {S['classic']:,}  per 1000 games: {1000*S['near']/tot:.1f} / {1000*S['full']/tot:.2f} / {1000*S['classic']/tot:.2f}")
print("  by speed (full+classic / near):", {sp: (bysp[(sp,'full')]+bysp[(sp,'classic')], bysp[(sp,'near')]) for sp in ("bullet","blitz","rapid","classical")})
print("  by rating (full+classic / near):", {b: (byband[(b,'full')]+byband[(b,'classic')], byband[(b,'near')]) for b in ("<1200","1200-1599","1600-1999","2000+")})
print("  top openings (ECO) for full+classic:", eco.most_common(10))
