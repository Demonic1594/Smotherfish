import json, random, subprocess, sys, numpy as np, torch, torch.nn as nn, chess, glob
sys.path.insert(0, __import__("os").path.dirname(__file__)); from classic_feats import feats, mat
from nn_data import window
ck = torch.load("mlp16.pt", weights_only=False); m = nn.Sequential(nn.Linear(167, 16), nn.ReLU(), nn.Linear(16, 1)); m.load_state_dict(ck["m"])
random.seed(1); L = [l for f in glob.glob("../diag/grid49/e1500_*.jsonl") for l in open(f)]; random.shuffle(L)
fens, py = [], []
for line in L:
    g = json.loads(line)
    if g.get("ours") != 1: continue
    us = g["ours_white"]; b = chess.Board(g["fen"])
    for i, u in enumerate(g["moves"].split()):
        b.push_uci(u)
        if b.turn == us and not b.is_game_over() and random.random() < 0.05 and mat(b, us) - mat(b, not us) >= 3:
            F = np.array(feats(b, us), np.float32); x = np.concatenate([(F - ck["mu"]) / ck["sd"], window(b, us)]).astype(np.float32)
            fens.append(b.fen()); py.append((F, m(torch.tensor(x)[None]).item()))
    if len(fens) >= 3000: break
inp = "".join(f"position fen {f}\nsmothernet\n" for f in fens) + "quit\n"
out = [l for l in subprocess.run(["/home/user/Smotherfish/src/stockfish"], input=inp, capture_output=True, text=True).stdout.splitlines() if l.startswith("smothernet")]
fd = np.zeros(17); dz = []
for (F, z), l in zip(py, out):
    v = l.split(); ef = np.array(list(map(float, v[1:18]))); fd += np.abs(ef - F) > 1e-4; dz.append(abs(float(v[19]) - z))
print(len(out), "positions; feature mismatches per feature:", fd.astype(int).tolist())
print("max |logit diff|", max(dz), "mean", np.mean(dz))
