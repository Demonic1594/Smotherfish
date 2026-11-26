#!/usr/bin/env python3
"""Maia-3 move probabilities as a line server, for the match harness's trap
prototype (HarnessTrap in match.py). Run with the Python that has maia3
installed (the cached ~/maia3env in experiment jobs).

Input lines: "ELO FEN"; output lines: JSON {uci_move: probability} for the
side to move, as a human of that rating would play (Maia-3 5M, CPU).
"""
import json, sys, chess, torch
_argv = sys.argv; sys.argv = [sys.argv[0]]
from maia3.uci import parse_args, Maia3UCIEngine
from maia3.dataset import get_legal_moves_mask
from maia3.utils import mirror_move
sys.argv = _argv
torch.set_num_threads(1)
cfg = parse_args(["--model", "maia3-5m", "--device", "cpu", "--no-use-amp", "--elo", "1500"])
eng = Maia3UCIEngine(cfg); eng.ensure_model_loaded()


@torch.no_grad()
def probs(board, elo):
    eng.board = board.copy(stack=False); eng._reset_history()
    mask = get_legal_moves_mask(eng.board, eng.all_moves_dict)
    tok = eng._tokens_from_history(eng.history).unsqueeze(0)
    e = torch.tensor([elo])
    lg = eng.model(tok, e, e)[0][0].float().masked_fill(~mask, float("-inf"))
    p = torch.softmax(lg, -1); out = {}
    for i in torch.nonzero(mask).flatten().tolist():
        u = eng.idx_to_move[i]
        if board.turn == chess.BLACK:
            u = mirror_move(u)
        out[u] = round(p[i].item(), 5)
    return out


print("ready", flush=True)
for line in sys.stdin:
    elo, fen = line.strip().split(" ", 1)
    print(json.dumps(probs(chess.Board(fen), int(elo))), flush=True)
