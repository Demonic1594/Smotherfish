#!/bin/bash
# usage: match.sh NAME ENGINE ELO GAMES [extra fastchess -engine options for ours...]
S=/tmp/claude-0/-home-user-Smotherfish/e1fa86d3-745c-55ff-be7c-77b42a0872f8/scratchpad
name=$1; eng=$2; elo=$3; games=$4; shift 4
cd $S/m
$S/tools/fastchess/fastchess -engine cmd=$eng name=$name "$@" \
  -engine cmd=$S/sf_stock name=weak option.UCI_LimitStrength=true option.UCI_Elo=$elo \
  -each tc=${TC:-5+0.05} option.Threads=1 option.Hash=16 \
  -openings file=$S/tools/books/8moves_v3.pgn format=pgn order=random \
  -rounds $((games/2)) -games 2 -repeat -concurrency 4 -pgnout file=$name.pgn > $name.log 2>&1
$S/venv/bin/python -I $S/handoff/smother-stockfish/match/count.py $name.pgn
