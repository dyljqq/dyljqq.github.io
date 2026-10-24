#!/usr/bin/env node
// Browser integration checks for assets/analytics/firebase-web-v1.js.
// Uses the installed Chrome + Node 22's built-in WebSocket; no dependencies.
//   /Users/polarisdev/.nvm/versions/node/v22.23.1/bin/node tools/test_analytics.mjs
import { createServer } from "node:http";
import { readFileSync, statSync, mkdtempSync, rmSync } from "node:fs";
import { spawn, execFileSync } from "node:child_process";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const APP_SDK = "https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js";
const ANALYTICS_SDK = "https://www.gstatic.com/firebasejs/12.4.0/firebase-analytics.js";
const failures = [];
let checks = 0;
const assert = (condition, message) => {
  checks++;
  if (!condition) failures.push(message);
};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

if (!statSync(CHROME).isFile()) throw new Error(`Chrome not found: ${CHROME}`);

const MIME = {
  ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".xml": "application/xml; charset=utf-8",
  ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
  ".webp": "image/webp", ".ico": "image/x-icon", ".woff2": "font/woff2"
};
const server = createServer((req, res) => {
  let path;
  try { path = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname); }
  catch { res.writeHead(400).end(); return; }
  if (path.endsWith("/")) path += "index.html";
  const file = resolve(ROOT, `.${path}`);
  if (file !== ROOT && !file.startsWith(ROOT + sep)) { res.writeHead(403).end(); return; }
  try {
    const body = readFileSync(file);
    res.writeHead(200, { "content-type": MIME[extname(file)] || "application/octet-stream", "cache-control": "no-store" });
    res.end(body);
  } catch { res.writeHead(404).end("Not found"); }
});
server.listen(0, "127.0.0.1");
await new Promise((resolve) => server.once("listening", resolve));
const base = `http://127.0.0.1:${server.address().port}`;
const profile = mkdtempSync(join(tmpdir(), "goka-analytics-test-"));
const debugPort = 10300 + Math.floor(Math.random() * 500);
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--disable-background-networking", "--disable-features=MediaRouter,OptimizationHints,Translate",
  `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });
let ws;

try {
  // Sitemap-wide metadata/script contract, checked against files served by this test server.
  const paths = execFileSync("python3", [join(ROOT, "tools/sitemap.py")], { encoding: "utf8" }).trim().split(/\r?\n/);
  const invalidPages = [];
  for (const path of paths) {
    const filePath = path.endsWith("/") ? `${path}index.html` : path;
    let html;
    try { html = readFileSync(resolve(ROOT, `.${filePath}`), "utf8"); }
    catch { invalidPages.push(`${path}: file missing`); continue; }
    const metas = html.match(/<meta\s+name=["']gk-analytics["'][^>]*>/gi) || [];
    const scripts = html.match(/<script\s+defer\s+src=["']\/assets\/analytics\/firebase-web-v1\.js["']\s*>\s*<\/script>/gi) || [];
    if (metas.length !== 1 || scripts.length !== 1) invalidPages.push(`${path}: metadata=${metas.length}, script=${scripts.length}`);
  }
  assert(paths.length > 0 && invalidPages.length === 0,
    `sitemap HTML contract (${paths.length} pages): ${invalidPages.slice(0, 5).join("; ") || "passed"}`);

  let debuggerUrl;
  for (let i = 0; i < 150; i++) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${debugPort}/json/list`)).json();
      const target = targets.find((t) => t.type === "page");
      if (target) { debuggerUrl = target.webSocketDebuggerUrl; break; }
    } catch {}
    await sleep(200);
  }
  if (!debuggerUrl) throw new Error("Chrome did not start");
  ws = new WebSocket(debuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });
  let seq = 0;
  const pending = new Map();
  const listeners = new Map();
  ws.addEventListener("message", ({ data }) => {
    const message = JSON.parse(data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message)); else resolve(message);
    }
    for (const fn of listeners.get(message.method) || []) fn(message.params);
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); } }, 15000).unref();
  });
  const on = (method, fn) => {
    if (!listeners.has(method)) listeners.set(method, new Set());
    listeners.get(method).add(fn);
    return () => listeners.get(method).delete(fn);
  };
  let failSdk = false;
  const mockModules = new Map([
    [APP_SDK, `export function getApps(){return []} export function initializeApp(config,name){return {config,name}}`],
    [ANALYTICS_SDK, `export async function isSupported(){return true}
      export function initializeAnalytics(app,options){window.__analyticsInit={app,options};return {app}}
      export function logEvent(_analytics,name,params){(window.__analyticsEvents??=[]).push({name,params})}`]
  ]);
  on("Fetch.requestPaused", async ({ requestId, request }) => {
    const source = mockModules.get(request.url);
    try {
      if (source && failSdk) {
        await send("Fetch.fulfillRequest", { requestId, responseCode: 503,
          responseHeaders: [{ name: "Content-Type", value: "text/javascript" }], body: "" });
      } else if (source) {
        await send("Fetch.fulfillRequest", { requestId, responseCode: 200,
          responseHeaders: [{ name: "Content-Type", value: "text/javascript; charset=utf-8" },
            { name: "Access-Control-Allow-Origin", value: "*" }], body: Buffer.from(source).toString("base64") });
      } else await send("Fetch.continueRequest", { requestId });
    } catch (error) { console.error(`Firebase mock failed for ${request.url}: ${error.message}`); }
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Fetch.enable", { patterns: [APP_SDK, ANALYTICS_SDK].map((urlPattern) => ({ urlPattern, requestStage: "Request" })) });

  const evaluate = async (expression) => {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.result.exceptionDetails) throw new Error(result.result.exceptionDetails.text || "page script exception");
    return result.result.result?.value;
  };
  async function navigate(path) {
    const loaded = new Promise((resolve) => {
      const remove = on("Page.loadEventFired", () => { remove(); resolve(); });
      setTimeout(() => { remove(); resolve(); }, 20000).unref();
    });
    await send("Page.navigate", { url: base + path });
    await loaded;
    await sleep(250);
  }
  async function waitFor(expression, description) {
    for (let i = 0; i < 100; i++) {
      if (await evaluate(expression)) return;
      await sleep(50);
    }
    throw new Error(`Timed out waiting for ${description}`);
  }
  const events = () => evaluate("window.__analyticsEvents || []");
  const clearEvents = () => evaluate("window.__analyticsEvents = []");
  async function dispatch(selector, targetSelector = selector, click = true) {
    return evaluate(`(() => { const el=document.querySelector(${JSON.stringify(selector)}); if(!el)return false;
      const target=el.querySelector(${JSON.stringify(targetSelector)}) || el;
      if (${click}) { const cancel=e=>e.preventDefault(); document.addEventListener('click',cancel,{capture:true,once:true});
        target.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window})); }
      return true; })()`);
  }
  async function eventCount(name) { return (await events()).filter((e) => e.name === name).length; }

  // Local preview mode is intentionally inert without the explicit debug query.
  failSdk = false;
  await navigate("/");
  await sleep(500);
  const localState = await evaluate("({started:!!window.__gkAnalyticsStarted, initialized:!!window.__analyticsInit, events:window.__analyticsEvents||[]})");
  assert(localState.started && !localState.initialized && localState.events.length === 0,
    "non-production local visit should not initialize analytics");

  // App landing page has real header, hero SVG CTA and end CTA placements.
  await navigate("/beforego/?analytics_debug=1");
  await waitFor("window.__analyticsInit && (window.__analyticsEvents||[]).some(e=>e.name==='page_view')", "Firebase stubs and initial page_view");
  let current = await events();
  assert(current.filter((e) => e.name === "page_view").length === 1, "one page_view on initial load");
  assert(current.some((e) => e.name === "app_store_impression" && e.params.target_app === "beforego"),
    "visible owned store links emit an impression");
  const init = await evaluate("window.__analyticsInit");
  assert(init.app?.name === "goka-web" && init.options?.config?.send_page_view === false &&
    init.options?.config?.allow_google_signals === false && init.options?.config?.allow_ad_personalization_signals === false,
    "Firebase analytics initialized with privacy/page-view config");
  const ctas = [
    ["header .header-download", "header", "header"],
    [".hero a[href*='apps.apple.com']", "svg path", "hero"],
    [".end a[href*='apps.apple.com']", "svg path", "end"]
  ];
  for (const [selector, child, section] of ctas) {
    await clearEvents();
    assert(await dispatch(selector, child), `${section} App Store target exists`);
    await sleep(100);
    current = await events();
    const clicks = current.filter((e) => e.name === "app_store_click");
    assert(clicks.length === 1 && clicks[0].params.section === section && clicks[0].params.app_store_id === "6786561175",
      `${section} App Store click emits one attributed app_store_click (got ${JSON.stringify(current)})`);
    assert(current.every((e) => e.name !== "button_click"), `${section} App Store click is not duplicated as button_click`);
  }

  // Footer app listing is classified from the page's owned app map; developer profile is not an app.
  await navigate("/?analytics_debug=1");
  await waitFor("window.__analyticsInit && (window.__analyticsEvents||[]).some(e=>e.name==='page_view')", "home page analytics");
  await clearEvents();
  assert(await dispatch("footer a.gk-foot-app[href*='apps.apple.com']"), "footer App Store link exists");
  await sleep(80);
  current = await events();
  const footerClick = current.filter((e) => e.name === "app_store_click");
  assert(footerClick.length === 1 && footerClick[0].params.target_app === "citu" && footerClick[0].params.section === "footer",
    `footer-owned app is recognized as an app_store_click (got ${JSON.stringify(current)})`);
  const developerLink = await evaluate("Array.from(document.querySelectorAll('a[href*=" + JSON.stringify("apps.apple.com/developer/") + "]')).map(a=>a.href)[0] || ''");
  if (developerLink) {
    await clearEvents();
    await dispatch("a[href*='apps.apple.com/developer/']");
    current = await events();
    assert(current.some((e) => e.name === "outbound_click") && !current.some((e) => e.name === "app_store_click" || e.name === "competitor_store_click"),
      `developer directory link is an outbound link, not an app/competitor store click (got ${JSON.stringify(current)})`);
  } else assert(false, "developer directory link exists for classification check");

  // Sensitive query strings must not enter page_location or event payloads.
  const sensitive = "/tools/days-until-halloween/?analytics_debug=1&name=SensitiveEmail%40example.com&share=https%3A%2F%2Fexample.com%2Fprivate%3Ftoken%3Dsecret";
  await navigate(sensitive);
  await waitFor("window.__analyticsInit && (window.__analyticsEvents||[]).some(e=>e.name==='page_view')", "tool page analytics");
  current = await events();
  const serialized = JSON.stringify({ init: await evaluate("window.__analyticsInit"), events: current });
  assert(!serialized.includes("SensitiveEmail") && !serialized.includes("example.com/private") && !serialized.includes("token"),
    "share/free-text query values are excluded from analytics payloads");

  // Language details and language links report state/category without values.
  await clearEvents();
  assert(await evaluate("(() => { const s=document.querySelector('details.lang-switch > summary'); if(!s)return false; s.click(); return true; })()"), "language disclosure exists");
  await sleep(80);
  current = await events();
  assert(current.some((e) => e.name === "content_toggle" && e.params.expanded === true), `language menu expansion is recorded (got ${JSON.stringify(current)})`);
  await clearEvents();
  await dispatch("details.lang-switch a[hreflang='ja']");
  current = await events();
  assert(current.some((e) => e.name === "language_switch" && e.params.target_language === "ja"), `language link reports target language (got ${JSON.stringify(current)})`);

  // A generated packing list uses native form/change/submit and creates checkbox controls.
  await navigate("/tools/disney-world-packing-list/?analytics_debug=1");
  await waitFor("window.__analyticsInit && (window.__analyticsEvents||[]).some(e=>e.name==='page_view')", "dynamic tool analytics");
  await clearEvents();
  await evaluate(`(() => { const form=document.querySelector('#pack'); const select=form.querySelector('[name="type"]');
    document.activeElement?.blur?.(); select.focus(); select.dispatchEvent(new FocusEvent('focusin',{bubbles:true}));
    select.value='toddler'; select.dispatchEvent(new Event('change',{bubbles:true}));
    form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})); return document.querySelectorAll('#pack-out input[type="checkbox"]').length; })()`);
  await sleep(80);
  current = await events();
  const formEvents = current.filter((e) => ["form_start", "form_submit", "control_change"].includes(e.name));
  assert(formEvents.some((e) => e.name === "form_start") && formEvents.some((e) => e.name === "form_submit") && formEvents.some((e) => e.name === "control_change"),
    `tool form focus, submit, and categorical changes are recorded (got ${JSON.stringify(current)})`);
  assert(formEvents.every((e) => !("value" in e.params) && !("checked" in e.params) && !("name" in e.params)),
    "form analytics omit form values, checked state, and field names");
  const generatedCount = await evaluate("document.querySelectorAll('#pack-out input[type=checkbox]').length");
  assert(generatedCount > 0, "tool submit generated interactive checklist controls");
  await evaluate("(() => { const box=document.querySelector('#pack-out input[type=checkbox]'); box.checked=true; box.dispatchEvent(new Event('change',{bubbles:true})); })()");
  current = await events();
  const changed = current.filter((e) => e.name === "control_change");
  assert(changed.length >= 2 && changed.every((e) => !JSON.stringify(e.params).includes("checked") && !JSON.stringify(e.params).includes("Passport")),
    "dynamically generated control changes reveal no checklist content/state");

  // No match means a competitor store page; expected owned-app links never take this branch.
  await navigate("/tools/best-countdown-widget-apps-iphone/?analytics_debug=1");
  await waitFor("window.__analyticsInit && (window.__analyticsEvents||[]).some(e=>e.name==='page_view')", "comparison page analytics");
  const competitorTarget = await evaluate(`Array.from(document.querySelectorAll('a[href*="apps.apple.com"]')).find(a=>!Object.prototype.hasOwnProperty.call(JSON.parse(document.querySelector('meta[name="gk-analytics"]').content).apps, new URL(a.href).pathname.match(/id(\\d+)/)?.[1]||''))?.outerHTML || ''`);
  if (competitorTarget) {
    const competitorSelector = await evaluate(`(() => { const a=Array.from(document.querySelectorAll('a[href*="apps.apple.com"]')).find(x=>!Object.prototype.hasOwnProperty.call(JSON.parse(document.querySelector('meta[name="gk-analytics"]').content).apps, new URL(x.href).pathname.match(/id(\\d+)/)?.[1]||'')); if(!a)return ''; a.id='analytics-competitor-target'; return a.id; })()`);
    await clearEvents();
    await dispatch(`#${competitorSelector}`);
    current = await events();
    assert(current.some((e) => e.name === "competitor_store_click" && e.params.target_app === "competitor") &&
      !current.some((e) => e.name === "app_store_click"), "unknown App Store listing is isolated as competitor click");
  } else assert(false, "comparison page contains an unknown App Store listing");

  // Firebase import failure must be contained by the production script's catch handler.
  failSdk = true;
  await navigate("/tools/invoice-template/?analytics_debug=1&sdk_fail=1");
  await sleep(400);
  assert(!await evaluate("!!window.__analyticsInit"), "SDK import failure does not initialize analytics");
  const stillUsable = await evaluate(`(() => { const before=document.querySelectorAll('#invoice-items [data-item]').length;
    document.querySelector('#add-invoice-item').click(); return document.querySelectorAll('#invoice-items [data-item]').length === before+1; })()`);
  assert(stillUsable, "tool remains interactive when the Firebase module import fails");
  failSdk = false;

  if (failures.length) {
    console.error(`Analytics integration: ${failures.length}/${checks} checks failed`);
    for (const failure of failures) console.error(`- ${failure}`);
    process.exitCode = 1;
  } else console.log(`Analytics integration: ${checks} checks passed (${paths.length} sitemap pages, Chrome CDP Firebase stubs)`);
} finally {
  try { ws?.close(); } catch {}
  chrome.kill("SIGTERM");
  server.close();
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
