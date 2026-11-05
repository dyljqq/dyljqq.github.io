import {spawn} from 'node:child_process';
import {mkdtempSync,rmSync,writeFileSync,readdirSync,mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,join} from 'node:path';
const out=resolve('docs/reviews/evidence/2026-11-05-independent'),profile=mkdtempSync(join(tmpdir(),'beforego-review-')),port=9547;
mkdirSync(out+'/downloads',{recursive:true});
const chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--no-first-run','--no-default-browser-check',`--remote-debugging-port=${port}`,`--user-data-dir=${profile}`,'about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let ws;
try{
 let target;for(let i=0;i<100;i++){try{target=(await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(t=>t.type==='page');if(target)break}catch{}await sleep(200)}
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));let seq=0;const pending=new Map(),events=[];ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){pending.get(m.id)?.(m);pending.delete(m.id)}else events.push(m)});const send=(method,params={})=>new Promise((res,rej)=>{let id=++seq;pending.set(id,res);ws.send(JSON.stringify({id,method,params}));setTimeout(()=>{if(pending.has(id)){pending.delete(id);rej(Error(method+' timeout'))}},15000)});const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.result?.exceptionDetails)throw Error(JSON.stringify(r.result.exceptionDetails));return r.result.result.value};
 await send('Page.enable');await send('Runtime.enable');await send('Log.enable');await send('Network.enable');await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:out+'/downloads',eventsEnabled:true});
 const paths=['/countdown/'];let results=[];
 for(const p of paths)for(const [mode,width,height] of [['desktop',1280,900],['mobile',375,812]]){
  events.length=0;await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:mode==='mobile'});await send('Emulation.setTouchEmulationEnabled',{enabled:mode==='mobile'});await send('Page.navigate',{url:'http://127.0.0.1:8801'+p});await sleep(1200);await ev('document.fonts.ready.then(()=>true)');await sleep(3000);
  let probe=await ev(`(()=>({title:document.title,width:document.documentElement.scrollWidth,viewport:${width},missingImages:[...document.images].filter(x=>x.complete&&!x.naturalWidth).map(x=>x.src),headerOutside:[...document.querySelectorAll('header a,header summary')].filter(x=>{let r=x.getBoundingClientRect();return r.width&&r.height&&(r.left<0||r.right>${width}+1)}).map(x=>x.textContent.trim()),languages:[...document.querySelectorAll('link[hreflang]')].map(x=>({lang:x.hreflang,href:x.href}))}))()`);
  let name=(p.replaceAll('/','_')||'home')+'-'+mode;let shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});writeFileSync(out+'/'+name+'-fixed.png',Buffer.from(shot.result.data,'base64'));
  let errs=events.filter(e=>e.method==='Runtime.exceptionThrown'||e.method==='Log.entryAdded'&&['error','warning'].includes(e.params.entry.level));results.push({path:p,mode,...probe,errors:errs,screenshot:name+'.png'});console.log(p,mode,probe.width,errs.length);
 }
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});await send('Emulation.setTouchEmulationEnabled',{enabled:false});await send('Page.navigate',{url:'http://127.0.0.1:8801/tools/countdown-wallpaper-maker/'});await sleep(1200);
 await ev(`(()=>{let f=document.querySelector('#wallpaper');f.elements.title.value='Independent review trip';f.elements.date.value='2026-12-25';f.dispatchEvent(new Event('input',{bubbles:true}));return true})()`);
 await ev("document.querySelector('#wp-save').click()");await sleep(1200);
 let exportState=await ev(`({title:document.querySelector('#wallpaper').elements.title.value,date:document.querySelector('#wallpaper').elements.date.value,dimensions:document.querySelector('#wp-dim').textContent,filesHint:document.querySelector('#wp-next').hidden})`);exportState.files=readdirSync(out+'/downloads');
 await ev("document.querySelector('#wp-canvas').scrollIntoView({block:'center'})");let sh=await send('Page.captureScreenshot',{format:'png'});writeFileSync(out+'/wallpaper-after-edit.png',Buffer.from(sh.result.data,'base64'));
 await send('Page.navigate',{url:'http://127.0.0.1:8801/countdown/'});await sleep(700);await ev("[...document.querySelectorAll('h2')].find(x=>x.textContent==='Features and backup limits')?.scrollIntoView()");sh=await send('Page.captureScreenshot',{format:'png'});writeFileSync(out+'/countdown-backup-desktop.png',Buffer.from(sh.result.data,'base64'));
 writeFileSync(out+'/browser-fixed-results.json',JSON.stringify({results,exportState},null,2));console.log('EXPORT',exportState);
}finally{ws?.close();chrome.kill();await sleep(500);try{rmSync(profile,{recursive:true,force:true})}catch{}}
