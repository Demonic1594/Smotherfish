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
# Targets come from notes/scripts/volunteers.py: every public fork of the
# main repository (the helpers, see docs/HELPING.md) plus this repository,
# as id:base:jobs (jobs at once the account lends: a fork's HELPER_JOBS
# variable, default 20, or notes/volunteers.json "jobs"); each account's
# share of the test is proportional to it. ONLY=id,id,... limits the targets (refills).
mapfile -t targets < <(python3 notes/scripts/volunteers.py targets ${ONLY:+--only "$ONLY"})
[ ${#targets[@]} -gt 0 ] || { echo "no targets"; exit 1; }
n=0; for t in "${targets[@]}"; do n=$((n + ${t##*:})); done
exp=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["exp"])' "$plan")
# GitHub runs at most 256 matrix jobs per workflow run: refuse a split that
# gives any target more (an account with several shares takes them in one
# run). Split the plan into parts, or lower that account's jobs.
python3 - "$plan" "$n" "${targets[@]}" <<'PY' || exit 1
import json, sys
plan = json.load(open(sys.argv[1])); n = int(sys.argv[2])
jobs = sum(-(-int(r["games"]) // (int(r.get("chunk", plan.get("chunk", 100))) // 2 * 2)) for r in plan["runs"])
for t in sys.argv[3:]:
    w = int(t.rsplit(":", 1)[1]); mine = -(-jobs * w // n)
    if mine > 256:
        sys.exit(f"{t.split(':')[0]} would get about {mine} jobs (limit 256 per run): split the plan or lower its jobs")
PY
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
p.setdefault("max_parallel", int(sys.argv[4]))  # its jobs at once
print(json.dumps(p, indent=1))
PY
  git add src notes/scripts notes/exp/plan.json
  git commit -q -m "$exp: $w of $n job slots" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KPLjFVqA3Ah52n9TgVXHRo"
  if [ "$id" = own ]; then ref=actions-exp/$exp; else ref=helper-exp/$id/$exp; fi
  git push -q -f origin tmp-dist:refs/heads/$ref
  echo "$ref: $w of $n job slots (base $base)"
done
git checkout -q "$cur"; git branch -D -q tmp-dist; rm -f "$tmp"
echo "progress: notes/scripts/volunteers.py status $exp; merge: notes/scripts/volunteers.py merge $exp OUTDIR"
