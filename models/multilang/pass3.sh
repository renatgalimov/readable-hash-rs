#!/bin/sh
# Pass 3: mixes of non-English languages, English-free variants, and the blocklist on the finalists.
set -u
cd "$(dirname "$0")"
PY="$HOME/data/phrase-langs/.venv/bin/python"
# mixes and English-free variants (fast, ~10 s each)
"$PY" experiment.py zu+xh zu+xh+lg+sn zu+eu tr+zu eo+la eu+fi &
"$PY" experiment.py --no-english tr fi zu eu &
wait
# blocklist + three-token bans on the finalists (~4 min each), three at a time
printf '%s\n' zu xh lg sn eu eo la fi tr kab el zu+xh zu+xh+lg+sn | xargs -P 3 -n 1 "$PY" experiment.py --blocklist
python3 report.py
