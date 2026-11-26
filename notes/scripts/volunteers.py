#!/usr/bin/env python3
"""Smotherfish volunteer testing network (docs/HELPING.md).

Helpers are the public forks of the main repository, found through the
GitHub API (no login needed). A fork's ID is the first 6 hex digits of
sha256 of its owner's name in lower case, as in helper-poll.yml.
notes/volunteers.json sets shares (weights) and exclusions by ID only, so no
helper names are stored in the repository.

usage:
  volunteers.py list                    helpers: ID, weight, last push
  volunteers.py targets [--only ID,...] target lines for distribute.sh
  volunteers.py status EXP              games delivered per account vs expected
  volunteers.py refill EXP              plan with the jobs of accounts that
                                        delivered nothing (notes/exp/EXP-rN.json)
  volunteers.py merge EXP OUTDIR        merge EXP and its refills from all accounts

A typical round: distribute.sh PLAN; later status EXP; if an account never
ran, refill EXP and distribute the refill to the accounts that did
(ONLY=id,id,own distribute.sh notes/exp/EXP-r1.json); merge EXP OUTDIR.
"""
import collections, hashlib, json, os, subprocess, sys, tempfile, urllib.request

MAIN = "Demonic1594/Smotherfish"
HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(HERE, "..", "volunteers.json")


def conf():
    c = json.load(open(CONF))
    c.setdefault("weights", {}); c.setdefault("exclude", []); c.setdefault("base", "33bbe361")
    return c


def hid(owner):
    return hashlib.sha256(owner.lower().encode()).hexdigest()[:6]


def forks():
    """[(id, clone URL, last push)] of the main repository's public forks."""
    out, page = [], 1
    while True:
        url = f"https://api.github.com/repos/{MAIN}/forks?per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                                   "User-Agent": "smotherfish-volunteers"})
        data = json.load(urllib.request.urlopen(req, timeout=30))
        out += [(hid(f["owner"]["login"]), f["clone_url"], f["pushed_at"]) for f in data]
        if len(data) < 100:
            return out
        page += 1


def accounts():
    """[(id, URL)] of every account that may run experiments: our repository
    ("own") and the forks not excluded in volunteers.json."""
    c = conf()
    return [("own", f"https://github.com/{MAIN}")] + [(i, u) for i, u, _ in forks() if i not in c["exclude"]]


def git_fetch(url, ref):
    """Temporary checkout dir of url's ref (depth 1), or None if missing."""
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=True)
    if subprocess.run(["git", "-C", d, "fetch", "-q", "--depth", "1", url, ref],
                      stderr=subprocess.DEVNULL).returncode:
        return None
    return d


def show(d, path):
    r = subprocess.run(["git", "-C", d, "show", f"FETCH_HEAD:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def ls(d, path):
    r = subprocess.run(["git", "-C", d, "ls-tree", "--name-only", "FETCH_HEAD", path + "/"],
                       capture_output=True, text=True)
    return r.stdout.split()


def plan_ref(acc, exp):
    return f"actions-exp/{exp}" if acc == "own" else f"helper-exp/{acc}/{exp}"


def jobs_of(plan_text):
    """The matrix jobs of a (sharded) plan, via expand_plan.py."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(plan_text)
    out = subprocess.run([sys.executable, os.path.join(HERE, "expand_plan.py"), f.name],
                         capture_output=True, text=True).stdout
    os.unlink(f.name)
    for line in out.splitlines():
        if line.startswith("matrix="):
            return json.loads(line[len("matrix="):])
    return []


def results(url, exp):
    """{run name: games} delivered by the account at url for exp."""
    d = git_fetch(url, f"actions-exp/{exp}")
    if not d:
        return None
    return {os.path.basename(f)[:-6]: (show(d, f) or "").count("\n")
            for f in ls(d, f"notes/results/{exp}") if f.endswith(".jsonl")}


def survey(exp):
    """Per account: (expected jobs, delivered games per run or None)."""
    main = f"https://github.com/{MAIN}"
    rows = []
    for acc, url in accounts():
        d = git_fetch(main, plan_ref(acc, exp))
        if not d:
            continue  # this account has no share of exp
        rows.append((acc, url, jobs_of(show(d, "notes/exp/plan.json") or "{}"), results(url, exp)))
    return rows


def cmd_list(_):
    c = conf()
    print(f"{'id':8s} weight  last push")
    print(f"{'own':8s} {c['weights'].get('own', 1):6d}  (main repository)")
    for i, _, pushed in forks():
        w = "excluded" if i in c["exclude"] else str(c["weights"].get(i, 1))
        print(f"{i:8s} {w:>6s}  {pushed}")


def fork_base(url, base):
    """The version a fork's share is built on: base if the fork's default
    branch contains it (synced), else the newest commit of ours it does
    contain (a fork with conflicting changes of its own is not synced by
    Helper kick; its share must not bring newer workflow files)."""
    if subprocess.run(["git", "fetch", "-q", url, "smotherfish"], stderr=subprocess.DEVNULL).returncode:
        return base
    head = subprocess.run(["git", "rev-parse", "FETCH_HEAD"], capture_output=True, text=True).stdout.strip()
    if not subprocess.run(["git", "merge-base", "--is-ancestor", base, head]).returncode:
        return base
    mb = subprocess.run(["git", "merge-base", base, head], capture_output=True, text=True).stdout.strip()
    return mb[:8] if mb else base


def cmd_targets(args):
    c = conf()
    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    for acc, url in accounts():
        if only is None or acc in only:
            b = c.get("bases", {}).get(acc)
            if b is None:
                b = c["base"] if acc == "own" else fork_base(url, c["base"])
                if b != c["base"]:
                    print(f"{acc}: not synced (changes of its own); its share is built on {b}", file=sys.stderr)
            print(f"{acc}:{b}:{c['weights'].get(acc, 1)}")


def cmd_status(args):
    exp = args[0]
    tot_e = tot_d = 0
    for acc, _, jobs, res in survey(exp):
        exp_g = collections.Counter()
        for j in jobs:
            exp_g[j["name"]] += j["games"]
        e = sum(exp_g.values()); got = sum((res or {}).values())
        tot_e += e; tot_d += got
        state = "not started" if res is None else "done" if got >= e else f"partial"
        print(f"{acc:8s} {got:6d} / {e:6d} games  {state}")
    print(f"{'total':8s} {tot_d:6d} / {tot_e:6d} games")


def cmd_refill(args):
    exp = args[0]
    missing, active = [], []
    for acc, _, jobs, res in survey(exp):
        if res:
            active.append(acc)
            continue
        missing += jobs
    if not missing:
        print("nothing to refill"); return
    base = json.load(open(os.path.join(HERE, "..", "exp", f"{exp}.json")))
    k = 1
    while os.path.exists(os.path.join(HERE, "..", "exp", f"{exp}-r{k}.json")):
        k += 1
    runs = [{"name": j["name"], "elo": j["elo"], "games": j["games"], "chunk": j["games"],
             "seed": j["seed"], "first_chunk": j["chunk"], "tc": j["tc"], "opts": j["opts"].split(),
             **({"opponent": j["opp"]} if j["opp"] else {}),
             **({"opp_opts": j["oppopts"].split()} if j["oppopts"] else {})} for j in missing]
    plan = {k2: v for k2, v in base.items() if k2 not in ("runs", "exp", "shard")}
    plan.update(exp=f"{exp}-r{k}", runs=runs)
    out = os.path.join(HERE, "..", "exp", f"{exp}-r{k}.json")
    json.dump(plan, open(out, "w"), indent=1)
    print(f"{len(missing)} jobs ({sum(j['games'] for j in missing)} games) -> {out}")
    print(f"distribute to the accounts that delivered: ONLY={','.join(active)} notes/scripts/distribute.sh {out}")


def cmd_merge(args):
    exp, outdir = args[0], args[1]
    os.makedirs(outdir, exist_ok=True)
    skip = set(conf().get("superseded", []))
    exps = [exp] + [f"{exp}-r{k}" for k in range(1, 10)
                    if os.path.exists(os.path.join(HERE, "..", "exp", f"{exp}-r{k}.json")) and f"{exp}-r{k}" not in skip]
    merged = collections.defaultdict(list)
    for e in exps:
        for acc, url in accounts():
            d = git_fetch(url, f"actions-exp/{e}")
            if not d:
                continue
            n = 0
            for f in ls(d, f"notes/results/{e}"):
                if f.endswith(".jsonl"):
                    data = show(d, f) or ""
                    merged[os.path.basename(f)].append(data if data.endswith("\n") or not data else data + "\n")
                    n += data.count("\n")
            print(f"{e:14s} {acc:8s} {n:6d} games")
    for name, parts in merged.items():
        open(os.path.join(outdir, name), "w").write("".join(parts))
    print(f"merged {len(merged)} files into {outdir}")


if __name__ == "__main__":
    cmds = {"list": cmd_list, "targets": cmd_targets, "status": cmd_status, "refill": cmd_refill, "merge": cmd_merge}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])
