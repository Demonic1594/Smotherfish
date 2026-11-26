#!/usr/bin/env python3
"""Build status.json for the test status page (fishtest-style).

Run by .github/workflows/status-data.yml every 15 minutes inside GitHub
Actions, or locally: status_data.py OUT.json [PREVIOUS.json]

For every recent experiment (notes/exp/<name>.json that has distributed
shares on helper-exp/* or actions-exp/* branches), it collects:
- games planned and delivered per account and in total (progress);
- live results per arm and opponent from the accounts' result files
  (games, wins/draws/losses, knight and any-piece smothers, score), with the
  change in knight smothers per 100 against the arm "B" and its z;
- every account's workflow activity (helpers shown by ID only);
- throughput (games per hour) from the previous snapshot.
Finished experiments are cached from PREVIOUS.json and not fetched again.
"""
import collections, concurrent.futures, datetime, hashlib, json, math, os, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import volunteers as V  # noqa: E402

MAIN = V.MAIN
TOKEN = os.environ.get("GH_TOKEN", "")
NOW = datetime.datetime.now(datetime.timezone.utc)
RECENT_DAYS = float(os.environ.get("STATUS_RECENT_DAYS", "4"))
OPP = {"e1500": "Stockfish 1500", "e2000": "Stockfish 2000", "e2500": "Stockfish 2500", "e2600": "Stockfish 2600",
       "e3000": "Stockfish 3000", "m1100": "Maia-3 1100", "m1500": "Maia-3 1500", "m1900": "Maia-3 1900"}


def api(path):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "smotherfish-status"}
    if TOKEN:
        h["Authorization"] = "Bearer " + TOKEN
    try:
        with urllib.request.urlopen(urllib.request.Request("https://api.github.com" + path, headers=h), timeout=30) as r:
            return json.loads(r.read())
    except Exception:
        return None


def heads(url, pat):
    out = subprocess.run(["git", "ls-remote", url, pat], capture_output=True, text=True).stdout
    return {l.split("\t")[1][len("refs/heads/"):]: l.split("\t")[0] for l in out.splitlines() if "\t" in l}


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def commit_date(repo, sha):
    c = api(f"/repos/{repo}/commits/{sha}")
    try:
        return c["commit"]["committer"]["date"]
    except Exception:
        return None


def plan_date(name, sha):
    d = commit_date(MAIN, sha) if sha else None
    if d:
        return d
    out = subprocess.run(["git", "-C", HERE, "log", "-1", "--format=%cI", "--", f"../exp/{name}.json"], capture_output=True, text=True).stdout.strip()
    if out:
        return iso(datetime.datetime.fromisoformat(out).astimezone(datetime.timezone.utc))
    return None


def fetch_part(main_heads, accounts, part, acc, url):
    ref = f"actions-exp/{part}" if acc == "own" else f"helper-exp/{acc}/{part}"
    if ref not in main_heads:
        return None
    d = None
    for _ in range(3):
        d = V.git_fetch(f"https://github.com/{MAIN}", ref)
        if d:
            break
    if not d:
        return None
    jobs = {(j["name"], j["seed"]): j["games"] for j in V.jobs_of(V.show(d, "notes/exp/plan.json") or "{}")}
    expected = sum(jobs.values())
    rd = None
    for _ in range(3):
        rd = V.git_fetch(url, f"actions-exp/{part}")
        if rd or not heads(url, f"refs/heads/actions-exp/{part}"):
            break
    files = {}
    if rd:
        for f in V.ls(rd, f"notes/results/{part}"):
            if f.endswith(".jsonl"):
                files[os.path.basename(f)[:-6]] = (V.show(rd, f) or "").splitlines()
    return {"part": part, "acc": acc, "expected": expected, "jobs": jobs, "copied": bool(rd), "files": files}


def describe(plan):
    """Arms and their options relative to arm B, and the opponents."""
    arms, opps, tcs = collections.OrderedDict(), [], set()
    for r in plan.get("runs", []):
        opp, _, arm = r["name"].partition("_")
        arms.setdefault(arm, r.get("opts", []))
        if opp not in opps:
            opps.append(opp)
        tcs.add(r.get("tc", plan.get("tc", "5+0.05")))
    base = set(arms.get("B", []))
    return [{"arm": a, "opts": [o for o in o_ if o not in base] if a != "B" else o_} for a, o_ in arms.items()], opps, sorted(tcs)


def arm_stats(lines):
    g = w = d = l = kn = full = 0
    for ln in lines:
        try:
            x = json.loads(ln)
        except Exception:
            continue
        g += 1
        s = x.get("ours")
        w += s == 1; d += s == 0.5; l += s == 0
        kn += x.get("smother") == "classic"
        full += x.get("smother") in ("classic", "any")
    return {"games": g, "w": w, "d": d, "l": l, "knight": kn, "full": full}


def zdiff(k1, n1, k0, n0):
    if not (n1 and n0):
        return None
    r1, r0 = k1 / n1, k0 / n0
    v = (max(k1, 1) / n1 ** 2) + (max(k0, 1) / n0 ** 2)
    return round((r1 - r0) / math.sqrt(v), 2)


def main(out, prev_path=None):
    prev = json.load(open(prev_path)) if prev_path and os.path.exists(prev_path) else {}
    prev_tests = {t["id"]: t for t in prev.get("tests", [])}
    conf = V.conf()
    forks = V.forks()                                   # [(id, url, pushed)]
    accounts = [("own", f"https://github.com/{MAIN}")] + [(i, u) for i, u, _ in forks if i not in conf["exclude"]]
    repo_of = {i: u.split("github.com/")[1].removesuffix(".git") for i, u in accounts}

    # Experiments: plan files with distributed shares.
    main_heads = heads(f"https://github.com/{MAIN}", "refs/heads/*")
    exp_dir = os.path.join(HERE, "..", "exp")
    names = set()
    for b in main_heads:
        if b.startswith("helper-exp/") and b.count("/") == 2:
            names.add(b.split("/")[2])
        elif b.startswith("actions-exp/"):
            names.add(b.split("/", 1)[1])
    names = {n for n in names if not n.startswith(("sprt", "conctest", "maia-grid", "helpercheck", "cachetest")) and n not in set(conf.get("superseded", []))}
    groups = collections.defaultdict(list)              # grid55-r1 belongs to grid55
    for n in names:
        groups[n.split("-r")[0] if "-r" in n and n.split("-r")[-1].isdigit() else n].append(n)

    # Every account's recent runs, fetched once: a test is "running" only while
    # a run of one of its parts is queued or in progress somewhere.
    runs_of = {}
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        for acc, rs in zip([a for a, _ in accounts], ex.map(
                lambda a: (api(f"/repos/{repo_of[a[0]]}/actions/runs?per_page=50") or {}).get("workflow_runs", []), accounts)):
            runs_of[acc] = [r for r in rs if r["name"] in ("Smother experiment", "SPRT")]
    live_exps = {r["head_branch"].replace("actions-exp/", "") for rs in runs_of.values() for r in rs if r["status"] != "completed"}

    tests = []
    for tid, parts in sorted(groups.items()):
        parts = sorted(parts, key=lambda p: (p != tid, p))
        if tid not in names:
            continue
        refs = ([f"actions-exp/{tid}"] if f"actions-exp/{tid}" in main_heads else []) + \
               [b for b in main_heads if b.startswith("helper-exp/") and b.endswith("/" + tid)]
        if not refs:
            continue
        sha = main_heads[refs[0]]
        created = plan_date(tid, sha)
        if created and (NOW - datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))).days > RECENT_DAYS:
            if tid in prev_tests:
                tests.append(prev_tests[tid])
            continue
        # Reuse a finished test unless one of its parts (a refill) is live again.
        if tid in prev_tests and str(prev_tests[tid].get("state", "")).startswith("finished") and not (set(parts) & live_exps):
            tests.append(prev_tests[tid])
            continue
        pd = V.git_fetch(f"https://github.com/{MAIN}", refs[0])
        try:
            plan = json.loads(V.show(pd, "notes/exp/plan.json") or "{}") if pd else {}
        except Exception:
            plan = {}
        plan.pop("shard", None)
        if not plan.get("runs"):
            continue
        arms, opps, tcs = describe(plan)
        planned_runs = collections.Counter({r["name"]: r["games"] for r in plan["runs"]})
        lines = collections.defaultdict(list)
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            got = [r for r in ex.map(lambda pa: fetch_part(main_heads, accounts, *pa),
                                     [(p, acc, url) for p in parts for acc, url in accounts]) if r]
        per_acc = {}
        for r in got:
            for name, data in r["files"].items():
                lines[name] += data
        for acc in {r["acc"] for r in got}:
            mine = [r for r in got if r["acc"] == acc]
            dl = lambda rs: sum(len(v) for r in rs for v in r["files"].values())
            # Jobs are identified by (run, seed): a refill repeating this
            # account's own jobs replaces them, other accounts' jobs add.
            union = {}
            for r in mine:
                union.update(r["jobs"])
            exp_ = sum(union.values())
            per_acc[acc] = {"expected": exp_, "delivered": dl(mine), "copied": any(r["copied"] for r in mine)}
        planned = sum(planned_runs.values())
        delivered = sum(len(v) for v in lines.values())
        stats = []
        for arm in arms:
            row = {"arm": arm["arm"], "opts": arm["opts"], "cells": {}}
            for opp in opps:
                name = f"{opp}_{arm['arm']}"
                if name not in planned_runs:
                    continue
                s = arm_stats(lines.get(name, []))
                s["planned"] = planned_runs[name]
                b = arm_stats(lines.get(f"{opp}_B", [])) if arm["arm"] != "B" else None
                if b and s["games"] and b["games"]:
                    s["dknight"] = round(100 * (s["knight"] / s["games"] - b["knight"] / b["games"]), 2)
                    s["z"] = zdiff(s["knight"], s["games"], b["knight"], b["games"])
                row["cells"][opp] = s
            stats.append(row)
        age_h = (NOW - datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))).total_seconds() / 3600 if created else 0
        # Running while any part has a live run, or in the first 2 hours (helper
        # forks may not have picked their share up yet); then finished, or
        # finished (partial) if games are missing.
        live = bool(set(parts) & live_exps)
        state = "running" if live or (delivered < planned and age_h < 2) else "finished" if delivered >= planned else "finished-partial"
        tests.append({"id": tid, "plan_sha": sha, "parts": parts, "created": created, "tc": tcs, "opponents": [{"key": o, "name": OPP.get(o, o)} for o in opps],
                      "planned": planned, "delivered": delivered, "state": state, "arms": stats,
                      "accounts": [{"id": k, **v} for k, v in sorted(per_acc.items())]})

    # Account activity.
    acc_out = []
    for acc, url in accounts:
        exp = runs_of.get(acc, [])
        live = [r for r in exp if r["status"] != "completed"]
        last = exp[0] if exp else None
        jobs = 0
        for r in live:
            j = api(f"/repos/{repo_of[acc]}/actions/runs/{r['id']}/jobs?filter=latest&per_page=100") or {}
            jobs += sum(1 for x in j.get("jobs", []) if x["status"] == "in_progress")
        games = sum(a["delivered"] for t in tests if t["state"] == "running" for a in t["accounts"] if a["id"] == acc)
        acc_out.append({"id": "main" if acc == "own" else acc, "share": V.jobs_for(acc, url, conf),
                        "running_runs": len(live), "jobs": jobs, "active_games": games,
                        "last": {"workflow": last["name"], "exp": last["head_branch"].replace("actions-exp/", ""), "status": last["status"],
                                 "conclusion": last["conclusion"], "updated": last["updated_at"]} if last else None})

    active_total = sum(t["delivered"] for t in tests if t["state"] == "running")
    hist = [h for h in prev.get("history", []) if (NOW - datetime.datetime.fromisoformat(h["t"].replace("Z", "+00:00"))).total_seconds() < 6 * 3600]
    done_total = sum(t["delivered"] for t in tests)
    hist.append({"t": iso(NOW), "games": done_total})
    gph = None
    if len(hist) >= 2:
        dt = (datetime.datetime.fromisoformat(hist[-1]["t"].replace("Z", "+00:00")) - datetime.datetime.fromisoformat(hist[0]["t"].replace("Z", "+00:00"))).total_seconds()
        if dt > 600:
            gph = max(0, round((hist[-1]["games"] - hist[0]["games"]) * 3600 / dt))
    status = {"generated": iso(NOW), "games_per_hour": gph, "jobs_running": sum(a["jobs"] for a in acc_out),
              "active_games": active_total, "accounts": acc_out, "tests": sorted(tests, key=lambda t: t.get("created") or "", reverse=True),
              "history": hist[-30:]}
    json.dump(status, open(out, "w"), indent=1)
    print(f"{len(tests)} tests, {len(acc_out)} accounts, {status['jobs_running']} jobs running, {gph} games/h")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
