import json, sys, collections as C
R=[json.loads(l) for f in sys.argv[1:] for l in open(f)]
print(len(R),"positions")
for k in sorted({r["k"] for r in R}):
    S=[r for r in R if r["k"]==k]; n=len(S)
    orc=[r for r in S if r["oracle"]]; no=len(orc)
    rp=sum(1 for r in S if r["real_proof"]); found=sum(1 for r in orc if r["real_proof"])
    same=sum(1 for r in S if r["same_move"])
    print(f" {k:2d} moves before mate: n {n:4d} | forced smother exists (oracle): {100*no/n:5.1f}% | engine proved it there: {100*found/max(no,1):5.1f}% of those | engine plays the human's move: {100*same/n:5.1f}%")
