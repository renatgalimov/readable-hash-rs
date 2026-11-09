#!/bin/sh
# Normalize everything downloaded so far, then build and measure tables for every language with enough words.
# Runs three languages at a time. Safe to re-run: languages with a result are skipped unless FORCE=1.
set -eu
cd "$(dirname "$0")"
PY="$HOME/data/phrase-langs/.venv/bin/python"
"$PY" normalize.py
"$PY" - <<'EOF' > /tmp/phrase-langs-todo.txt
import json, os
from pathlib import Path
langs = json.loads((Path.home() / "data/phrase-langs/words/languages.json").read_text())
done = {p.stem for p in Path("results").glob("*.json")}
for code, info in sorted(langs.items(), key=lambda kv: -kv[1]["words"]):
    if info["words"] >= 15000 and (os.environ.get("FORCE") or code not in done):
        print(code)
EOF
echo "$(wc -l < /tmp/phrase-langs-todo.txt) languages to build"
xargs -P 3 -n 4 "$PY" experiment.py < /tmp/phrase-langs-todo.txt
python3 report.py
