import numpy as np, torch, torch.nn as nn, sys, time
torch.set_num_threads(4); torch.manual_seed(0)
def auc(y, p):
    r = np.empty(len(p)); r[np.argsort(p, kind='stable')] = np.arange(1, len(p) + 1)
    n1 = y.sum(); n0 = len(y) - n1; return (r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
d = np.load(sys.argv[1]); F, W, Y, G = d["F"], d["W"].astype(np.float32), d["Y"], d["G"]
mu, sd = F.mean(0), F.std(0) + 1e-6
X = np.concatenate([(F - mu) / sd, W], 1).astype(np.float32)
te = (G % 5) == 0; tr = ~te
Xtr, Ytr, Xte = torch.tensor(X[tr]), torch.tensor(Y[tr]), torch.tensor(X[te])
for H, E in [(int(a.split(":")[0]), int(a.split(":")[1])) for a in sys.argv[2:]]:
    m = nn.Sequential(nn.Linear(X.shape[1], H), nn.ReLU(), nn.Linear(H, 1))
    opt = torch.optim.Adam(m.parameters(), 3e-3); sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, E)
    lf = nn.BCEWithLogitsLoss(); best = 0
    for ep in range(E):
        perm = torch.randperm(len(Ytr))
        for i in range(0, len(perm), 2048):
            idx = perm[i:i+2048]; opt.zero_grad(); lf(m(Xtr[idx]).squeeze(1), Ytr[idx]).backward(); opt.step()
        sch.step()
        with torch.no_grad(): p = m(Xte).squeeze(1).numpy()
        a = auc(Y[te], p)
        if ep % 5 == 4 or ep == E - 1: print(f"H={H} ep{ep} auc={a:.4f}", flush=True)
    torch.save({"m": m.state_dict(), "mu": mu, "sd": sd}, f"mlp{H}.pt"); np.save(f"pte{H}.npy", p)
