#!/usr/bin/env python3
"""Write lichess-bot's config.yml for Smotherfish from lichess-bot's own
config.yml.default (so every other setting keeps lichess-bot's default).

usage: lichess_config.py config.yml.default config.yml [THREADS] [HASH_MB] [GAMES] [OPTS]

OPTS: extra engine options, "Name=Value;Name=Value" (e.g. "SmotherGoal=Near").

GAMES games are played at once (each engine runs THREADS search threads
plus one smother-prover thread).

The token is not written: lichess-bot reads it from the LICHESS_BOT_TOKEN
environment variable (a repository secret).
"""
import sys
import yaml

src, dst = sys.argv[1], sys.argv[2]
threads = int(sys.argv[3]) if len(sys.argv) > 3 else 3
hash_mb = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
games = int(sys.argv[5]) if len(sys.argv) > 5 else 1
extra = dict(kv.split("=", 1) for kv in sys.argv[6].split(";") if "=" in kv) if len(sys.argv) > 6 else {}
c = yaml.safe_load(open(src))

e = c["engine"]
e["dir"] = "./engines/"
e["name"] = "smotherfish"
e["protocol"] = "uci"
e["ponder"] = True
# Threads: one core is left for the smother prover's own thread.
e["uci_options"] = {"Threads": threads, "Hash": hash_mb, "Move Overhead": 150, **extra}
e["polyglot"]["enabled"] = False

ch = c["challenge"]
ch["concurrency"] = games
ch["accept_bot"] = True
ch["only_bot"] = False
ch["time_controls"] = ["bullet", "blitz", "rapid"]
ch["modes"] = ["casual", "rated"]
ch["variants"] = ["standard"]
# Our own bots never play each other (that would look like rating
# manipulation): declined as challengers, never challenged.
OWN_BOTS = [f"SmotherfishBot{i}" for i in range(1, 9)]
ch["block_list"] = OWN_BOTS
# No 30-second games: at 30+0 we lost twice on the clock (Nov 25) and there
# is no time to build a smother. At most 2 games per bot per hour (one 3124
# bot played bot 4 about 30 times in a row, all draws or losses).
ch["min_base"] = 60
ch["bullet_requires_increment"] = True
ch["recent_bot_challenge_age"] = 3600
ch["max_recent_bot_challenges"] = 2

mm = c["matchmaking"]
mm["allow_matchmaking"] = True
mm["challenge_variant"] = "standard"
mm["challenge_timeout"] = 1          # challenge a bot after 1 idle minute
mm["challenge_initial_time"] = [120, 180]
mm["challenge_increment"] = [1, 2]
mm["challenge_mode"] = "rated"
mm["opponent_rating_difference"] = 400
# Do not keep re-challenging bots that decline (slowed the first session).
mm["challenge_filter"] = "coarse"
mm["block_list"] = OWN_BOTS
mm["include_challenge_block_list"] = True
# Two thirds of challenges go to weaker bots, where smothers happen
# (lichess-bot picks the base settings or one override at random).
mm["overrides"] = {
    "weaker_1500_2000": {"opponent_min_rating": 1500, "opponent_max_rating": 2000,
                         "opponent_rating_difference": None},
    "weaker_2000_2400": {"opponent_min_rating": 2000, "opponent_max_rating": 2400,
                         "opponent_rating_difference": None},
}

c["pgn_directory"] = "game_records"
c["pgn_file_grouping"] = "game"
c["quit_after_all_games_finish"] = True  # Ctrl-C (SIGINT) lets games finish

yaml.safe_dump(c, open(dst, "w"), sort_keys=False)
print(f"wrote {dst}: {games} games at once, Threads {threads}, Hash {hash_mb}, matchmaking "
      f"{mm['challenge_initial_time']}+{mm['challenge_increment']} {mm['challenge_mode']}")
