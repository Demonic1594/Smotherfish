# Helping test Smotherfish

Smotherfish improvements are tested by playing thousands of games. Anyone
with a GitHub account can lend their GitHub Actions minutes to these tests.
Your fork plays its share of each experiment on GitHub's machines; nothing
runs on your own computer and there is nothing to install.

All of this is testing of Smotherfish itself: each job builds Smotherfish
from the experiment's branch and plays it against Stockfish or Maia.

## Joining (about two minutes)

1. Fork this repository on GitHub (keep the `smotherfish` branch; you only
   need that branch).
2. Open your fork's **Actions** tab and enable workflows (GitHub disables
   them on new forks).
3. Still in Actions, choose **Helper poll** and press **Run workflow** once.
   It should finish green in under a minute.

That is all. Your fork is found automatically from the list of forks of
this repository. Its helper poll runs on a schedule; it copies any
experiment meant for your fork and starts it there.

## What your fork does

- Every experiment is split over the helpers in proportion to the jobs each
  lends at once (20 by default).
- Your fork plays up to 20 jobs at once (or your `HELPER_JOBS`, see below),
  each about 25 games on a 4-core GitHub machine, and writes the results to the branch `actions-exp/<experiment>`
  in your fork. The maintainers read them from there; nothing is pushed to
  this repository.
- Public repositories have free Actions minutes on GitHub's standard
  machines.

## Choosing how much your fork runs

By default your fork lends all of a free account's capacity: 20 jobs at
once. To lend less (or more, on a paid or organisation account), set a
repository variable in your fork: **Settings**, **Secrets and variables**,
**Actions**, **Variables**, **New repository variable**, name `HELPER_JOBS`,
value the number of jobs at once (1 to 256). Your fork's Helper poll
publishes it on a small branch named `helper-info`, and your share of each
test is proportional to it: a fork lending 10 jobs gets half the share of
one lending 20, and its test runs never use more than 10 jobs at once.
Changes apply from the next test.

## Starting automatically

The main repository's "Helper kick" workflow starts your fork's Helper poll
within about 15 minutes of a new experiment, so you do not need to press
anything. For that, add the repository owner as a collaborator on your fork
(your fork's Settings, Collaborators). Without it, your fork still picks up
experiments on its own schedule, about once an hour, or when you press
**Run workflow** on **Helper poll**.

## Keeping your fork up to date

With the repository owner as a collaborator (see above), the maintainers
keep your fork synced for you: the "Helper kick" workflow uses GitHub's
own **Sync fork**. If you have changes of your own, ours are merged in
alongside them when they do not conflict; when they do conflict, your fork
is left exactly as it is, and its share of each test is built on the newest
version it already has. Without a collaborator, use
**Sync fork** on your fork's main page when the maintainers ask:
experiments are built on the version your fork is on.

## Leaving

Disable the workflows in the Actions tab, or delete the fork. If your fork
stops running, its share is re-issued to the other helpers
(`notes/scripts/volunteers.py refill`), so nothing is lost.

## For maintainers

- `notes/scripts/volunteers.py list` shows the helpers (by ID only).
- `notes/scripts/distribute.sh PLAN.json` spreads an experiment over all
  of them (shares from `notes/volunteers.json`).
- `notes/scripts/volunteers.py status EXP` shows games delivered per
  account; `refill EXP` writes a plan with the shares of accounts that never
  ran (distribute it with `ONLY=...` as the command prints);
  `merge EXP OUTDIR` collects everything, refills included.

## Questions

**Does it cost anything?** No. Public repositories have free GitHub Actions
minutes on GitHub's standard runners; the tests only use those.

**What exactly runs?** Each job builds Smotherfish from the experiment's
branch, plays games against Stockfish (and sometimes the human-like Maia-3
network) and saves the results to your fork. It is testing of Smotherfish
itself, as GitHub's terms for Actions allow.

**Is my account name shown anywhere?** No. Forks are identified by a short ID
(the first 6 hex digits of a hash of the account name) in the repository and
on the status page.

**How do I see my fork's work?** Your fork's Actions tab, or the
[test status page](https://demonic1594.github.io/Smotherfish/), which lists
every helper with its latest run.

**Do I need to keep my fork in sync?** Not if the owner is a collaborator:
it is synced automatically when needed. Otherwise only when the maintainers
ask (after a release). Experiments carry their own engine code, so an
unsynced fork keeps working until then.
