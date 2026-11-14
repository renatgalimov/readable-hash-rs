#!/usr/bin/env python3
"""Find the English Wikipedia article for each language the explainer game names.

Asks Wikidata which item has each ISO 639 code (639-1, 639-3, then 639-2 and 639-5 for groups like "ber") and
takes its English Wikipedia article. Writes models/phrase-corpus/language-wikipedia.json ({code: article title}),
which game/build_space_game.py turns into links. Codes Wikidata can't place are listed for a manual entry in
OVERRIDES.

    python3 models/phrase-corpus/language_wikipedia.py
"""
import json
import subprocess
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORDS = HERE.parent / "training-data" / "phrase-words.json"
OUT = HERE / "language-wikipedia.json"
# Codes whose Wikidata answer is missing or ambiguous (a code shared by a macrolanguage and a member, etc.).
OVERRIDES = {"vro": "Võro_language",  # Wikidata also maps vro to South_Estonian, the wider group
             # Wiktionary's own codes (no ISO code to look up).
             "roa-brg": "Burgundian_language_(Oïl)", "roa-opt": "Galician–Portuguese",
             "sla-pro": "Proto-Slavic_language",
             # Tolkien's smaller languages have no ISO code; some only have a section in a broader article.
             "x-gnomish": "Languages_constructed_by_Tolkien#Elvish_languages",
             "x-telerin": "Elvish_languages_of_Middle-earth#Internal_history",
             "x-nandorin": "Elvish_languages_of_Middle-earth#Internal_history",
             "x-ilkorin": "Elvish_languages_of_Middle-earth", "x-adunaic": "Adûnaic", "x-khuzdul": "Khuzdul",
             "x-blackspeech": "Black_Speech", "x-westron": "Westron", "x-valarin": "Valarin",
             "x-rohirric": "Languages_constructed_by_Tolkien#Rohirric"}


def sparql(query):
    out = subprocess.run(["curl", "-s", "-m", "120", "-H", "User-Agent: readable-hash-game/0.1 (renat2017@gmail.com)",
                          "-H", "Accept: application/sparql-results+json", "--data-urlencode", f"query={query}",
                          "https://query.wikidata.org/sparql"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["results"]["bindings"]


def main():
    info = json.loads(WORDS.read_text())
    codes = sorted(set(info["languages"]) | set(info["list_languages"]))
    values = " ".join(f'"{code}"' for code in codes)
    found = {}
    for prop in ("P218", "P220", "P219", "P1798"):  # ISO 639-1, 639-3, 639-2, 639-5
        rows = sparql(f"""SELECT ?code ?item ?article WHERE {{
            VALUES ?code {{ {values} }}
            ?item wdt:{prop} ?code .
            ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> .
        }}""")
        for row in rows:
            code = row["code"]["value"]
            title = urllib.parse.unquote(row["article"]["value"].rsplit("/wiki/", 1)[1])
            found.setdefault(code, {}).setdefault(prop, set()).add(title)
    result, unsure = {}, {}
    for code in codes:
        if code in OVERRIDES:
            result[code] = OVERRIDES[code]
            continue
        by_prop = found.get(code, {})
        first = next((sorted(by_prop[p]) for p in ("P218", "P220", "P219", "P1798") if p in by_prop), [])
        if len(first) == 1:
            result[code] = first[0]
        else:
            unsure[code] = {p: sorted(t) for p, t in by_prop.items()}
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"{len(result)} of {len(codes)} codes have an article; unsure: {json.dumps(unsure, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
