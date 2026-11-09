// Headless check of the spaces game: walk every branch, collect end states, take screenshots.
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const OUT = process.env.OUT_DIR || path.join(process.env.TMPDIR || tmpdir(), "space-game-check");
mkdirSync(OUT, { recursive: true });
// Build first (python3 game/build_space_game.py), or point GAME_URL at a served copy.
const HERE = path.dirname(fileURLToPath(import.meta.url));
const URL_ = process.env.GAME_URL || pathToFileURL(path.join(HERE, "space-game.html")).href;
const failures = [];
const expect = (ok, what) => { if (!ok) failures.push(what); };
const PORT = 9333;
const profile = mkdtempSync(path.join(process.env.TMPDIR || tmpdir(), "chr-"));
const chrome = spawn("chromium", [
  "--headless=new", `--remote-debugging-port=${PORT}`, "--remote-debugging-address=127.0.0.1",
  `--user-data-dir=${profile}`, "--no-proxy-server", "--window-size=900,1100", "about:blank",
], { stdio: "ignore" });
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
await send("Emulation.setDeviceMetricsOverride", { width: 760, height: 900, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url: URL_ });
await sleep(1500);

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
        spare: $('spare').textContent, missing: document.querySelectorAll('.bit.missing').length,
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
expect(walk.out.length === 32, `32 layouts, got ${walk.out.length}`);
expect(walk.out.every((o) => o.count === "64" && !o.spare && !o.missing), "every layout is exactly 64 bits");

// Screenshots: start, a page with a dropped option, a forced-tail summary.
await shot("01-start.png");
const clickPath = async (labels) => evaluate(`(() => { document.getElementById('reset').click();
  for (const l of ${JSON.stringify(labels)}) { const b = [...document.querySelectorAll('#panel .choices button')].find(x => x.textContent.startsWith(l)); if (!b) return 'missing ' + l; b.click(); } return 'ok'; })()`);
console.log(await clickPath(["5 tokens"]));
await shot("02-after-5.png");
console.log(await clickPath(["3 tokens", "4 tokens"]));
await shot("03-after-3-4.png");
console.log(await clickPath(["2 tokens", "4 tokens", "5 tokens"]));
await shot("04-summary-2-4-5.png");
// The beginning page (after the layout 2-4-5): pickable buttons, muted groups, the key.
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
console.log(await clickPath(["2 tokens", "4 tokens", "5 tokens"]));
const before = await tokenPage();
writeFileSync(path.join(OUT, "token-page.json"), JSON.stringify(before, null, 1));
console.log("beginning page: pick", before.pick.length, "groups", before.groups.map(g => `${g.cls}:${g.chips}`).join(" "),
  "total", before.pick.length + before.groups.reduce((s, g) => s + g.chips, 0));
await evaluate(`document.querySelectorAll('#panel details.group').forEach(d => d.open = true)`);
await shot("05-beginning-page-open.png");
await evaluate(`document.querySelectorAll('#panel details.group').forEach(d => d.open = false)`);
await shot("06-beginning-page.png");
const pickToken = (text) => evaluate(`(() => { const b = [...document.querySelectorAll('#panel .tokens button')].find(x => x.textContent === ${JSON.stringify(text)}); if (!b) return 'missing ${text}'; b.click(); return 'ok'; })()`);
const summarize = (pg) => ({ pick: pg.pick.length, groups: Object.fromEntries(pg.groups.map(g => [g.cls.replace("group ", ""), g.chips])) });
// Expected counts come from the Python mirror of the compiler's rules (build_space_game.follow_groups: same
// order: on the list, banned, no vowel, join, clash, less). The 16-ending after st shows all six reasons.
const cases = [
  { name: "middle after re (3+3+5)", path: ["3 tokens", "3 tokens", "5 tokens"], first: "re", kind: "c", size: 32 },
  { name: "32-ending after re (2+4+5)", path: ["2 tokens", "4 tokens", "5 tokens"], first: "re", kind: "e", size: 32 },
  { name: "16-ending after st (2+3+3+3)", path: ["2 tokens", "3 tokens", "3 tokens"], first: "st", kind: "e", size: 16 },
];
const mirror = spawnSync("python3", ["-c", `
import json, sys
sys.path.insert(0, ${JSON.stringify(HERE)})
import build_space_game as game
model = json.load(open(${JSON.stringify(path.join(HERE, "..", "models", "phrase_model.json"))}))
text = [game.phrase.text_of(t) for t in model["tokens"]]
cases = json.loads(sys.argv[1])
out = []
for c in cases:
    groups = game.follow_groups(model, text.index(c["first"]), c["kind"], c["size"])
    out.append({"pick": len(groups.pop("pick")), "groups": {k: len(v) for k, v in groups.items() if v}})
print(json.dumps(out))
`, JSON.stringify(cases)], { encoding: "utf8" });
expect(mirror.status === 0, "python mirror of the page rules runs: " + mirror.stderr.trim().slice(-300));
JSON.parse(mirror.stdout || "[]").forEach((e, i) => { cases[i].expect = e; });
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
  console.log("  pick", second, await pickToken(second));
  const done = await tokenPage();
  console.log("  after:", JSON.stringify({ msg: done.msg.slice(0, 260), slots: done.slots.slice(0, 3), pick: done.pick.length, random: done.random }));
  await evaluate(`document.getElementById('undo').click()`);
  console.log("  undo ->", (await tokenPage()).pick.length);
  n++;
}
await evaluate(`document.querySelectorAll('#panel details.group').forEach(d => d.open = true)`);
await shot("11-st-open.png");
// Whole phrases: drive step() to the end many times; Python checks each phrase against the reference encoder.
const runs = await evaluate(`(() => { const out = [];
  for (let r = 0; r < 200; r++) { document.getElementById('reset').click(); while (step()); render();
    const v = phraseNumber(); out.push({ phrase: layout().map((_, w) => wordText(w)).join(' '), value: v.value.toString(), bits: v.offset,
      shown: document.querySelector('#msg b.final')?.textContent, slots: [...document.querySelectorAll('#phrase .slot')].map(s => s.textContent).join('|') }); }
  return out; })()`);
writeFileSync(path.join(OUT, "phrases.json"), JSON.stringify(runs, null, 1));
const verify = spawnSync("python3", ["-c", `
import json, sys
sys.path.insert(0, ${JSON.stringify(path.join(HERE, "..", "models"))})
import compile_phrase as phrase
model = json.load(open(${JSON.stringify(path.join(HERE, "..", "models", "phrase_model.json"))}))
runs = json.load(open(${JSON.stringify(path.join(OUT, "phrases.json"))}))
bad = [r for r in runs if phrase.encode(model, int(r["value"])) != r["phrase"]]
print(len(runs) - len(bad), len({int(r["value"]) & 31 for r in runs}), json.dumps(bad[:2]))
`], { encoding: "utf8" });
const [same, layouts] = verify.stdout.trim().split(" ").map(Number);
console.log("python encoder agrees:", same, "of", runs.length, "| layouts covered:", layouts, verify.stderr.trim());
expect(same === runs.length, "every game phrase equals the reference encoder's phrase for its number");
expect(runs.every((r) => r.bits === 64 && r.shown === r.phrase), "every full phrase is 64 bits and shown as built");
console.log("full phrases", runs.length, "all 64 bits:", runs.every(r => r.bits === 64), "shown == built:", runs.every(r => r.shown === r.phrase), "examples:", JSON.stringify(runs.slice(0, 4).map(r => r.phrase)));
// Click through one phrase by hand: 2+4+5, first pickable token each time; shoot the second word's beginning and the end.
console.log(await clickPath(["2 tokens", "4 tokens", "5 tokens"]));
for (let i = 0; i < 11; i++) {
  const pg = await tokenPage();
  if (i === 2) { console.log("word 2 beginning page:", pg.msg.slice(0, 260), "| why:", pg.why); await shot("12-word2-beginning.png"); }
  if (!pg.pick.length) break;
  await pickToken(pg.pick[i % pg.pick.length]);
}
const fin = await tokenPage();
console.log("final:", fin.msg.slice(-700), "| buttons left:", fin.pick.length, "random disabled:", fin.random);
await shot("13-final.png");
// Fill randomly runs to completion (through the beginning page)
await evaluate(`document.getElementById('reset').click(); document.getElementById('random').click();`);
await sleep(3000);
console.log("random:", await evaluate(`document.getElementById('formula').textContent`),
  JSON.stringify((await tokenPage()).slots), (await tokenPage()).random);
console.log("errors", JSON.stringify(errors));
expect(errors.length === 0, "no JS errors");
ws.close();
chrome.kill();
if (failures.length) { console.error("FAILED:\n- " + failures.join("\n- ")); process.exitCode = 1; } else console.log("ALL CHECKS PASSED");
