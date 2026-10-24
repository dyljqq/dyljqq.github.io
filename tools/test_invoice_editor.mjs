#!/usr/bin/env node
// Real-browser contract checks for the English invoice editor. Node 22 + local Chrome only.
//   node tools/test_invoice_editor.mjs
// Optional screenshots: INVOICE_SCREENSHOT_DIR=/tmp/invoice-shots node tools/test_invoice_editor.mjs
import { createServer } from "node:http";
import { readFileSync, statSync, mkdtempSync, rmSync, mkdirSync, writeFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const failures = [];
let checks = 0;
const assert = (ok, message) => { checks++; if (!ok) failures.push(message); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
if (!statSync(CHROME).isFile()) throw new Error(`Chrome not found: ${CHROME}`);

const MIME = { ".html":"text/html; charset=utf-8", ".css":"text/css; charset=utf-8", ".js":"text/javascript; charset=utf-8", ".svg":"image/svg+xml", ".woff2":"font/woff2", ".png":"image/png" };
const server = createServer((req, res) => {
  let path;
  try { path = decodeURIComponent(new URL(req.url, "http://127.0.0.1").pathname); } catch { res.writeHead(400).end(); return; }
  if (path.endsWith("/")) path += "index.html";
  const file = resolve(ROOT, `.${path}`);
  if (file !== ROOT && !file.startsWith(ROOT + sep)) { res.writeHead(403).end(); return; }
  try { const body=readFileSync(file); res.writeHead(200, { "content-type": MIME[extname(file)] || "application/octet-stream", "cache-control":"no-store" }); res.end(body); }
  catch { res.writeHead(404).end("Not found"); }
});
server.listen(0, "127.0.0.1");
await new Promise((r) => server.once("listening", r));
const base = `http://127.0.0.1:${server.address().port}`;
const profile = mkdtempSync(join(tmpdir(), "goka-invoice-test-"));
const port = 10800 + Math.floor(Math.random() * 500);
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--disable-background-networking", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "about:blank"], { stdio:"ignore" });
let ws;
try {
  let debuggerUrl;
  for (let i=0; i<150 && !debuggerUrl; i++) { try { debuggerUrl=(await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t=>t.type==="page")?.webSocketDebuggerUrl; } catch {} if(!debuggerUrl) await sleep(200); }
  if (!debuggerUrl) throw new Error("Chrome did not start");
  ws = new WebSocket(debuggerUrl);
  await new Promise((r,j)=>{ws.addEventListener("open",r,{once:true});ws.addEventListener("error",j,{once:true});});
  let seq=0; const pending=new Map(), listeners=new Map();
  ws.addEventListener("message",({data})=>{const m=JSON.parse(data); if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(m.error.message)):p.resolve(m);} for(const f of listeners.get(m.method)||[])f(m.params);});
  const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);reject(new Error(`CDP timeout: ${method}`));}},15000).unref();});
  const on=(method,fn)=>{if(!listeners.has(method))listeners.set(method,new Set());listeners.get(method).add(fn);return()=>listeners.get(method).delete(fn);};
  await send("Page.enable"); await send("Runtime.enable"); await send("DOM.enable");
  await send("Fetch.enable",{patterns:[{urlPattern:"*",requestStage:"Request"}]});
  on("Fetch.requestPaused",({requestId,request})=>send(request.url.startsWith(base)?"Fetch.continueRequest":"Fetch.failRequest",request.url.startsWith(base)?{requestId}:{requestId,errorReason:"BlockedByClient"}).catch(()=>{}));
  await send("Page.addScriptToEvaluateOnNewDocument",{source:"window.__invoicePrintCount=0; window.print=()=>{window.__invoicePrintCount++}"});
  const evaluate=async(expression)=>{const r=await send("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});if(r.result.exceptionDetails)throw new Error(r.result.exceptionDetails.text||"page exception");return r.result.result?.value;};
  const navigate=async(path)=>{const loaded=new Promise(resolve=>{const off=on("Page.loadEventFired",()=>{off();resolve();});setTimeout(()=>{off();resolve();},15000).unref();});await send("Page.navigate",{url:base+path});await loaded;await sleep(180);};
  const state=(expr)=>evaluate(expr);
  const box=async(selector)=>evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;const r=e.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()`);
  const scrollIntoView=async(selector)=>{const d=await send("DOM.getDocument");const q=await send("DOM.querySelector",{nodeId:d.result.root.nodeId,selector});if(!q.result.nodeId)return false;await send("DOM.scrollIntoViewIfNeeded",{nodeId:q.result.nodeId});return true;};
  const click=async(selector)=>{if(!await scrollIntoView(selector))throw new Error(`Missing clickable element: ${selector}`);const b=await box(selector);if(!b)throw new Error(`Missing clickable element: ${selector}`);await send("Input.dispatchMouseEvent",{type:"mouseMoved",x:b.x,y:b.y});await send("Input.dispatchMouseEvent",{type:"mousePressed",x:b.x,y:b.y,button:"left",clickCount:1});await send("Input.dispatchMouseEvent",{type:"mouseReleased",x:b.x,y:b.y,button:"left",clickCount:1});};
  const type=async(selector,value)=>{await click(selector);await send("Input.dispatchKeyEvent",{type:"keyDown",key:"a",code:"KeyA",modifiers:4,commands:["selectAll"]});await send("Input.dispatchKeyEvent",{type:"keyUp",key:"a",code:"KeyA",modifiers:4});await send("Input.insertText",{text:String(value)});};
  const wait=async(expr,label)=>{for(let i=0;i<100;i++){if(await evaluate(expr))return;await sleep(40);}throw new Error(`Timed out: ${label}`);};

  await navigate("/tools/invoice-template/");
  // A form that has not been initialized must never submit its placeholder invoice.
  await send("Emulation.setScriptExecutionDisabled",{value:true});
  await navigate("/tools/invoice-template/");
  assert(await state("(()=>{const w=document.querySelector('.invoice-workspace');return !!w&&w.hidden&&getComputedStyle(w).display==='none'})()"),"without JavaScript the invoice workspace stays hidden");
  assert(await state("(()=>{const f=document.querySelector('#invoice-form');return !!f&&[...f.querySelectorAll('input,textarea,button')].every(e=>e.getClientRects().length===0)})()"),"without JavaScript invoice fields and actions are not interactive");
  assert(await state("document.querySelector('#print-invoice')?.disabled===true"),"without JavaScript the print button is disabled");
  assert(await state("!!document.querySelector('noscript')?.textContent.trim()"),"without JavaScript a noscript instruction is present");
  await send("Emulation.setEmulatedMedia",{media:"print"});
  assert(await state("document.querySelector('#invoice-preview')?.getClientRects().length===0"),"without JavaScript print media does not expose the placeholder invoice");
  assert(await state("document.querySelector('noscript')?.getClientRects().length>0"),"without JavaScript print media explains why the editor is unavailable");
  await send("Emulation.setEmulatedMedia",{media:"screen"});
  await send("Emulation.setScriptExecutionDisabled",{value:false});
  await navigate("/tools/invoice-template/");
  // Keep migration failures explicit and continue collecting evidence where possible.
  const initial=await state(`(()=>({form:!!document.querySelector('#invoice-form'),business:document.querySelector('#business-name')?.value??null,placeholder:document.querySelector('#business-name')?.placeholder??null,labels:!!document.querySelector('label[for="business-name"]'),legacy:!!document.querySelector('#inv')}))()`);
  assert(initial.form,"form#invoice-form exists");
  assert(initial.business==="" && !!initial.placeholder,"business name starts blank with a placeholder");
  assert(initial.labels,"business name has an explicitly associated label");
  assert(await state("document.querySelector('#client-name')?.value==='' && !!document.querySelector('#client-name')?.placeholder"),"client name starts blank with a placeholder");
  assert(await state("document.querySelector('#invoice-tax')?.value==='0'"),"tax rate defaults to zero");
  assert(await state("[...document.querySelectorAll('#invoice-form input,#invoice-form textarea')].every(el=>el.labels?.length)"),"all form inputs and textareas have associated labels");
  assert(await state("!!document.querySelector('#client-name[required]')"),"required client name field exists");
  assert(await state("!!document.querySelector('#business-name[required]')"),"required business name field exists");
  assert(await state("document.querySelector('#invoice-number')?.value==='INV-0001'"),"invoice number defaults to INV-0001");
  assert(await state("['issue-date','due-date'].every(id=>document.querySelector('#'+id)?.type==='date')"),"issue and due dates are date controls");
  assert(await state("['business-details','client-details','payment-details','invoice-notes'].every(id=>document.querySelector('#'+id)?.tagName==='TEXTAREA')"),"details, payment and notes are textareas");
  assert(await state("document.querySelectorAll('#invoice-items [data-item]').length===1"),"one invoice item row starts in the form");
  assert(await state("['description','quantity','price'].every(n=>document.querySelector('#invoice-items [data-item] [name='+JSON.stringify(n)+']'))"),"item row has description, quantity and price fields");
  assert(await state("!!document.querySelector('#add-invoice-item') && !!document.querySelector('#invoice-tax')"),"add-item and tax controls exist");
  assert(await state("['invoice-preview','invoice-subtotal','invoice-tax-total','invoice-total'].every(id=>document.getElementById(id))"),"live preview and subtotal/tax/total fields exist");
  assert(await state("!!document.querySelector('#print-invoice')"),"print control exists");
  assert(await state("document.querySelector('#print-invoice')?.form?.id==='invoice-form'"),"print control submits the invoice form even when placed outside it");

  if (initial.form) {
    const initialPreview=await state("document.querySelector('#invoice-preview').innerText");
    assert(initialPreview.includes("Your business")&&initialPreview.includes("Your client")&&initialPreview.includes("Your item"),"empty preview uses helpful business, client and item placeholders");
    await type("#business-name","Acme Studio"); await type("#client-name","Example Client");
    await type("#business-details","123 Main Street"); await type("#client-details","456 Client Road");
    await type('#invoice-items [data-item] [name="description"]','<script>alert("x")</script>');
    await type('#invoice-items [data-item] [name="quantity"]',"3"); await type('#invoice-items [data-item] [name="price"]',"0.10");
    await type("#invoice-tax","10");
    await wait("document.querySelector('#invoice-total')?.textContent.includes('0.33')","computed total");
    let values=await state(`(()=>({preview:document.querySelector('#invoice-preview').innerText,subtotal:document.querySelector('#invoice-subtotal').innerText,tax:document.querySelector('#invoice-tax-total').innerText,total:document.querySelector('#invoice-total').innerText,script:document.querySelector('#invoice-preview script')?.textContent||''}))()`);
    assert(values.preview.includes("Acme Studio")&&values.preview.includes("Example Client"),"business and client fields sync to preview");
    assert(values.preview.includes('<script>alert("x")</script>')&&!values.script,"description renders as text, not executable markup");
    assert(/0\.30/.test(values.subtotal),`subtotal is 0.30 (got ${values.subtotal})`);
    assert(/0\.03/.test(values.tax),`10% tax is 0.03 (got ${values.tax})`);
    assert(/0\.33/.test(values.total),`total is 0.33 (got ${values.total})`);
    await click("#add-invoice-item");
    assert(await state("document.activeElement?.matches('#invoice-items [data-item]:last-child [name=description]')"),"adding item focuses its description field");
    await send("Input.insertText",{text:"Design work"}); await type('#invoice-items [data-item]:last-child [name="quantity"]',"1"); await type('#invoice-items [data-item]:last-child [name="price"]',"1.00");
    await click('#invoice-items [data-item]:last-child button[data-remove-item]');
    assert(await state("document.querySelectorAll('#invoice-items [data-item]').length===1"),"remove item deletes the selected row and keeps one row");
    values=await state("({subtotal:document.querySelector('#invoice-subtotal').innerText,total:document.querySelector('#invoice-total').innerText})");
    assert(/0\.30/.test(values.subtotal)&&/0\.33/.test(values.total),"totals recalculate after removing an item");
    await type('#invoice-items [data-item] [name="quantity"]',"1000000");
    await type('#invoice-items [data-item] [name="price"]',"100000000");
    await wait("!!document.querySelector('#invoice-amount-error')?.textContent.trim()","amount limit error appears");
    assert(await state("document.querySelector('#invoice-amount-error')?.getAttribute('role')==='alert'"),"amount limit is announced as an alert");
    assert(await state("document.querySelector('#invoice-total').innerText.trim()==='—'"),"over-limit invoice total is not presented as a valid amount");
    await type('#invoice-items [data-item] [name="quantity"]',"3");
    await type('#invoice-items [data-item] [name="price"]',"0.10");
    assert(await state("document.querySelector('#invoice-amount-error')?.hidden===true"),"correcting the amount hides the limit error");
    await type('#invoice-items [data-item] [name="price"]',"-1");
    assert(await state("document.querySelector('#invoice-items [data-item] [name=price]').validity.valid===false"),"negative item price fails native validation");
    await click("#print-invoice");
    assert(await state("window.__invoicePrintCount===0"),"invalid form does not invoke print");
    await type('#invoice-items [data-item] [name="price"]',"0.10");
    await click("#print-invoice");
    assert(await state("window.__invoicePrintCount===1"),"valid form invokes print exactly once");
    await send("Emulation.setEmulatedMedia",{media:"print"});
    const printState=await state(`(()=>{const s=e=>getComputedStyle(document.querySelector(e)).display;return{form:s('#invoice-form'),buttonVisible:document.querySelector('#print-invoice').getClientRects().length>0,preview:s('#invoice-preview'),text:document.querySelector('#invoice-preview').innerText,total:document.querySelector('#invoice-total').innerText}})()`);
    assert(printState.form==="none"&&!printState.buttonVisible&&printState.preview!=="none",`print media hides form/button and shows preview (${printState.form}/button:${printState.buttonVisible}/${printState.preview})`);
    assert(printState.text.includes("Acme Studio")&&/0\.33/.test(printState.total),"print view preserves invoice content and total");
    assert(await state("document.querySelector('noscript').getClientRects().length===0"),"a valid printed invoice does not include the JavaScript fallback message");
    await send("Emulation.setEmulatedMedia",{media:"screen"});
  }

  for(const width of [320,375,768,1280]){
    await send("Emulation.setDeviceMetricsOverride",{width,height:900,deviceScaleFactor:1,mobile:width<600});
    const probe=await state(`(()=>({w:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,controls:[...document.querySelectorAll('#invoice-form input,#invoice-form textarea,#invoice-form button')].map(e=>({w:e.getBoundingClientRect().width,min:getComputedStyle(e).minWidth}))}))()`);
    assert(probe.scroll<=width+1,`${width}px viewport has no horizontal overflow (scrollWidth ${probe.scroll})`);
    if(width<900) assert(await state("document.querySelector('.invoice-mobile-preview')?.getClientRects().length>0"),`${width}px viewport offers a preview link in the top toolbar`);
  }
  if(process.env.INVOICE_SCREENSHOT_DIR){
    mkdirSync(process.env.INVOICE_SCREENSHOT_DIR,{recursive:true});
    await send("Emulation.setEmulatedMedia",{media:"screen"});
    await navigate("/tools/invoice-template/");
    for(const [width,height,name] of [[1280,900,"desktop"],[375,812,"mobile"]]){await send("Emulation.setDeviceMetricsOverride",{width,height,deviceScaleFactor:1,mobile:width<600});const shot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});writeFileSync(join(process.env.INVOICE_SCREENSHOT_DIR,`invoice-${name}.png`),Buffer.from(shot.result.data,"base64"));}
  }
  if(failures.length){console.error(`Invoice editor integration: ${failures.length}/${checks} checks failed`);for(const f of failures)console.error(`- ${f}`);process.exitCode=1;}
  else console.log(`Invoice editor integration: ${checks} checks passed`);
} finally { try{ws?.close();}catch{} chrome.kill("SIGTERM"); server.close(); try{rmSync(profile,{recursive:true,force:true});}catch{} }
