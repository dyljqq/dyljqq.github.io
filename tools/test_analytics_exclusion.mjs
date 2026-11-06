#!/usr/bin/env node
// Fully offline regression checks: SDK imports are replaced only inside this VM.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const source = readFileSync(new URL("../assets/analytics/firebase-web-v4.js", import.meta.url), "utf8");
const imports = source.match(/import\("https:\/\/www\.gstatic\.com\/firebasejs\/12\.4\.0\/firebase-(?:app|analytics)\.js"\)/g);
assert.equal(imports.length, 2);
const executable = source.replace(/\bimport\(/g, "mockImport(");
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
}
function visit({ search = "", storage = new Map(), webdriver = false, blockedStorage = false,
  quotaExceeded = false,
  importsReady = Promise.resolve(), supportReady = Promise.resolve(true) } = {}) {
  const events = [], requests = [], initialized = [];
  const listeners = new Map();
  const addEventListener = (name, callback) => {
    if (!listeners.has(name)) listeners.set(name, []);
    listeners.get(name).push(callback);
  };
  const dispatch = (name, event) => listeners.get(name)?.forEach(callback => callback(event));
  const button = {
    tagName: "BUTTON", id: "restore-button", dataset: {}, matches: () => false,
    closest: selector => selector.startsWith("a[href]") ? button : null
  };
  const location = new URL("https://beforego.art/countdown/" + search);
  const sdk = {
    getApps: () => [], initializeApp: (_config, name) => ({ name }),
    isSupported: () => supportReady,
    initializeAnalytics: (app, options) => { initialized.push({ app, options }); return {}; },
    logEvent: (_analytics, name, params) => events.push({ name, params })
  };
  const context = {
    URL, URLSearchParams, location, navigator: { webdriver },
    document: {
      querySelector: () => ({ content: JSON.stringify({ page_type: "product", page_app: "countdown", apps: {} }) }),
      querySelectorAll: () => [], documentElement: { lang: "en" },
      title: "Countdown", referrer: "", addEventListener
    },
    localStorage: Object.fromEntries(["getItem", "setItem", "removeItem"].map(method => [method, (key, value) => {
      if (blockedStorage) throw new Error("Storage disabled");
      if (quotaExceeded && method === "setItem") throw new Error("QuotaExceededError");
      if (method === "getItem") return storage.get(key) ?? null;
      if (method === "setItem") storage.set(key, value);
      else if (method === "removeItem") storage.delete(key);
    }])),
    addEventListener,
    mockImport: async url => { requests.push(url); await importsReady; return sdk; }
  };
  context.window = context;
  vm.runInNewContext(executable, context);
  return { events, requests, initialized, context, storage, listeners,
    show: () => dispatch("pageshow", { persisted: false }),
    restore: () => dispatch("pageshow", { persisted: true }),
    click: () => dispatch("click", { type: "click", target: button }) };
}
let checks = 0;
function silent(result, noImport = true) {
  assert.equal(result.events.length, 0);
  assert.equal(result.initialized.length, 0);
  if (noImport) assert.equal(result.requests.length, 0);
  checks++;
}

for (const search of ["", "?analytics_debug=1", "?internal=0&analytics_debug=1"]) {
  const result = visit({ search, webdriver: true });
  await tick(); silent(result);
}
const storage = new Map();
let result = visit({ search: "?internal=1&analytics_debug=1", storage });
await tick(); silent(result); assert.equal(storage.get("gk_analytics_internal"), "1");
result = visit({ storage }); await tick(); silent(result);
result = visit({ search: "?internal=0", storage }); await tick();
assert.equal(storage.has("gk_analytics_internal"), false);
assert.equal(result.events.filter(e => e.name === "page_view").length, 1); checks++;
assert.equal(result.initialized[0].options.config.send_page_view, false);
result.restore(); assert.equal(result.events.length, 2); checks++;
result = visit({ search: "?internal=1", blockedStorage: true }); await tick(); silent(result);
result = visit({ blockedStorage: true }); await tick();
assert.equal(result.events.length, 1); checks++;

// A cached page that skipped startup can become a normal visit after a separate
// page clears the marker. Its old internal=1 query must not set the marker again.
for (const search of ["?internal=1", ""]) {
  const storage = new Map(search ? [] : [["gk_analytics_internal", "1"]]);
  const cached = visit({ search, storage });
  await tick(); cached.click(); cached.show(); cached.restore(); await tick(); silent(cached);
  const clearing = visit({ search: "?internal=0", storage });
  await tick();
  assert.equal(clearing.events.filter(e => e.name === "page_view").length, 1);
  cached.show(); await tick(); silent(cached);
  cached.restore(); cached.click(); await tick();
  assert.equal(storage.has("gk_analytics_internal"), false);
  assert.deepEqual(cached.events.map(e => e.name), ["page_view", "button_click"]);
  assert.equal(cached.events[1].params.control_id, "restore-button");
  assert.equal(cached.initialized.length, 1);
  assert.equal(cached.requests.length, 2); checks++;
  cached.restore(); cached.click(); await tick();
  assert.deepEqual(cached.events.map(e => e.name), ["page_view", "button_click", "page_view", "button_click"]);
  assert.equal(cached.initialized.length, 1);
  assert.equal(cached.requests.length, 2); checks++;
}

// Clearing persistence never permits webdriver traffic to resume from BFCache.
result = visit({ search: "?internal=1", webdriver: true });
visit({ search: "?internal=0", storage: result.storage });
result.restore(); result.click(); await tick(); silent(result);
// A blocked store cannot confirm that the original per-page exclusion was cleared.
result = visit({ search: "?internal=1", blockedStorage: true });
result.restore(); result.click(); await tick(); silent(result);

// Full storage can still be read. An unsuccessful internal=1 write must remain
// excluded on restoration even though reading the absent marker succeeds.
const fullStorage = new Map();
result = visit({ search: "?internal=1", storage: fullStorage, quotaExceeded: true });
await tick(); silent(result);
assert.equal(fullStorage.has("gk_analytics_internal"), false);
result.restore(); result.click(); await tick(); silent(result);
result.restore(); result.click(); await tick(); silent(result);
const explicitClear = visit({ search: "?internal=0", storage: fullStorage, quotaExceeded: true });
await tick(); explicitClear.click();
assert.deepEqual(explicitClear.events.map(e => e.name), ["page_view", "button_click"]); checks++;

// Restored startup must retain the same asynchronous exclusion guards.
for (const phase of ["imports", "support"]) {
  const delay = deferred();
  const options = phase === "imports" ? { importsReady: delay.promise } : { supportReady: delay.promise };
  const cached = visit({ ...options, search: "?internal=1" });
  await tick(); silent(cached);
  visit({ search: "?internal=0", storage: cached.storage });
  cached.restore(); cached.click(); await tick();
  cached.storage.set("gk_analytics_internal", "1");
  delay.resolve(true); await tick(); silent(cached, false);
  const listenerCounts = [...cached.listeners].map(([name, callbacks]) => [name, callbacks.length]);
  const clearing = visit({ search: "?internal=0", storage: cached.storage });
  await tick();
  assert.equal(clearing.events.filter(e => e.name === "page_view").length, 1);
  cached.restore(); cached.click(); await tick();
  assert.deepEqual(cached.events.map(e => e.name), ["page_view", "button_click"]);
  assert.equal(cached.initialized.length, 1);
  assert.equal(cached.requests.length, 4);
  assert.deepEqual([...cached.listeners].map(([name, callbacks]) => [name, callbacks.length]), listenerCounts); checks++;
  cached.restore(); cached.click(); await tick();
  assert.deepEqual(cached.events.map(e => e.name), ["page_view", "button_click", "page_view", "button_click"]);
  assert.equal(cached.initialized.length, 1);
  assert.equal(cached.requests.length, 4);
  assert.deepEqual([...cached.listeners].map(([name, callbacks]) => [name, callbacks.length]), listenerCounts); checks++;
}

// Another tab can exclude this browser while imports or support detection are pending.
for (const phase of ["imports", "support"]) {
  const delay = deferred();
  const result = visit(phase === "imports" ? { importsReady: delay.promise } : { supportReady: delay.promise });
  await tick();
  result.storage.set("gk_analytics_internal", "1");
  delay.resolve(true); await tick(); silent(result, false);
  visit({ search: "?internal=0", storage: result.storage });
  result.restore(); result.click(); await tick();
  assert.deepEqual(result.events.map(e => e.name), ["page_view", "button_click"]);
  assert.equal(result.initialized.length, 1);
  assert.equal(result.requests.length, 4); checks++;
}
// The webdriver property may change while SDK work is pending too.
const delay = deferred();
result = visit({ supportReady: delay.promise }); await tick();
result.context.navigator.webdriver = true; delay.resolve(true); await tick(); silent(result, false);

// Event handlers and BFCache restores recheck exclusion after initialization.
result = visit(); await tick();
assert.deepEqual(result.events.map(e => e.name), ["page_view"]);
result.click(); result.show();
assert.deepEqual(result.events.map(e => e.name), ["page_view", "button_click"]);
result.restore();
assert.deepEqual(result.events.map(e => e.name), ["page_view", "button_click", "page_view"]);
assert.equal(result.initialized.length, 1); checks++;
result.events.length = 0;
result.storage.set("gk_analytics_internal", "1");
result.restore(); result.click(); assert.equal(result.events.length, 0); checks++;
result.storage.delete("gk_analytics_internal");
result.context.navigator.webdriver = true;
result.restore(); result.click(); assert.equal(result.events.length, 0); checks++;
console.log(`Analytics exclusion: ${checks} checks passed (offline VM, mocked SDK imports only)`);
