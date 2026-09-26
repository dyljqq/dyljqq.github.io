#!/usr/bin/env node
// 手机端渲染检查：真实 375×812 手机视口（CDP 设备模拟，不是缩小窗口——桌面 Chrome 最小窗口约 500px，截图会骗人）。
//   node tools/check_mobile.mjs <base-url> <path> [<path> ...]
// 每页检查：
//   1. 页面横向溢出：document.documentElement.scrollWidth 必须 == 375
//   2. 按钮 / 链接按钮高度异常（>80px）——09-26 苹果图标没限尺寸把按钮撑成 240px 高
//   3. 按钮里的 svg 超过 40px
//   4. 页头：每个链接 / 语言切换必须完整落在视口内（09-26 评审：德语导航挤成 3 行、第一行被顶到 top=-16；西语导航右侧被裁成「CONTAC」）
// 有问题退出码 1。只依赖 Node 22 自带的 WebSocket 和本机 Chrome。
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const [base, ...paths] = process.argv.slice(2);
if (!base || !paths.length) { console.error("usage: check_mobile.mjs <base-url> <path>..."); process.exit(2); }

const profile = mkdtempSync(join(tmpdir(), "goka-check-"));
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function wsUrl() {
  for (let i = 0; i < 150; i++) {   // Chrome 冷启动可能要 5 秒以上，最多等 30 秒
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find((t) => t.type === "page");
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(200);
  }
  throw new Error("Chrome 没起来");
}

const ws = new WebSocket(await wsUrl());
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let seq = 0; const pending = new Map(); const waiters = [];
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method) waiters.filter((w) => w.method === m.method).forEach((w) => { w.resolve(m); waiters.splice(waiters.indexOf(w), 1); });
});
const send = (method, params = {}) => new Promise((res) => { const id = ++seq; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
const once = (method, ms = 15000) => new Promise((resolve) => { waiters.push({ method, resolve }); setTimeout(() => resolve(null), ms); });

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 375, height: 812, deviceScaleFactor: 3, mobile: true });
await send("Emulation.setTouchEmulationEnabled", { enabled: true });

const PROBE = `(() => {
  const vw = 375, out = { scrollWidth: document.documentElement.scrollWidth, vw, tall: [], bigsvg: [], header: [] };  // 固定比 375：手机模拟下内容过宽时浏览器会自动缩放、innerWidth 跟着变大，拿它比会漏报
  for (const el of document.querySelectorAll('a.btn, a.cta, a.get, button, .btn, .cta')) {
    const r = el.getBoundingClientRect();
    if (r.height > 80) out.tall.push((el.className || el.tagName) + ' ' + Math.round(r.height) + 'px: ' + el.textContent.trim().slice(0, 40));
    for (const s of el.querySelectorAll('svg')) { const b = s.getBoundingClientRect(); if (b.width > 40 || b.height > 40) out.bigsvg.push(Math.round(b.width) + 'x' + Math.round(b.height) + ' in ' + el.textContent.trim().slice(0, 30)); }
  }
  const hd = document.querySelector('header');
  if (hd) for (const el of hd.querySelectorAll('a, summary')) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    if (r.top < 0 || r.left < 0 || r.right > vw + 0.5) out.header.push(el.textContent.trim().slice(0, 24) + ' @' + Math.round(r.left) + ',' + Math.round(r.top) + '→' + Math.round(r.right));
  }
  return JSON.stringify(out);
})()`;

let failed = 0;
for (const p of paths) {
  const loaded = once("Page.loadEventFired");
  await send("Page.navigate", { url: base.replace(/\/$/, "") + p });
  await loaded; await sleep(400);
  const r = await send("Runtime.evaluate", { expression: PROBE, returnByValue: true });
  const o = JSON.parse(r.result.result.value);
  const bad = [];
  if (o.scrollWidth > o.vw) bad.push(`横向溢出 scrollWidth=${o.scrollWidth} > ${o.vw}`);
  if (o.tall.length) bad.push(`按钮过高: ${o.tall.slice(0, 3).join(" | ")}`);
  if (o.bigsvg.length) bad.push(`按钮里图标过大: ${o.bigsvg.slice(0, 3).join(" | ")}`);
  if (o.header.length) bad.push(`页头元素出了视口: ${o.header.slice(0, 4).join(" | ")}`);
  if (bad.length) { failed++; console.log(`✗ ${p}\n    ${bad.join("\n    ")}`); }
}
console.log(`手机端检查 ${paths.length} 页，${failed ? `${failed} 页有问题` : "全部通过"}`);
ws.close(); chrome.kill(); try { rmSync(profile, { recursive: true, force: true }); } catch {}
process.exit(failed ? 1 : 0);
