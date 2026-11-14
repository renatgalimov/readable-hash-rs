// Headless check of the spaces game: walk every branch, collect end states, take screenshots.
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const OUT = process.env.OUT_DIR || path.join(process.env.TMPDIR || tmpdir(), "space-game-check");
mkdirSync(OUT, { recursive: true });
// Build first (python3 game/build_space_game.py), or point GAME_URL at a served copy.
const HERE = path.dirname(fileURLToPath(import.meta.url));
// The paths it clicks: word lengths for the first screenshots, one full layout, one with a middle.
const TOKENS = 10;
const F = { layouts: 16, shots: [["4 tokens"], ["2 tokens", "2 tokens"]], layout: ["2 tokens", "4 tokens", "4 tokens"],
  middle: ["3 tokens", "3 tokens", "4 tokens"] };
const MODEL = path.join(HERE, "..", "models", "phrase_model.json");
const URL_ = process.env.GAME_URL || pathToFileURL(path.join(HERE, "space-game.html")).href;
const failures = [];
const expect = (ok, what) => { if (!ok) failures.push(what); };
const PORT = 9333;
const profile = mkdtempSync(path.join(process.env.TMPDIR || tmpdir(), "chr-"));
const chrome = spawn("chromium", [
  "--headless=new", `--remote-debugging-port=${PORT}`, "--remote-debugging-address=127.0.0.1",
  `--user-data-dir=${profile}`, "--no-proxy-server", "--window-size=900,1100", "about:blank",
], { stdio: "ignore", detached: true });
// However the run ends (a check that throws included), kill the browser with its helper processes and delete its
// profile: a browser left on the port would be driven by the next run.
chrome.unref();
process.on("exit", () => {
  try { process.kill(-chrome.pid, "SIGKILL"); } catch {}
  rmSync(profile, { recursive: true, force: true, maxRetries: 5 });
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let targets;
for (let i = 0; i < 50; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); if (targets.length) break; } catch {}
  await sleep(200);
}
const page = targets.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let id = 0;
const pending = new Map();
const errors = [];
ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  if (msg.method === "Runtime.exceptionThrown") errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
  if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") errors.push(JSON.stringify(msg.params.args));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expression) => {
  const res = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (res.result.exceptionDetails) throw new Error(JSON.stringify(res.result.exceptionDetails));
  return res.result.result.value;
};
const shot = async (name) => {
  const res = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  const file = path.join(OUT, name);
  writeFileSync(file, Buffer.from(res.result.data, "base64"));
  console.log("screenshot", file);
};

await send("Runtime.enable");
await send("Page.enable");
await send("Emulation.setFocusEmulationEnabled", { enabled: true });  // focus and blur fire as in a focused window
await send("Emulation.setDeviceMetricsOverride", { width: 760, height: 900, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: URL_ });
await sleep(1500);
expect(await evaluate(`!!window.SPACE_GAME_ORIGINS`), "the language data (space-game-origins.js) loads");

const walk = await evaluate(`(() => {
  const out = [];
  const pages = [];
  const $ = (i) => document.getElementById(i);
  const reset = () => $('reset').click();
  const buttons = () => [...document.querySelectorAll('#panel .choices button')];
  function walk(p) {
    reset();
    for (const i of p) buttons()[i].click();
    const bs = buttons();
    if (!bs.length) {
      out.push({ path: p, phrase: [...document.querySelectorAll('#phrase .word')].map(w => w.children.length).join('+'),
        count: $('count').textContent, formula: $('formula').textContent, msg: $('msg').textContent,
        randomDisabled: $('random').disabled });
      return;
    }
    pages.push({ path: p, options: bs.map(b => b.textContent), msg: $('msg').textContent, formula: $('formula').textContent });
    for (let i = 0; i < bs.length; i++) walk([...p, i]);
  }
  walk([]);
  reset();
  return { out, pages, key: $('key').innerText };
})()`);
writeFileSync(path.join(OUT, "walk.json"), JSON.stringify(walk, null, 1));
console.log("end states", walk.out.length, "pages", walk.pages.length);
expect(walk.out.length === F.layouts, `${F.layouts} layouts, got ${walk.out.length}`);
expect(walk.out.every((o) => o.count === "64"), "every layout is exactly 64 bits");
// The printed bits add up: every formula, and the length choices in each summary ("add up to 1.193 + 1.222 + 1.585 = 4").
const sumsUp = (line) => { const [terms, total] = line.split(" = ");
  return Math.abs((terms.match(/\d+(\.\d+)?/g) || []).reduce((s, x) => s + Number(x), 0) - parseFloat(total)) < 1e-9; };
const sums = [...walk.out, ...walk.pages].flatMap((o) => [o.formula, ...(o.msg.match(/add up to [^=]+ = [\d.]+/g) || [])
  .map((s) => s.slice("add up to ".length))]).filter(Boolean);
console.log("printed sums:", sums.length, "e.g.", sums.find((s) => s.includes(".")));
expect(sums.length > walk.out.length && sums.every(sumsUp), "the printed bits add up: " + sums.filter((s) => !sumsUp(s)).slice(0, 3).join(" | "));

// Screenshots: start, a page with a dropped option, a forced-tail summary.
await shot("01-start.png");
const clickPath = async (labels) => evaluate(`(() => { document.getElementById('reset').click();
  for (const l of ${JSON.stringify(labels)}) { const b = [...document.querySelectorAll('#panel .choices button')].find(x => x.textContent.startsWith(l)); if (!b) return 'missing ' + l; b.click(); } return 'ok'; })()`);
const pathName = (labels) => labels.map((l) => l[0]).join("-");
console.log(await clickPath(F.shots[0]));
await shot(`02-after-${pathName(F.shots[0])}.png`);
console.log(await clickPath(F.shots[1]));
await shot(`03-after-${pathName(F.shots[1])}.png`);
console.log(await clickPath(F.layout));
await shot(`04-summary-${pathName(F.layout)}.png`);
// The beginning page (after the layout 2-4-4): pickable buttons, muted groups, the key.
const tokenPage = () => evaluate(`(() => {
  const q = (s) => [...document.querySelectorAll(s)];
  return { pick: q('#panel .tokens button').map(b => b.textContent),
    groups: q('#panel details.group').map(d => ({ cls: d.className, summary: d.querySelector('summary').textContent,
      chips: d.querySelectorAll('.chip').length, first: [...d.querySelectorAll('.chip')].slice(0, 3).map(c => c.textContent + ' | ' + c.title) })),
    key: document.querySelector('#panel .tkey')?.innerText, why: document.querySelector('#panel .why')?.innerText,
    msg: document.getElementById('msg').textContent, count: document.getElementById('count').textContent,
    slots: q('#phrase .slot').map(s => s.textContent), undo: document.getElementById('undo').disabled,
    random: document.getElementById('random').disabled };
})()`);
console.log(await clickPath(F.layout));
const before = await tokenPage();
writeFileSync(path.join(OUT, "token-page.json"), JSON.stringify(before, null, 1));
console.log("beginning page: pick", before.pick.length, "groups", before.groups.map(g => `${g.cls}:${g.chips}`).join(" "),
  "total", before.pick.length + before.groups.reduce((s, g) => s + g.chips, 0));
const dropped = spawnSync("python3", ["-c", `
import json, sys
sys.path.insert(0, ${JSON.stringify(HERE)})
import build_space_game as game
model = json.load(open(${JSON.stringify(MODEL)}))
text = [game.phrase.text_of(t) for t in model["tokens"]]
print(json.dumps([d[0] for d in game.ban_reasons(model, text)[4]]))
`], { encoding: "utf8" });
const droppedBegin = JSON.parse(dropped.stdout || "null");
const bannedGroup = before.groups.find((g) => g.cls === "group banned");
console.log("dropped beginnings (python):", JSON.stringify(droppedBegin), "| page:", JSON.stringify(bannedGroup?.first));
expect(bannedGroup && droppedBegin && bannedGroup.chips === droppedBegin.length && droppedBegin.length > 0,
  "the beginning page marks every word start dropped as offensive");
expect(bannedGroup && bannedGroup.first.every((c) => / \| .*offensive-word list/.test(c)), "each dropped word start names its list");
// Point at a token: the line under the grid says which languages' words it comes from.
const hover = async (text) => evaluate(`(() => { const b = [...document.querySelectorAll('#panel .tokens button')].find(x => x.textContent === ${JSON.stringify(text)});
  b.dispatchEvent(new MouseEvent('mouseenter')); return document.querySelector('#panel .origin').innerText; })()`);
const hoverBegin = await hover("ma");
console.log("hover ma:", hoverBegin);
expect(/^Words start with ma in (all )?\d+ languages, like /.test(hoverBegin), "pointing at a beginning shows its languages");
const links = await evaluate(`(() => ({
  origin: [...document.querySelectorAll('#panel .origin a')].map(a => [a.textContent, a.href, a.target]),
  banned: [...document.querySelectorAll('#panel details.banned .chip small a')].map(a => [a.textContent, a.href]),
  afterLeave: (() => { document.querySelector('#panel .tokens button').dispatchEvent(new MouseEvent('mouseleave'));
    return document.querySelectorAll('#panel .origin a').length; })() }))()`);
console.log("wikipedia links:", JSON.stringify(links.origin.slice(0, 3)), JSON.stringify(links.banned.slice(0, 2)), "after leaving:", links.afterLeave);
const wiki = (l) => /^https:\/\/en\.wikipedia\.org\/wiki\/\S+$/.test(l[1]);
expect(links.origin.length >= 1 && links.origin.every(wiki) && links.origin.every((l) => l[2] === "_blank"),
  "languages in the origin line link to Wikipedia in a new tab");
expect(links.banned.length === droppedBegin.length && links.banned.every(wiki), "the lists' languages on banned chips link to Wikipedia");
expect(links.afterLeave === links.origin.length, "the origin line stays after the pointer leaves, so its links can be clicked");
await evaluate(`document.querySelectorAll('#panel details.group').forEach(d => d.open = true)`);
await shot("05-beginning-page-open.png");
await evaluate(`document.querySelectorAll('#panel details.group').forEach(d => d.open = false)`);
await shot("06-beginning-page.png");
const pickToken = (text) => evaluate(`(() => { const b = [...document.querySelectorAll('#panel .tokens button')].find(x => x.textContent === ${JSON.stringify(text)}); if (!b) return 'missing ${text}'; b.click(); return 'ok'; })()`);
const summarize = (pg) => ({ pick: pg.pick.length, groups: Object.fromEntries(pg.groups.map(g => [g.cls.replace("group ", ""), g.chips])) });
// Expected counts come from the Python mirror of the compiler's rules (build_space_game.follow_groups: same
// order: on the list, banned, no vowel, a letter three times, join, clash, less).
const cases = [
  { name: `middle after re (${pathName(F.middle)})`, path: F.middle, first: "re", kind: "c" },
  { name: `ending after re (${pathName(F.layout)})`, path: F.layout, first: "re", kind: "e" },
  // The same letter three times in a row: the beginning with the most such tokens, chosen by the mirror below
  // (tables change, so a fixed beginning may drop out; the reported word was za+na+ss+sa).
  { name: `middle after the beginning with the most tripled letters (${pathName(F.middle)})`, path: F.middle,
    first: null, most: "triple", kind: "c" },
  // No vowel: the beginning without one that rules out the most middles.
  { name: `middle after the beginning with the most tokens out for no vowel (${pathName(F.middle)})`, path: F.middle,
    first: null, most: "vowel", kind: "c" },
];
const mirror = spawnSync("python3", ["-c", `
import json, sys
sys.path.insert(0, ${JSON.stringify(HERE)})
import build_space_game as game
model = json.load(open(${JSON.stringify(MODEL)}))
text = [game.phrase.text_of(t) for t in model["tokens"]]
cases = json.loads(sys.argv[1])
out = []
for c in cases:
    if c.get("most"):  # the chosen beginning with the most tokens out for this reason
        c["first"] = text[max(sorted(model["begin"], key=lambda b: text[b]),
                              key=lambda b: len(game.follow_groups(model, b, c["kind"])[c["most"]]))]
    previous = text.index(c["first"])
    groups = game.follow_groups(model, previous, c["kind"])
    out.append({"first": c["first"], "pick": len(groups.pop("pick")), "groups": {k: len(v) for k, v in groups.items() if v}})
print(json.dumps(out))
`, JSON.stringify(cases)], { encoding: "utf8" });
expect(mirror.status === 0, "python mirror of the page rules runs: " + mirror.stderr.trim().slice(-300));
JSON.parse(mirror.stdout || "[]").forEach(({ first, ...e }, i) => { cases[i].first = first; cases[i].expect = e; });
let n = 8;
for (const c of cases) {
  console.log(await clickPath(c.path), await pickToken(c.first));
  const pg = await tokenPage();
  const got = summarize(pg);
  const ok = JSON.stringify(got) === JSON.stringify(c.expect) || (got.pick === c.expect.pick && Object.keys(c.expect.groups).every(k => got.groups[k] === c.expect.groups[k]) && Object.keys(got.groups).length === Object.keys(c.expect.groups).length);
  expect(ok, `${c.name}: counts match the compiler`);
  console.log(c.name, ok ? "MATCH" : "MISMATCH", JSON.stringify(got), "total", got.pick + Object.values(got.groups).reduce((s, x) => s + x, 0));
  writeFileSync(path.join(OUT, `page-${n}.json`), JSON.stringify(pg, null, 1));
  console.log("  msg:", pg.msg.slice(0, 330));
  console.log("  key:", JSON.stringify(pg.key));
  console.log("  groups:", JSON.stringify(pg.groups.map(g => g.summary)));
  console.log("  chips:", JSON.stringify(pg.groups.map(g => g.first)));
  await shot(`${String(n).padStart(2, "0")}-${c.first}-${c.path.map(x => x[0]).join("")}.png`);
  const second = pg.pick[0];
  const hoverText = await hover(second);
  console.log("  hover", second + ":", hoverText);
  await shot(`${String(n).padStart(2, "0")}-${c.first}-hover-${second}.png`);
  expect(/in words of (all )?\d+ languages?, like |No word in the list has /.test(hoverText), `${c.name}: pointing at a token shows its languages`);
  console.log("  pick", second, await pickToken(second));
  const done = await tokenPage();
  expect(done.msg.includes(hoverText.slice(0, 40)), `${c.name}: the picked sentence says where the token comes from`);
  console.log("  after:", JSON.stringify({ msg: done.msg.slice(0, 260), slots: done.slots.slice(0, 3), pick: done.pick.length, random: done.random }));
  await evaluate(`document.getElementById('undo').click()`);
  console.log("  undo ->", (await tokenPage()).pick.length);
  n++;
}
await evaluate(`document.querySelectorAll('#panel details.group').forEach(d => d.open = true)`);
await shot("11-last-case-open.png");
// Every banned token's tooltip, on every page, must be true of the letters: "spells" and "would finish" name a term
// that ends inside this token; "the token after it" needs a token on this token's own lists that ends the term.
const bans = await evaluate(`(() => {
  const counts = {}, bad = [];
  const ids = [...BEGIN.map((t) => TABLE_TOKENS.indexOf(t)), ...Array.from({ length: 512 }, (_, i) => 512 + i)];
  for (const id of ids) for (const k of ["c", "e"]) {
    const prev = TABLE_TOKENS[id];
    const group = followPage({ k, w: 0, j: 1, n: 4, bits: tokenBits(k) }, { id, t: prev }).groups.find((g) => g.reason === "blocked");
    for (const e of group ? group.items : []) {
      const tip = group.tip(e), next = /token after it/.test(tip);
      const kind = !e.term ? "unknown" : next ? "next" : /spells/.test(tip) ? "spells" : "finish";
      counts[kind] = (counts[kind] || 0) + 1;
      const after = next && e.id >= 512 ? [...TABLE_MIDDLE[rowOf(e.id)], ...TABLE_END32[rowOf(e.id)]].map((u) => TABLE_TOKENS[u]) : [""];
      // The letters up to each place the term may end: in this token, or in a token after it.
      const ends = after.flatMap((u) => [...(next ? u : e.t)].map((_, i) => prev + (next ? e.t + u.slice(0, i + 1) : e.t.slice(0, i + 1))));
      const ok = !e.term || (/starts in the tokens before/.test(tip)
        ? ends.some((s) => e.term.endsWith(s) && e.term.length > s.length) : ends.some((s) => s.endsWith(e.term)));
      if (!ok && bad.length < 5) bad.push([prev, e.t, e.term, tip]);
    }
  }
  return { counts, bad, total: Object.values(TABLE_BANNED).reduce((s, l) => s + l.length, 0) };
})()`);
console.log("ban tooltips:", JSON.stringify(bans));
expect(bans.bad.length === 0 && bans.counts.next > 0 && Object.values(bans.counts).reduce((s, x) => s + x, 0) === bans.total,
  "every ban's tooltip is true of its letters, on every page");
// Keyboard previews: focusing an option shows a faded token; it must go when focus leaves, and on Undo.
const previews = await evaluate(`(() => {
  const $ = (i) => document.getElementById(i), n = () => document.querySelectorAll('#phrase .slot.preview').length;
  const focusThen = (selector, act) => { const b = document.querySelector(selector); b.focus(); const shown = n(); act(b); return [shown, n()]; };
  $('reset').click();
  const option = focusThen('#panel .choices button', (b) => b.blur());
  for (const l of ${JSON.stringify(F.layout)}) [...document.querySelectorAll('#panel .choices button')].find((x) => x.textContent.startsWith(l)).click();
  const token = focusThen('#panel .tokens button', (b) => b.blur());
  const undo = focusThen('#panel .tokens button', () => $('undo').click());
  return { option, token, undo };
})()`);
console.log("previews [shown, after]:", JSON.stringify(previews));
expect(Object.values(previews).every(([shown, after]) => shown > 0 && after === 0), "keyboard previews go away on blur and on Undo");
// 15: Fill randomly animates a step every 260 ms. Wait until its timer stops, then check the end state; its
// phrase joins the encoder check below.
await evaluate(`document.getElementById('reset').click(); document.getElementById('random').click();`);
const busy = await evaluate(`['random', 'undo'].map((b) => document.getElementById(b).disabled)`);
for (let i = 0; i < 150 && await evaluate(`state.timer !== null`); i++) await sleep(100);
const filled = await evaluate(`(() => { const v = phraseNumber(), $ = (i) => document.getElementById(i);
  return { phrase: layout().map((_, w) => wordText(w)).join(' '), value: v.value.toString(), bits: v.offset,
    shown: document.querySelector('#msg b.final')?.textContent, slots: [...document.querySelectorAll('#phrase .slot')].map(s => s.textContent).join('|'),
    stopped: state.timer === null, random: $('random').disabled, undo: $('undo').disabled, count: $('count').textContent }; })()`);
console.log("fill randomly:", JSON.stringify(filled), "| while filling, random and undo disabled:", JSON.stringify(busy));
expect(busy.every(Boolean), "while Fill randomly runs, it and Undo are disabled");
expect(filled.stopped && filled.random && !filled.undo && filled.count === "64", "Fill randomly ends at 64 bits, with itself off and Undo on");
expect(filled.slots.split("|").length === TOKENS && filled.slots.split("|").join("") === filled.phrase.replaceAll(" ", ""),
  `Fill randomly fills all ${TOKENS} slots with its phrase`);
// Whole phrases: drive step() to the end many times; Python checks each phrase against the reference encoder.
const runs = await evaluate(`(() => { const out = [];
  for (let r = 0; r < 200; r++) { document.getElementById('reset').click(); while (step()); render();
    const v = phraseNumber(); out.push({ phrase: layout().map((_, w) => wordText(w)).join(' '), value: v.value.toString(), bits: v.offset,
      shown: document.querySelector('#msg b.final')?.textContent, slots: [...document.querySelectorAll('#phrase .slot')].map(s => s.textContent).join('|') }); }
  return out; })()`);
runs.push(filled);
writeFileSync(path.join(OUT, "phrases.json"), JSON.stringify(runs, null, 1));
const verify = spawnSync("python3", ["-c", `
import json, sys
sys.path.insert(0, ${JSON.stringify(path.join(HERE, "..", "models"))})
import compile_phrase as phrase
model = json.load(open(${JSON.stringify(MODEL)}))
runs = json.load(open(${JSON.stringify(path.join(OUT, "phrases.json"))}))
bad = [r for r in runs if phrase.encode(model, int(r["value"])) != r["phrase"]]
print(len(runs) - len(bad), len({int(r["value"]) & (len(phrase.layouts()) - 1) for r in runs}), json.dumps(bad[:2]))
`], { encoding: "utf8" });
const [same, layouts] = verify.stdout.trim().split(" ").map(Number);
console.log("python encoder agrees:", same, "of", runs.length, "| layouts covered:", layouts, verify.stderr.trim());
expect(same === runs.length, "every game phrase equals the reference encoder's phrase for its number");
expect(runs.every((r) => r.bits === 64 && r.shown === r.phrase), "every full phrase is 64 bits and shown as built");
console.log("full phrases", runs.length, "all 64 bits:", runs.every(r => r.bits === 64), "shown == built:", runs.every(r => r.shown === r.phrase), "examples:", JSON.stringify(runs.slice(0, 4).map(r => r.phrase)));
// Click through one phrase by hand (2+4+4), a different pickable token each time; shoot the second
// word's beginning and the end.
console.log(await clickPath(F.layout));
for (let i = 0; i < TOKENS; i++) {
  const pg = await tokenPage();
  if (i === 2) { console.log("word 2 beginning page:", pg.msg.slice(0, 260), "| why:", pg.why); await shot("12-word2-beginning.png"); }
  if (!pg.pick.length) break;
  await pickToken(pg.pick[i % pg.pick.length]);
}
const fin = await tokenPage();
console.log("final:", fin.msg.slice(-700), "| buttons left:", fin.pick.length, "random disabled:", fin.random);
await shot("13-final.png");
// Example words are shown as their languages write them (onların, not onlarin). In every example on the page, the
// bold letters must fold back to the token's letters. A token can start or end inside one original letter (mæt:
// æ is "ae", the ending is "et"); then that whole letter is bold, so extra folded letters may come only from it.
const marks = await evaluate(`(() => {
  const o = origins();
  if (!o) return { error: "origins not loaded" };
  let checked = 0, original = 0, otherScript = 0;
  const bad = [], samples = [], badLatin = [], scriptSamples = [];
  const check = (packed, token, kind, before) => {
    const u = unpackOrigin(packed);
    for (const g of (u ? u.groups : []).filter((g) => g.word)) {
      const html = markWord(g.word, token, kind, before);
      const bold = (html.match(/<b>(.*)<\\/b>/) || [])[1];
      const boldLetters = [...(bold ?? "")].map((ch) => o.FOLD[ch] ?? ch);
      const folded = boldLetters.join("");
      const at = folded.indexOf(token);
      // A middle follows the previous token: right after a beginning ("^ta"), at letter 2 or later after a middle.
      const pre = [...((html.match(/<i>(.*?)<b>/) || [])[1] ?? "")].map((ch) => o.FOLD[ch] ?? ch).join("") + folded.slice(0, at);
      const placed = kind !== "c" || !before
        || (before.startsWith("^") ? pre === before.slice(1) : pre.endsWith(before) && pre.length >= before.length + 2);
      const ok = at >= 0 && at < Math.max(1, (boldLetters[0] || "").length) && placed
        && folded.length - at - token.length < Math.max(1, (boldLetters.filter((l) => l).at(-1) || "").length);
      checked += 1;
      if (!/^[a-z]+$/.test(g.word)) { original += 1; if (samples.length < 4 && kind === "c") samples.push(html); }
      if (!ok && bad.length < 5) bad.push([g.word, token, kind, bold]);
      // A word in another script also shows its a-z form, with exactly the token in bold.
      const latin = latinWord(g.word, token, kind, before);
      if (OTHER_SCRIPT.test(g.word)) {
        otherScript += 1;
        const plain = [...g.word].map((ch) => o.FOLD[ch] ?? ch).join("");
        const latinBold = (latin.match(/<b>(.*)<\\/b>/) || [])[1];
        if ((latinBold !== token || latin.replace(/<[^>]*>/g, "") !== plain) && badLatin.length < 5) badLatin.push([g.word, token, latin]);
        if (scriptSamples.length < 6 && !scriptSamples.some((x) => x[0] === [...g.word][0])) scriptSamples.push([[...g.word][0], html + " (" + latin + ")"]);
      } else if (latin && badLatin.length < 5) badLatin.push([g.word, token, "Latin word with an a-z form"]);
    }
  };
  for (const [id, packed] of Object.entries(o.BEGIN)) check(packed, TABLE_TOKENS[id], "b");
  let turkishSentence = null, scriptSentence = null;  // what the page says for a word with ı, and for a Greek word
  for (const [previous, row] of Object.entries(o.FOLLOW)) {
    const r = rowOf(Number(previous));
    row.split(" ").forEach((packed, slot) => {
      const id = slot < MIDDLE.length ? TABLE_MIDDLE[r][slot] : TABLE_END32[r][slot - MIDDLE.length];
      const kind = slot < MIDDLE.length ? "c" : "e";
      check(packed, TABLE_TOKENS[id], kind, (Number(previous) < 256 ? "^" : "") + TABLE_TOKENS[previous]);
      const u = unpackOrigin(packed);
      if (!turkishSentence && u && u.groups.some((g) => g.word && g.word.includes("ı"))) {
        turkishSentence = originSentence({ id, t: TABLE_TOKENS[id] }, kind, { id: Number(previous), t: TABLE_TOKENS[previous] })
          .replace(/<a [^>]*>|<\\/a>/g, "");
      }
      if (!scriptSentence && u && u.groups.some((g) => g.word && /\\p{Script=Greek}/u.test(g.word))) {
        scriptSentence = originSentence({ id, t: TABLE_TOKENS[id] }, kind, { id: Number(previous), t: TABLE_TOKENS[previous] })
          .replace(/<a [^>]*>|<\\/a>/g, "");
      }
    });
  }
  return { checked, original, bad, samples, turkishSentence, otherScript, badLatin, scriptSamples: scriptSamples.map((x) => x[1]),
    scriptSentence, dotless: o.EXAMPLES.split(" ").filter((w) => w.includes("ı")).length };
})()`);
console.log("original spellings:", JSON.stringify(marks));
expect(!marks.error && marks.checked > 10000 && marks.bad.length === 0, "every example's bold letters fold to its token");
expect(marks.original > 1000, "examples keep their original spelling (diacritics, other scripts)");
expect(marks.dotless > 0 && /ı/.test(marks.turkishSentence || ""), "Turkish words keep their letters (ı, not i)");
expect(marks.otherScript > 100 && marks.badLatin.length === 0, "words in other scripts show their a-z form, the token in bold");
// How these sentences look on the page: shown at the top, in the page's own fonts.
await evaluate(`(() => {
  const box = document.createElement("p");
  box.className = "check-sample";
  box.innerHTML = ${JSON.stringify([marks.scriptSentence, marks.turkishSentence].join("<br>"))};
  document.body.prepend(box);
  window.scrollTo(0, 0);
})()`);
await send("Emulation.setDeviceMetricsOverride", { width: 760, height: 260, deviceScaleFactor: 1, mobile: false });
const fullPage = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: 760, height: 260, scale: 1 } });
writeFileSync(path.join(OUT, "14-other-scripts.png"), Buffer.from(fullPage.result.data, "base64"));
console.log("screenshot", path.join(OUT, "14-other-scripts.png"));
console.log("errors", JSON.stringify(errors));
expect(errors.length === 0, "no JS errors");
ws.close();
if (failures.length) { console.error("FAILED:\n- " + failures.join("\n- ")); process.exitCode = 1; } else console.log("ALL CHECKS PASSED");
