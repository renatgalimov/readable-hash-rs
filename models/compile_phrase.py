#!/usr/bin/env python3
"""Compile the phrase tables (format phrase-v7): 10 tokens, 16 layouts, context tables that decode by letters alone.

    python3 models/compile_phrase.py [--check]

Format (see src/phrase.rs):
- A phrase is 3 or 4 words, 10 tokens in all; each word is 2-4 tokens: a beginning, 0-2 middles, an ending.
  That gives 16 layouts, so the layout takes the low 4 bits. Allowing 5-token words would give 23 layouts
  (5+5 among them), and 4 bits can still tell only 16 apart, so they would add nothing.
- Beginning: 7 bits (128, prefix-free). Middle: 6 bits (64). Ending: 5 bits (32). Every layout is exactly
  64 bits: 4 + 3*7 + 4*6 + 3*5 (3 words) and 4 + 4*7 + 2*6 + 4*5 (4 words). With 32 middles a phrase would hold
  only 60 or 62 bits; doubling the beginnings or the endings instead would leave the 3-word layouts at 63.
- Why 10 tokens: 9 reach 64 bits only with all 256 beginning candidates (rare word starts), 64 endings and a
  layout code of 2-4 bits; 11 make phrases about 2 letters longer (25.0 against 23.1 on average).
- Each middle/ending row depends on the previous token (its context).

Table rules:
- The corpus is a word list from 153 languages (training-data/phrase-words.txt.xz, made by
  phrase-corpus/build_corpus.py): each language that isn't consonant-heavy contributes its 2,500 most frequent
  words, and so do hand-picked ones (English, German, Old English, Old Norse, Old High German, Zulu, Xhosa, constructed
  languages).
- No token is shorter than 2 letters. The corpus is re-tokenized with a vocabulary of 2+ letter pieces.
- The 256 beginning candidates are prefix-free: the most common word starts, skipping any that starts another
  one already taken. (In many languages the most common starts chain, like co/con/cont.)
- In every context, the 64 middles and the 32 endings together are prefix-free. So at each point at
  most one token matches the letters, and the decoder finds where a word ends without knowing its
  length. Rows that are prefix-free only separately would be ambiguous (ab+ou+s = ab+ous).
- Every token in a row joins plausibly to its context: each 3-letter sequence across the join occurs in
  some corpus word. This keeps fillers (tokens never seen after the context) from making words like
  bl+ness.
  A row that can't be filled this way (few letters can follow some pairs, like "ss" or "oq") lowers the
  minimum one word at a time (4, 3, 2, 1) until it fills; the model's "relaxed" lists those contexts with their
  minimum. The rule is never dropped. Such rows are made unreachable: a middle whose own row needs a lower
  minimum is never offered after any token (with "ss" reachable, 9 % of phrases had words like "tassde").
  validate() checks that no chosen beginning and no offered middle has a relaxed row.
- No letter appears three times in a row ("zanasssa"), and no three vowels (a, e, i, o, u) follow each other
  ("aaee", "oieieiaa"). Before this rule, 2.3 % of words had such a vowel run and some words had no consonant at
  all. Y doesn't count: between vowels it is read as a consonant (maya, ayudar), and counting it would rule out
  5.2 % of corpus words instead of 1.3 %. Tokens have 2+ letters, so either run always spans at most one join,
  and checking each previous token + token is enough.
- Every word has a vowel (a, e, i, o, u or y): after a beginning without one, every middle and ending
  has one. Words have at least 2 tokens, so that is enough.
- No word the tables can produce contains an offensive word from any language's list
  (training-data/blocklist.txt.xz): no word contains a listed term of 5+ letters, and no word starts with a
  listed 4-letter term. Strong English terms (severity 2-4 on the dsojevic list, or racial slurs) are stricter,
  because English is what most readers will read into a phrase: no word contains one of 4 letters, and no word
  starts with one of 3. Other 3-letter terms aren't checked (words have 4+ letters, and banning 3 letters
  inside words removes too much). Tokens that would
  complete a term after the previous token are left out of that context's row. Then an automaton of all the
  terms walks every word the tables can produce; each place a term completes bans that token after that
  context, and the rows are rebuilt until no word contains a term. validate() repeats that walk.
  When the same earlier part of a term completes after two or more tokens of one row (lu+bi+ch+ann and
  ro+bi+ch+ale both spell "bicha"), the cause is the join before: the previous token is banned after the tokens
  that led to it on those paths (ch after bi). Banning the last join instead removes one token per round from a
  hub row like ch (ann, ale, ane, ...: no "cha" left after 40+ rounds, and no convergence in 100).
  Once no word contains a term, bans that no longer matter are lifted once (stale_bans: ch+ann after bi+ch is
  banned; a third of the reachable bans were such leftovers) and the walk runs again until no word contains a
  term.
"""
import argparse
import itertools
import json
import lzma
import math
import re
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "training-data" / "phrase-words.txt.xz"
BLOCKLIST = ROOT / "training-data" / "blocklist.txt.xz"
MODEL_PATH = ROOT / "phrase_model.json"
REPORT_PATH = ROOT / "phrase_report.json"
RUST_PATH = ROOT.parent / "src" / "phrase_data.rs"

MIN_TOKEN = 2
MAX_TOKEN = 6
NUM_BEGIN, NUM_END, NUM_MIDDLE = 256, 256, 512
BEGIN_SIZE, MIDDLE_SIZE, END_SIZE = 128, 64, 32
TOTAL_TOKENS, MAX_WORDS, MIN_WORD, MAX_WORD = 10, 4, 2, 4
VERSION = "phrase-v7"


# ---------------------------------------------------------------- vocabulary and corpus counts

def read_text(path):
    return lzma.decompress(path.read_bytes()).decode() if path.suffix == ".xz" else path.read_text(encoding="utf-8")


def corpus_words():
    return re.findall(r"[a-z]+", read_text(CORPUS).lower())


STRONG = {"dsojevic-en-2", "dsojevic-en-3", "dsojevic-en-4", "dsojevic-en-racial"}


def blocklist():
    """Offensive terms from every language's list, folded to a-z: (terms banned at a word's start, anywhere)."""
    start, anywhere = set(), set()
    for line in read_text(BLOCKLIST).splitlines():
        term, sources = line.split("\t")
        strong = bool(STRONG & set(sources.split(",")))
        if len(term) >= 5 or (len(term) == 4 and strong):
            anywhere.add(term)
        elif len(term) == 4 or (len(term) == 3 and strong):
            start.add(term)
    return sorted(start), sorted(anywhere)


def offensive_token(text, starts_word, start_terms, anywhere_terms):
    """A token that is offensive on its own: it contains a term, or starts a word with one."""
    return any(t in text for t in anywhere_terms) or (starts_word and text.startswith(tuple(start_terms)))


def build_vocabulary(words, start_terms=(), anywhere_terms=()):
    """Top n-grams of 2-6 letters by position: ids 0-255 beginnings, 256-511 endings, 512-1023 middles.

    Beginnings are prefix-free (the most common starts first, skipping any that starts another one already taken).
    Tokens that are offensive on their own are left out.
    """
    begin, end, middle = Counter(), Counter(), Counter()
    for word in words:
        for length in range(MIN_TOKEN, min(MAX_TOKEN, len(word)) + 1):
            begin[word[:length]] += 1
            end[word[-length:]] += 1
        for start in range(1, len(word) - 1):
            for length in range(MIN_TOKEN, MAX_TOKEN + 1):
                if start + length < len(word):
                    middle[word[start:start + length]] += 1
    tokens = []
    for counts, size, kind in ((begin, NUM_BEGIN, "^"), (end, NUM_END, "$"), (middle, NUM_MIDDLE, "")):
        top = []
        for text, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            if offensive_token(text, kind == "^", start_terms, anywhere_terms):
                continue
            if kind == "^" and any(conflicts(text, other) for other in top):
                continue
            top.append(text)
            if len(top) == size:
                break
        assert len(top) == size, (kind, len(top))
        tokens += [("^" + text) if kind == "^" else (text + "$") if kind == "$" else text for text in top]
    return tokens


def text_of(token):
    return token.removeprefix("^").removesuffix("$")


def segment(word, begin_ids, middle_ids, end_ids, frequency):
    """Best split into beginning, middles, ending (all 2+ letters): fewest tokens, then most frequent pieces."""
    n = len(word)
    best = {}  # position -> (tokens, -score, ids) for the best split of word[position:] into middles + ending

    def tail(position):
        if position in best:
            return best[position]
        result = None
        for length in range(MIN_TOKEN, min(MAX_TOKEN, n - position) + 1):
            piece = word[position:position + length]
            if position + length == n:
                if piece in end_ids:
                    option = (1, -math.log(frequency[end_ids[piece]]), (end_ids[piece],))
                    result = option if result is None or option < result else result
            elif piece in middle_ids:
                rest = tail(position + length)
                if rest is not None:
                    token = middle_ids[piece]
                    option = (rest[0] + 1, rest[1] - math.log(frequency[token]), (token,) + rest[2])
                    result = option if result is None or option < result else result
        best[position] = result
        return result

    result = None
    for length in range(MIN_TOKEN, min(MAX_TOKEN, n - MIN_TOKEN) + 1):
        piece = word[:length]
        if piece in begin_ids:
            rest = tail(length)
            if rest is not None:
                token = begin_ids[piece]
                option = (rest[0] + 1, rest[1] - math.log(frequency[token]), (token,) + rest[2])
                result = option if result is None or option < result else result
    return None if result is None else list(result[2])


def count_transitions(words, tokens):
    begin_ids = {text_of(t): i for i, t in enumerate(tokens[:NUM_BEGIN])}
    end_ids = {text_of(t): NUM_BEGIN + i for i, t in enumerate(tokens[NUM_BEGIN:NUM_BEGIN + NUM_END])}
    middle_ids = {t: NUM_BEGIN + NUM_END + i for i, t in enumerate(tokens[NUM_BEGIN + NUM_END:])}
    # Tie-break between equally short splits: prefer pieces ranked higher in their vocabulary block
    # (blocks are sorted by corpus count), using rank as a stand-in for frequency.
    frequency = {i: 1024 - i % 512 for i in range(1024)}
    begin, middle, ending = Counter(), defaultdict(Counter), defaultdict(Counter)
    segmented = skipped = 0
    cache = {}
    for word in words:
        if word not in cache:
            cache[word] = segment(word, begin_ids, middle_ids, end_ids, frequency) if len(word) >= 2 * MIN_TOKEN else None
        ids = cache[word]
        if ids is None:
            skipped += 1
            continue
        segmented += 1
        begin[ids[0]] += 1
        for previous, following in zip(ids, ids[1:]):
            (ending if NUM_BEGIN <= following < NUM_BEGIN + NUM_END else middle)[previous][following] += 1
    return {"begin": begin, "middle": middle, "end": ending, "segmented": segmented, "skipped": skipped}


# ---------------------------------------------------------------- table selection

def context(token):
    return token if token < 256 else token - 256


CONTEXTS = list(range(256)) + list(range(512, 1024))  # beginnings and middles can be followed by a token


def conflicts(a, b):
    return a.startswith(b) or b.startswith(a)


def choose_prefix_free(candidates, size):
    """Greedy: highest (local, global) weight first, skipping any token that is a prefix of a chosen one or vice versa."""
    chosen = []
    for text, _ in sorted(candidates.items(), key=lambda item: (-item[1][0], -item[1][1], item[0])):
        if all(not conflicts(text, other) for other in chosen):
            chosen.append(text)
            if len(chosen) == size:
                return chosen
    raise ValueError("not enough prefix-free tokens")


VOWELS = set("aeiouy")
MIN_TRIGRAM_WORDS = 5  # a 3-letter sequence counts as English if at least this many corpus words contain it


def trigram_counts(words):
    """How many distinct corpus words contain each 3-letter sequence."""
    return Counter(trigram for word in set(words) for trigram in {word[i:i + 3] for i in range(len(word) - 2)})


def letter_trigrams(words, minimum=None, counts=None):
    """3-letter sequences found in at least `minimum` distinct corpus words (one odd word like "bitblt" isn't enough)."""
    minimum = MIN_TRIGRAM_WORDS if minimum is None else minimum
    counts = trigram_counts(words) if counts is None else counts
    return {trigram for trigram, count in counts.items() if count >= minimum}


def triple_free(previous_text, token_text):
    """No letter three times in a row, and no three vowels in a row, across the join (or inside the token)."""
    return not re.search(r"(.)\1\1|[aeiou]{3}", previous_text[-2:] + token_text)


def joins_well(previous_text, token_text, trigrams):
    """Every 3-letter sequence across the join must occur in some corpus word (rules out bl+ness: "bln").

    Tokens are 2+ letters, so the last 2 letters before the join and the first 2 after it cover every
    sequence that crosses it. A token seen after this context in the corpus always passes.
    """
    joined = previous_text[-2:] + token_text[:2]
    return all(joined[i:i + 3] in trigrams for i in range(len(joined) - 2))


def has_vowel(text):
    return bool(VOWELS & set(text))


def choose_row(previous_text, local_middle, local_end, global_middle, global_end, middle_pool, end_pool, trigrams,
               needs_vowel=False):
    """MIDDLE_SIZE middles + END_SIZE endings, prefix-free together, each joining plausibly to the previous token.

    Attested tokens first (by local count, either kind); then filler endings, then filler middles.
    Endings go first among fillers because their pool is half the size. A few tight contexts
    ("qu", "sw": a vowel must follow) have so many attested 2-letter middles that 32 endings can't
    fit; there, the rarest attested middles are treated as fillers, one count level at a time,
    until both rows fill.
    """
    def allowed(token):
        return (joins_well(previous_text, TEXT[token], trigrams) and triple_free(previous_text, TEXT[token])
                and (has_vowel(TEXT[token]) or not needs_vowel))

    middles = [(local_middle.get(t, 0), global_middle[t], "m", t) for t in middle_pool if allowed(t)]
    endings = [(local_end.get(t, 0), global_end[t], "e", t) for t in end_pool if allowed(t)]
    for demoted_below in [0] + sorted({local for local, *_ in middles if local}):
        def order(item):
            local, global_count, kind, token = item
            filler = local == 0 or (kind == "m" and local <= demoted_below)
            return (filler, filler and kind == "m", -local, -global_count, kind, token)

        rows = {"m": [], "e": []}
        limits = {"m": MIDDLE_SIZE, "e": END_SIZE}
        chosen_texts = []
        for _, _, kind, token in sorted(middles + endings, key=order):
            if len(rows[kind]) == limits[kind]:
                continue
            piece = TEXT[token]
            if any(conflicts(piece, other) for other in chosen_texts):
                continue
            rows[kind].append(token)
            chosen_texts.append(piece)
            if len(rows["m"]) == MIDDLE_SIZE and len(rows["e"]) == END_SIZE:
                return rows["m"], rows["e"]
    raise ValueError(f"row too small after {previous_text!r}")


TEXT = []


class Terms:
    """An Aho-Corasick automaton over the banned terms; a word is read as "^" + its letters."""

    def __init__(self, start_terms, anywhere_terms):
        patterns = ["^" + t for t in start_terms] + list(anywhere_terms)
        self.patterns = set(patterns)
        self.goto, self.fail, self.out, self.label = [{}], [0], [False], [""]  # label: the letters a state stands for
        for pattern in patterns:
            node = 0
            for ch in pattern:
                if ch not in self.goto[node]:
                    self.goto.append({})
                    self.fail.append(0)
                    self.out.append(False)
                    self.label.append(self.label[node] + ch)
                    self.goto[node][ch] = len(self.goto) - 1
                node = self.goto[node][ch]
            self.out[node] = True
        queue = deque(self.goto[0].values())
        while queue:
            node = queue.popleft()
            for ch, child in self.goto[node].items():
                queue.append(child)
                fallback = self.fail[node]
                while fallback and ch not in self.goto[fallback]:
                    fallback = self.fail[fallback]
                self.fail[child] = self.goto[fallback].get(ch, 0) if self.goto[fallback].get(ch, 0) != child else 0
                self.out[child] = self.out[child] or self.out[self.fail[child]]
        self.memo = {}

    def step(self, node, ch):
        key = (node, ch)
        if key not in self.memo:
            state = node
            while state and ch not in self.goto[state]:
                state = self.fail[state]
            self.memo[key] = self.goto[state].get(ch, 0)
        return self.memo[key]

    def parts_before(self, node, previous_text, text):
        """For each term that completes while reading text in state node (reached after previous_text): the part
        of the term before previous_text ("bi" for bi+ch+ann spelling "bicha"); "" if it starts inside it."""
        path, parts = self.label[node], set()
        for end in range(1, len(text) + 1):
            letters = path + text[:end]
            for length in range(end + 1, len(letters) + 1):
                if letters[-length:] in self.patterns:
                    parts.add(letters[-length:][:max(0, length - end - len(previous_text))])
        return parts

    def feed(self, node, text):
        """The state after reading text, and whether a term completed on the way."""
        hit = False
        for ch in text:
            node = self.step(node, ch)
            hit = hit or self.out[node]
        return node, hit


def violations(model, terms, causes=None):
    """Every (context, token) pair where some word the tables can produce completes a banned term.

    causes, if given, collects for each pair (part of the term before the context, token before the context):
    the part is Terms.parts_before; the token is one that led to the context on a path spelling that part (None
    if the term starts inside the context, or the context is a beginning).

    Walks all words: a beginning, up to MAX_WORD - 2 middles, an ending, carrying the automaton's state, so it
    sees terms that span any number of tokens.
    """
    text = [text_of(t) for t in model["tokens"]]
    start, _ = terms.feed(0, "^")
    found = set()
    stack, seen = [], set()
    parents, hits = defaultdict(set), []  # item -> tokens that led to it; (item, token) where a term completes
    for token in model["begin"]:
        state, hit = terms.feed(start, text[token])
        assert not hit, f"beginning {text[token]!r} is offensive"
        stack.append((token, state, 0))
    while stack:
        item = stack.pop()
        if item in seen:
            continue
        seen.add(item)
        token, state, middles = item
        row = context(token)
        for ending in model["end32"][row]:
            if terms.feed(state, text[ending])[1]:
                found.add((token, ending))
                hits.append((item, ending))
        if middles < MAX_WORD - 2:
            for middle in model["middle"][row]:
                following, hit = terms.feed(state, text[middle])
                if hit:
                    found.add((token, middle))
                    hits.append((item, middle))
                else:
                    parents[(middle, following, middles + 1)].add(token)
                    stack.append((middle, following, middles + 1))
    if causes is not None:
        for item, following in hits:
            token, state, _ = item
            for part in terms.parts_before(state, text[token], text[following]):
                for parent in (parents.get(item) or {None}) if part else {None}:
                    causes[(token, following)].add((part, parent))
    return found


def stale_bans(model, terms, banned):
    """Bans in reachable rows that no longer matter: on no path to their context would the banned token complete
    a term, either itself or (a middle) with a token of its own row. Bans of rows no phrase reaches are kept."""
    text = [text_of(t) for t in model["tokens"]]
    needed, reached = set(), set()
    start = terms.feed(0, "^")[0]
    stack, seen = [(b, terms.feed(start, text[b])[0], 0) for b in model["begin"]], set()
    while stack:
        item = stack.pop()
        if item in seen:
            continue
        seen.add(item)
        token, state, middles = item
        reached.add(token)
        for banned_token in banned[token]:
            if (token, banned_token) in needed:
                continue
            after, hit = terms.feed(state, text[banned_token])
            if not hit and banned_token >= NUM_BEGIN + NUM_END and middles < MAX_WORD - 2:
                row = context(banned_token)
                hit = any(terms.feed(after, text[t])[1] for t in model["middle"][row] + model["end32"][row])
            if hit:
                needed.add((token, banned_token))
        if middles < MAX_WORD - 2:
            for middle in model["middle"][context(token)]:
                following, hit = terms.feed(state, text[middle])
                if not hit:
                    stack.append((middle, following, middles + 1))
    return {(ctx, t) for ctx in reached for t in banned[ctx] if (ctx, t) not in needed}


def compile_model(max_rounds=100):
    global TEXT
    words = corpus_words()
    start_terms, anywhere_terms = blocklist()
    tokens = build_vocabulary(words, start_terms, anywhere_terms)
    TEXT = [text_of(t) for t in tokens]
    assert all(len(t) >= MIN_TOKEN for t in TEXT)
    counts = count_transitions(words, tokens)
    seen = trigram_counts(words)
    trigrams = {minimum: letter_trigrams(words, minimum, seen) for minimum in range(1, MIN_TRIGRAM_WORDS + 1)}
    terms = Terms(start_terms, anywhere_terms)
    global_middle = Counter()
    global_end = Counter()
    for row in counts["middle"].values():
        global_middle.update(row)
    for row in counts["end"].values():
        global_end.update(row)
    begin_candidates = {TEXT[i]: (counts["begin"].get(i, 0), 0) for i in range(NUM_BEGIN)}
    begin_texts = choose_prefix_free(begin_candidates, BEGIN_SIZE)
    begin_index = {TEXT[i]: i for i in range(NUM_BEGIN)}
    begin = [begin_index[t] for t in begin_texts]

    def direct_ban(ctx, token):
        """The previous token and this one already spell a term (the walk finds longer spans)."""
        return terms.feed(terms.feed(0, "^")[0] if ctx < NUM_BEGIN else 0, TEXT[ctx] + TEXT[token])[1]

    banned = {ctx: {t for t in range(NUM_BEGIN, 1024) if direct_ban(ctx, t)} for ctx in CONTEXTS}

    families = defaultdict(set)  # context -> parts of terms before it that already got a token banned after it
    lifted = None  # the stale bans lifted once the walk first finds nothing
    unreachable = set()  # middles whose own row needs a lower join minimum: never offered
    rounds = []
    for _ in range(max_rounds):
        middle, end32, relaxed = [], [], {}
        for ctx in CONTEXTS:
            local_middle = counts["middle"].get(ctx, Counter())
            local_end = counts["end"].get(ctx, Counter())
            # Every word needs a vowel: words have 2+ tokens, so a beginning without one must be followed by one.
            needs_vowel = ctx < NUM_BEGIN and not has_vowel(TEXT[ctx])
            middle_pool = [t for t in range(512, 1024) if t not in banned[ctx] and t not in unreachable]
            end_pool = [t for t in range(256, 512) if t not in banned[ctx]]
            for minimum in range(MIN_TRIGRAM_WORDS, 0, -1):
                try:
                    m, e = choose_row(TEXT[ctx], local_middle, local_end, global_middle, global_end,
                                           middle_pool, end_pool, trigrams[minimum], needs_vowel)
                    break
                except ValueError:
                    if minimum == 1:
                        raise
            if minimum < MIN_TRIGRAM_WORDS:
                relaxed[str(ctx)] = minimum
            middle.append(m)
            end32.append(e)
        model = {"version": VERSION, "tokens": tokens, "contexts": CONTEXTS, "begin": begin,
                 "middle": middle, "end32": end32, "relaxed": relaxed}
        causes = defaultdict(set)
        found = violations(model, terms, causes)
        rounds.append(len(found))
        newly = {int(ctx) for ctx in relaxed if int(ctx) >= NUM_BEGIN + NUM_END} - unreachable
        if not found and not newly:
            if lifted is not None:
                break
            lifted = stale_bans(model, terms, banned)
            if not lifted:
                break
            for ctx, token in lifted:
                banned[ctx].discard(token)
            continue
        unreachable |= newly
        for ctx, token in sorted(found):
            roots, parts = set(), set()
            for part, parent in sorted(causes[(ctx, token)], key=lambda cause: (cause[0], cause[1] is None, cause[1] or 0)):
                if parent is not None and part in families[ctx] and ctx not in banned[parent]:
                    roots.add(parent)
                parts.add(part)
            families[ctx] |= parts
            for parent in roots:
                banned[parent].add(ctx)
            if not roots:
                banned[ctx].add(token)
    else:
        raise ValueError(f"offensive words still reachable after {max_rounds} rounds: {rounds}")
    assert not set(begin) & {int(ctx) for ctx in relaxed}, "a chosen beginning needs a lower join minimum"
    # The tokens left out after each context because they would spell a term (directly or across tokens).
    model["banned"] = {str(ctx): sorted(b) for ctx, b in banned.items() if b}
    validate(model)
    statistics = report(model, counts)
    statistics["statistics"].update({
        "blocklist_terms_checked": len(start_terms) + len(anywhere_terms),
        "banned_pairs": sum(len(b) for b in banned.values()),
        "ban_rounds": rounds,
        "stale_bans_lifted": len(lifted or ()),
        "relaxed_contexts": len(relaxed),
        "unreachable_middles": len(unreachable),
    })
    return model, statistics


def validate(model):
    text = [text_of(t) for t in model["tokens"]]
    seen = trigram_counts(corpus_words())
    trigrams = {minimum: letter_trigrams(None, minimum, seen) for minimum in range(1, MIN_TRIGRAM_WORDS + 1)}
    assert not any(re.search(r"(.)\1\1", piece) for piece in text), "a token has a letter three times in a row"
    assert all(len(t) >= MIN_TOKEN and t.isascii() and t.isalpha() and t.islower() for t in text)
    begin = [text[i] for i in model["begin"]]
    assert len(begin) == BEGIN_SIZE and all(i < 256 for i in model["begin"])
    assert all(not conflicts(a, b) for a, b in itertools.combinations(begin, 2)), "beginnings must be prefix-free"
    assert all(triple_free("", b) for b in begin), "a beginning has three in a row"
    for index in range(len(CONTEXTS)):
        m, e = model["middle"][index], model["end32"][index]
        assert len(m) == MIDDLE_SIZE and all(512 <= i < 1024 for i in m)
        assert len(e) == END_SIZE and all(256 <= i < 512 for i in e)
        union = [text[i] for i in m + e]
        assert all(not conflicts(a, b) for a, b in itertools.combinations(union, 2)), f"context {index} not prefix-free"
        previous = text[CONTEXTS[index]]
        minimum = model["relaxed"].get(str(CONTEXTS[index]), MIN_TRIGRAM_WORDS)
        assert all(joins_well(previous, piece, trigrams[minimum]) for piece in union), f"context {index} has an implausible join"
        assert all(triple_free(previous, piece) for piece in union), f"context {index}: three in a row"
        assert not {str(t) for t in model["middle"][index]} & model["relaxed"].keys(), f"context {index} offers a relaxed middle"
        if CONTEXTS[index] < NUM_BEGIN and not has_vowel(previous):
            assert all(has_vowel(piece) for piece in union), f"beginning {previous!r} allows a word with no vowel"
    assert not {str(t) for t in model["begin"]} & model["relaxed"].keys(), "a chosen beginning has a relaxed row"
    found = violations(model, Terms(*blocklist()))
    assert not found, f"{len(found)} places still spell an offensive word, e.g. {sorted(found)[:3]}"
    for ctx, tokens in model.get("banned", {}).items():
        row = context(int(ctx))
        assert not set(tokens) & set(model["middle"][row] + model["end32"][row]), f"context {ctx} uses a banned token"


def report(model, counts):
    """How much of each row was seen after its context in the corpus (higher reads more naturally)."""
    stats = {"corpus_words": counts["segmented"] + counts["skipped"], "segmented_words": counts["segmented"],
             "skipped_words": counts["skipped"]}
    for label, kind in (("middle", "middle"), ("end32", "end")):
        attested = total = 0
        for index, ctx in enumerate(CONTEXTS):
            local = counts[kind].get(ctx, {})
            row = model[label][index]
            attested += sum(1 for t in row if t in local)
            total += len(row)
        stats[f"{label}_attested_fraction"] = attested / total
    stats["begin_attested"] = sum(1 for i in model["begin"] if counts["begin"].get(i))
    return {"statistics": stats}


# ---------------------------------------------------------------- reference codec (mirrors src/phrase.rs)

def layouts():
    result = []
    for words in range(1, MAX_WORDS + 1):
        for lengths in itertools.product(range(MIN_WORD, MAX_WORD + 1), repeat=words):
            if sum(lengths) == TOTAL_TOKENS:
                result.append(lengths)
    result.sort()
    assert len(result) & (len(result) - 1) == 0, f"{len(result)} layouts: not a power of two"
    return result


def layout_bits():
    return len(layouts()).bit_length() - 1


def encode(model, value):
    """The layout's index in the low bits, then each word's tokens left to right, each above the one before."""
    text = [text_of(t) for t in model["tokens"]]
    table = layouts()
    lengths = table[value & (len(table) - 1)]
    value >>= layout_bits()
    words = []
    for length in lengths:
        token = model["begin"][value % BEGIN_SIZE]
        value //= BEGIN_SIZE
        word = text[token]
        for _ in range(length - 2):
            token = model["middle"][context(token)][value % MIDDLE_SIZE]
            value //= MIDDLE_SIZE
            word += text[token]
        token = model["end32"][context(token)][value % END_SIZE]
        value //= END_SIZE
        words.append(word + text[token])
    assert value == 0
    return " ".join(words)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files would change")
    args = parser.parse_args()
    model, rep = compile_model()
    outputs = {
        MODEL_PATH: json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n",
        REPORT_PATH: json.dumps(rep, sort_keys=True, indent=1) + "\n",
        RUST_PATH: rust_source(model),
    }
    for path, content in outputs.items():
        if args.check:
            if path.read_text() != content:
                raise SystemExit(f"generated file differs: {path}")
        else:
            path.write_text(content)
    print(json.dumps(rep["statistics"], indent=1))


def rust_source(model):
    out = "// Generated by models/compile_phrase.py; do not edit.\n#![allow(clippy::unreadable_literal)]\n"
    out += "#[rustfmt::skip]\npub static TOKENS: [&str; 1024] = " + json.dumps(model["tokens"]) + ";\n"
    out += f"#[rustfmt::skip]\npub static BEGIN: [u16; {BEGIN_SIZE}] = " + json.dumps(model["begin"]) + ";\n"
    out += f"#[rustfmt::skip]\npub static MIDDLE: [[u16; {MIDDLE_SIZE}]; 768] = " + json.dumps(model["middle"]) + ";\n"
    out += f"#[rustfmt::skip]\npub static END32: [[u16; {END_SIZE}]; 768] = " + json.dumps(model["end32"]) + ";\n"
    return out


if __name__ == "__main__":
    main()
