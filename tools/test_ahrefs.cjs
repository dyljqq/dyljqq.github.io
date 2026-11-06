// Offline app + real official SDK contract. All XHR bodies are captured locally.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const source = fs.readFileSync(__dirname + '/../assets/analytics/firebase-web-v4.js','utf8').replace(/\bimport\(/g,'mockImport(');
const sdk = fs.readFileSync(process.env.AHREFS_SDK_PATH || __dirname + '/fixtures/ahrefs-analytics-2026-11-06.js','utf8');
function visit({host='beforego.art',search='',referrer='',webdriver=false,delay=false}={}) {
 const scripts=[],requests=[],listeners={},storage=new Map();
 const on=(n,f)=>(listeners[n]??=[]).push(f);
 const document={title:'Wallpaper',referrer,readyState:'complete',documentElement:{lang:'en'},addEventListener:on,dispatchEvent:e=>(listeners[e.type]||[]).forEach(f=>f(e)),querySelector:()=>({content:JSON.stringify({page_type:'tool',page_app:'countdown',apps:{},ahrefs_key:'test-only'})}),querySelectorAll:()=>[],head:{appendChild:s=>scripts.push(s)},createElement:()=>{const attrs={};return {setAttribute:(k,v)=>attrs[k]=String(v),removeAttribute:k=>delete attrs[k],getAttribute:k=>attrs[k]??null,get attributes(){return Object.entries(attrs).map(([name,value])=>({name,value}))}}}};
 const location=new URL(`https://${host}/tools/countdown-wallpaper-maker/${search}`);
 const c={URL,URLSearchParams,document,location,navigator:{webdriver,language:'en'},screen:{width:390,height:844},addEventListener:on,localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},mockImport:()=>new Promise(()=>{}),console:{warn(){}},CustomEvent:class {constructor(type,options={}){this.type=type;this.detail=options.detail}},XMLHttpRequest:class {open(method,url){this.url=url}setRequestHeader(){}send(body){requests.push({url:this.url,body:JSON.parse(body)})}}};c.window=c;
 const context=vm.createContext(c);vm.runInContext(source,context);
 const load=()=>{if(!scripts.length)return;document.currentScript=scripts[0];vm.runInContext(sdk,context);scripts[0].onload()};
 const emit=(detail)=>document.dispatchEvent({type:'goka:tool',detail});
 if(!delay)load();return{scripts,requests,load,emit,storage};
}
const ordinary=visit({search:'?t=PRIVATE_NAME&d=2026-01-01'});
assert.deepEqual(ordinary.requests.map(r=>r.body.n),['pageview','tool_open']);
ordinary.emit({action:'export',outcome:'download_started',name:'PRIVATE_NAME',file_count:7});
assert.equal(ordinary.requests.length,3);const result=ordinary.requests.at(-1).body;
assert.deepEqual(JSON.parse(result.p),{page_language:'en',tool:'/tools/countdown-wallpaper-maker/',action:'export',outcome:'download_started'});
assert.equal(JSON.parse(result.p).tool, JSON.parse(ordinary.requests.find(r=>r.body.n==='tool_open').body.p).tool, 'opening and output share one tool filter');
assert.ok(!JSON.stringify(ordinary.requests).includes('PRIVATE_NAME'));
assert.equal(ordinary.scripts[0].getAttribute('data-key'),null);
ordinary.emit({action:'invalid',outcome:'download_started'});assert.equal(ordinary.requests.length,3);
ordinary.storage.set('gk_analytics_internal','1');ordinary.emit({action:'export',outcome:'failed'});assert.equal(ordinary.requests.length,3);
for(const options of [{search:'?internal=1'},{webdriver:true},{host:'localhost'},{host:'localhost',search:'?analytics_debug=1'},...['https://beforego.art/?t=PRIVATE','https://beforego.art/#PRIVATE','https://user:secret@example.com/','invalid'].map(referrer=>({referrer}))]){
 const x=visit(options);x.emit({action:'export',outcome:'download_started'});assert.equal(x.scripts.length,0,JSON.stringify(options));assert.equal(x.requests.length,0);
}
const delayed=visit({delay:true});delayed.emit({action:'share',outcome:'cancelled'});delayed.storage.set('gk_analytics_internal','1');delayed.load();assert.equal(delayed.requests.length,0,'excluded queued interactions never flush');
console.log('Ahrefs: PASS — real SDK, string props, one pageview, tool open/results, delayed exclusion, preview and sensitive-referrer guards; SHA256 '+crypto.createHash('sha256').update(sdk).digest('hex'));
