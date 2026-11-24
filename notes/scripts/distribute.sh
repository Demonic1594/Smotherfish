#!/usr/bin/env bash
# Spread one experiment over our account and every helper fork (default for
# all tests: faster results). Each target gets the plan with "shard": [i, n]
# (i a list for an account with a larger share).
#
# usage: notes/scripts/distribute.sh PLAN.json [SRC_REF]
#   PLAN.json  experiment plan (notes/exp/plan.json format, "exp" = name)
#   SRC_REF    branch/commit whose src/ and notes/scripts/ are tested
#              (default: current branch)
#
# Branches are built on each fork's own default-branch version (the fork's
# token cannot push workflow changes), with src/ and notes/scripts/ from
# SRC_REF and the plan. Helper forks pick them up on their poll (about
# hourly, or "Run workflow" on Actions > Helper poll); our shard starts on
# push.
set -euo pipefail
plan=$1; src=${2:-$(git rev-parse --abbrev-ref HEAD)}
# id:base:weight (base = the version the fork is on; update after a "Sync
# fork"; weight = shares of the experiment, 20 jobs at once per share)
targets=(
  "8e9ce5:33bbe361:1"
  "acf111:33bbe361:1"
  "7a213a:33bbe361:1"
  "0f17ee:33bbe361:1"
  "dc665d:33bbe361:1"   # no working schedule: Run workflow by hand
  "d32e35:33bbe361:2"   # enterprise account: 42 jobs at once on Nov 24
                        # (limit 360, ramping up until ~Nov 29); its poll
                        # can be dispatched from the session
  "own:33bbe361:1"      # this repository
)
n=0; for t in "${targets[@]}"; do n=$((n + ${t##*:})); done
exp=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["exp"])' "$plan")
tmp=$(mktemp); cp "$plan" "$tmp"
cur=$(git rev-parse --abbrev-ref HEAD)
git fetch -q origin smotherfish
k=0
for t in "${targets[@]}"; do
  id=${t%%:*}; rest=${t#*:}; base=${rest%%:*}; w=${rest#*:}
  idx=$(python3 -c "print(list(range($k, $k + $w)))"); k=$((k + w))
  git checkout -q -B tmp-dist "$base"
  git checkout -q "$src" -- src notes/scripts
  mkdir -p notes/exp
  python3 - "$tmp" "$idx" "$n" "$w" > notes/exp/plan.json <<'PY'
import json, sys
p = json.load(open(sys.argv[1])); idx = json.loads(sys.argv[2])
p["shard"] = [idx if len(idx) > 1 else idx[0], int(sys.argv[3])]
p.setdefault("max_parallel", 20 * int(sys.argv[4]))
print(json.dumps(p, indent=1))
PY
  git add src notes/scripts notes/exp/plan.json
  git commit -q -m "$exp: shards $idx of $n" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AXQtdwTBPTjdbfRvbZua89"
  if [ "$id" = own ]; then ref=actions-exp/$exp; else ref=helper-exp/$id/$exp; fi
  git push -q -f origin tmp-dist:refs/heads/$ref
  echo "$ref: shards $idx of $n (base $base)"
done
git checkout -q "$cur"; git branch -D -q tmp-dist; rm -f "$tmp"
echo "merge when done: notes/scripts/merge_shards.py $exp OUTDIR <fork URLs>@actions-exp/$exp"
