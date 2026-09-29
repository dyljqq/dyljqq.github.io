#!/usr/bin/env python3
"""免费工具页 / 指南页（/tools/…）：吃 Google 长尾和 AI 引用的页面，每页挂对应 app 的入口。

  python3 tools/build_tools.py     # 生成全部工具页 + 目录页，并写 tools/tools.json 清单
                                   # 然后跑 tools/build_seo.py（head / sitemap / llms.txt 按清单补）

内容全在本文件里（PAGES），日期类数字在构建时算一次写进静态文本，页面上的 JS 再按访问当天更新。
"""
import datetime as dt, json, html, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_pages as bp

ROOT, CFG, APPS, BY_KEY, EMAIL = bp.ROOT, bp.CFG, bp.APPS, bp.BY_KEY, bp.EMAIL
ORIGIN = CFG["site"]["origin"]
TODAY = dt.date.today()
esc = bp.esc

TS = {  # 工具页专用界面词
  "en": {"tools": "Tools", "hub_title": "Free tools & guides", "hub_lede": "Small, free, no sign-up. Each one does the same everyday thing our apps do — in the browser.",
         "faq": "Questions people ask", "published": "Published", "updated": "Updated", "get": "Do this on your iPhone",
         "ask": "Ask an AI about this page", "days": "days", "day": "day", "weeks": "weeks", "today": "That's today!", "passed": "days ago",
         "home": "Home", "other_lang": "Ferramentas grátis em português", "other_lang_href": "/tools/pt-br/"},
  "pt-BR": {"tools": "Ferramentas", "hub_title": "Ferramentas e guias grátis", "hub_lede": "Pequenas, grátis, sem cadastro. Cada uma faz no navegador a mesma coisa do dia a dia que os nossos apps fazem.",
            "faq": "Perguntas frequentes", "published": "Publicado em", "updated": "Atualizado em", "get": "Leve para o seu iPhone",
            "ask": "Pergunte a uma IA sobre esta página", "days": "dias", "day": "dia", "weeks": "semanas", "today": "É hoje!", "passed": "dias atrás",
            "home": "Início", "other_lang": "Free tools & guides in English", "other_lang_href": "/tools/"},
  # 09-29：日本线走 Countdown（日本真人靠小组件留存；共通テスト是 1 月的全国考试）
  "ja": {"tools": "ツール", "hub_title": "無料ツールとガイド", "hub_lede": "登録不要で使える無料の小さなツールです。どれも、私たちの iPhone アプリと同じことをブラウザで行えます。",
         "faq": "よくある質問", "published": "公開", "updated": "更新", "get": "iPhone で続ける", "ask": "このページを AI に要約してもらう",
         "days": "日", "day": "日", "weeks": "週", "today": "今日です！", "passed": "日前",
         "home": "ホーム", "other_lang": "Free tools & guides in English", "other_lang_href": "/tools/"},
  # 09-29：港台线走 InvoiceQR（繁中商店名「開單、報價單、收據、送貨單產生器」）
  "zh-Hant": {"tools": "工具", "hub_title": "免費工具與指南", "hub_lede": "小工具，免費、不用註冊。每個工具都能在瀏覽器裡完成我們 iPhone App 做的事。",
              "faq": "常見問題", "published": "發布", "updated": "更新", "get": "在 iPhone 上完成", "ask": "請 AI 摘要這一頁",
              "days": "天", "day": "天", "weeks": "週", "today": "就是今天！", "passed": "天前",
              "home": "首頁", "other_lang": "Free tools & guides in English", "other_lang_href": "/tools/"},
  # 09-28：墨西哥线走 InvoiceQR（西语本地化完整；Countdown 没有西语版，不做西语倒数页）
  "es-MX": {"tools": "Herramientas", "hub_title": "Herramientas y guías gratis", "hub_lede": "Pequeñas, gratis y sin registro. Cada una hace en el navegador lo mismo que nuestras apps hacen en el iPhone.",
            "faq": "Preguntas frecuentes", "published": "Publicado", "updated": "Actualizado", "get": "Llévalo a tu iPhone",
            "ask": "Pregúntale a una IA sobre esta página", "days": "días", "day": "día", "weeks": "semanas", "today": "¡Es hoy!", "passed": "días atrás",
            "home": "Inicio", "other_lang": "Free tools & guides in English", "other_lang_href": "/tools/"},
}
HUBS = {"en": "/tools/", "pt-BR": "/tools/pt-br/", "es-MX": "/tools/es-mx/", "zh-Hant": "/tools/zh-hant/", "ja": "/tools/ja/"}
HOMES = {"en": "/", "pt-BR": "/pt-br/", "es-MX": "/es-mx/", "zh-Hant": "/zh-hant/", "ja": "/ja/"}
def ts(lang, k): return TS.get(lang, TS["en"])[k]
def fmt(d, lang):
    if lang == "pt-BR":
        wd = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"][d.weekday()]
        mo = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"][d.month - 1]
        return f"{wd}, {'1º' if d.day == 1 else d.day} de {mo} de {d.year}"
    if lang == "es-MX":
        wd = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][d.weekday()]
        mo = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][d.month - 1]
        return f"{wd}, {d.day} de {mo} de {d.year}"
    if lang == "ja":
        return f"{d.year}年{d.month}月{d.day}日（{'月火水木金土日'[d.weekday()]}）"
    if lang == "zh-Hant":
        return f"{d.year}年{d.month}月{d.day}日（星期{'一二三四五六日'[d.weekday()]}）"
    return d.strftime("%A, %-d %B %Y")
def days_to(d): return (d - TODAY).days

# 共用 JS：data-date 的元素按访问当天重算天数；data-until 的把整句里的数字替换
COUNT_JS = """
(function(){var T={en:['days','day','That\\'s today!','days ago'],'pt-BR':['dias','dia','É hoje!','dias atrás'],ja:['日','日','今日です！','日前'],'zh-Hant':['天','天','就是今天！','天前']}[document.documentElement.lang]||['days','day','Today','days ago'];
var now=new Date();now=new Date(now.getFullYear(),now.getMonth(),now.getDate());
document.querySelectorAll('[data-date]').forEach(function(el){var p=el.getAttribute('data-date').split('-');var d=new Date(+p[0],+p[1]-1,+p[2]);var n=Math.round((d-now)/864e5);
var num=el.querySelector('[data-n]'),unit=el.querySelector('[data-unit]');if(!num)return;
if(n===0){num.textContent='';unit.textContent=T[2];}else if(n<0){num.textContent=-n;unit.textContent=T[3];}else{num.textContent=n;unit.textContent=n===1?T[1]:T[0];}
var w=el.querySelector('[data-weeks]')||(el.nextElementSibling&&el.nextElementSibling.querySelector('[data-weeks]')),L=document.documentElement.lang;if(w&&n<7)w.textContent='';if(w&&n>=7){w.textContent=L==='ja'?Math.floor(n/7)+(n%7?'週と'+(n%7)+'日':'週間'):L==='zh-Hant'?Math.floor(n/7)+' 週'+(n%7?'又 '+(n%7)+' 天':''):Math.floor(n/7)+' '+(L==='pt-BR'?'semanas':'weeks')+(n%7?' + '+(n%7)+' '+(n%7===1?T[1]:T[0]):'');}});})();
"""
CALC_JS = """
(function(){var f=document.getElementById('calc');if(!f)return;var out=document.getElementById('calc-out');var name=f.querySelector('[name=name]'),date=f.querySelector('[name=date]');
var q=new URLSearchParams(location.search);if(q.get('date'))date.value=q.get('date');if(q.get('name'))name.value=q.get('name');
function run(e){if(e)e.preventDefault();if(!date.value)return;var p=date.value.split('-');var d=new Date(+p[0],+p[1]-1,+p[2]);var now=new Date();now=new Date(now.getFullYear(),now.getMonth(),now.getDate());
var n=Math.round((d-now)/864e5);var PT=document.documentElement.lang==='pt-BR',JA=document.documentElement.lang==='ja';var pl=function(k,a,b){return k===1?a:b};
var label=(name.value.trim().slice(0,60)||(PT?'Sua data':JA?'その日':'that day')).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]});var pretty=JA?d.toLocaleDateString('ja-JP',{year:'numeric',month:'long',day:'numeric',weekday:'short'}):d.toLocaleDateString(PT?'pt-BR':'en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});if(PT)pretty=pretty.replace(/(^|, )1 de /,'$11º de ');var s,w=Math.floor(n/7),r=n%7;
if(PT){/* 名字在前加冒号：用户输入的名字没法配冠词（o Natal / a viagem） */
if(n===0)s='<strong>'+label+'</strong>: é hoje ('+pretty+').';else if(n<0)s='<strong>'+label+'</strong>: foi há <strong>'+(-n)+pl(-n,' dia',' dias')+'</strong> ('+pretty+').';
else s='<strong>'+label+'</strong>: '+pl(n,'falta ','faltam ')+'<strong>'+n+pl(n,' dia',' dias')+'</strong> — '+pretty+'.'+(n>=7?(w===1?' É ':' São ')+w+pl(w,' semana',' semanas')+(r?' e '+r+pl(r,' dia',' dias'):'')+'.':'');}
else if(JA){if(n===0)s='<strong>'+label+'</strong>は今日です（'+pretty+'）。';else if(n<0)s='<strong>'+label+'</strong>から<strong>'+(-n)+'日</strong>たちました（'+pretty+'）。';
else s='<strong>'+label+'</strong>まで、あと<strong>'+n+'日</strong>（'+pretty+'）。'+(n>=7?(r?w+'週と'+r+'日':w+'週間')+'です。':'');}
else if(n===0)s='<strong>'+label+'</strong> is today ('+pretty+').';else if(n<0)s='<strong>'+label+'</strong> was <strong>'+(-n)+' day'+(n===-1?'':'s')+' ago</strong> ('+pretty+').';
else{s='<strong>'+n+' day'+(n===1?'':'s')+'</strong> until <strong>'+label+'</strong> — '+pretty+'.'+(n>=7?' That\\'s '+w+' week'+(w===1?'':'s')+(r?' and '+r+' day'+(r===1?'':'s'):'')+'.':'');}
out.innerHTML='<p class="big">'+s+'</p><p class="share"><a href="?date='+date.value+'&name='+encodeURIComponent(name.value.trim())+'" id="share">'+(PT?'Link para esta contagem':JA?'このカウントダウンのリンク':'Link to this countdown')+'</a></p>';out.hidden=false;
var a=document.getElementById('share');a.addEventListener('click',function(ev){if(navigator.clipboard){ev.preventDefault();navigator.clipboard.writeText(location.origin+location.pathname+a.getAttribute('href'));a.textContent=PT?'Link copiado':JA?'リンクをコピーしました':'Link copied';}});}
f.addEventListener('submit',run);if(date.value)run();})();
"""
INVOICE_JS = """
(function(){var t=document.getElementById('inv');if(!t)return;var body=t.querySelector('tbody');
function money(n){return n.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});}
function calc(){var sub=0;body.querySelectorAll('tr').forEach(function(tr){var q=parseFloat(tr.children[1].textContent)||0,p=parseFloat(tr.children[2].textContent.replace(/[^0-9.\\-]/g,''))||0;var a=q*p;tr.children[3].textContent=money(a);sub+=a;});
var rate=parseFloat(document.getElementById('taxrate').textContent)||0;var tax=sub*rate/100;document.getElementById('sub').textContent=money(sub);document.getElementById('tax').textContent=money(tax);document.getElementById('total').textContent=money(sub+tax);}
document.getElementById('addrow').addEventListener('click',function(){var tr=body.rows[0].cloneNode(true);tr.children[0].textContent=t.getAttribute('data-newitem')||'Item';tr.children[1].textContent='1';tr.children[2].textContent='0.00';body.appendChild(tr);calc();});
document.getElementById('print').addEventListener('click',function(){window.print();});
t.addEventListener('input',calc);document.getElementById('taxrate').addEventListener('input',calc);var L=document.documentElement.lang,loc=L==='en'?undefined:L;document.getElementById('today').textContent=new Date().toLocaleDateString(loc);
var dd=document.getElementById('due');if(dd){var due=new Date();due.setDate(due.getDate()+(+t.getAttribute('data-days')||30));dd.textContent=due.toLocaleDateString(loc);}calc();})();
"""
PACK_JS = """
(function(){var f=document.getElementById('pack');if(!f)return;var out=document.getElementById('pack-out');var L=JSON.parse(document.getElementById('pack-data').textContent);
var KEY='goka-packlist';var saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function build(){var type=f.querySelector('[name=type]').value,days=+f.querySelector('[name=days]').value;var groups=[];
Object.keys(L.base).forEach(function(g){groups.push([g,L.base[g].slice()]);});(L.types[type]||[]).forEach(function(x){var g=groups.find(function(y){return y[0]===x[0]});if(g)g[1]=g[1].concat(x[1]);else groups.push([x[0],x[1].slice()]);});
var h='';groups.forEach(function(g){h+='<h3>'+g[0]+'</h3><ul class="check">';g[1].forEach(function(item){var it=item.replace(/\\{n\\}/g,String(Math.max(1,Math.ceil(days*(item.indexOf('socks')>-1||item.indexOf('underwear')>-1?1:0.5)))));var id=type+'|'+it;
h+='<li><label><input type="checkbox" data-id="'+id.replace(/"/g,'&quot;')+'"'+(saved[id]?' checked':'')+'> '+it+'</label></li>';});h+='</ul>';});
out.innerHTML=h;out.hidden=false;document.getElementById('pack-actions').hidden=false;}
f.addEventListener('change',build);f.addEventListener('submit',function(e){e.preventDefault();build();});
out.addEventListener('change',function(e){if(e.target.type==='checkbox'){saved[e.target.getAttribute('data-id')]=e.target.checked;try{localStorage.setItem(KEY,JSON.stringify(saved))}catch(x){}}});
document.getElementById('pack-print').addEventListener('click',function(){window.print();});
document.getElementById('pack-copy').addEventListener('click',function(){var s='';out.querySelectorAll('h3,li').forEach(function(el){s+=(el.tagName==='H3'?'\\n'+el.textContent.toUpperCase()+'\\n':'- '+el.textContent.trim()+'\\n');});if(navigator.clipboard)navigator.clipboard.writeText(s.trim()).then(function(){document.getElementById('pack-copy').textContent='Copied';});});
build();})();
"""

CSS = bp.CSS + """
.crumbs{margin:18px 0 0;padding:0;list-style:none;display:flex;gap:8px;font-size:13px;color:var(--soft)}.crumbs a{color:var(--soft);text-decoration:none}.crumbs a:hover{text-decoration:underline}
.crumbs li+li::before{content:"›";margin-right:8px}
html[lang^=th] *{letter-spacing:0!important}
.shot{margin:28px 0;display:flex;flex-direction:column;align-items:center;gap:10px}.shot img{width:min(100%,280px);height:auto;border-radius:24px;background:var(--cream)}.shot figcaption{font-size:13px;color:var(--soft);text-align:center}
@media (max-width:760px){.crumbs li:last-child{display:none}}
.article{max-width:720px}.article h1{font-size:clamp(32px,5vw,50px)}.article .lede{font-size:18px}
.article h2{font:500 clamp(24px,3vw,32px)/1.2 var(--display);margin:44px 0 14px}.article h3{font:600 18px/1.4 var(--text);margin:26px 0 8px}
.article p,.article li{color:var(--muted)}.article ul,.article ol{padding-left:22px}.article li{margin:0 0 6px}
.tbl{overflow-x:auto;max-width:100%;margin:12px 0;-webkit-overflow-scrolling:touch}.tbl.full{max-width:none;width:min(1032px,calc(100vw - 2 * var(--gutter)))}.article table{border-collapse:collapse;width:100%;font-size:15px;margin:0}.article table.cmp{min-width:720px}.article th,.article td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--rule);vertical-align:top}.article th{font-weight:700;color:var(--ink)}
.count{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:22px 0 6px;font:500 clamp(48px,9vw,96px)/1 var(--display);letter-spacing:-.04em}.count small{font:600 16px/1 var(--text);letter-spacing:.5px;color:var(--muted)}
.count-sub{margin:0 0 6px;color:var(--muted);font-size:15px}
.calc{display:grid;gap:12px;grid-template-columns:1fr 1fr auto;align-items:end;margin:22px 0;padding:22px;border:1.5px solid var(--ink);border-radius:20px;background:var(--cream)}
.calc label{display:grid;gap:6px;font:700 12px/1 var(--text);letter-spacing:1.2px;text-transform:uppercase;color:var(--muted)}
.calc input,.calc select{font:400 16px/1.3 var(--text);padding:12px 14px;border:1.5px solid var(--rule);border-radius:12px;background:#fff;color:var(--ink);min-width:0}
.calc button,.btn{font:700 14px/1 var(--text);padding:15px 20px;border:0;border-radius:999px;background:var(--ink);color:#fff;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:8px}
.calc button:hover,.btn:hover{background:var(--yellow);color:var(--ink)}.btn svg{width:18px;height:18px;flex:none;fill:currentColor}.appcard .btn{white-space:nowrap}.btn.ghost{background:transparent;color:var(--ink);border:1.5px solid var(--ink)}
#calc-out .big,.tool-out .big{font:500 clamp(22px,3.4vw,32px)/1.3 var(--display);letter-spacing:-.02em;margin:8px 0 6px;color:var(--ink)}#calc-out .share a,.tool-out .share a{font-size:14px}
.tool-out p{margin:6px 0}.tool-out ul{margin:10px 0 6px}.calc.c2{grid-template-columns:minmax(0,1fr) auto}.calc.c4{grid-template-columns:minmax(0,.8fr) minmax(0,1.3fr) minmax(0,1fr) auto}
.pop{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0 0}.pop a{text-decoration:none;border:1px solid var(--rule);border-radius:16px;padding:16px;display:block}.pop a:hover{background:var(--cream)}
.pop b{display:block;font:500 30px/1 var(--display);letter-spacing:-.03em}.pop span{display:block;color:var(--muted);font-size:14px;margin-top:6px}
.appcard{display:flex;gap:18px;align-items:center;margin:48px 0 0;padding:22px;border:1.5px solid var(--ink);border-radius:22px;background:#fff}
.appcard img{width:72px;height:72px;border-radius:16px;flex:none}.appcard b{display:block;font:600 18px/1.3 var(--text)}.appcard p{margin:4px 0 12px;color:var(--muted);font-size:15px}
.ask{margin:36px 0 0;padding-top:18px;border-top:1px solid var(--rule);font-size:14px;color:var(--muted)}.ask a{margin-right:14px;text-underline-offset:3px}
.meta{font-size:13px;color:var(--soft);margin:16px 0 0}
.hub{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin:28px 0 0}.hub a{text-decoration:none;border:1px solid var(--rule);border-radius:20px;padding:22px;display:block;transition:background .2s}.hub a:hover{background:var(--cream)}
.hub b{display:block;font:500 22px/1.25 var(--display);letter-spacing:-.02em}.hub span{display:block;color:var(--muted);font-size:14.5px;margin-top:8px}.hub small{display:block;margin-top:12px;font:700 11px/1 var(--text);letter-spacing:1.6px;text-transform:uppercase;color:var(--soft)}
.inv-wrap{margin:22px 0}.inv-tools{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.inv{border:1.5px solid var(--ink);border-radius:16px;padding:32px;background:#fff;font-size:15px;color:var(--ink)}
.inv [contenteditable]{outline:none;border-bottom:1px dashed #cfcac0;min-width:2ch}.inv [contenteditable]:focus{background:var(--cream)}
.inv-head{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap}.inv-title{margin:0;font:600 34px/1 var(--display);letter-spacing:-.02em}
.inv-parties{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:24px 0}.inv-parties .k,.inv-meta .k{margin:0 0 6px;font:700 11px/1 var(--text);letter-spacing:1.6px;text-transform:uppercase;color:var(--soft)}
.inv table{width:100%;border-collapse:collapse;margin:8px 0}.inv th{font:700 11px/1 var(--text);letter-spacing:1.4px;text-transform:uppercase;color:var(--soft);text-align:left;padding:8px 6px;border-bottom:1.5px solid var(--ink)}
.inv td{padding:9px 6px;border-bottom:1px solid var(--rule)}.inv td:nth-child(n+2),.inv th:nth-child(n+2){text-align:right;width:14%}
.inv .totals{margin-left:auto;width:min(100%,320px);margin-top:12px}.inv .totals div{display:flex;justify-content:space-between;padding:6px 0}.inv .totals .grand{border-top:1.5px solid var(--ink);font-weight:800;font-size:18px;margin-top:6px;padding-top:10px}
.inv .notes{margin-top:22px;color:var(--muted);font-size:14px}
.rcpt-line{margin:14px 0;font-size:17px;line-height:1.7}.rcpt-line strong{font-size:19px;letter-spacing:.06em}.rcpt-sign{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px 24px;margin-top:40px}
.check{list-style:none;padding:0;margin:0 0 18px;columns:2;column-gap:32px}.check li{break-inside:avoid;margin:0 0 6px}.check label{display:flex;gap:10px;align-items:flex-start;color:var(--ink);cursor:pointer}.check input{margin-top:5px;accent-color:var(--ink)}
@media (max-width:760px){.calc,.calc.c2,.calc.c4{grid-template-columns:1fr}.inv{padding:20px}.inv-parties{grid-template-columns:1fr}.check{columns:1}.appcard{flex-direction:column;align-items:flex-start}}
@media print{header,.crumbs,.calc,.appcard,.ask,.meta,footer,#faq-section,.article>*:not(.inv-wrap):not(#pack-out):not(.pack-head){display:none!important}.inv{border:0;padding:0}.inv [contenteditable]{border:0}.inv-tools,#pack-actions{display:none!important}body{font-size:13px}}
"""

def app_card(app_key, lang):
    """页尾「去 iPhone 上做这件事」卡片：图标 + 商店名 + 一句话 + 商店按钮。"""
    p = BY_KEY[app_key]; s = bp.store_of({"variantOf": app_key, "lang": lang} if lang != "en" else p)
    page = bp.sibling_path(p, lang) if lang != "en" else p["path"]
    icon = bp.cdn(s["icon"], 256) if s.get("icon", "").startswith("http") else p["icon"]
    return (f'<aside class="appcard"><img src="{icon}" width="72" height="72" alt="" loading="lazy"><div>'
            f'<p class="label" style="margin:0 0 6px">{esc(ts(lang, "get"))}</p><b>{esc(s["name"])}</b><p>{esc(p["home"]["blurb"] if lang == "en" else s["description"].split(chr(10))[0][:160])}</p>'
            f'<a class="btn" href="{esc(bp.store_link({"variantOf": app_key, "lang": lang} if lang != "en" else p, s, "tool"))}">{bp.APPLE}{esc(bp.t(lang, "cta_store"))}</a> &nbsp; <a href="{page}" style="font-size:14px">{esc(p["home"]["label"])} →</a></div></aside>')

def ask_ai(url, lang):
    q = {"pt-BR": f"Leia {url} e resuma os pontos principais em poucas frases.",
         "es-MX": f"Lee {url} y resume sus puntos principales en pocas frases.",
         "zh-Hant": f"請閱讀 {url}，用幾句話摘要重點。",
         "ja": f"{url} を読んで、要点を数文でまとめてください。"}.get(lang, f"Read {url} and summarise its key points in a few sentences.")
    from urllib.parse import quote
    return (f'<p class="ask">{esc(ts(lang, "ask"))}: <a href="https://chatgpt.com/?q={quote(q)}" rel="nofollow noopener">ChatGPT</a>'
            f'<a href="https://www.perplexity.ai/search?q={quote(q)}" rel="nofollow noopener">Perplexity</a>'
            f'<a href="https://claude.ai/new?q={quote(q)}" rel="nofollow noopener">Claude</a></p>')

def faq_html(faq, lang):
    rows = "\n".join(f'    <div class="card"><h3>{esc(q)}</h3><p>{esc(a)}</p></div>' for q, a in faq)
    return f'<section class="sec" id="faq-section"><h2 id="faq">{esc(ts(lang, "faq"))}</h2><div class="grid">\n{rows}\n</div></section>'

def counter(d, lang, label=""):
    n = days_to(d); unit = ts(lang, "today") if n == 0 else (ts(lang, "passed") if n < 0 else (ts(lang, "day") if n == 1 else ts(lang, "days")))
    w = f"{n // 7} {ts(lang, 'weeks')}" + (f" + {n % 7} {ts(lang, 'days') if n % 7 != 1 else ts(lang, 'day')}" if n % 7 else "") if n >= 7 else ""
    if lang == "ja" and n >= 7: w = f"{n // 7}週と{n % 7}日" if n % 7 else f"{n // 7}週間"
    if lang == "zh-Hant" and n >= 7: w = f"{n // 7} 週又 {n % 7} 天" if n % 7 else f"{n // 7} 週"
    return (f'<div class="count" data-date="{d.isoformat()}"><span data-n>{abs(n) if n else ""}</span><small data-unit>{esc(unit)}</small></div>'
            f'<p class="count-sub">{esc(label + " · " if label else "")}{esc(fmt(d, lang))}{f" · <span data-weeks>{esc(w)}</span>" if w else ""}</p>')

def wrap_tables(body):
    """表格外包 .tbl（overflow-x:auto），手机上表格自己滚，不把页面撑宽。"""
    return body.replace("<table>", '<div class="tbl"><table>').replace('<table class="cmp">', '<div class="tbl full"><table class="cmp">').replace("</table>", "</table></div>")

def shell(pg, body):
    body = wrap_tables(body)
    lang = pg["lang"]; T = lambda k, **kw: bp.t(lang, k, **kw)
    hub, home = HUBS.get(lang, "/tools/"), HOMES.get(lang, "/")
    if pg["path"].startswith("/blog/"):
        crumbs = [(ts(lang, "home"), "/"), ("Blog", "/blog/" if pg["path"] != "/blog/" else None)] + ([(pg["crumb"], None)] if pg.get("crumb") else [])
    else:
        crumbs = [(ts(lang, "home"), home), (ts(lang, "tools"), hub)] + ([(pg["crumb"], None)] if pg.get("crumb") else [])
    crumb_html = "".join(f'<li>{f"<a href={chr(34)}{h}{chr(34)}>{esc(l)}</a>" if h else esc(l)}</li>' for l, h in crumbs)
    meta = ""
    if pg.get("published"):
        meta = f'<p class="meta">{esc(ts(lang, "published"))} {pg["published"]} · {esc(ts(lang, "updated"))} {pg.get("updated", pg["published"])} · go ka</p>'
    scripts = "".join(f"<script>{js}</script>" for js in pg.get("js", []))
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(pg["title"])}</title>
<meta name="theme-color" content="#ffffff">
<meta name="color-scheme" content="light">
<link rel="icon" href="/assets/brand/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/josefin-sans-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/manrope-latin.woff2" as="font" type="font/woff2" crossorigin>
<style>{CSS}</style>
</head>
<body>
<header class="wrap top">
  <a class="brand" href="{home}">{bp.LOGO}<b>go ka</b></a>
  <nav class="nav" aria-label="Main">
    <a href="{home}">{esc(T("nav_all_apps"))}</a>
    <a href="{hub}">{esc(ts(lang, "tools"))}</a>
    <a href="/blog/">Blog</a>
    <a href="mailto:{EMAIL}">{esc(T("nav_support"))}</a>
  </nav>
  <!-- lang:start -->
  <!-- lang:end -->
</header>
<main class="wrap">
<ol class="crumbs">{crumb_html}</ol>
<article class="article">
{body}
{meta}
</article>
{faq_html(pg["faq"], lang) if pg.get("faq") else ""}
{app_card(pg["app"], lang) if pg.get("app") else ""}
{ask_ai(ORIGIN + pg["path"], lang)}
<div style="height:48px"></div>
</main>
<!-- sitefooter:start --><!-- sitefooter:end -->
{scripts}
</body>
</html>
"""

# ------------------------------------------------------------------ 内容
XMAS, NYE, HALLOWEEN, REV = dt.date(2026, 12, 25), dt.date(2027, 1, 1), dt.date(2026, 10, 31), dt.date(2026, 12, 31)
DIWALI = dt.date(2026, 11, 8)   # Lakshmi Puja；11-06 Dhanteras、11-07 Choti Diwali 各家一致。Govardhan Puja / Bhai Dooj 各历书差一天
# （维基 11-09/11-10，samvat.in 都在 11-10，dekhopanchang Bhai Dooj 11-11）——页面只写「11 月 9–11 日，按你用的历书」，不写死（09-28 评审）
ENEM1, ENEM2 = dt.date(2026, 11, 8), dt.date(2026, 11, 15)
CARN_SAT, CARN_TUE, ASH = dt.date(2027, 2, 6), dt.date(2027, 2, 9), dt.date(2027, 2, 10)

def holiday_page(slug, name, d, lang, title, desc, h1, intro, glance, ideas, faq, next_dates, moving=False, published="2026-09-26"):
    # moving：按阴历 / 印度历定日子的节日（排灯节等）每年公历日期不同，「每年重复」会数错，改成提示明年另加
    repeat = ("The date moves every year, so add next year's date as a new event instead of turning on <strong>Repeat yearly</strong>."
              if moving else "Turn on <strong>Repeat yearly</strong> if you want it back next year.")
    body = f"""<h1>{esc(h1)}</h1>
<p class="lede">{intro}</p>
{counter(d, lang, name)}
<h2>{esc(name)} at a glance</h2>
<table><tbody>{"".join(f"<tr><th>{esc(k)}</th><td>{v}</td></tr>" for k, v in glance)}</tbody></table>
<h2>Put the countdown on your Home Screen</h2>
<p>A countdown you have to open an app to see is a countdown you forget. With <a href="/countdown/">Countdown Widget: Any Event</a> you add the date once and it sits on the Home Screen or Lock Screen as a widget — every widget size is free, events are unlimited, and it can remind you on the day and as far ahead as you like.</p>
<ol><li>Install the app and tap <strong>+</strong>. Pick the template or type the name.</li><li>Set the date to {esc(fmt(d, lang))}. {repeat}</li><li>Long-press the Home Screen → <strong>Edit</strong> → <strong>Add Widget</strong> (on iOS 17, tap <strong>+</strong>) → Countdown. Choose the size you like.</li></ol>
<h2>Countdown ideas</h2>
<ul>{"".join(f"<li>{i}</li>" for i in ideas)}</ul>
<h2>{esc(re.sub(r'\s\d{4}$', '', name))} in the next few years</h2>
<table><thead><tr><th>Year</th><th>Date</th><th>Day of the week</th></tr></thead><tbody>{"".join(f"<tr><td>{y}</td><td>{esc(fmt(dd, lang))}</td><td>{dd.strftime('%A')}</td></tr>" for y, dd in next_dates)}</tbody></table>"""
    return {"path": f"/tools/{slug}/", "lang": lang, "title": title, "description": desc, "crumb": name, "kind": "Article",
            "app": "countdown", "faq": faq, "published": published, "js": [COUNT_JS], "body": body, "hub_title": h1, "hub_desc": desc}

PAGES = []

# 1. 通用计算器
PAGES.append({"path": "/tools/days-until/", "lang": "en", "kind": "WebApplication", "app": "countdown", "published": "2026-09-26",
  "title": "Days Until Calculator — how many days until any date", "crumb": "Days until calculator",
  "description": "Free days-until calculator: type a date and get the exact number of days, weeks and the weekday. No sign-up. Link to your countdown to share it.",
  "hub_title": "Days until calculator", "hub_desc": "How many days until any date — plus a link you can share.",
  "js": [COUNT_JS, CALC_JS], "faq": [
    ("How are the days counted?", "The calculator counts whole calendar days between today and the date you enter, in your device's time zone. Today counts as 0; tomorrow counts as 1. The day of the event itself is not added on top."),
    ("Does it handle leap years?", "Yes. It uses the calendar of the browser, so 29 February is counted in leap years such as 2028."),
    ("Can I count up from a date in the past?", "Yes. Enter a past date and it shows how many days ago it was. The Countdown Widget app does the same on your Home Screen, counting up from a birthday, a sober date or a first day at work."),
    ("Can I share the result?", "Yes. After you calculate, the page gives you a link that contains the date and name, so anyone who opens it sees the same countdown, updated to the day they open it."),
    ("Is there an app that keeps the countdown on my phone?", "Countdown Widget: Any Event is our free iPhone app: unlimited events, every widget size on the Home Screen and Lock Screen, reminders and iCloud sync, with no account to create."),
  ],
  "body": f"""<h1>How many days until…?</h1>
<p class="lede">Type any date and get the number of days, weeks and the day of the week. Free, no sign-up, and you can share the link.</p>
<form class="calc" id="calc"><label>Event<input type="text" name="name" placeholder="Wedding, exam, trip…" maxlength="60"></label><label>Date<input type="date" name="date" required></label><button type="submit">Count the days</button></form>
<div id="calc-out" hidden aria-live="polite"></div>
<h2>Popular countdowns</h2>
<div class="pop">
<a href="/tools/days-until-christmas/" data-date="{XMAS.isoformat()}"><b data-n>{days_to(XMAS)}</b><span><span data-unit>days</span> until Christmas 2026</span></a>
<a href="/tools/days-until-halloween/" data-date="{HALLOWEEN.isoformat()}"><b data-n>{days_to(HALLOWEEN)}</b><span><span data-unit>days</span> until Halloween 2026</span></a>
<a href="/tools/days-until-diwali/" data-date="{DIWALI.isoformat()}"><b data-n>{days_to(DIWALI)}</b><span><span data-unit>days</span> until Diwali 2026</span></a>
<a href="/tools/days-until-new-year/" data-date="{NYE.isoformat()}"><b data-n>{days_to(NYE)}</b><span><span data-unit>days</span> until New Year 2027</span></a>
</div>
<p class="meta">Numbers above were computed on {TODAY.isoformat()} and update live when the page loads.</p>
<h2>How the count works</h2>
<p>The result is the number of midnights between today and your date, in your own time zone — the same way people usually say "12 days to go". If your date is today, the answer is 0. A date in the past gives you the days since, which is handy for anniversaries and streaks.</p>
<p>For a countdown you can see without opening anything, put it on your iPhone Home Screen with the app below.</p>"""})

# 2–4. 节日页
PAGES.append(holiday_page("days-until-christmas", "Christmas 2026", XMAS, "en",
  "How many days until Christmas 2026? Live countdown", "Christmas Day 2026 is on Friday, 25 December 2026. Live countdown in days and weeks, plus a free Home Screen widget for your iPhone.",
  "How many days until Christmas 2026?",
  f"Christmas Day 2026 falls on <strong>Friday, 25 December 2026</strong>. Christmas Eve is Thursday the 24th and Boxing Day is Saturday the 26th. The counter below updates every day.",
  [("Christmas Day", "Friday, 25 December 2026"), ("Christmas Eve", "Thursday, 24 December 2026"), ("Boxing Day / St Stephen's Day", "Saturday, 26 December 2026"), ("First Sunday of Advent", "Sunday, 29 November 2026"), ("Twelve days of Christmas end", "Wednesday, 6 January 2027 (Epiphany)")],
  ["A countdown to Christmas Eve for the kids, with a reminder the morning before.", "One countdown per December event: the school play, the last working day, the flight home.", "A count-up from last Christmas to see how fast the year went."],
  [("What day of the week is Christmas 2026?", "Christmas Day 2026 is a Friday. That gives most people a long weekend from Friday 25 December to Sunday 27 December, and many workplaces add Christmas Eve, Thursday 24 December."),
   ("How many weeks until Christmas 2026?", f"Divide the days by seven: on {TODAY.strftime('%-d %B %Y')} there were {days_to(XMAS)} days, which is about {days_to(XMAS)//7} weeks. The counter at the top of this page recalculates it on the day you visit."),
   ("How many days between Halloween and Christmas?", "55 days. Halloween is 31 October and Christmas Day is 25 December, so there are 55 days from one to the other in any year."),
   ("When is Christmas 2027?", "Saturday, 25 December 2027. Christmas 2028 is on a Monday, and Christmas 2029 on a Tuesday."),
   ("How do I put a Christmas countdown on my iPhone Home Screen?", "Add the date in Countdown Widget: Any Event, then long-press the Home Screen, tap Edit → Add Widget (on iOS 17, tap +), and choose Countdown. The widgets are free in every size, and the event can repeat every year.")],
  [(2026, XMAS), (2027, dt.date(2027, 12, 25)), (2028, dt.date(2028, 12, 25)), (2029, dt.date(2029, 12, 25))]))

PAGES.append(holiday_page("days-until-halloween", "Halloween 2026", HALLOWEEN, "en",
  "How many days until Halloween 2026? Live countdown", "Halloween 2026 is on Saturday, 31 October 2026. Live countdown in days and weeks, plus a free Home Screen widget for your iPhone.",
  "How many days until Halloween 2026?",
  "Halloween 2026 falls on <strong>Saturday, 31 October 2026</strong> — a weekend Halloween, which last happened in 2021. The counter below updates every day.",
  [("Halloween", "Saturday, 31 October 2026"), ("All Saints' Day", "Sunday, 1 November 2026"), ("Día de los Muertos", "Monday, 2 November 2026"), ("Days from Halloween to Christmas", "55")],
  ["A countdown to the party with a reminder a week before, so the costume gets ordered in time.", "A trick-or-treat countdown on the kids' shared iPad.", "A Home Screen widget counting down the days to October 31."],
  [("What day of the week is Halloween 2026?", "Saturday. Halloween 2026 is on Saturday, 31 October 2026, so parties and trick-or-treating fall on a weekend."),
   ("How many weeks until Halloween 2026?", f"On {TODAY.strftime('%-d %B %Y')} there were {days_to(HALLOWEEN)} days, about {days_to(HALLOWEEN)//7} weeks. The counter on this page recalculates when you open it."),
   ("When is Halloween 2027?", "Sunday, 31 October 2027. Halloween 2028 falls on a Tuesday."),
   ("How do I get a Halloween countdown widget on iPhone?", "Add 31 October as an event in Countdown Widget: Any Event and set it to repeat yearly, then add the widget from the Home Screen's Edit → Add Widget (on iOS 17, tap +) menu. Every widget size is free.")],
  [(2026, HALLOWEEN), (2027, dt.date(2027, 10, 31)), (2028, dt.date(2028, 10, 31)), (2029, dt.date(2029, 10, 31))]))

# 09-28 借势：排灯节搜索高峰在节前 4–6 周（现在），Countdown 有印度真实用户；首页被几个小倒数站占着，没有一家给 app / 小组件入口
PAGES.append(holiday_page("days-until-diwali", "Diwali 2026", DIWALI, "en",
  "How many days until Diwali 2026? Live countdown", "Diwali 2026 is on Sunday, 8 November 2026, the day of Lakshmi Puja, with Dhanteras on 6 November. Live countdown in days and weeks, plus a free iPhone widget.",
  "How many days until Diwali 2026?",
  "Diwali 2026 — the day of Lakshmi Puja — falls on <strong>Sunday, 8 November 2026</strong>. The festival opens with Dhanteras on Friday, 6 November; Govardhan Puja and Bhai Dooj follow between 9 and 11 November, depending on the panchang you follow. The counter below updates every day.",
  [("Dhanteras", "Friday, 6 November 2026"), ("Choti Diwali (Naraka Chaturdashi)", "Saturday, 7 November 2026"),
   ("Diwali (Lakshmi Puja)", "Sunday, 8 November 2026"), ("Govardhan Puja and Bhai Dooj", "9–11 November 2026, depending on the panchang")],
  ["A countdown to Lakshmi Puja with a reminder a week before, for the shopping and the cleaning.", "A countdown to the trip home for the festival, with the train or flight details written on the back of the event.",
   "A second countdown for Dhanteras on 6 November, so the shopping day does not sneak up on you."],
  [("What date is Diwali in 2026?", "Sunday, 8 November 2026. That is the day of Lakshmi Puja, the main day of the festival. Dhanteras is on 6 November and Choti Diwali on 7 November; the dates given for Govardhan Puja and Bhai Dooj differ by a day between panchangs, somewhere from 9 to 11 November."),
   ("How many weeks until Diwali 2026?", f"On {TODAY.strftime('%-d %B %Y')} there were {days_to(DIWALI)} days, about {days_to(DIWALI)//7} weeks. The counter on this page recalculates when you open it."),
   ("Why does the date of Diwali change every year?", "Diwali follows the Hindu lunisolar calendar: it falls on the new-moon night (Amavasya) of the month of Kartik, so its date in the Gregorian calendar moves between mid-October and mid-November."),
   ("How do I get a Diwali countdown widget on iPhone?", "Add 8 November 2026 as an event in Countdown Widget: Any Event, then add the widget from the Home Screen's Edit → Add Widget (on iOS 17, tap +) menu. Because the date moves, add next year's Diwali as a new event rather than repeating it yearly. Every widget size is free.")],
  [(2026, DIWALI), (2027, dt.date(2027, 10, 29)), (2028, dt.date(2028, 10, 17))], moving=True, published="2026-09-28"))

PAGES.append(holiday_page("days-until-new-year", "New Year 2027", NYE, "en",
  "How many days until New Year 2027? Live countdown", "New Year's Day 2027 is on Friday, 1 January 2027; New Year's Eve is Thursday, 31 December 2026. Live countdown plus a free iPhone widget.",
  "How many days until New Year 2027?",
  "New Year's Day 2027 falls on <strong>Friday, 1 January 2027</strong>, so New Year's Eve is Thursday, 31 December 2026. The counter below updates every day.",
  [("New Year's Eve", "Thursday, 31 December 2026"), ("New Year's Day", "Friday, 1 January 2027"), ("Lunar New Year 2027", "Saturday, 6 February 2027 (Year of the Goat)"), ("Days left in 2026", f"{days_to(REV) + 1} (as of {TODAY.isoformat()})")],
  ["A countdown to midnight with the party address in the notes on the back of the event.", "A count-up from 1 January for a new habit — the widget shows the streak in days.", "One countdown for the first working day, so the holiday has a shape."],
  [("What day of the week is New Year's Day 2027?", "Friday. New Year's Eve 2026 is a Thursday and 1 January 2027 is a Friday, which makes a three-day weekend for many people."),
   ("How many days are left in 2026?", f"As of {TODAY.strftime('%-d %B %Y')} there were {days_to(REV) + 1} days left in 2026, counting today. The counter on this page recalculates when you open it."),
   ("When is Lunar New Year 2027?", "Saturday, 6 February 2027. It begins the Year of the Goat."),
   ("How do I keep a New Year countdown on my Lock Screen?", "Add 1 January 2027 in Countdown Widget: Any Event, then on the Lock Screen long-press → Customize → add the Countdown widget. Lock Screen widgets are free, like every other size.")],
  [(2027, NYE), (2028, dt.date(2028, 1, 1)), (2029, dt.date(2029, 1, 1)), (2030, dt.date(2030, 1, 1))]))

# 5. ENEM 2026（pt-BR）
PAGES.append({"path": "/tools/pt-br/dias-para-o-enem-2026/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-26",
  "title": "Quantos dias faltam para o ENEM 2026? Contagem regressiva", "crumb": "ENEM 2026",
  "description": "As provas do ENEM 2026 são em 8 e 15 de novembro de 2026 (Edital nº 64 do Inep). Contagem regressiva ao vivo e widget grátis para a Tela de Início do iPhone.",
  "hub_title": "Quantos dias faltam para o ENEM 2026?", "hub_desc": "Contagem regressiva para os dois domingos de prova, 8 e 15 de novembro.",
  "js": [COUNT_JS], "faq": [
    ("Quando é o ENEM 2026?", "As provas serão aplicadas nos domingos 8 de novembro e 15 de novembro de 2026, conforme o Edital nº 64, publicado pelo Inep em 22 de maio de 2026."),
    ("Quando foram as inscrições do ENEM 2026?", "De 25 de maio a 12 de junho de 2026, pela Página do Participante do Inep."),
    ("O que cai em cada dia do ENEM 2026?", "No primeiro dia (8/11): Linguagens, Códigos e suas Tecnologias, Redação e Ciências Humanas e suas Tecnologias. No segundo dia (15/11): Ciências da Natureza e suas Tecnologias e Matemática e suas Tecnologias, com 90 questões objetivas."),
    ("Quando sai o gabarito do ENEM 2026?", "Segundo o edital, até o 10º dia útil após o segundo dia de prova."),
    ("Como coloco a contagem regressiva do ENEM na Tela de Início?", "Adicione 8 de novembro de 2026 no app Countdown: Contagem regressiva, depois segure a Tela de Início → Editar → Adicionar widget (no iOS 17, toque em +) → Countdown. Todos os tamanhos de widget são grátis e você pode criar outro evento para o dia 15."),
  ],
  "body": f"""<h1>Quantos dias faltam para o ENEM 2026?</h1>
<p class="lede">O ENEM 2026 tem dois domingos de prova: <strong>8 de novembro</strong> e <strong>15 de novembro de 2026</strong> (Edital nº 64 do Inep, 22 de maio de 2026). Os contadores abaixo atualizam todo dia.</p>
<h2>1º dia — Linguagens, Redação e Ciências Humanas</h2>
{counter(ENEM1, "pt-BR", "1º dia")}
<h2>2º dia — Ciências da Natureza e Matemática</h2>
{counter(ENEM2, "pt-BR", "2º dia")}
<h2>Datas do ENEM 2026</h2>
<table><tbody>
<tr><th>Edital</th><td>Edital nº 64, publicado pelo Inep em 22 de maio de 2026</td></tr>
<tr><th>Inscrições</th><td>25 de maio a 12 de junho de 2026 (Página do Participante)</td></tr>
<tr><th>1º dia de prova</th><td>domingo, 8 de novembro de 2026 — Linguagens, Códigos e suas Tecnologias; Redação; Ciências Humanas e suas Tecnologias</td></tr>
<tr><th>2º dia de prova</th><td>domingo, 15 de novembro de 2026 — Ciências da Natureza e suas Tecnologias; Matemática e suas Tecnologias (90 questões)</td></tr>
<tr><th>Gabarito</th><td>até o 10º dia útil após o 2º dia de aplicação</td></tr>
</tbody></table>
<p>Confira sempre as datas na página oficial do Inep (gov.br/inep); o cronograma acima segue o edital publicado.</p>
<h2>A contagem na Tela de Início, sem abrir nada</h2>
<p>Uma contagem regressiva que você precisa abrir para ver é uma contagem que você esquece. Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — todos os tamanhos são grátis, os eventos são ilimitados e o app avisa no dia e com a antecedência que você quiser.</p>
<ol><li>Instale o app e toque em <strong>+</strong>. Dê o nome "ENEM — 1º dia".</li><li>Coloque a data <strong>8 de novembro de 2026</strong>. Crie outro evento para o dia 15.</li><li>Segure a Tela de Início → <strong>Editar</strong> → <strong>Adicionar widget</strong> (no iOS 17, toque em <strong>+</strong>) → Countdown. Escolha o tamanho.</li></ol>
<h2>Ideias para a reta final</h2>
<ul><li>Um evento por simulado, com lembrete na véspera.</li><li>Uma contagem progressiva desde o primeiro dia de estudo — o widget mostra a sequência em dias.</li><li>Depois da prova, uma contagem para a divulgação do resultado.</li></ul>"""})

# 6. Réveillon + Carnaval 2027（pt-BR）
PAGES.append({"path": "/tools/pt-br/contagem-regressiva-reveillon-2027/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-26",
  "title": "Quantos dias faltam para o Réveillon 2027 e o Carnaval 2027?", "crumb": "Réveillon e Carnaval 2027",
  "description": "Réveillon: quinta-feira, 31 de dezembro de 2026. Carnaval 2027: de sábado 6 a terça 9 de fevereiro. Contagem regressiva ao vivo e widget grátis para o iPhone.",
  "hub_title": "Quantos dias faltam para o Réveillon 2027?", "hub_desc": "Réveillon, Ano-Novo e Carnaval 2027 na mesma página, com contagem ao vivo.",
  "js": [COUNT_JS], "faq": [
    ("Em que dia da semana cai o Réveillon 2026/2027?", "A virada é na quinta-feira, 31 de dezembro de 2026, e o Ano-Novo, 1º de janeiro de 2027, cai numa sexta-feira — emenda com o fim de semana."),
    ("Quando é o Carnaval 2027?", "A terça-feira de Carnaval é 9 de fevereiro de 2027; os desfiles e blocos vão do sábado 6 à terça 9, e a Quarta-feira de Cinzas é 10 de fevereiro. A data vem da Páscoa (28 de março de 2027): o Carnaval é sempre 47 dias antes."),
    ("Quantos dias faltam para o Ano-Novo?", f"Em {TODAY.strftime('%d/%m/%Y')} faltavam {days_to(NYE)} dias para 1º de janeiro de 2027. O contador desta página recalcula no dia em que você abre."),
    ("Como coloco a contagem do Réveillon na Tela Bloqueada?", "Crie o evento 31 de dezembro de 2026 no Countdown: Contagem regressiva, marque repetir todo ano, e na Tela Bloqueada segure → Personalizar → adicione o widget Countdown. Os widgets são grátis em todos os tamanhos."),
  ],
  "body": f"""<h1>Quantos dias faltam para o Réveillon 2027?</h1>
<p class="lede">A virada do ano é na <strong>quinta-feira, 31 de dezembro de 2026</strong>, e o Ano-Novo, 1º de janeiro de 2027, cai numa sexta. O Carnaval 2027 vai de <strong>sábado, 6</strong> a <strong>terça-feira, 9 de fevereiro</strong>. Contadores ao vivo abaixo.</p>
<h2>Réveillon — 31 de dezembro de 2026</h2>
{counter(REV, "pt-BR", "Réveillon")}
<h2>Carnaval 2027 — terça-feira, 9 de fevereiro</h2>
{counter(CARN_TUE, "pt-BR", "Terça de Carnaval")}
<h2>Datas de uma vez</h2>
<table><tbody>
<tr><th>Réveillon</th><td>quinta-feira, 31 de dezembro de 2026</td></tr>
<tr><th>Ano-Novo</th><td>sexta-feira, 1º de janeiro de 2027</td></tr>
<tr><th>Sábado de Carnaval</th><td>6 de fevereiro de 2027</td></tr>
<tr><th>Terça-feira de Carnaval</th><td>9 de fevereiro de 2027</td></tr>
<tr><th>Quarta-feira de Cinzas</th><td>10 de fevereiro de 2027</td></tr>
<tr><th>Páscoa 2027</th><td>domingo, 28 de março de 2027</td></tr>
<tr><th>Dias que restam em 2026</th><td>{days_to(REV) + 1} (em {TODAY.strftime('%d/%m/%Y')}, contando hoje)</td></tr>
</tbody></table>
<h2>A contagem na Tela de Início</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou de bloqueio como widget — grátis em todos os tamanhos, eventos ilimitados, com lembrete no dia. Marque <strong>repetir todo ano</strong> e o Réveillon volta sozinho em 2027.</p>
<ol><li>Toque em <strong>+</strong> e dê o nome «Réveillon».</li><li>Data: 31 de dezembro de 2026, repetir todo ano.</li><li>Segure a Tela de Início → Editar → Adicionar widget (no iOS 17, toque em +) → Countdown.</li></ol>
<h2>Ideias</h2>
<ul><li>Uma contagem para a viagem de Carnaval, com o endereço no verso do evento.</li><li>Uma contagem progressiva desde 1º de janeiro para a meta do ano — o widget mostra os dias de sequência.</li><li>Um evento para o primeiro dia de trabalho depois das festas, para o feriado ter começo e fim.</li></ul>"""})

# 6b. Black Friday + Natal 2026（pt-BR）——09-28 借势：巴西是 Countdown 唯一有付费 + 五星的市场，节前 4–6 周要被收录
# 13º 日期依据 Lei 4.749/1965（1ª parcela até 30/11，2ª até 20/12；pt.wikipedia「Décimo terceiro salário」09-28 核对）。
# 2026 年 20/12 是周日 → 付款提前到前一个工作日 18/12（周五）：Contábeis 09-13、O Povo 两处 09-28 核对（评审第 5 轮指出）
BF26, CYBER26, BF27, BF28 = dt.date(2026, 11, 27), dt.date(2026, 11, 30), dt.date(2027, 11, 26), dt.date(2028, 11, 24)
DEC13_1, DEC13_2, DEC13_2_PAY = dt.date(2026, 11, 30), dt.date(2026, 12, 20), dt.date(2026, 12, 18)
PAGES.append({"path": "/tools/pt-br/contagem-regressiva-black-friday-2026/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-28",
  "title": "Quantos dias faltam para a Black Friday 2026? Contagem regressiva", "crumb": "Black Friday 2026",
  "description": "A Black Friday 2026 é na sexta-feira, 27 de novembro de 2026, e a Cyber Monday na segunda, 30 de novembro. Contagem ao vivo e widget grátis para o iPhone.",
  "hub_title": "Quantos dias faltam para a Black Friday 2026?", "hub_desc": "Black Friday e Cyber Monday com contagem ao vivo, mais a 1ª parcela do 13º.",
  "js": [COUNT_JS], "faq": [
    ("Quando é a Black Friday 2026?", "Na sexta-feira, 27 de novembro de 2026. A Black Friday é sempre a sexta-feira depois do Dia de Ação de Graças dos Estados Unidos, que em 2026 cai na quinta-feira, 26 de novembro."),
    ("Quando é a Cyber Monday 2026?", "Na segunda-feira, 30 de novembro de 2026 — a segunda-feira logo depois da Black Friday."),
    ("Quantos dias faltam para a Black Friday?", f"Em {TODAY.strftime('%d/%m/%Y')} faltavam {days_to(BF26)} dias para 27 de novembro de 2026. O contador desta página recalcula no dia em que você abre."),
    ("Até quando sai a 1ª parcela do 13º salário?", "Pela Lei 4.749/1965, a primeira parcela do 13º deve ser paga até 30 de novembro — em 2026, uma segunda-feira, três dias depois da Black Friday. A segunda parcela tem prazo legal em 20 de dezembro; como em 2026 esse dia é um domingo, o pagamento vai para o dia útil anterior, sexta-feira, 18 de dezembro."),
    ("Como coloco a contagem da Black Friday na Tela de Início?", "Crie o evento 27 de novembro de 2026 no Countdown: Contagem regressiva e, na Tela de Início, segure → Editar → Adicionar widget (no iOS 17, toque em +) → Countdown. A data da Black Friday muda todo ano, então para 2027 crie um evento novo (26 de novembro) em vez de repetir. Os widgets são grátis em todos os tamanhos."),
  ],
  "body": f"""<h1>Quantos dias faltam para a Black Friday 2026?</h1>
<p class="lede">A Black Friday 2026 é na <strong>sexta-feira, 27 de novembro de 2026</strong>, e a Cyber Monday na <strong>segunda-feira, 30 de novembro</strong>. No mesmo dia 30 termina o prazo da 1ª parcela do 13º salário. Os contadores abaixo atualizam todo dia.</p>
<h2>Black Friday — 27 de novembro de 2026</h2>
{counter(BF26, "pt-BR", "Black Friday")}
<h2>Cyber Monday — 30 de novembro de 2026</h2>
{counter(CYBER26, "pt-BR", "Cyber Monday")}
<h2>Datas de uma vez</h2>
<table><tbody>
<tr><th>Black Friday 2026</th><td>{fmt(BF26, "pt-BR")}</td></tr>
<tr><th>Cyber Monday 2026</th><td>{fmt(CYBER26, "pt-BR")}</td></tr>
<tr><th>1ª parcela do 13º (prazo legal)</th><td>até {fmt(DEC13_1, "pt-BR")}</td></tr>
<tr><th>2ª parcela do 13º</th><td>até {fmt(DEC13_2_PAY, "pt-BR")} (o prazo legal, 20/12, cai num domingo)</td></tr>
<tr><th>Da Black Friday ao Natal</th><td>{(XMAS - BF26).days} dias</td></tr>
</tbody></table>
<h2>A Black Friday nos próximos anos</h2>
<table><thead><tr><th>Ano</th><th>Data</th></tr></thead><tbody>
<tr><td>2026</td><td>{fmt(BF26, "pt-BR")}</td></tr>
<tr><td>2027</td><td>{fmt(BF27, "pt-BR")}</td></tr>
<tr><td>2028</td><td>{fmt(BF28, "pt-BR")}</td></tr>
</tbody></table>
<h2>A contagem na Tela de Início</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — todos os tamanhos são grátis, os eventos são ilimitados e o app avisa no dia e com a antecedência que você quiser.</p>
<ol><li>Toque em <strong>+</strong> e dê o nome «Black Friday».</li><li>Data: 27 de novembro de 2026. Como a data muda todo ano, não marque repetir — em 2027 crie um evento novo para 26 de novembro.</li><li>Segure a Tela de Início → <strong>Editar</strong> → <strong>Adicionar widget</strong> (no iOS 17, toque em <strong>+</strong>) → Countdown.</li></ol>
<h2>Ideias</h2>
<ul><li>Uma contagem para a Black Friday com a lista do que você quer comprar escrita no verso do evento.</li><li>Um lembrete uma semana antes, para acompanhar os preços antes da data e saber se o desconto é real.</li><li>Logo em seguida, a contagem para o <a href="/tools/pt-br/quantos-dias-faltam-para-o-natal-2026/">Natal 2026</a> — são {(XMAS - BF26).days} dias entre uma data e outra.</li></ul>"""})

PAGES.append({"path": "/tools/pt-br/quantos-dias-faltam-para-o-natal-2026/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-28",
  "title": "Quantos dias faltam para o Natal 2026? Contagem regressiva", "crumb": "Natal 2026",
  "description": "O Natal 2026 é na sexta-feira, 25 de dezembro, e a véspera na quinta, 24. Contagem regressiva ao vivo em dias e semanas e widget grátis para o iPhone.",
  "hub_title": "Quantos dias faltam para o Natal 2026?", "hub_desc": "Contagem ao vivo para 25 de dezembro, com a véspera e o prazo da 2ª parcela do 13º (18/12 em 2026).",
  "js": [COUNT_JS], "faq": [
    ("Em que dia da semana cai o Natal 2026?", "Numa sexta-feira: 25 de dezembro de 2026. A véspera, 24 de dezembro, é uma quinta-feira, e o Natal emenda com o fim de semana."),
    ("Quantas semanas faltam para o Natal?", f"Em {TODAY.strftime('%d/%m/%Y')} faltavam {days_to(XMAS)} dias, cerca de {days_to(XMAS) // 7} semanas. O contador desta página recalcula no dia em que você abre."),
    ("Até quando sai a 2ª parcela do 13º salário?", "Pela Lei 4.749/1965, o prazo legal da segunda parcela do 13º é 20 de dezembro. Em 2026 esse dia cai num domingo, então o pagamento vai para o dia útil anterior: sexta-feira, 18 de dezembro, uma semana antes do Natal. A primeira parcela vai até 30 de novembro."),
    ("Quando é o Natal 2027?", "Num sábado, 25 de dezembro de 2027. Em 2028, o Natal cai numa segunda-feira."),
    ("Como coloco a contagem do Natal na Tela Bloqueada?", "Crie o evento 25 de dezembro de 2026 no Countdown: Contagem regressiva, marque repetir todo ano e, na Tela Bloqueada, segure → Personalizar → adicione o widget Countdown. Os widgets são grátis em todos os tamanhos."),
  ],
  "body": f"""<h1>Quantos dias faltam para o Natal 2026?</h1>
<p class="lede">O Natal 2026 é na <strong>sexta-feira, 25 de dezembro de 2026</strong>, e a véspera na <strong>quinta-feira, 24</strong>. O contador abaixo atualiza todo dia.</p>
{counter(XMAS, "pt-BR", "Natal")}
<h2>Datas de fim de ano</h2>
<table><tbody>
<tr><th>Véspera de Natal</th><td>{fmt(dt.date(2026, 12, 24), "pt-BR")}</td></tr>
<tr><th>Natal</th><td>{fmt(XMAS, "pt-BR")}</td></tr>
<tr><th>Réveillon</th><td>{fmt(REV, "pt-BR")}</td></tr>
<tr><th>2ª parcela do 13º</th><td>até {fmt(DEC13_2_PAY, "pt-BR")} (o prazo legal, 20/12, cai num domingo)</td></tr>
<tr><th>Black Friday 2026</th><td>{fmt(BF26, "pt-BR")}</td></tr>
</tbody></table>
<h2>O Natal nos próximos anos</h2>
<table><thead><tr><th>Ano</th><th>Dia da semana</th></tr></thead><tbody>
<tr><td>2026</td><td>{fmt(XMAS, "pt-BR")}</td></tr>
<tr><td>2027</td><td>{fmt(dt.date(2027, 12, 25), "pt-BR")}</td></tr>
<tr><td>2028</td><td>{fmt(dt.date(2028, 12, 25), "pt-BR")}</td></tr>
</tbody></table>
<h2>A contagem na Tela de Início</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — grátis em todos os tamanhos, eventos ilimitados, com lembrete no dia. Marque <strong>repetir todo ano</strong> e o Natal volta sozinho em 2027.</p>
<ol><li>Toque em <strong>+</strong> e dê o nome «Natal».</li><li>Data: 25 de dezembro de 2026, repetir todo ano.</li><li>Segure a Tela de Início → <strong>Editar</strong> → <strong>Adicionar widget</strong> (no iOS 17, toque em <strong>+</strong>) → Countdown.</li></ol>
<h2>Ideias</h2>
<ul><li>Uma contagem para a ceia com o que cada pessoa vai levar escrito no verso do evento.</li><li>Um lembrete duas semanas antes para os presentes que vêm pelo correio.</li><li>Depois do Natal, a contagem para o <a href="/tools/pt-br/contagem-regressiva-reveillon-2027/">Réveillon e o Carnaval 2027</a>.</li></ul>"""})

# 6c. 葡语计算器（09-29）：「quantos dias faltam para…」是巴西倒数类最大的词根，联想词前几位是
# acabar o ano / 2027 / natal / enem（「as eleições de 2026」不做：政治话题，一轮 10-04 来不及收录）；
# 「contador de dias」联想里有 entre datas / de namoro（正数）/ corridos。页面只算自然日，FAQ 里写明不算工作日。
PAGES.append({"path": "/tools/pt-br/quantos-dias-faltam/", "lang": "pt-BR", "kind": "WebApplication", "app": "countdown", "published": "2026-09-29",
  "title": "Quantos dias faltam? Contador de dias até qualquer data", "crumb": "Quantos dias faltam?",
  "description": "Contador de dias grátis: digite uma data e veja quantos dias e semanas faltam e o dia da semana. Também conta os dias desde uma data. Sem cadastro.",
  "hub_title": "Quantos dias faltam? (contador de dias)", "hub_desc": "Dias até qualquer data — ou desde uma data — com link para compartilhar.",
  "js": [COUNT_JS, CALC_JS], "faq": [
    ("Como os dias são contados?", "A calculadora conta os dias corridos inteiros entre hoje e a data que você digitar, no fuso horário do seu aparelho. Hoje vale 0 e amanhã vale 1; o próprio dia do evento não entra na conta."),
    ("Ela conta dias úteis?", "Não. Ela conta dias corridos: todos os dias do calendário, com fins de semana e feriados. Para um prazo em dias úteis, é preciso descontar os sábados, os domingos e os feriados do período."),
    ("Dá para contar os dias desde uma data?", "Sim. Digite uma data que já passou e ela mostra há quantos dias foi — serve para o aniversário de namoro, os dias sem fumar ou o tempo no emprego novo. O app Countdown faz o mesmo na Tela de Início: conta até uma data ou a partir de uma data."),
    ("Posso compartilhar o resultado?", "Sim. Depois de calcular, a página gera um link com a data e o nome; quem abrir vê a mesma contagem, atualizada para o dia em que abrir."),
    ("Existe um app que deixa a contagem no celular?", "O Countdown: Contagem regressiva é o nosso app grátis para iPhone: eventos ilimitados, todos os widgets e tamanhos na Tela de Início e na Tela Bloqueada, lembretes e sincronização com o iCloud, sem criar conta."),
  ],
  "body": f"""<h1>Quantos dias faltam?</h1>
<p class="lede">Digite uma data e veja quantos dias e semanas faltam, e em que dia da semana ela cai. Também conta os dias desde uma data que já passou. Grátis, sem cadastro, com link para compartilhar.</p>
<form class="calc" id="calc"><label>Evento<input type="text" name="name" placeholder="Aniversário, casamento, viagem…" maxlength="60"></label><label>Data<input type="date" name="date" required></label><button type="submit">Contar os dias</button></form>
<div id="calc-out" hidden aria-live="polite"></div>
<h2>As contagens mais procuradas</h2>
<div class="pop">
<a href="/tools/pt-br/quantos-dias-faltam-para-o-natal-2026/" data-date="{XMAS.isoformat()}"><b data-n>{days_to(XMAS)}</b><span><span data-unit>dias</span> para o Natal 2026</span></a>
<a href="/tools/pt-br/contagem-regressiva-reveillon-2027/" data-date="{NYE.isoformat()}"><b data-n>{days_to(NYE)}</b><span><span data-unit>dias</span> para 2027 (fim do ano)</span></a>
<a href="/tools/pt-br/dias-para-o-enem-2026/" data-date="{ENEM1.isoformat()}"><b data-n>{days_to(ENEM1)}</b><span><span data-unit>dias</span> para o 1º dia do ENEM 2026</span></a>
<a href="/tools/pt-br/contagem-regressiva-black-friday-2026/" data-date="{BF26.isoformat()}"><b data-n>{days_to(BF26)}</b><span><span data-unit>dias</span> para a Black Friday 2026</span></a>
</div>
<p class="meta">Os números acima foram calculados em {TODAY.strftime("%d/%m/%Y")} e se atualizam quando a página abre.</p>
<h2>Como a conta é feita</h2>
<p>O resultado é a quantidade de dias corridos entre hoje e a data escolhida, no fuso horário do seu aparelho — do jeito que a gente fala «faltam 12 dias». Se a data é hoje, a resposta é 0. Uma data no passado mostra quantos dias se passaram, o que serve para aniversário de namoro, dias sem fumar ou o tempo no emprego novo.</p>
<h2>Contadores prontos</h2>
<ul><li><a href="/tools/pt-br/quantos-dias-faltam-para-o-meu-aniversario/">Quantos dias faltam para o meu aniversário</a> — com os anos que você vai fazer</li><li><a href="/tools/pt-br/quantos-dias-faltam-para-as-ferias/">Quantos dias faltam para as férias</a> — com os dias úteis</li><li><a href="/tools/pt-br/contador-de-dias-de-namoro/">Contador de dias de namoro</a> — há quantos dias vocês estão juntos</li></ul>
<p>Para ver a contagem sem abrir nada, coloque-a na Tela de Início do iPhone com o app abaixo.</p>"""})
_first_pt = next(i for i, p in enumerate(PAGES) if p["lang"] == "pt-BR")
PAGES.insert(_first_pt, PAGES.pop())   # 计算器排在葡语工具目录第一个

# 6d. 葡语场景页（09-29，Google 巴西联想词）：
#   aniversário — quantos dias faltam para o meu aniversário / … do meu filho, da minha filha, do meu amor / frases / instagram / dias e horas
#   férias      — quantos dias faltam para as férias (de julho, de dezembro, escolares, acabarem)；学校假期各州不同，不写死日期
#   namoro      — contador de dias de namoro / quantos dias de namoro eu tenho / quantos dias tem N meses de namoro / 100 dias / qr code
# 三个都只收日期和数字，结果里不拼任何用户输入的文字（没有 ?name= 那种注入面）。
SCENE_JS = r"""
(function(){var pl=function(n,a,b){return n===1?a:b},dias=function(n){return n+pl(n,' dia',' dias')};
function today(){var t=new Date();return new Date(t.getFullYear(),t.getMonth(),t.getDate());}
function diff(a,b){return Math.round((b-a)/864e5);}
function pretty(d){return d.toLocaleDateString('pt-BR',{weekday:'long',day:'numeric',month:'long',year:'numeric'}).replace(/(^|, )1 de /,'$11º de ');}
function parse(v){if(!/^\d{4}-\d{2}-\d{2}$/.test(v||''))return null;var p=v.split('-');return new Date(+p[0],+p[1]-1,+p[2]);}
function addMonths(d,k,day){var y=d.getFullYear(),m=d.getMonth()+k,last=new Date(y,m+1,0).getDate();return new Date(y,m,Math.min(day,last));}
function ymd(from,to){var day=from.getDate(),k=0;while(addMonths(from,k+1,day)<=to)k++;return [Math.floor(k/12),k%12,diff(addMonths(from,k,day),to)];}
function ymdText(a){var o=[];if(a[0])o.push(a[0]+pl(a[0],' ano',' anos'));if(a[1])o.push(a[1]+pl(a[1],' mês',' meses'));if(a[2]||!o.length)o.push(dias(a[2]));return o.length>1?o.slice(0,-1).join(', ')+' e '+o[o.length-1]:o[0];}
function falta(t,d){var r=diff(t,d);return r===0?'é hoje!':pl(r,'falta ','faltam ')+dias(r);}
function show(el,h){el.innerHTML=h;el.hidden=false;}
function share(id){var a=document.getElementById(id);if(a)a.addEventListener('click',function(ev){if(navigator.clipboard){ev.preventDefault();navigator.clipboard.writeText(location.origin+location.pathname+a.getAttribute('href'));a.textContent='Link copiado';}});}
var fa=document.getElementById('bday');if(fa){var oa=document.getElementById('bday-out');fa.addEventListener('submit',function(e){e.preventDefault();
 var dd=+fa.dia.value,mm=+fa.mes.value,yy=+fa.ano.value||0,t=today(),h;
 if(new Date(2024,mm-1,dd).getMonth()!==mm-1){show(oa,'<p class="big">Essa data não existe — confira o dia e o mês.</p>');return;}
 var occ=function(y){var leap=(y%4===0&&y%100!==0)||y%400===0;return new Date(y,mm-1,(mm===2&&dd===29&&!leap)?28:dd);};
 var nx=occ(t.getFullYear());if(nx<t)nx=occ(t.getFullYear()+1);var n=diff(t,nx);
 if(n===0)h='<p class="big"><strong>É hoje!</strong> Feliz aniversário.</p>';
 else h='<p class="big">'+pl(n,'Falta ','Faltam ')+'<strong>'+dias(n)+'</strong> para o aniversário — '+pretty(nx)+'.</p><p>'+(n>=31?'Isso dá '+ymdText(ymd(t,nx))+'. ':'')+'São cerca de '+Math.max(0,Math.floor((nx-new Date())/36e5))+' horas.</p>';
 if(yy>=1900&&yy<=t.getFullYear()){var age=nx.getFullYear()-yy;if(age>0)h+='<p>'+(n===0?'Hoje você faz ':'Vai fazer ')+'<strong>'+age+pl(age,' ano',' anos')+'</strong>.</p>';}
 show(oa,h);});}
var ff=document.getElementById('ferias');if(ff){var of=document.getElementById('ferias-out');ff.addEventListener('submit',function(e){e.preventDefault();
 var s=parse(ff.inicio.value),f=parse(ff.fim.value),t=today(),h;if(!s)return;
 if(f&&f<s){show(of,'<p class="big">O último dia precisa ser depois do primeiro.</p>');return;}
 var n=diff(t,s);
 if(n>0){var u=0;for(var d=new Date(t.getFullYear(),t.getMonth(),t.getDate()+1);d<s;d.setDate(d.getDate()+1)){var w=d.getDay();if(w>0&&w<6)u++;}var wk=Math.floor(n/7);
  h='<p class="big">'+pl(n,'Falta ','Faltam ')+'<strong>'+dias(n)+'</strong> para as férias — '+pretty(s)+'.</p><p>Dias úteis até lá (de segunda a sexta, de amanhã até a véspera, sem descontar feriados): <strong>'+u+'</strong>.'+(n>=7?' Em semanas: '+wk+pl(wk,' semana',' semanas')+(n%7?' e '+dias(n%7):'')+'.':'')+'</p>';
  if(f)h+='<p>As férias duram <strong>'+dias(diff(s,f)+1)+'</strong>, até '+pretty(f)+'.</p>';}
 else if(f&&diff(t,f)>=0){var r=diff(t,f);h='<p class="big">Você está de férias: '+(r===0?'<strong>hoje é o último dia</strong>':pl(r,'falta ','faltam ')+'<strong>'+dias(r)+'</strong> para acabar')+' — último dia: '+pretty(f)+'.</p>';}
 else if(f)h='<p class="big">Essas férias acabaram há <strong>'+dias(-diff(t,f))+'</strong>.</p>';
 else h='<p class="big">'+(n===0?'<strong>As férias começam hoje!</strong>':'As férias começaram há <strong>'+dias(-n)+'</strong>.')+'</p><p>Informe o último dia para ver quanto falta para acabarem.</p>';
 show(of,h);});}
var fn=document.getElementById('namoro');if(fn){var on=document.getElementById('namoro-out');
 var q=new URLSearchParams(location.search).get('desde');if(parse(q))fn.desde.value=q;
 var run=function(e){if(e)e.preventDefault();var s=parse(fn.desde.value),t=today(),h;if(!s)return;var n=diff(s,t);
  if(n<0){show(on,'<p class="big">Essa data ainda não chegou: '+pl(-n,'falta ','faltam ')+'<strong>'+dias(-n)+'</strong>.</p>');return;}
  h='<p class="big">'+(n===0?'<strong>Hoje é o primeiro dia</strong> de namoro.':'Vocês estão juntos há <strong>'+dias(n)+'</strong>.')+'</p>';
  if(n>=31){var wk=Math.floor(n/7);h+='<p>Isso dá '+ymdText(ymd(s,t))+' — ou '+wk+pl(wk,' semana',' semanas')+'.</p>';}
  var k=n>0&&n%100===0?n:(Math.floor(n/100)+1)*100,c=new Date(s.getFullYear(),s.getMonth(),s.getDate()+k),day=s.getDate(),mi=1,yi=1;
  while(addMonths(s,mi,day)<t)mi++;while(addMonths(s,12*yi,day)<t)yi++;var mv=addMonths(s,mi,day),an=addMonths(s,12*yi,day);
  h+='<ul><li><strong>'+k+' dias</strong>: '+pretty(c)+' ('+falta(t,c)+')</li>'+(mi%12?'<li>Próximo mesversário, <strong>'+mi+pl(mi,' mês',' meses')+'</strong>: '+pretty(mv)+' ('+falta(t,mv)+')</li>':'')
   +'<li><strong>'+yi+pl(yi,' ano',' anos')+'</strong> de namoro: '+pretty(an)+' ('+falta(t,an)+')</li></ul><p class="share"><a href="?desde='+fn.desde.value+'" id="namoro-share">Link para esta contagem</a></p>';
  show(on,h);share('namoro-share');};
 fn.addEventListener('submit',run);if(fn.desde.value)run();}
})();
"""

def month_span(n):
    """n 个月有几天：从每个月 1 号起算，覆盖一个闰年周期，取最少和最多。"""
    spans = [(dt.date(y + (m - 1 + n) // 12, (m - 1 + n) % 12 + 1, 1) - dt.date(y, m, 1)).days for y in range(2025, 2029) for m in range(1, 13)]
    return min(spans), max(spans)
M3_LO, M3_HI = 100 - month_span(3)[1], 100 - month_span(3)[0]   # 100 天 = 3 个月又几天
M7_LO, M7_HI = month_span(7)
PT_MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
PT_WIDGET_STEP = "<li>Segure a Tela de Início → <strong>Editar</strong> → <strong>Adicionar widget</strong> (no iOS 17, toque em <strong>+</strong>) → Countdown.</li>"

SCENES = [
 {"path": "/tools/pt-br/quantos-dias-faltam-para-o-meu-aniversario/", "lang": "pt-BR", "kind": "WebApplication", "app": "countdown", "published": "2026-09-29",
  "title": "Quantos dias faltam para o meu aniversário? Contagem regressiva", "crumb": "Meu aniversário",
  "description": "Escolha o dia e o mês do seu aniversário e veja quantos dias, meses e horas faltam, em que dia da semana ele cai e quantos anos você vai fazer.",
  "hub_title": "Quantos dias faltam para o meu aniversário?", "hub_desc": "Dias, meses e horas até o próximo aniversário — e quantos anos você vai fazer.",
  "js": [SCENE_JS], "faq": [
    ("Como a conta é feita?", "São dias corridos entre hoje e o próximo aniversário, no fuso horário do seu aparelho. Se o aniversário deste ano já passou, a conta vai para o do ano que vem; se é hoje, a página diz que é hoje."),
    ("E quem nasceu em 29 de fevereiro?", "Nos anos que não são bissextos, a página conta até 28 de fevereiro. O próximo 29 de fevereiro é em 2028."),
    ("Dá para contar os dias para o aniversário do meu filho?", "Sim: escolha o dia e o mês em que ele nasceu. No Countdown dá para ter um evento para cada pessoa da família, porque os eventos são ilimitados, e cada um pode aparecer num widget."),
    ("Quantos dias e horas faltam?", "Depois de contar, a página mostra também as horas que faltam até a meia-noite em que o aniversário começa, no seu fuso horário."),
    ("Existe um app com a contagem do aniversário no celular?", "O Countdown: Contagem regressiva é o nosso app grátis para iPhone: widgets em todos os tamanhos na Tela de Início e na Tela Bloqueada, eventos ilimitados, repetição todo ano e lembretes no dia e com a antecedência que você quiser."),
  ],
  "body": f"""<h1>Quantos dias faltam para o meu aniversário?</h1>
<p class="lede">Escolha o dia e o mês em que você nasceu e veja quantos dias faltam para o próximo aniversário e em que dia da semana ele cai. Informe o ano, se quiser, para ver quantos anos vai fazer. Serve também para o aniversário do filho, da filha ou do amor.</p>
<form class="calc c4" id="bday"><label>Dia<select name="dia" required>{"".join(f'<option value="{d}">{d}</option>' for d in range(1, 32))}</select></label><label>Mês<select name="mes" required>{"".join(f'<option value="{i}">{m}</option>' for i, m in enumerate(PT_MONTHS, 1))}</select></label><label>Ano (opcional)<input type="number" name="ano" min="1900" max="{TODAY.year}" placeholder="1995" inputmode="numeric"></label><button type="submit">Contar</button></form>
<div id="bday-out" class="tool-out" hidden aria-live="polite"></div>
<h2>A contagem na Tela de Início</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> o aniversário fica na Tela de Início ou na Tela Bloqueada como widget, grátis em todos os tamanhos. O app tem modelos prontos, entre eles o de aniversário, que já vêm com a repetição e os lembretes certos. Os eventos são ilimitados: cabem o seu, o dos filhos e o de quem mais você quiser.</p>
<ol><li>Toque em <strong>+</strong> e escolha o modelo de aniversário.</li><li>Informe a data de nascimento.</li>{PT_WIDGET_STEP}</ol>
<p>Quando a contagem chega a um marco — cem dias, uma semana, a manhã do dia —, o app abre o número em tela cheia e prepara um cartão para compartilhar.</p>
<h2>Frases para a contagem regressiva</h2>
<p>Para o story ou a legenda do Instagram:</p>
<ul><li>«Contagem regressiva oficialmente aberta: falta uma semana para o meu dia.»</li><li>«Faltam 10 dias para mais um ano de história.»</li><li>«3, 2, 1… faltam só 3 dias!»</li><li>«Falta 1 dia. Amanhã é festa.»</li><li>«Faltam 30 dias para o aniversário do meu pequeno, e ele já pergunta todo dia quanto falta.»</li><li>«Um mês para o aniversário do meu amor — a surpresa já está sendo preparada.»</li></ul>
<p>Para qualquer outra data, use o <a href="/tools/pt-br/quantos-dias-faltam/">contador de dias</a>.</p>"""},
 {"path": "/tools/pt-br/quantos-dias-faltam-para-as-ferias/", "lang": "pt-BR", "kind": "WebApplication", "app": "countdown", "published": "2026-09-29",
  "title": "Quantos dias faltam para as férias? Contagem com dias úteis", "crumb": "Férias",
  "description": "Informe o primeiro dia das férias e veja quantos dias e quantos dias úteis faltam. Com o último dia, mostra a duração e quanto falta para acabarem.",
  "hub_title": "Quantos dias faltam para as férias?", "hub_desc": "Dias corridos e dias úteis até as férias — e quanto falta para acabarem.",
  "js": [SCENE_JS], "faq": [
    ("Como os dias úteis são contados?", "São os dias de segunda a sexta entre amanhã e a véspera do primeiro dia de férias. Os feriados não são descontados, porque mudam de cidade para cidade: se houver feriado de segunda a sexta no período, tire um dia por feriado."),
    ("Quando são as férias escolares?", "Depende do estado, da cidade e da rede de ensino. O calendário oficial é publicado pela secretaria de educação ou pela escola; digite a data de início no contador acima."),
    ("Em quantas partes posso dividir as férias pela CLT?", "Em até três, se você concordar: um período de pelo menos 14 dias corridos e os outros de pelo menos 5 dias corridos cada (art. 134, § 1º, da CLT)."),
    ("Quanto falta para as minhas férias acabarem?", "Informe o primeiro e o último dia. Se hoje estiver dentro desse intervalo, a página mostra quantos dias faltam para acabarem."),
    ("Dá para ver a contagem das férias no celular?", "Sim. No Countdown: Contagem regressiva, grátis para iPhone, a contagem fica num widget da Tela de Início ou da Tela Bloqueada, com lembretes no dia e com antecedência. Os eventos são ilimitados e sincronizam pelo iCloud, sem criar conta."),
  ],
  "body": f"""<h1>Quantos dias faltam para as férias?</h1>
<p class="lede">Informe o primeiro dia das férias e veja quantos dias faltam — e quantos dias úteis ainda tem pela frente. Com o último dia, a página mostra quanto tempo as férias duram e, se você já estiver de férias, quanto falta para acabarem.</p>
<form class="calc" id="ferias"><label>Primeiro dia<input type="date" name="inicio" required></label><label>Último dia (opcional)<input type="date" name="fim"></label><button type="submit">Contar</button></form>
<div id="ferias-out" class="tool-out" hidden aria-live="polite"></div>
<h2>Férias escolares</h2>
<p>O calendário escolar muda de estado para estado e entre as redes estadual, municipal e particular. Por isso a página não traz uma data pronta: confira o calendário publicado pela secretaria de educação ou pela escola e digite o primeiro dia acima. Em geral há um recesso no meio do ano, em julho, e as férias grandes no fim do ano.</p>
<h2>Férias do trabalho (CLT)</h2>
<ul><li>São 30 dias corridos a cada 12 meses de trabalho para quem teve até 5 faltas injustificadas no período (art. 130).</li><li>Com a sua concordância, podem ser divididas em até três períodos: um de pelo menos 14 dias e os outros de pelo menos 5 dias cada (art. 134, § 1º).</li><li>A empresa comunica as férias por escrito com pelo menos 30 dias de antecedência (art. 135), e o pagamento sai até 2 dias antes do início (art. 145).</li></ul>
<h2>A contagem na Tela de Início</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> a contagem das férias fica na Tela de Início ou na Tela Bloqueada como widget, grátis em todos os tamanhos, com lembretes no dia e com a antecedência que você quiser.</p>
<ol><li>Toque em <strong>+</strong> e dê o nome «Férias».</li><li>Data: o primeiro dia das férias. Adicione um lembrete uma semana antes, para arrumar as malas com calma.</li>{PT_WIDGET_STEP}</ol>
<p>Se as férias vão ter viagem, o <a href="/beforego/pt-br/">BeforeGo</a> monta um roteiro dia a dia a partir do print de um post de viagem, e a lista de bagagem se monta sozinha a partir do destino e das datas.</p>
<p>Para qualquer outra data, use o <a href="/tools/pt-br/quantos-dias-faltam/">contador de dias</a>.</p>"""},
 {"path": "/tools/pt-br/contador-de-dias-de-namoro/", "lang": "pt-BR", "kind": "WebApplication", "app": "countdown", "published": "2026-09-29",
  "title": "Contador de dias de namoro: há quantos dias vocês estão juntos", "crumb": "Dias de namoro",
  "description": "Digite a data em que começaram a namorar e veja há quantos dias, meses e anos estão juntos, o próximo mesversário, os 100 dias e o aniversário de namoro.",
  "hub_title": "Contador de dias de namoro", "hub_desc": "Há quantos dias vocês estão juntos, os próximos marcos e um link para compartilhar.",
  "js": [SCENE_JS], "faq": [
    ("Como sei quantos dias de namoro eu tenho?", "Digite a data em que vocês começaram. A página conta os dias corridos até hoje, no fuso horário do seu aparelho; o dia em que começaram vale 0."),
    ("Quantos dias tem 7 meses de namoro?", f"Entre {M7_LO} e {M7_HI} dias, conforme o mês em que o namoro começou. Os outros meses estão na tabela desta página."),
    ("100 dias de namoro são quantos meses?", f"São 3 meses e mais {M3_LO} a {M3_HI} dias, conforme o mês em que vocês começaram."),
    ("O link mostra a nossa contagem para outra pessoa?", "Sim. O link leva só a data (?desde=…), nenhum nome; quem abrir vê a contagem atualizada para o dia em que abrir. Dá para transformar o link num QR code de presente."),
    ("Tem app para ver os dias de namoro no celular?", "O Countdown: Contagem regressiva, grátis para iPhone, conta até uma data ou a partir de uma data e mostra o número num widget da Tela de Início ou da Tela Bloqueada. Widgets grátis em todos os tamanhos, eventos ilimitados e sincronização com o iCloud, sem criar conta."),
  ],
  "body": f"""<h1>Contador de dias de namoro</h1>
<p class="lede">Digite a data em que vocês começaram a namorar e veja há quantos dias estão juntos — em dias, semanas, meses e anos — e quando caem o próximo mesversário, a próxima centena de dias e o próximo aniversário de namoro. A página gera um link para compartilhar.</p>
<form class="calc c2" id="namoro"><label>Começamos a namorar em<input type="date" name="desde" max="{TODAY.isoformat()}" required></label><button type="submit">Contar os dias</button></form>
<div id="namoro-out" class="tool-out" hidden aria-live="polite"></div>
<h2>Quantos dias têm os meses de namoro</h2>
<p>Os meses não têm o mesmo tamanho, então «7 meses de namoro» dá um número de dias diferente conforme o mês em que vocês começaram. A tabela mostra o mínimo e o máximo:</p>
<table><thead><tr><th>Tempo de namoro</th><th>Dias</th></tr></thead><tbody>{"".join(f"<tr><td>{n} {'mês' if n == 1 else 'meses'}</td><td>{lo} a {hi} dias</td></tr>" for n, (lo, hi) in ((n, month_span(n)) for n in range(1, 12)))}<tr><td>1 ano</td><td>365 ou 366 dias</td></tr></tbody></table>
<h2>Marcos para comemorar</h2>
<ul><li><strong>Mesversário</strong>: todo mês, no mesmo dia em que começaram; quando o mês não tem esse dia, no último dia do mês.</li><li><strong>100 dias</strong>: dá 3 meses e mais {M3_LO} a {M3_HI} dias, conforme o mês de início. Depois vêm os 200, os 500 e os 1.000 dias.</li><li><strong>Aniversário de namoro</strong>: 365 dias, ou 366 quando o ano passa por um 29 de fevereiro.</li></ul>
<h2>A contagem no celular</h2>
<p>No <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> um evento pode contar a partir de uma data: crie o dia em que vocês começaram e ele mostra há quantos dias estão juntos num widget grátis da Tela de Início. No verso do evento dá para escrever algumas linhas, guardar fotos e gravar uma voz — a história do dia fica junto com o dia.</p>
<ol><li>Toque em <strong>+</strong>, dê um nome e escolha a data em que começaram.</li><li>Escolha contar a partir dessa data.</li><li>Para o mesversário, crie outro evento que se repete todo mês.</li>{PT_WIDGET_STEP}</ol>
<p>Quer dar a contagem de presente em QR code? Copie o link gerado acima e transforme em QR code com qualquer gerador — o nosso é o <a href="/qrcodestudio/" hreflang="en">QR Studio</a>, para iPhone (página em inglês).</p>"""},
]
_ci = next(i for i, p in enumerate(PAGES) if p["path"] == "/tools/pt-br/quantos-dias-faltam/")
PAGES[_ci + 1:_ci + 1] = SCENES   # 场景页紧跟在计算器后面（常青页排在节日页前面）

# 7. 发票模板
PAGES.append({"path": "/tools/invoice-template/", "lang": "en", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-09-26",
  "title": "Free Invoice Template — fill in, print or save as PDF (no sign-up)", "crumb": "Invoice template",
  "description": "A free invoice template you fill in on the page: your details, the client, line items with automatic totals and tax, then print or save as PDF. No sign-up.",
  "hub_title": "Free invoice template", "hub_desc": "Fill it in on the page, totals add up by themselves, print or save as PDF.",
  "js": [INVOICE_JS], "faq": [
    ("Is this invoice template really free?", "Yes. Everything happens in your browser: nothing is uploaded, there is no account and no watermark. Fill in the fields, then print or save as PDF."),
    ("What must an invoice include?", "The word Invoice, a unique invoice number, the issue date and due date, your business name and contact details, the client's name and address, a description of each item with quantity and price, the subtotal, any tax with its rate, the total due, and how to pay."),
    ("How do I save the invoice as a PDF?", "Click Print / Save as PDF. In the print dialog choose 'Save as PDF' as the destination. Only the invoice is printed — the rest of the page is hidden."),
    ("Does it calculate tax?", "Yes. Type a tax rate in the Tax field and the tax amount and total update. Leave it at 0 if you do not charge tax."),
    ("Is there an app that keeps invoices, clients and payments?", "Smart Invoice & Estimate Maker is our iPhone app for exactly that: 100+ templates, estimates and quotes that turn into invoices, a payment QR code on every invoice, and paid / unpaid / overdue tracking. Three documents are free, with no account."),
  ],
  "body": f"""<h1>Free invoice template</h1>
<p class="lede">Fill it in right here — click any dashed field to edit. Totals and tax add up by themselves. Then print it or save it as a PDF. Nothing leaves your browser.</p>
<div class="inv-wrap">
<div class="inv-tools"><button class="btn" id="print" type="button">Print / Save as PDF</button><button class="btn ghost" id="addrow" type="button">+ Add line</button></div>
<div class="inv" id="inv">
<div class="inv-head"><div><div class="inv-title">INVOICE</div><p style="margin:6px 0 0"><span contenteditable="true">Your Business Name</span><br><span contenteditable="true">Street, City, Country</span><br><span contenteditable="true">you@example.com · +1 000 000 0000</span></p></div>
<div class="inv-meta"><div class="k">Invoice number</div><p style="margin:0 0 10px"><span contenteditable="true">INV-0001</span></p><div class="k">Date</div><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><div class="k">Due</div><p style="margin:0"><span contenteditable="true" id="due"></span></p></div></div>
<div class="inv-parties"><div><div class="k">Bill to</div><p style="margin:0"><span contenteditable="true">Client name</span><br><span contenteditable="true">Client address</span><br><span contenteditable="true">client@example.com</span></p></div>
<div><div class="k">Payment</div><p style="margin:0"><span contenteditable="true">Bank transfer — IBAN / account number</span><br><span contenteditable="true">Other ways to pay (optional)</span></p></div></div>
<table><thead><tr><th>Description</th><th>Qty</th><th>Price</th><th>Amount</th></tr></thead>
<tbody><tr><td contenteditable="true">Design work — logo suite</td><td contenteditable="true">1</td><td contenteditable="true">1200.00</td><td>1,200.00</td></tr>
<tr><td contenteditable="true">Landing page</td><td contenteditable="true">1</td><td contenteditable="true">800.00</td><td>800.00</td></tr></tbody></table>
<div class="totals"><div><span>Subtotal</span><span id="sub">2,000.00</span></div><div><span>Tax (<span contenteditable="true" id="taxrate">0</span>%)</span><span id="tax">0.00</span></div><div class="grand"><span>Total due</span><span id="total">2,000.00</span></div></div>
<p class="notes" contenteditable="true">Payment is due within 30 days. Thank you for your business.</p>
</div></div>
<h2>What an invoice must include</h2>
<ul><li><strong>The word "Invoice"</strong> and a unique, sequential invoice number.</li><li><strong>Issue date</strong> and <strong>due date</strong> (or payment terms such as "Net 30").</li><li><strong>Your details</strong>: business name, address, email or phone, and tax ID where required.</li><li><strong>The client's details</strong>: name and address.</li><li><strong>Line items</strong>: description, quantity, unit price and amount.</li><li><strong>Subtotal, tax</strong> (with the rate) and the <strong>total due</strong>.</li><li><strong>How to pay</strong>: bank details, a payment link or a QR code.</li></ul>
<h2>Invoice, estimate, quote or receipt?</h2>
<table><thead><tr><th>Document</th><th>When you send it</th><th>What it means</th></tr></thead><tbody>
<tr><td>Estimate</td><td>Before the work</td><td>An approximate price; it can change.</td></tr>
<tr><td>Quote</td><td>Before the work</td><td>A fixed price, valid for a stated time.</td></tr>
<tr><td>Invoice</td><td>After the work (or a milestone)</td><td>A request for payment with a due date.</td></tr>
<tr><td>Receipt</td><td>After payment</td><td>Confirmation that the invoice was paid.</td></tr></tbody></table>
<p>If you send more than a few invoices a month, an app that remembers clients, items and tax rates and shows what is paid, unpaid and overdue saves real time. That is what <a href="/invoiceqr/">Smart Invoice &amp; Estimate Maker</a> does on iPhone — including a payment QR code on every invoice.</p>"""})

# 7b. 墨西哥：formato de cotización / nota de venta（es-MX，InvoiceQR）——09-28 借势
# 依据：tools/store/invoiceqr.json es-MX 描述（3 documentos gratis sin cuenta；cotización → nota de venta con un toque；CLABE / QR de pago；
# 「No emite CFDI ni facturas fiscales ante el SAT」）。IVA 只写「tasa general 16 %」（LIVA art. 1）；边境 8 % 是否延续没核实，不写。
# ⛔ 不把我们的单据叫 factura（墨西哥 factura = CFDI）
MX_NOTE = ('<p class="meta" style="margin-top:18px"><strong>Importante:</strong> una cotización o una nota de venta no es una factura. '
           'En México, la factura es un CFDI: un comprobante fiscal digital que se emite a través del SAT o de un proveedor autorizado (PAC). '
           'Ni este formato ni nuestra app emiten CFDI ni facturas fiscales ante el SAT.</p>')
MX_APP = ('Nota de Venta, Cotización, nuestra app para iPhone, hace esto mismo y guarda tus clientes y conceptos: envía primero la cotización y conviértela en nota de venta con un toque, '
          'agrega tus datos de transferencia (CLABE) o un código QR de pago, y comparte el PDF por WhatsApp. Puedes crear 3 documentos gratis, sin cuenta ni registro.')

PAGES.append({"path": "/tools/es-mx/formato-de-cotizacion/", "lang": "es-MX", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-09-28",
  "title": "Formato de cotización gratis — llénalo, imprímelo o guárdalo en PDF", "crumb": "Formato de cotización",
  "description": "Formato de cotización gratis para llenar en línea: tus datos, el cliente, los conceptos con importe e IVA que se calculan solos. Imprime o guarda en PDF, sin registro.",
  "hub_title": "Formato de cotización gratis", "hub_desc": "Llénalo aquí mismo: importes, IVA y total se calculan solos. Imprime o guarda en PDF.",
  "js": [INVOICE_JS], "faq": [
    ("¿Este formato de cotización es gratis?", "Sí. Todo pasa en tu navegador: no se sube nada, no hay cuenta ni marca de agua. Llena los campos y luego imprime o guarda en PDF."),
    ("¿Qué debe llevar una cotización?", "La palabra Cotización y un folio, la fecha y la vigencia, tus datos de contacto, los datos del cliente, cada concepto con cantidad, precio unitario e importe, el subtotal, el IVA con su tasa y el total, y las condiciones: forma de pago, tiempo de entrega y anticipo si lo pides."),
    ("¿Qué es la vigencia de una cotización?", "Es la fecha hasta la que respetas los precios. En este formato se llena sola a 15 días de hoy; cámbiala si ofreces otro plazo."),
    ("¿Una cotización sirve como factura?", "No. La cotización es una propuesta de precio antes de la venta. Si tu cliente necesita factura, esa tiene que ser un CFDI emitido a través del SAT o de un proveedor autorizado (PAC)."),
    ("¿Cómo guardo la cotización en PDF?", "Haz clic en Imprimir / Guardar PDF y, en la ventana de impresión, elige «Guardar como PDF» como destino. Solo se imprime la cotización; el resto de la página se oculta."),
    ("¿Hay una app para hacer cotizaciones en el iPhone?", MX_APP),
  ],
  "body": f"""<h1>Formato de cotización gratis</h1>
<p class="lede">Llénalo aquí mismo: haz clic en cualquier campo punteado para editarlo. El importe de cada concepto, el IVA y el total se calculan solos. Después imprímelo o guárdalo en PDF. Nada sale de tu navegador.</p>
<div class="inv-wrap">
<div class="inv-tools"><button class="btn" id="print" type="button">Imprimir / Guardar PDF</button><button class="btn ghost" id="addrow" type="button">+ Agregar concepto</button></div>
<div class="inv" id="inv" data-newitem="Concepto" data-days="15">
<div class="inv-head"><div><div class="inv-title">COTIZACIÓN</div><p style="margin:6px 0 0"><span contenteditable="true">Nombre de tu negocio</span><br><span contenteditable="true">Calle, colonia, ciudad</span><br><span contenteditable="true">tucorreo@ejemplo.com · 55 0000 0000</span></p></div>
<div class="inv-meta"><div class="k">Folio</div><p style="margin:0 0 10px"><span contenteditable="true">COT-0001</span></p><div class="k">Fecha</div><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><div class="k">Vigencia</div><p style="margin:0"><span contenteditable="true" id="due"></span></p></div></div>
<div class="inv-parties"><div><div class="k">Cliente</div><p style="margin:0"><span contenteditable="true">Nombre del cliente</span><br><span contenteditable="true">Dirección del cliente</span><br><span contenteditable="true">cliente@ejemplo.com</span></p></div>
<div><div class="k">Condiciones</div><p style="margin:0"><span contenteditable="true">Anticipo del 50 %, resto a la entrega</span><br><span contenteditable="true">Transferencia — CLABE 000 000 00000000000 0</span></p></div></div>
<table><thead><tr><th>Concepto</th><th>Cant.</th><th>Precio unitario</th><th>Importe</th></tr></thead>
<tbody><tr><td contenteditable="true">Diseño de logotipo</td><td contenteditable="true">1</td><td contenteditable="true">4500.00</td><td>4,500.00</td></tr>
<tr><td contenteditable="true">Tarjetas de presentación (millar)</td><td contenteditable="true">2</td><td contenteditable="true">650.00</td><td>1,300.00</td></tr></tbody></table>
<div class="totals"><div><span>Subtotal</span><span id="sub">5,800.00</span></div><div><span>IVA (<span contenteditable="true" id="taxrate">16</span>%)</span><span id="tax">928.00</span></div><div class="grand"><span>Total</span><span id="total">6,728.00</span></div></div>
<p class="notes" contenteditable="true">Precios en pesos mexicanos (MXN). Cotización válida hasta la fecha de vigencia.</p>
</div></div>
<h2>Qué debe llevar una cotización</h2>
<ul><li><strong>La palabra «Cotización»</strong> y un folio para identificarla.</li><li><strong>Fecha</strong> y <strong>vigencia</strong>: hasta cuándo respetas los precios.</li><li><strong>Tus datos</strong>: nombre o razón social y cómo contactarte.</li><li><strong>Los datos del cliente</strong>: nombre y dirección o correo.</li><li><strong>Conceptos</strong>: descripción, cantidad, precio unitario e importe.</li><li><strong>Subtotal, IVA</strong> (con la tasa que aplique; la tasa general es 16 %) y <strong>total</strong>.</li><li><strong>Condiciones</strong>: forma de pago, tiempo de entrega y anticipo, si lo pides.</li></ul>
<h2>Cotización, nota de venta, remisión o factura</h2>
<table><thead><tr><th>Documento</th><th>Cuándo se hace</th><th>Para qué sirve</th></tr></thead><tbody>
<tr><td>Cotización</td><td>Antes de la venta</td><td>Propone un precio que respetas hasta la fecha de vigencia.</td></tr>
<tr><td>Nota de venta</td><td>Al vender</td><td>Deja constancia de la venta entre tú y tu cliente. No es un comprobante fiscal.</td></tr>
<tr><td>Remisión</td><td>Al entregar</td><td>Acredita que la mercancía se entregó; la firma quien la recibe.</td></tr>
<tr><td>Factura (CFDI)</td><td>Cuando el cliente la pide o la ley lo exige</td><td>Comprobante fiscal digital, emitido a través del SAT o de un proveedor autorizado (PAC).</td></tr></tbody></table>
<p>¿Tu cliente ya aceptó? Pasa los mismos conceptos a un <a href="/tools/es-mx/nota-de-venta/">formato de nota de venta</a>. Si haces varias cotizaciones al mes, <a href="/invoiceqr/es-mx/">Nota de Venta, Cotización</a> en el iPhone guarda clientes y conceptos y convierte la cotización en nota de venta con un toque.</p>
{MX_NOTE}"""})

PAGES.append({"path": "/tools/es-mx/nota-de-venta/", "lang": "es-MX", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-09-28",
  "title": "Formato de nota de venta gratis — llénalo, imprímelo o guárdalo en PDF", "crumb": "Formato de nota de venta",
  "description": "Formato de nota de venta gratis para llenar en línea: folio, fecha, cliente y conceptos con importes e IVA que se calculan solos. Imprime o guarda en PDF, sin registro.",
  "hub_title": "Formato de nota de venta gratis", "hub_desc": "Folio, cliente y conceptos; los importes se suman solos. Imprime o guarda en PDF.",
  "js": [INVOICE_JS], "faq": [
    ("¿Este formato de nota de venta es gratis?", "Sí. Se llena en tu navegador, no se sube nada y no pide cuenta. Al terminar, imprímelo o guárdalo en PDF."),
    ("¿Qué debe llevar una nota de venta?", "La leyenda Nota de venta y un folio, la fecha, tus datos, el nombre del cliente, cada concepto con cantidad, precio unitario e importe, el total y la forma de pago."),
    ("¿La nota de venta sirve como factura?", "No. La nota de venta deja constancia de la venta entre tú y tu cliente, pero no es un comprobante fiscal. Si el cliente necesita factura, tiene que ser un CFDI emitido a través del SAT o de un proveedor autorizado (PAC)."),
    ("¿Cómo guardo la nota de venta en PDF?", "Haz clic en Imprimir / Guardar PDF y elige «Guardar como PDF» como destino en la ventana de impresión. Solo se imprime la nota."),
    ("¿Hay una app para hacer notas de venta en el iPhone?", MX_APP),
  ],
  "body": f"""<h1>Formato de nota de venta gratis</h1>
<p class="lede">Llénalo aquí mismo: haz clic en cualquier campo punteado para editarlo. Los importes y el total se calculan solos; si cobras IVA, escribe la tasa. Después imprímelo o guárdalo en PDF. Nada sale de tu navegador.</p>
<div class="inv-wrap">
<div class="inv-tools"><button class="btn" id="print" type="button">Imprimir / Guardar PDF</button><button class="btn ghost" id="addrow" type="button">+ Agregar concepto</button></div>
<div class="inv" id="inv" data-newitem="Concepto">
<div class="inv-head"><div><div class="inv-title">NOTA DE VENTA</div><p style="margin:6px 0 0"><span contenteditable="true">Nombre de tu negocio</span><br><span contenteditable="true">Calle, colonia, ciudad</span><br><span contenteditable="true">tucorreo@ejemplo.com · 55 0000 0000</span></p></div>
<div class="inv-meta"><div class="k">Folio</div><p style="margin:0 0 10px"><span contenteditable="true">NV-0001</span></p><div class="k">Fecha</div><p style="margin:0"><span contenteditable="true" id="today"></span></p></div></div>
<div class="inv-parties"><div><div class="k">Cliente</div><p style="margin:0"><span contenteditable="true">Nombre del cliente</span><br><span contenteditable="true">Teléfono o correo</span></p></div>
<div><div class="k">Forma de pago</div><p style="margin:0"><span contenteditable="true">Efectivo / transferencia</span><br><span contenteditable="true">CLABE 000 000 00000000000 0</span></p></div></div>
<table><thead><tr><th>Concepto</th><th>Cant.</th><th>Precio unitario</th><th>Importe</th></tr></thead>
<tbody><tr><td contenteditable="true">Pastel de chocolate (20 personas)</td><td contenteditable="true">1</td><td contenteditable="true">850.00</td><td>850.00</td></tr>
<tr><td contenteditable="true">Cupcakes decorados</td><td contenteditable="true">12</td><td contenteditable="true">35.00</td><td>420.00</td></tr></tbody></table>
<div class="totals"><div><span>Subtotal</span><span id="sub">1,270.00</span></div><div><span>IVA (<span contenteditable="true" id="taxrate">0</span>%)</span><span id="tax">0.00</span></div><div class="grand"><span>Total</span><span id="total">1,270.00</span></div></div>
<p class="notes" contenteditable="true">Gracias por tu compra.</p>
</div></div>
<h2>Qué debe llevar una nota de venta</h2>
<ul><li><strong>La leyenda «Nota de venta»</strong> y un folio consecutivo.</li><li><strong>La fecha</strong> de la venta.</li><li><strong>Tus datos</strong>: nombre del negocio y cómo contactarte.</li><li><strong>El cliente</strong>: nombre y teléfono o correo.</li><li><strong>Conceptos</strong>: descripción, cantidad, precio unitario e importe.</li><li><strong>Total</strong> (con IVA si lo cobras; escribe la tasa que aplique) y <strong>forma de pago</strong>.</li></ul>
<h2>¿Nota de venta o factura?</h2>
<p>La nota de venta deja constancia de la venta entre tú y tu cliente; sirve para llevar tus cuentas y para que el cliente tenga un comprobante de lo que pagó. No es un comprobante fiscal: si tu cliente necesita deducir la compra, pídele sus datos y emite un CFDI a través del SAT o de un proveedor autorizado (PAC).</p>
<p>¿Todavía no cierras la venta? Empieza por un <a href="/tools/es-mx/formato-de-cotizacion/">formato de cotización</a>. En el iPhone, <a href="/invoiceqr/es-mx/">Nota de Venta, Cotización</a> guarda tus clientes y conceptos, lleva la cuenta de lo pagado y lo pendiente, y agrega tu CLABE o un código QR de pago a cada nota.</p>
{MX_NOTE}"""})

# 7c. 港台：報價單範本 / 收據範本（zh-Hant，InvoiceQR）——09-29
# 依据：Google HK / TW 联想词（報價單範本 excel/word/下載/pdf、報價單產生器；收據範本 word/excel/茲收到/數字/香港、免用統一發票 收據格式）；
# app 说法全部出自 tools/store/invoiceqr.json zh-Hant 描述（商店名「開單、報價單、收據、送貨單產生器」；先寄報價單，確認後一鍵轉帳單；
# 收款 QR Code；手寫簽名；結清後同一份帳單當收據分享；免費 3 份免註冊；「不用於開立稅務發票」）。
# ⛔ 台灣的「發票」＝統一發票（稅務憑證），我們不開——同墨西哥 CFDI 的口径。營業稅只写一般稅率 5%；香港無營業稅。
ZH_NOTE = ('<p class="meta" style="margin-top:18px"><strong>提醒：</strong>報價單和收據都不是稅務發票。在台灣，營業人依法開立的是統一發票；'
           '這個範本和我們的 App 都不開立統一發票或其他稅務發票。</p>')
ZH_APP = ('「開單、報價單、收據、送貨單產生器」是我們的 iPhone App，做的就是這件事，還會記住客戶與項目：先寄報價單，客戶確認後一鍵轉成帳單；'
          '每份帳單都可以附上收款 QR Code，簽名直接在 iPhone 上手寫；收款結清後，同一份帳單可以直接當作收據分享。免費建立 3 份，免註冊帳號。')
RECEIPT_JS = r"""
(function(){var r=document.getElementById('rcpt');if(!r)return;
function cnUpper(n){if(!(n>=0)||n>=1e12)return '';n=Math.floor(n);if(n===0)return '零元整';
 var D='零壹貳參肆伍陸柒捌玖',U=['','拾','佰','仟'],S=['','萬','億'],s=String(n),L=s.length,out='',zero=false;
 for(var i=0;i<L;i++){var d=+s[i],p=L-1-i,u=p%4,g=Math.floor(p/4);
  if(d===0)zero=true;else{if(zero){out+='零';zero=false;}out+=D[d]+U[u];}
  if(u===0&&g>0&&+s.substring(Math.max(0,i-3),i+1)>0){out+=S[g];zero=false;}}
 return out+'元整';}
var a=document.getElementById('amt'),o=document.getElementById('amt-cn');
function upd(){var v=parseFloat((a.textContent||'').replace(/[^0-9.]/g,''));o.textContent=isNaN(v)?'（請輸入數字）':(cnUpper(v)||'（金額太大）');}
a.addEventListener('input',upd);upd();
a.addEventListener('blur',function(){var v=parseFloat((a.textContent||'').replace(/[^0-9.]/g,''));if(!isNaN(v))a.textContent=Math.floor(v).toLocaleString('en-US');});
var t=document.getElementById('today');if(t)t.textContent=new Date().toLocaleDateString('zh-Hant');
document.getElementById('print').addEventListener('click',function(){window.print();});})();
"""

PAGES.append({"path": "/tools/zh-hant/bao-jia-dan-fan-ben/", "lang": "zh-Hant", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-09-29",
  "title": "報價單範本（免費）— 線上填寫、列印或存成 PDF", "crumb": "報價單範本",
  "description": "免費報價單範本：線上填好公司、客戶與品項，金額、稅額與總計自動計算，再列印或存成 PDF。不用註冊，港台都適用。",
  "hub_title": "報價單範本", "hub_desc": "線上填寫，金額與總計自動計算；列印或存成 PDF。",
  "js": [INVOICE_JS], "faq": [
    ("這個報價單範本免費嗎？", "是。整份在你的瀏覽器裡填寫，不會上傳，不用帳號，也沒有浮水印。填好後列印或存成 PDF。"),
    ("報價單要寫哪些內容？", "「報價單」字樣與編號、日期與有效期限、你的公司名稱與聯絡方式（台灣可加上統一編號）、客戶資料、每個項目的數量、單價與金額、小計、稅額與總計，以及付款條件和交期。"),
    ("報價單的有效期限怎麼寫？", "就是你保證這個價格到哪一天。範本預設為今天起 15 天，可以直接改。"),
    ("報價單要含稅嗎？", "在台灣，營業稅的一般稅率是 5%，報價時寫清楚含稅或未稅，之後比較不會有爭議；把稅率欄改成 5，稅額就會自動算出來。香港沒有營業稅，稅率欄保持 0。"),
    ("有 Excel 或 Word 版本嗎？", "沒有。這個範本直接在網頁上填，完成後存成 PDF 寄給客戶，排版不會跑掉；如果要重複使用客戶與項目，可以用我們的 iPhone App。"),
    ("怎麼存成 PDF？", "按「列印／存成 PDF」（香港叫打印），在列印視窗把目的地選成「另存為 PDF」。只會印出報價單本身，頁面其他內容會自動隱藏。"),
    ("有 App 可以在 iPhone 上開報價單嗎？", ZH_APP),
  ],
  "body": f"""<h1>報價單範本</h1>
<p class="lede">直接在這裡填：點任何虛線欄位就能修改。每個項目的金額、稅額與總計會自動計算，填好後列印或存成 PDF。資料不會離開你的瀏覽器。</p>
<div class="inv-wrap">
<div class="inv-tools"><button class="btn" id="print" type="button">列印／存成 PDF</button><button class="btn ghost" id="addrow" type="button">+ 新增項目</button></div>
<div class="inv" id="inv" data-newitem="項目" data-days="15">
<div class="inv-head"><div><div class="inv-title">報價單</div><p style="margin:6px 0 0"><span contenteditable="true">你的公司名稱</span><br><span contenteditable="true">統一編號／商業登記號碼</span><br><span contenteditable="true">地址 · 電話 · Email</span></p></div>
<div class="inv-meta"><div class="k">報價單號</div><p style="margin:0 0 10px"><span contenteditable="true">Q-0001</span></p><div class="k">日期</div><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><div class="k">有效期限</div><p style="margin:0"><span contenteditable="true" id="due"></span></p></div></div>
<div class="inv-parties"><div><div class="k">客戶</div><p style="margin:0"><span contenteditable="true">客戶名稱／聯絡人</span><br><span contenteditable="true">電話或 Email</span></p></div>
<div><div class="k">條件</div><p style="margin:0"><span contenteditable="true">付款方式：訂金 50%，交貨後付清</span><br><span contenteditable="true">交期：確認後 14 天</span></p></div></div>
<table><thead><tr><th>項目</th><th>數量</th><th>單價</th><th>金額</th></tr></thead>
<tbody><tr><td contenteditable="true">網站設計（5 頁）</td><td contenteditable="true">1</td><td contenteditable="true">18000.00</td><td>18,000.00</td></tr>
<tr><td contenteditable="true">商品攝影（半天）</td><td contenteditable="true">1</td><td contenteditable="true">6000.00</td><td>6,000.00</td></tr></tbody></table>
<div class="totals"><div><span>小計</span><span id="sub">24,000.00</span></div><div><span>稅額（<span contenteditable="true" id="taxrate">0</span>%）</span><span id="tax">0.00</span></div><div class="grand"><span>總計</span><span id="total">24,000.00</span></div></div>
<p class="notes" contenteditable="true">幣別：新台幣／港幣（請改成你的幣別）。本報價於有效期限內有效。客戶確認簽名／公司印章：</p>
</div></div>
<h2>報價單要寫什麼</h2>
<ul><li><strong>「報價單」字樣</strong>與報價單號，方便日後對照。</li><li><strong>日期</strong>與<strong>有效期限</strong>：價格保證到哪一天。</li><li><strong>你的資料</strong>：公司或個人名稱、聯絡方式；台灣可加上統一編號。</li><li><strong>客戶資料</strong>：名稱、聯絡人、電話或 Email。</li><li><strong>項目</strong>：名稱、數量、單價、金額。</li><li><strong>小計、稅額、總計</strong>：台灣寫清楚含稅或未稅。</li><li><strong>條件</strong>：付款方式、訂金、交期，以及客戶確認回簽的位置。</li></ul>
<h2>報價單、估價單、帳單、收據、統一發票</h2>
<table><thead><tr><th>文件</th><th>什麼時候開</th><th>用途</th></tr></thead><tbody>
<tr><td>報價單</td><td>成交前</td><td>提出價格，在有效期限內照這個價格做。</td></tr>
<tr><td>估價單</td><td>成交前</td><td>估計費用，常見於工程與維修，實際金額可能再調整。</td></tr>
<tr><td>帳單／請款單</td><td>交貨或完工後</td><td>向客戶請款，寫明金額與付款期限。</td></tr>
<tr><td>收據</td><td>收到款項後</td><td>證明已經收到錢。</td></tr>
<tr><td>統一發票（台灣）</td><td>依法開立</td><td>營業人開立的稅務憑證，多半是電子發票。</td></tr></tbody></table>
<h2>要不要含稅</h2>
<p>在台灣，營業稅的一般稅率是 5%。報價單上寫清楚「含稅」或「未稅」，之後開發票時才不會有爭議；要含稅就把稅率欄改成 5。香港沒有營業稅或增值稅，稅率欄保持 0 就好。</p>
<p>客戶確認以後，收錢時用<a href="/tools/zh-hant/shou-ju-fan-ben/">收據範本</a>開收據。常常要報價的話，iPhone 上的<a href="/invoiceqr/zh-hant/">開單、報價單、收據、送貨單產生器</a>會記住客戶與項目，報價單確認後一鍵轉成帳單。</p>
{ZH_NOTE}"""})

PAGES.append({"path": "/tools/zh-hant/shou-ju-fan-ben/", "lang": "zh-Hant", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-09-29",
  "title": "收據範本（免費）— 茲收到格式，金額自動轉大寫", "crumb": "收據範本",
  "description": "免費收據範本：線上填寫「茲收到」格式的收據，輸入金額就自動寫出中文大寫，再列印或存成 PDF。不用註冊，港台都適用。",
  "hub_title": "收據範本", "hub_desc": "「茲收到」格式，輸入金額自動寫出大寫；列印或存成 PDF。",
  "js": [RECEIPT_JS], "faq": [
    ("這個收據範本免費嗎？", "是。整份在你的瀏覽器裡填寫，不會上傳，不用帳號，也沒有浮水印。填好後列印或存成 PDF。"),
    ("收據金額為什麼要寫大寫？", "大寫數字筆畫多、不容易被塗改，例如「壹萬貳仟參佰元整」；最後的「整」表示沒有零頭。在範本裡輸入數字，大寫會自動寫出來。"),
    ("「茲收到」後面要寫什麼？", "寫付款人的姓名或公司名稱，接著寫「繳付」與款項的事由，例如「茲收到 王小明 繳付 十月份房租 款項」。"),
    ("金額有小數怎麼辦？", "範本的大寫以整數元計算，小數會捨去；金額有角或分的話，請在大寫欄自己補上。"),
    ("收據可以當發票用嗎？", "不行。收據證明你收到了款項；在台灣，營業人依法要開的是統一發票。在香港，「發票」通常指請款用的單據（invoice），不是稅務憑證。這個範本和我們的 App 都不開立稅務發票。"),
    ("有 App 可以在 iPhone 上開收據嗎？", "有。在我們的「開單、報價單、收據、送貨單產生器」裡，收款結清後，同一份帳單可以直接當作收據分享：標記為已付，並附上結清日期。帳單可以附收款 QR Code，也能在 iPhone 上手寫簽名。免費建立 3 份，免註冊帳號。"),
  ],
  "body": f"""<h1>收據範本</h1>
<p class="lede">直接在這裡填：點任何虛線欄位就能修改。輸入金額，下面會自動寫出中文大寫；填好後列印或存成 PDF。資料不會離開你的瀏覽器。</p>
<div class="inv-wrap">
<div class="inv-tools"><button class="btn" id="print" type="button">列印／存成 PDF</button></div>
<div class="inv" id="rcpt">
<div class="inv-head"><div><div class="inv-title">收據</div><p style="margin:6px 0 0"><span contenteditable="true">收款人或公司名稱</span><br><span contenteditable="true">地址 · 電話</span></p></div>
<div class="inv-meta"><div class="k">收據編號</div><p style="margin:0 0 10px"><span contenteditable="true">R-0001</span></p><div class="k">日期</div><p style="margin:0"><span contenteditable="true" id="today"></span></p></div></div>
<p class="rcpt-line">茲收到 <span contenteditable="true">付款人姓名／公司</span> 繳付 <span contenteditable="true">網站設計費用</span> 款項</p>
<p class="rcpt-line">金額：<span contenteditable="true">新台幣</span> <strong id="amt-cn">參萬元整</strong></p>
<p class="rcpt-line">（<span contenteditable="true">NT$</span> <span contenteditable="true" id="amt">30,000</span>）</p>
<p class="rcpt-line">付款方式：<span contenteditable="true">銀行轉帳</span></p>
<div class="rcpt-sign"><div>收款人簽名：＿＿＿＿＿＿</div><div>蓋章：</div></div>
<p class="notes" contenteditable="true">此據。</p>
</div></div>
<h2>收據要寫什麼</h2>
<ul><li><strong>「收據」字樣</strong>與收據編號。</li><li><strong>日期</strong>：收到款項的那一天。</li><li><strong>「茲收到 某某 繳付 某某款項」</strong>：付款人與事由。</li><li><strong>金額</strong>：中文大寫加阿拉伯數字，大寫最後寫「元整」，不容易被塗改。香港填港幣時，把「新台幣」和「NT$」改成「港幣」和「HK$」。</li><li><strong>付款方式</strong>：現金、轉帳、支票。</li><li><strong>收款人簽名或蓋章</strong>。</li></ul>
<h2>金額大寫對照</h2>
<table><thead><tr><th>數字</th><th>大寫</th></tr></thead><tbody>
<tr><td>1 2 3 4 5</td><td>壹 貳 參 肆 伍</td></tr><tr><td>6 7 8 9 0</td><td>陸 柒 捌 玖 零</td></tr><tr><td>十、百、千</td><td>拾、佰、仟</td></tr><tr><td>萬、億</td><td>萬、億</td></tr>
<tr><td>1,010</td><td>壹仟零壹拾元整</td></tr><tr><td>12,300</td><td>壹萬貳仟參佰元整</td></tr><tr><td>101,000</td><td>壹拾萬壹仟元整</td></tr><tr><td>100,001,000</td><td>壹億零壹仟元整</td></tr></tbody></table>
<p>中間有零時只寫一個「零」，例如 10,005 是「壹萬零伍元整」；某一段整段是零時也要補「零」，所以 100,001,000 是「壹億零壹仟元整」。</p>
<h2>營業用的收據</h2>
<p>在台灣，已核准免用統一發票的小規模營業人開給客人的收據，格式要符合國稅局的規定；這個範本是一般的收款證明，營業用請先向國稅局確認。</p>
<p>還沒成交的話，先用<a href="/tools/zh-hant/bao-jia-dan-fan-ben/">報價單範本</a>。在 iPhone 上，<a href="/invoiceqr/zh-hant/">開單、報價單、收據、送貨單產生器</a>收款結清後，同一份帳單可以直接當作收據分享。</p>
{ZH_NOTE}"""})

# 7e. 港台：農曆新年 2027 倒數（zh-Hant，Countdown）——09-29
# 依据：Google HK / TW 联想词（農曆新年 2027 日期 / 假期 / 香港假期 / 生肖；過年 倒數 幾天；2027 春節連假 / 放幾天；2027 過年時間）。
# 日期：GovHK「2027 年公眾假期」（初一 2/6 六、初三 2/8 一、初四 2/9 二，初二逢星期日→初四補假）；
# 行政院人事行政總處 116 年辦公日曆表新聞稿（春節假期 7 日，初一初二逢週末→2/9、2/10 補假；區間 2/4–2/10 據 104 職場力等轉述）。
# App 没有农历重复（HolidayTemplates.swift：农历节日是一次性，"Set to this year's date, which moves every year"）——页面教「明年另加新日期」。
CNY_EVE, CNY = dt.date(2027, 2, 5), dt.date(2027, 2, 6)
CNY_MD = lambda d: f"{d.month}月{d.day}日（星期{'一二三四五六日'[d.weekday()]}）"   # 句中不带年份，避免「年初一（2027年…（星期六））」括号套括号
PAGES.append({"path": "/tools/zh-hant/nong-li-xin-nian-2027/", "lang": "zh-Hant", "kind": "Article", "app": "countdown", "published": "2026-09-29",
  "title": "2027 農曆新年倒數：過年還有幾天？（除夕 2/5、初一 2/6）", "crumb": "農曆新年 2027",
  "description": "2027 年農曆新年是 2 月 6 日（星期六），除夕是 2 月 5 日。每天更新的過年倒數，加上台灣春節連假 7 天與香港公眾假期的日期。",
  "hub_title": "2027 農曆新年倒數", "hub_desc": "除夕、初一與港台假期日期，每天更新的過年倒數。",
  "js": [COUNT_JS], "faq": [
    ("2027 年農曆新年是哪一天？", f"大年初一是{fmt(CNY, 'zh-Hant')}，除夕是{fmt(CNY_EVE, 'zh-Hant')}。"),
    ("2027 年台灣過年放幾天？", f"依行政院人事行政總處公布的 116 年辦公日曆表，春節假期共 7 天，從{fmt(dt.date(2027, 2, 4), 'zh-Hant')}放到{fmt(dt.date(2027, 2, 10), 'zh-Hant')}；初一、初二逢週末，於2月9日、10日補假。"),
    ("2027 年香港農曆新年有哪幾天公眾假期？", f"年初一是{CNY_MD(CNY)}、年初三是{CNY_MD(dt.date(2027, 2, 8))}、年初四是{CNY_MD(dt.date(2027, 2, 9))}。年初二是星期日，所以年初四定為補假。"),
    ("2027 年是什麼生肖？", "羊年，天干地支是丁未。"),
    ("過年還有幾天？", f"在{TODAY.year}年{TODAY.month}月{TODAY.day}日，離大年初一還有 {days_to(CNY)} 天，約 {days_to(CNY) // 7} 週。本頁的倒數會在你打開當天重新計算。"),
    ("怎麼把過年倒數放在 iPhone 鎖定畫面？", "在倒數計時 Widget：紀念日提醒 建立2027年2月6日的事件，然後長按鎖定畫面 →「自訂」→ 鎖定畫面 → 加入小工具 → 選 Countdown。小工具全部尺寸都免費。"),
  ],
  "body": f"""<h1>2027 農曆新年倒數</h1>
<p class="lede">2027 年的農曆新年（大年初一）是<strong>{CNY_MD(CNY)}</strong>，除夕是{CNY_MD(CNY_EVE)}，這一年是羊年。下面的倒數每天更新。</p>
{counter(CNY, "zh-Hant", "大年初一")}
<h2>過年的日期</h2>
<table><tbody>
<tr><th>除夕</th><td>{fmt(CNY_EVE, "zh-Hant")}</td></tr>
<tr><th>初一</th><td>{fmt(CNY, "zh-Hant")}</td></tr>
<tr><th>初二</th><td>{fmt(dt.date(2027, 2, 7), "zh-Hant")}</td></tr>
<tr><th>初三</th><td>{fmt(dt.date(2027, 2, 8), "zh-Hant")}</td></tr>
<tr><th>初四</th><td>{fmt(dt.date(2027, 2, 9), "zh-Hant")}</td></tr>
<tr><th>生肖</th><td>羊（丁未年）</td></tr>
</tbody></table>
<h2>台灣：春節連假 7 天</h2>
<p>依行政院人事行政總處公布的 116 年政府行政機關辦公日曆表，春節假期從{fmt(dt.date(2027, 2, 4), "zh-Hant")}放到{fmt(dt.date(2027, 2, 10), "zh-Hant")}，共 7 天。初一、初二（2月6日、7日）剛好是週六、週日，所以在2月9日、10日補假。</p>
<h2>香港：農曆新年公眾假期</h2>
<p>依政府公布的 2027 年公眾假期，放假的是年初一{CNY_MD(CNY)}、年初三{CNY_MD(dt.date(2027, 2, 8))}和年初四{CNY_MD(dt.date(2027, 2, 9))}。年初二是星期日，所以年初四定為補假。</p>
<p class="meta">資料來源：行政院人事行政總處新聞稿、香港政府一站通「2027 年公眾假期」（{TODAY.year}年{TODAY.month}月{TODAY.day}日確認）。公司與學校的假期可能不同。</p>
<h2>把過年倒數放在鎖定畫面</h2>
<p>不想每次打開網頁，可以把倒數放在 iPhone 的主畫面或鎖定畫面。<a href="/countdown/zh-hant/">倒數計時 Widget：紀念日提醒</a>的小工具全部尺寸都免費，事件數量不限；倒數走到一百天、一週、當天早上這些節點時，App 會以整螢幕的數字打開，並給你一張可以分享的卡片。</p>
<ol><li>點 <strong>+</strong>，輸入「過年」。</li><li>日期設為2027年2月6日。農曆新年的國曆日期每年都不同，所以不要開「每年重複」；明年再另外加一個新日期。</li><li>長按鎖定畫面 →「自訂」→ 鎖定畫面 → 加入小工具 → Countdown。主畫面則是長按 →「編輯」→「加入小工具」（iOS 17 是長按後點左上角的「＋」）。</li></ol>
<p>點一下事件，它會翻到自己的背面：可以寫下年貨清單、放幾張照片，這一天的故事就留在這一天裡。</p>"""})

# 7d. 日本：あと何日（日数計算）+ 共通テスト2027（ja，Countdown）——09-29
# 依据：Google JP 联想词（共通テスト まであと何日 2027 / カウントダウン 待ち受け / あと何日 アプリ / 共通テスト 100日前 いつ；
# あと何日 計算 / 今日 入れる / あと何日で今年終わる、日数計算 / 営業日）。
# 日期出自大学入試センター「令和9年度試験」「令和10年度試験」页（09-29 取）：本試験 2027-01-16/17，追・再試験 01-23/24；2028-01-15/16。
# app 说法只用 ja 商店描述里「免费」那部分（ウィジェットはすべて無料 / ホーム画面・ロック画面 / 節目の全画面 / 裏面 / カウントアップ）；
# ⚠ jp 商店 09-29 还是 1.4.10，Pro 范围与 1.4.11 不同，所以页面不写 Pro 包含什么。
KT1, KT2, KTM1, KTM2, KT28A, KT28B = (dt.date(2027, 1, 16), dt.date(2027, 1, 17), dt.date(2027, 1, 23), dt.date(2027, 1, 24),
                                       dt.date(2028, 1, 15), dt.date(2028, 1, 16))
JA_APP = ("「カウントダウン ウィジェット: 記念日」は私たちの無料 iPhone アプリです。ウィジェットはすべて無料で、ホーム画面にもロック画面にも置けます。"
          "イベント数は無制限、繰り返しと通知、アカウント不要の iCloud 同期にも対応しています。")
PAGES.append({"path": "/tools/ja/ato-nannichi/", "lang": "ja", "kind": "WebApplication", "app": "countdown", "published": "2026-09-29",
  "title": "あと何日？日数計算ツール（今日から指定日まで）", "crumb": "あと何日？",
  "description": "日付を入れるだけで、今日からその日まであと何日か、何週間か、何曜日かを計算します。過ぎた日なら何日たったかも分かります。登録不要、結果はリンクで共有できます。",
  "hub_title": "あと何日？（日数計算）", "hub_desc": "今日から指定日までの日数と曜日。過ぎた日からの日数も。",
  "js": [COUNT_JS, CALC_JS], "faq": [
    ("今日は日数に入れますか？", "入れません。今日は0日、明日が1日です。指定した日そのものも足しません。「あと3日」なら、3回寝るとその日が来るという数え方です。"),
    ("営業日（土日祝日を除く）で数えられますか？", "いいえ。このツールは土日や祝日も含めた暦の上の日数で数えます。営業日で数えるときは、期間中の土日と祝日を引いてください。"),
    ("過ぎた日から何日たったかも分かりますか？", "はい。過去の日付を入れると、その日から何日たったかを表示します。カウントダウン ウィジェット: 記念日 でも、ある日からのカウントアップができます。"),
    ("結果を共有できますか？", "はい。計算すると、日付と名前が入ったリンクが作られます。開いた人には、開いた日に合わせて再計算された日数が表示されます。"),
    ("スマホに残り日数をずっと表示できるアプリは？", JA_APP),
  ],
  "body": f"""<h1>あと何日？</h1>
<p class="lede">日付を入れるだけで、今日からその日まで<strong>あと何日</strong>か、何週間か、何曜日かが分かります。過ぎた日なら、何日たったかを表示します。登録不要で、結果はリンクで共有できます。</p>
<form class="calc" id="calc"><label>イベント<input type="text" name="name" placeholder="誕生日、旅行、試験…" maxlength="60"></label><label>日付<input type="date" name="date" required></label><button type="submit">日数を数える</button></form>
<div id="calc-out" hidden aria-live="polite"></div>
<h2>よく数える日</h2>
<div class="pop">
<a href="/tools/ja/kyotsu-test-2027/" data-date="{KT1.isoformat()}"><b data-n>{days_to(KT1)}</b><span><span data-unit>日</span>（共通テスト2027まで）</span></a>
<a href="/tools/days-until-new-year/" hreflang="en" data-date="{NYE.isoformat()}"><b data-n>{days_to(NYE)}</b><span><span data-unit>日</span>（2027年のお正月まで）</span></a>
</div>
<p class="meta">上の数字は {TODAY.year}年{TODAY.month}月{TODAY.day}日に計算したもので、ページを開いたときに更新されます。お正月のページは英語です。</p>
<h2>数え方</h2>
<p>今日を0日として、指定した日までに日付が何回変わるかを数えます。時刻はあなたの端末のタイムゾーンで数えます。指定した日が今日なら0日、過去の日付なら「何日たったか」になるので、記念日や禁煙の日数にも使えます。</p>
<p>サイトを開かなくても残り日数が見えるように、下のアプリで iPhone のホーム画面やロック画面に置くこともできます。</p>"""})

PAGES.append({"path": "/tools/ja/kyotsu-test-2027/", "lang": "ja", "kind": "Article", "app": "countdown", "published": "2026-09-29",
  "title": "共通テスト2027まであと何日？カウントダウン（1月16日・17日）", "crumb": "共通テスト2027",
  "description": f"2027年の大学入学共通テストは1月16日（土）・17日（日）。本試験まであと何日かを毎日更新でカウントダウンし、100日前・1週間前の日付と、iPhoneのロック画面に置く方法をまとめました。",
  "hub_title": "共通テスト2027まであと何日？", "hub_desc": "本試験（1月16日・17日）までのカウントダウンと、100日前・30日前・1週間前の日付。",
  "js": [COUNT_JS], "faq": [
    ("共通テスト2027はいつですか？", f"本試験は{fmt(KT1, 'ja')}と{fmt(KT2, 'ja')}です。追・再試験は{fmt(KTM1, 'ja')}と{fmt(KTM2, 'ja')}です（大学入試センター「令和9年度試験」）。"),
    ("共通テストまであと何週間ですか？", f"{TODAY.year}年{TODAY.month}月{TODAY.day}日の時点で本試験まで{days_to(KT1)}日、約{days_to(KT1) // 7}週間です。このページのカウントダウンは、開いた日に合わせて再計算されます。"),
    ("共通テストの100日前はいつですか？", f"{fmt(KT1 - dt.timedelta(days=100), 'ja')}です。50日前は{fmt(KT1 - dt.timedelta(days=50), 'ja')}、1週間前は{fmt(KT1 - dt.timedelta(days=7), 'ja')}です。"),
    ("2028年の共通テストはいつですか？", f"令和10年度の本試験は{fmt(KT28A, 'ja')}と{fmt(KT28B, 'ja')}です（大学入試センター「令和10年度試験」）。"),
    ("iPhone の待ち受け（ロック画面）にカウントダウンを置くには？", "カウントダウン ウィジェット: 記念日で「共通テスト」を2027年1月16日に作り、ロック画面を長押し →「カスタマイズ」→ ロック画面 → ウィジェットを追加 → Countdown、の順に進みます。ウィジェットはすべて無料です。"),
  ],
  "body": f"""<h1>共通テスト2027まであと何日？</h1>
<p class="lede">令和9年度（2027年）の大学入学共通テストは、<strong>{fmt(KT1, "ja")}・{KT2.day}日（{'月火水木金土日'[KT2.weekday()]}）</strong>です。下のカウントダウンは毎日更新されます。</p>
{counter(KT1, "ja", "本試験1日目")}
<h2>日程</h2>
<table><tbody>
<tr><th>本試験</th><td>{fmt(KT1, "ja")}・{fmt(KT2, "ja")}</td></tr>
<tr><th>追・再試験</th><td>{fmt(KTM1, "ja")}・{fmt(KTM2, "ja")}</td></tr>
<tr><th>2028年（令和10年度）の本試験</th><td>{fmt(KT28A, "ja")}・{fmt(KT28B, "ja")}</td></tr>
</tbody></table>
<p class="meta">出典：大学入試センター「令和9年度試験」「令和10年度試験」（{TODAY.year}年{TODAY.month}月{TODAY.day}日に確認）。出願の手続きや時間割は、大学入試センターの案内で確認してください。</p>
<h2>節目の日付</h2>
<table><thead><tr><th>節目</th><th>日付</th></tr></thead><tbody>{"".join(f"<tr><td>{k}</td><td>{fmt(KT1 - dt.timedelta(days=n), 'ja')}</td></tr>" for k, n in (("100日前", 100), ("50日前", 50), ("30日前", 30), ("1週間前", 7), ("前日", 1)))}</tbody></table>
<h2>ロック画面・待ち受けに置く</h2>
<p>毎回サイトを開かなくても残り日数が見えるように、iPhone のロック画面やホーム画面にウィジェットとして置けます。<a href="/countdown/ja/">カウントダウン ウィジェット: 記念日</a>なら、すべてのサイズのウィジェットが無料です。100日前・1週間前・当日の朝といった節目に達すると、アプリが全画面の数字で開き、共有できるカードを用意します。</p>
<ol><li>アプリで <strong>+</strong> をタップし、「共通テスト」と入力します。</li><li>日付を{fmt(KT1, "ja")}に設定します。通知は当日のほか、何日前でも好きなだけ追加できます。</li><li>ロック画面を長押し →「カスタマイズ」→ ロック画面 → ウィジェットを追加 → Countdown。ホーム画面なら、長押し →「編集」→「ウィジェットを追加」です（iOS 17 では長押しして左上の「＋」）。</li></ol>
<h2>カウントダウンの使い方</h2>
<ul><li>イベントの裏面に、科目ごとの目標や模試の結果を書いておく。</li><li>追・再試験や二次試験、私立大学の入試日も別のイベントにして、「次の予定リスト」のウィジェットで並べる。</li><li>過ぎた日は削除されず、振り返れるタイムラインとして残ります。</li></ul>
<p>ほかの日付は<a href="/tools/ja/ato-nannichi/">あと何日？（日数計算）</a>で数えられます。</p>"""})

# 8. 如何写发票（指南）
PAGES.append({"path": "/tools/how-to-write-an-invoice/", "lang": "en", "kind": "Article", "app": "invoiceqr", "published": "2026-09-26",
  "title": "How to Write an Invoice (freelancers & small businesses) — 8 steps", "crumb": "How to write an invoice",
  "description": "How to write an invoice that gets paid: what to include, how to number it, payment terms that work, and the mistakes that delay payment. With a free template.",
  "hub_title": "How to write an invoice", "hub_desc": "The eight things every invoice needs, numbering, payment terms and the mistakes that delay payment.",
  "faq": [
    ("What should I put on an invoice?", "The word Invoice, a unique number, issue and due dates, your business details, the client's details, each item with quantity and price, subtotal, tax and total, and how to pay. Add your tax ID if your country requires it."),
    ("How do I number invoices?", "Sequentially and never reused: INV-0001, INV-0002… Many freelancers prefix the year (2026-001) so the sequence resets each January. Never reuse a number, and check local rules: some countries, such as France and Germany, expect an unbroken sequence."),
    ("What payment terms should a freelancer use?", "Net 14 or Net 30 are the most common — payment due 14 or 30 days after the invoice date. For new clients or small jobs, 'due on receipt' is normal. State the terms and the due date on the invoice itself."),
    ("Can I charge a late fee?", "Usually yes if the terms were agreed before the work — put them on the estimate or contract and repeat them on the invoice. Check local rules; some countries cap late interest."),
    ("What's the difference between an invoice and a receipt?", "An invoice asks for payment and has a due date. A receipt confirms that payment was made. Once an invoice is paid, the same document marked Paid with the paid date can serve as the receipt."),
  ],
  "body": f"""<h1>How to write an invoice</h1>
<p class="lede">An invoice is a request for payment. Done right, it answers every question the client's accountant might have, so it goes straight to the "pay" pile. Here is what goes on it, in the order people read it.</p>
<h2>The 8 things every invoice needs</h2>
<ol>
<li><strong>The word "Invoice" and a unique number.</strong> Sequential (INV-0001, INV-0002…), never reused. Accountants file by number.</li>
<li><strong>Issue date and due date.</strong> "Due on receipt", "Net 14" or "Net 30" — and write the actual due date, not just the term.</li>
<li><strong>Who you are.</strong> Business name, address, email, phone, and your tax or registration ID if required where you are.</li>
<li><strong>Who the client is.</strong> Legal name and billing address; the person who ordered the work if it's a large company.</li>
<li><strong>What you did.</strong> One line per item or milestone: description, quantity, unit price, amount. Clear descriptions get paid faster than "Services rendered".</li>
<li><strong>Subtotal, tax and total.</strong> Show the tax rate. If you don't charge tax, say so if your jurisdiction expects a note.</li>
<li><strong>How to pay.</strong> Bank details, a payment link, or a payment QR code the client can scan with their phone. Fewer steps, faster payment.</li>
<li><strong>Terms and a thank-you.</strong> Late-fee terms if agreed, a reference to the estimate or contract, and one polite line.</li>
</ol>
<h2>Numbering that survives an audit</h2>
<p>Pick one pattern and keep it: <code>INV-0042</code>, or year-based <code>2026-042</code>. Estimates get their own prefix (<code>EST-</code>) so they never collide with invoices. When an estimate is accepted, the invoice should reference it ("as per estimate EST-017").</p>
<h2>Payment terms that actually work</h2>
<table><thead><tr><th>Term</th><th>Meaning</th><th>Use it when</th></tr></thead><tbody>
<tr><td>Due on receipt</td><td>Pay now</td><td>Small jobs, new clients, retail</td></tr>
<tr><td>Net 14</td><td>Within 14 days</td><td>Freelance work, repeat clients</td></tr>
<tr><td>Net 30</td><td>Within 30 days</td><td>Companies with accounts-payable cycles</td></tr>
<tr><td>50% upfront</td><td>Half before, half after</td><td>Projects longer than a couple of weeks</td></tr></tbody></table>
<h2>Mistakes that delay payment</h2>
<ul><li>No due date, only "Net 30" — the client has to compute it, and won't.</li><li>Vague line items. "Consulting" gets queried; "Kick-off workshop, 3 h, 12 March" gets paid.</li><li>Missing bank details or a wrong account number — the most common reason for a two-week delay.</li><li>Sending it to the wrong person. Ask who approves invoices before you send the first one.</li><li>No follow-up. A friendly reminder the day after the due date is normal and expected.</li></ul>
<h2>Do it in a minute</h2>
<p>Use the <a href="/tools/invoice-template/">free invoice template</a> on this site for a one-off. If you invoice regularly, <a href="/invoiceqr/">Smart Invoice &amp; Estimate Maker</a> on iPhone keeps clients, items and tax rates, puts a payment QR code on each one and shows what's paid, unpaid and overdue.</p>"""})

# 9. 打包清单
PACK = {"base": {
  "Documents & money": ["Passport or ID", "Tickets and booking confirmations", "Travel insurance details", "Bank card + some local cash", "Copies of documents (photo on your phone)"],
  "Clothes": ["Underwear × {n}", "Socks × {n}", "T-shirts / tops × {n}", "Trousers or skirts × 2", "One warm layer", "Sleepwear", "Comfortable walking shoes"],
  "Toiletries": ["Toothbrush and toothpaste", "Deodorant", "Shampoo / soap (travel size)", "Razor", "Sunscreen", "Any medication you take", "Small first-aid kit"],
  "Tech": ["Phone and charger", "Power adapter for the destination", "Power bank", "Headphones"],
  "Extras": ["Reusable water bottle", "Day bag", "Snacks for the journey", "Pen"]},
 "types": {
  "beach": [["Clothes", ["Swimwear × 2", "Flip-flops or sandals", "Hat", "Light cover-up"]], ["Extras", ["Sunglasses", "Beach towel", "After-sun lotion", "Waterproof phone pouch", "Book or e-reader"]]],
  "city": [["Clothes", ["One smart outfit", "Light rain jacket"]], ["Extras", ["Transit card or app installed", "Umbrella", "Museum / attraction tickets booked"]]],
  "winter": [["Clothes", ["Thermal base layers × 2", "Fleece or wool mid-layer", "Insulated jacket", "Waterproof trousers", "Gloves, hat, scarf", "Warm boots", "Ski socks × {n}"]], ["Extras", ["Lip balm", "Hand warmers", "Goggles or sunglasses", "Ski pass / lift tickets"]]],
  "business": [["Clothes", ["Suit or blazer", "Dress shirts × 3", "Formal shoes", "Belt and tie"]], ["Tech", ["Laptop and charger", "Presentation clicker", "Business cards"]], ["Extras", ["Meeting agenda printed or saved offline", "Steamer or wrinkle-release spray"]]],
  "backpacking": [["Clothes", ["Quick-dry clothes", "Rain shell", "Sandals + hiking shoes"]], ["Extras", ["Padlock", "Microfibre towel", "Earplugs and eye mask", "Sewing kit", "Dry bag", "Laundry detergent sheets"]]]}}

PAGES.append({"path": "/tools/packing-list/", "lang": "en", "kind": "WebApplication", "app": "beforego", "published": "2026-09-26",
  "title": "Packing List Generator — free checklist you can tick off and print", "crumb": "Packing list",
  "description": "Free packing list generator: pick the trip type and length and get a travel checklist you can tick off, print or copy. Beach, city, winter, business or backpacking.",
  "hub_title": "Packing list generator", "hub_desc": "Pick trip type and length, get a checklist you can tick, print or copy.",
  "js": [PACK_JS], "faq": [
    ("How many clothes should I pack for a 7-day trip?", "A good rule is one set of underwear and socks per day and half as many tops, then wear each pair of trousers two or three times. For a week: 7 underwear, 7 socks, 4 tops, 2 trousers, one warm layer. Plan one laundry day for anything longer than 10 days."),
    ("Does the checklist remember what I ticked?", "Yes, in this browser. Ticks are stored on your device and come back when you reopen the page; nothing is sent anywhere. Use the app if you want the list on your phone with reminders."),
    ("What do people forget most often?", "Chargers and the right power adapter, medication, a copy of the passport, sunscreen, and the one thing they forgot on the last trip too — which is exactly what BeforeGo carries over to the next packing list."),
    ("When should I start packing?", "Put the documents and bookings together a week out, pack clothes and toiletries three days before, and do a final check the night before: passport, tickets, wallet, phone, charger, keys."),
    ("Is there an app that makes the packing list for my destination?", "BeforeGo: AI Itinerary Planner writes the packing list from your destination and dates — plugs, currency, entry rules and transit apps for where you are going — with reminders at 7 days, 3 days, 24 hours and 3 hours before departure."),
  ],
  "body": f"""<h1>Packing list generator</h1>
<p class="lede">Pick the kind of trip and how long you're going. You get a checklist you can tick off, print, or copy into your notes. Ticks are saved on this device.</p>
<form class="calc pack-head" id="pack"><label>Trip type<select name="type"><option value="beach">Beach</option><option value="city" selected>City break</option><option value="winter">Winter / ski</option><option value="business">Business</option><option value="backpacking">Backpacking</option></select></label>
<label>Length<select name="days"><option value="3">Weekend (3 days)</option><option value="7" selected>One week</option><option value="14">Two weeks</option></select></label><button type="submit">Make my list</button></form>
<div id="pack-out" hidden></div>
<p id="pack-actions" hidden><button class="btn ghost" id="pack-print" type="button">Print</button> <button class="btn ghost" id="pack-copy" type="button">Copy as text</button></p>
<script type="application/json" id="pack-data">{json.dumps(PACK)}</script>
<h2>The three-day rule</h2>
<p>Documents and bookings a week before. Clothes and toiletries three days before, so there is time to buy what's missing. The night before, only the six things that cannot be replaced at the destination: passport, tickets, wallet, phone, charger, keys.</p>
<h2>What people forget</h2>
<ul><li>The <strong>power adapter</strong> for the destination's sockets — the plug type matters more than the voltage.</li><li><strong>Medication</strong> for the whole trip plus a couple of days.</li><li>A <strong>photo of the passport</strong> on the phone.</li><li><strong>Sunscreen</strong> — pricey at resorts, hard to find in cities.</li><li>The thing you forgot last time. That is the one to write down now.</li></ul>
<p>For a list built for your actual destination and dates — plugs, currency, entry rules, transit apps, and reminders before departure — that is what <a href="/beforego/">BeforeGo</a> does on iPhone, and it carries the forgotten items over to the next trip.</p>"""})


# 10. 榜单：iPhone 倒数日 app（含竞品；数据来自 09-26 美区 App Store 查询，只写商店描述里写明的事）
BEST = [
  {"name": "Countdown Widget: Any Event", "by": "go ka (that's us)", "id": 6799846628, "rating": None, "since": 2026, "ours": True,
   "free": "Unlimited events, every widget size on Home Screen and Lock Screen, reminders, repeats, iCloud sync — all free. Pro adds backdrops, your own photos, typefaces, the Live Activity and counting down with someone you invite.",
   "widgets": "Home Screen + Lock Screen, all sizes, free", "recur": "Yearly, monthly, weekly, every N days", "sync": "iCloud, no account", "ads": "None",
   "take": "Here the widgets are not the paid feature: every widget size, unlimited events, recurring dates, reminders and iCloud sync are free; the subscription adds backdrops, your own photos behind a countdown, the Pro typefaces, the Lock Screen Live Activity and inviting someone to count down with you. It also keeps a daily on-device snapshot so an update or reinstall never loses the events. New in 2026, so it has few ratings yet — judge it by what the free tier covers."},
  {"name": "Countdown Star", "by": "Joseph Merrill", "id": 576177593, "rating": (4.8, 215672), "since": 2012,
   "free": "Add as many events as you like; iCloud sync, repeating events and Home Screen widgets are listed as features (the listing does not spell out what is paid).",
   "widgets": "Home Screen (small, medium, large) + Apple Watch", "recur": "Annual events advance automatically", "sync": "iCloud across iPhone, iPad, Apple Watch", "ads": "Not stated",
   "take": "The veteran: on the App Store since 2012 with over 200,000 ratings. Strong on the countdown itself — time-zone support, a slider that flips between seconds and years, celebration animations at zero, and an Apple Watch app. The listing does not describe Lock Screen widgets."},
  {"name": "Countdown", "by": "Find Appiness LLC", "id": 1403367428, "rating": (4.8, 186570), "since": 2018,
   "free": "Unlimited events, count-up, iCloud sync and reminders 1 day / 1 week before. Home Screen widget, Lock Screen widget, StandBy and calendar auto-import are Premium.",
   "widgets": "Home Screen, Lock Screen, StandBy — Premium", "recur": "Yearly, monthly, weekly, daily", "sync": "iCloud", "ads": "Not stated",
   "take": "Very popular and easy to use, with sharing and a StandBy widget. The catch for widget fans: the listing marks the Home Screen widget, the Lock Screen widget and calendar auto-import as Premium features, so the free version is mostly the in-app list."},
  {"name": "Countdown: Event Countdown", "by": "ROOT38 LIMITED", "id": 983258067, "rating": (4.7, 23840), "since": 2015,
   "free": "Unlimited countdowns and a Next Event Home Screen widget are free; the ticking, multi-event, Lock Screen and StandBy widgets are part of the paid tier.",
   "widgets": "Next Event widget free; live, multi-event, Lock Screen, StandBy paid", "recur": "Repeats, shows ages on birthdays", "sync": "Not stated", "ads": "Not stated",
   "take": "The prettiest calendar view of the group: every event on a month grid, colour-coded, with Live Activities in the Dynamic Island as the moment approaches and countdowns you can export as a video. Unlimited events are free; most widget sizes are not."},
  {"name": "DayCount", "by": "Zaminiti Pty Ltd", "id": 1121088244, "rating": (4.7, 26260), "since": 2016,
   "free": "Event counters, categories, notes, streaks; reminders before or after events; widgets with custom fonts and textures (the listing does not state a free limit).",
   "widgets": "Home Screen + Lock Screen, custom filters and textures", "recur": "Daily, weekly, fortnightly, monthly, yearly, custom", "sync": "Not stated", "ads": "Not stated",
   "take": "For people who count in both directions: counters track time before and after the date, streaks sit next to events, and reminders can fire minutes to years before or after. Widgets are unusually configurable — filters, fonts, textures, borders — on both Home and Lock Screen."},
  {"name": "Countdown Buddy", "by": "Taptics Ltd.", "id": 1534850579, "rating": (4.6, 25893), "since": 2020,
   "free": "One countdown widget with the basic design; 11 widget styles and more widgets are paid.",
   "widgets": "Home Screen + Lock Screen, small and medium, 11 styles", "recur": "Not stated; weekend exclusion for deadlines", "sync": "Not stated", "ads": "Not stated",
   "take": "A widget designer more than an event list: you build a countdown or count-up widget from 11 styles and drop it on the Home or Lock Screen, and work deadlines can skip weekends. The free version is one basic widget, so it is best if you only ever need one countdown."},
  {"name": "Days • Countdown & Widgets", "by": "MD Apps LTD", "id": 939368917, "rating": (4.8, 12517), "since": 2015,
   "free": "Countdown and count-up with full-screen photos, Home Screen and Lock Screen widgets, recurring events (the listing does not state a free limit).",
   "widgets": "Home Screen + Lock Screen", "recur": "Yearly, monthly, weekly", "sync": "Not stated", "ads": "Not stated",
   "take": "The photo-first option: each event is a full-screen picture you swipe through, with subtle animations. Recurring birthdays and anniversaries, count-up for past events, and widgets on both screens."},
]
def best_page():
    rows = "".join(f"<tr><th>{esc(b['name'])}{' <small>(ours)</small>' if b.get('ours') else ''}</th><td>{esc(b['free'])}</td><td>{esc(b['widgets'])}</td><td>{esc(b['recur'])}</td><td>{esc(b['sync'])}</td><td>{('★ %.1f · %s ratings' % (b['rating'][0], format(b['rating'][1], ','))) if b['rating'] else 'New in 2026 — few ratings yet'}</td></tr>" for b in BEST)
    entries = "".join(f"""<h3>{i}. {esc(b['name'])} <span style="font-weight:400;color:var(--soft)">— {esc(b['by'])}</span></h3>
<p>{esc(b['take'])}</p>
<p><strong>Free tier:</strong> {esc(b['free'])}<br><strong>Widgets:</strong> {esc(b['widgets'])} · <strong>Repeats:</strong> {esc(b['recur'])} · <strong>Sync:</strong> {esc(b['sync'])}</p>
<p><a href="{'/countdown/' if b.get('ours') else 'https://apps.apple.com/us/app/id%d' % b['id']}"{'' if b.get('ours') else ' rel="nofollow noopener"'}>{'Our product page' if b.get('ours') else 'View on the App Store'} →</a></p>""" for i, b in enumerate(BEST, 1))
    body = f"""<h1>Best countdown widget apps for iPhone (2026)</h1>
<p class="lede">Seven countdown apps that put a widget on your Home Screen or Lock Screen, compared on the things that actually differ: what the free tier includes, which widgets cost money, repeats, reminders and sync. Data comes from each app's US App Store listing on 26 September 2026. One of the seven is ours; it is marked, and it is judged by the same table as the rest.</p>
<h2>The comparison</h2>
<table class="cmp"><thead><tr><th>App</th><th>Free tier</th><th>Widgets</th><th>Repeats</th><th>Sync</th><th>US rating</th></tr></thead><tbody>{rows}</tbody></table>
<p class="meta">"Not stated" means the App Store description does not say. Ratings are the US storefront on 26 September 2026 and change daily.</p>
<h2>Which one to pick</h2>
<ul>
<li><strong>You want widgets without paying:</strong> Countdown Widget: Any Event (ours) — every widget size is free, and so are unlimited events, repeats, reminders and iCloud sync. Countdown: Event Countdown gives you one free Next Event widget.</li>
<li><strong>You want the longest track record:</strong> Countdown Star — on the App Store since 2012, with over 200,000 ratings, with an Apple Watch app and time zones per event.</li>
<li><strong>You count streaks and time since:</strong> DayCount — counters run before and after the date, with reminders on either side.</li>
<li><strong>You want the prettiest calendar:</strong> Countdown: Event Countdown — month grid, Live Activities, countdown videos.</li>
<li><strong>You only need one widget and want to design it:</strong> Countdown Buddy — 11 widget styles, one free.</li>
<li><strong>You want full-screen photos:</strong> Days • Countdown & Widgets.</li>
</ul>
<h2>The seven apps</h2>
{entries}
<h2>How we chose</h2>
<p>We searched the US App Store for "countdown widget", "days until countdown" and "countdown app", took the countdown-specific apps with the most ratings, and read each listing for what it says about the free tier, widgets, repeats, reminders and sync. Apps that are general widget makers (Widgetsmith) or visual timers for kids were left out. We did not test paid tiers, and we did not rank by rating — the list is grouped by what each app is best at. We make one of these apps; it is included because it is a countdown widget app for iPhone, and it is described with the same fields as everyone else.</p>"""
    return {"path": "/tools/best-countdown-widget-apps-iphone/", "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-09-26",
            "title": "Best Countdown Widget Apps for iPhone (2026) — free tiers compared", "crumb": "Best countdown widget apps",
            "description": "Seven iPhone countdown widget apps compared on free tier, which widgets cost money, repeats, reminders and sync — from their App Store listings, Sept 2026.",
            "hub_title": "Best countdown widget apps for iPhone (2026)", "hub_desc": "Seven apps compared on free tier, widgets, repeats, reminders and sync.",
            "items": [{"name": b["name"], "url": ("https://apps.apple.com/us/app/id%d" % b["id"])} for b in BEST],
            "faq": [
              ("Which countdown app has free Lock Screen widgets on iPhone?", "Countdown Widget: Any Event (ours) makes every widget size free, on both the Home Screen and the Lock Screen. In Countdown by Find Appiness and Countdown: Event Countdown, the Lock Screen widget is part of the paid tier according to their listings; DayCount and Days list Lock Screen widgets without stating a limit."),
              ("Which countdown apps allow unlimited events for free?", "Countdown Widget: Any Event, Countdown Star ('add as many events as you like'), Countdown by Find Appiness ('create as many events as you'd like') and Countdown: Event Countdown ('unlimited countdowns') all state unlimited events in their free version."),
              ("Do these apps sync between iPhone and iPad?", "Countdown Widget: Any Event, Countdown Star and Countdown by Find Appiness list iCloud sync. The other listings do not state it."),
              ("Can I count up from a past date?", "Yes in Countdown Widget: Any Event, Countdown Star, Countdown by Find Appiness, DayCount, Countdown Buddy and Days — all list count-up from a past date."),
              ("Is this list independent?", "We make Countdown Widget: Any Event, so no. Everything in the table comes from the public App Store listings, the fields are the same for every app, and each competitor is linked so you can check. We did not test paid tiers."),
            ], "js": [], "body": body}
PAGES.append(best_page())

# 10b. 葡语榜单（09-29）：联想词 app contagem regressiva (iphone / widget / grátis)、melhor app de contagem regressiva、
# widget contagem regressiva iphone gratuito。选法同英文版：巴西区搜「contagem regressiva」「countdown widget」，
# 取倒数专用 app 里巴西评分数最多的 6 个（Widgetsmith 是通用小组件，不收），只写 BR 商店描述（lang=pt_br，09-29 lookup）里写明的事。
BEST_PT = [
  {"name": "Countdown: Contagem regressiva", "by": "go ka (o nosso)", "id": 6799846628, "t": ("Tudo grátis; Pro: fundos, fotos e extras", "Início e Bloqueada, todos grátis", "Ano, mês, semana, a cada N dias", "iCloud, sem conta", "Não"), "rating": None, "since": 2026, "ours": True,
   "free": "Eventos ilimitados, todos os widgets na Tela de Início e na Tela Bloqueada, repetição, lembretes e iCloud — tudo grátis. O Pro libera fundos Pro, suas próprias fotos, fontes, a Atividade ao Vivo e o convite para contar junto.",
   "widgets": "Tela de Início e Tela Bloqueada, todos os tamanhos, grátis", "recur": "Todo ano, mês, semana ou a cada poucos dias", "sync": "iCloud, sem criar conta", "ads": "Sem anúncios",
   "take": "Aqui os widgets não são o recurso pago: todos os tamanhos, eventos ilimitados, repetição, lembretes e sincronização com o iCloud são grátis; a assinatura libera fundos Pro, suas próprias fotos como fundo, as fontes Pro, a Atividade ao Vivo na Tela Bloqueada e o convite para alguém contar junto com você. Guarda todo dia uma cópia dos eventos no aparelho, para que uma atualização não apague nada, e cada evento tem um verso com texto, fotos e voz. É novo em 2026 e ainda tem poucas avaliações no Brasil — julgue pelo que a versão grátis cobre."},
  {"name": "Countdown Star", "by": "Joseph Merrill", "id": 576177593, "t": ("Com anúncios; uma compra remove", "Início (P, M, G)", "Anual", "iCloud + Apple Watch", "Sim, na grátis"), "rating": (4.8, 16068), "since": 2012,
   "free": "Versão gratuita com anúncios e uma compra opcional para removê-los; há também uma versão paga sem anúncios. iCloud, recorrência e widgets aparecem como recursos, sem separar o que é pago.",
   "widgets": "Tela de Início: pequeno, médio e grande", "recur": "Eventos anuais avançam sozinhos", "sync": "iCloud (iPhone, iPad, Apple Watch)", "ads": "Sim, na versão grátis",
   "take": "O veterano: está na App Store desde 2012 e é o mais avaliado entre os apps que encontramos na App Store do Brasil. Conta para frente e para trás, sincroniza com o Apple Watch e agrupa os eventos em contagem regressiva e progressiva. A versão grátis tem anúncios; a descrição não fala em widget na Tela Bloqueada."},
  {"name": "Widget Casal: Dias Juntos", "by": "Jae Young Kim", "id": 1127692604, "t": ("Não informado", "Início, com fotos do casal", "Não informado", "Com o parceiro", "Não informado"), "rating": (4.7, 9956), "since": 2016,
   "free": "Não informado.", "widgets": "Tela de Início, com temas e fotos do casal", "recur": "Não informado", "sync": "Compartilhado com o parceiro", "ads": "Não informado",
   "take": "Não é um app de contagem regressiva geral: é feito para casais. Mostra os dias juntos em tempo real, lembra dos 10 e dos 100 dias, tem um diário do casal com fotos, um calendário com os aniversários e deixa o parceiro comentar e curtir as publicações."},
  {"name": "Contagem Regressiva ◎", "by": "Find Appiness LLC", "id": 1403367428, "t": ("Eventos sem limite; widgets Premium", "Início e bloqueada — Premium", "Ano, mês, semana", "iCloud", "Não informado"), "rating": (4.8, 5263), "since": 2018,
   "free": "Contador grátis com eventos sem limite, lembrete 1 dia ou 1 semana antes, iCloud, repetição e Apple Watch; os widgets da Tela de Início e da tela bloqueada e os formatos de contagem são Premium.",
   "widgets": "Tela de Início e tela bloqueada — Premium", "recur": "Todo ano, mês ou semana", "sync": "iCloud", "ads": "Não informado",
   "take": "Gratuito e muito fácil de usar: eventos sem limite, lembretes 1 dia e 1 semana antes, repetição, iCloud, Apple Watch, compartilhamento, tags e contagem para a frente de eventos passados. O ponto para quem quer widget: a descrição marca como Premium o widget da Tela de Início, o da tela bloqueada e a escolha do formato da contagem — sem pagar, a contagem fica no app e no Apple Watch."},
  {"name": "Big Days - Contagem Regressiva", "by": "astrovicApps", "id": 940109775, "t": ("Não informado", "Início e Em Espera", "Não informado", "Não informado", "Não informado"), "rating": (4.7, 981), "since": 2014,
   "free": "Não informado.", "widgets": "Tela de Início e modo Em Espera", "recur": "Não informado", "sync": "Não informado", "ads": "Não informado",
   "take": "Para quem gosta de foto: cada contagem tem papel de parede, com busca de imagens do Pixabay dentro do app, dezenas de fontes e a opção de exportar a contagem para as redes sociais ou salvar como papel de parede. Conta os dias que faltam e os que já passaram, com lembretes personalizados."},
  {"name": "Countdown Buddy", "by": "Taptics Ltd.", "id": 1534850579, "t": ("Não informado", "Início, 10 estilos", "Não informado", "Não informado", "Não informado"), "rating": (4.8, 810), "since": 2020,
   "free": "Não informado.", "widgets": "Tela de Início, 10 estilos", "recur": "Não informado", "sync": "Não informado", "ads": "Não informado",
   "take": "Mais um criador de widget do que uma lista de eventos: você monta um widget de contagem regressiva ou progressiva escolhendo entre 10 estilos e coloca na Tela de Início. Bom para quem só precisa de uma ou duas contagens à vista."},
  {"name": "Contagens - Tempo de Eventos", "by": "Shayes Apps LLC", "id": 917514700, "t": ("Widgets grátis; iCloud pago", "iPhone, iPad e Mac — grátis", "Sim, grátis", "iCloud (pago)", "Não informado"), "rating": (4.8, 709), "since": 2014,
   "free": "Grátis: widgets no iPhone, iPad e Mac, timers ilimitados e timers que repetem. iCloud e notificações personalizadas são pagos (assinatura ou compra única).",
   "widgets": "iPhone, iPad e Mac — grátis", "recur": "Timers que repetem (grátis)", "sync": "iCloud — pago", "ads": "Não informado",
   "take": "Para quem usa vários aparelhos: os timers rodam no iPhone, iPad, Mac e Apple Watch e contam para frente ou para trás — dos dias sem fumar ao próximo evento. Widgets e timers ilimitados são grátis; a sincronização pelo iCloud é paga."},
]
def best_page_pt():
    rate = lambda b, short=False: ("★ %s · %s%s" % (str(b["rating"][0]).replace(".", ","), format(b["rating"][1], ",").replace(",", "."), "" if short else " avaliações")) if b["rating"] else ("Novo (poucas avaliações)" if short else "Novo em 2026 — poucas avaliações")
    link = lambda b: "/countdown/pt-br/" if b.get("ours") else "https://apps.apple.com/br/app/id%d" % b["id"]
    rows = "".join(f"<tr><th>{esc(b['name'])}{' <small>(nosso)</small>' if b.get('ours') else ''}</th>" + "".join(f"<td>{esc(x)}</td>" for x in b["t"]) + f"<td>{esc(rate(b, short=True))}</td></tr>" for b in BEST_PT)
    entries = "".join(f"""<h3>{i}. {esc(b['name'])} <span style="font-weight:400;color:var(--soft)">— {esc(b['by'])}</span></h3>
<p>{esc(b['take'])}</p>
<p><strong>Versão grátis:</strong> {esc(b['free'])}<br><strong>Widgets:</strong> {esc(b['widgets'])} · <strong>Repetição:</strong> {esc(b['recur'])} · <strong>Sincronização:</strong> {esc(b['sync'])} · <strong>Anúncios:</strong> {esc(b['ads'])}</p>
<p><a href="{link(b)}"{'' if b.get('ours') else ' rel="nofollow noopener"'}>{'A nossa página do app' if b.get('ours') else 'Ver na App Store'} →</a></p>""" for i, b in enumerate(BEST_PT, 1))
    body = f"""<h1>Melhores apps de contagem regressiva para iPhone (2026)</h1>
<p class="lede">Sete apps de contagem regressiva para iPhone comparados no que realmente muda de um para outro: o que a versão grátis inclui, quais widgets são pagos, repetição, sincronização e anúncios. Os dados vêm da página de cada app na App Store do Brasil em 29 de setembro de 2026. Um dos sete é nosso; ele está marcado e é julgado pela mesma tabela que os outros.</p>
<h2>A comparação</h2>
<table class="cmp"><thead><tr><th>App</th><th>Versão grátis</th><th>Widgets</th><th>Repetição</th><th>Sincronização</th><th>Anúncios</th><th>Nota no Brasil</th></tr></thead><tbody>{rows}</tbody></table>
<p class="meta">«Não informado» quer dizer que a descrição na App Store não diz. As avaliações são da App Store do Brasil em 29/09/2026 e mudam todo dia.</p>
<h2>Qual escolher</h2>
<ul>
<li><strong>Quer widget sem pagar:</strong> Countdown: Contagem regressiva (o nosso) — todos os tamanhos são grátis, na Tela de Início e na Tela Bloqueada, sem anúncios. No Contagens, os widgets também fazem parte da versão gratuita.</li>
<li><strong>Quer o mais avaliado desta lista:</strong> Countdown Star — desde 2012, com mais de 16 mil avaliações no Brasil e sincronização com o Apple Watch; a versão grátis tem anúncios.</li>
<li><strong>Quer contar os dias de namoro:</strong> Widget Casal — feito para casais, com diário de fotos e lembretes de 10 e 100 dias. Para só calcular, use o nosso <a href="/tools/pt-br/contador-de-dias-de-namoro/">contador de dias de namoro</a>.</li>
<li><strong>Quer foto e papel de parede:</strong> Big Days — busca de imagens do Pixabay e exportação da contagem como papel de parede.</li>
<li><strong>Quer desenhar um único widget:</strong> Countdown Buddy — 10 estilos, contagem regressiva ou progressiva.</li>
<li><strong>Usa Mac e Apple Watch:</strong> Contagens — timers em todos os aparelhos; o iCloud é pago.</li>
</ul>
<h2>Os sete apps</h2>
{entries}
<h2>Como escolhemos</h2>
<p>Pesquisamos na App Store do Brasil «contagem regressiva» e «countdown widget», ficamos com os apps feitos para contagem com mais avaliações no Brasil e lemos a descrição de cada um em português para ver o que ela diz sobre a versão grátis, os widgets, a repetição, a sincronização e os anúncios. Criadores de widget em geral (como o Widgetsmith) ficaram de fora. Não testamos as versões pagas e não ordenamos por nota: o nosso vem primeiro porque somos nós que fazemos a lista, e os outros seguem pelo número de avaliações no Brasil. Nós fazemos um desses apps; ele entra porque é um app de contagem regressiva com widget para iPhone e é descrito com os mesmos campos que os outros. A <a href="/tools/best-countdown-widget-apps-iphone/" hreflang="en">versão em inglês desta lista</a> usa a App Store dos Estados Unidos, por isso os apps não são os mesmos.</p>"""
    return {"path": "/tools/pt-br/melhores-apps-contagem-regressiva/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-29",
            "title": "Melhores apps de contagem regressiva para iPhone (2026) com widget", "crumb": "Melhores apps",
            "description": "Sete apps de contagem regressiva para iPhone comparados: o que é grátis, quais widgets são pagos, repetição e anúncios. Dados da App Store Brasil, set. 2026.",
            "hub_title": "Melhores apps de contagem regressiva para iPhone (2026)", "hub_desc": "Sete apps comparados: versão grátis, widgets, repetição, sincronização e anúncios.",
            "items": [{"name": b["name"], "url": ("https://apps.apple.com/br/app/id%d" % b["id"])} for b in BEST_PT],
            "faq": [
              ("Qual app de contagem regressiva tem widget grátis na tela bloqueada?", "O Countdown: Contagem regressiva (o nosso) deixa todos os tamanhos de widget grátis, na Tela de Início e na Tela Bloqueada. No Contagem Regressiva ◎, o widget da tela bloqueada é recurso Premium, segundo a descrição; os outros da lista não dizem se o widget da tela bloqueada é grátis."),
              ("Quais apps deixam criar eventos ilimitados de graça?", "Pela descrição na App Store do Brasil: o Countdown: Contagem regressiva («eventos ilimitados»), o Contagens («um número ilimitado de timers» na versão gratuita) e o Contagem Regressiva ◎ («crie quantos eventos quiser», sem marcar como Premium). O Countdown Star diz «adicione quantos eventos quiser», sem separar o que é grátis e o que é pago. Os outros não dizem."),
              ("Qual é o melhor app para contar os dias de namoro?", "O Widget Casal é feito para isso: dias juntos, diário do casal e lembretes de 10 e 100 dias. O Countdown: Contagem regressiva também conta a partir de uma data e guarda texto, fotos e voz no verso do evento."),
              ("Algum desses apps tem anúncios?", "O Countdown Star tem anúncios na versão grátis, com uma compra para removê-los. O Countdown: Contagem regressiva não tem anúncios. Os outros não dizem na descrição."),
              ("Esta lista é independente?", "Não: nós fazemos o Countdown: Contagem regressiva. Tudo na tabela vem das páginas públicas na App Store do Brasil, os campos são os mesmos para todos os apps e cada concorrente tem link para você conferir. Não testamos as versões pagas."),
            ], "js": [], "body": body}
_ci = next(i for i, p in enumerate(PAGES) if p["path"] == "/tools/pt-br/contador-de-dias-de-namoro/")
PAGES.insert(_ci + 1, best_page_pt())   # 常青页一组：计算器 → 场景页 → 榜单 → 节日页

# ------------------------------------------------------------------ 目录页
def hub_page(lang):
    hub_path = HUBS[lang]
    items = [p for p in PAGES if p["lang"] == lang]
    # 卡片小字：英文目录用 app 短名；其它语言用该语言商店名（09-28：西语目录显示 Invoice Maker 是英文）
    label = lambda k: BY_KEY[k]["home"]["label"] if lang == "en" else bp.store_of({"variantOf": k, "lang": lang})["name"]
    cards = "\n".join(f'  <a href="{p["path"]}"><b>{esc(p["hub_title"])}</b><span>{esc(p["hub_desc"])}</span><small>{esc(label(p["app"]))}</small></a>' for p in items)
    body = f"""<h1>{esc(ts(lang, "hub_title"))}</h1>
<p class="lede">{esc(ts(lang, "hub_lede"))}</p>
<div class="hub">
{cards}
</div>"""
    title, desc = {
        "en": ("Free tools & guides — go ka", "Free, no-sign-up tools from go ka: days-until calculator and holiday countdowns, an invoice template and guide, and a packing list generator."),
        "pt-BR": ("Ferramentas e guias grátis — go ka", "Ferramentas grátis da go ka, sem cadastro: contador de dias, aniversário, férias com dias úteis, dias de namoro e contagem para o ENEM e o Natal."),
        "es-MX": ("Herramientas y guías gratis — go ka", "Herramientas gratis y sin registro de go ka: formato de cotización y formato de nota de venta para llenar en línea, imprimir o guardar en PDF."),
        "ja": ("無料ツールとガイド — go ka", "go ka の無料ツール（登録不要）：今日からあと何日かを数える日数計算と、共通テスト2027までのカウントダウン。"),
        "zh-Hant": ("免費工具與指南 — go ka", "go ka 的免費工具，不用註冊：報價單範本、收據範本（線上填寫、自動計算、存成 PDF），以及 2027 農曆新年倒數。"),
    }[lang]
    return {"path": hub_path, "lang": lang, "kind": "CollectionPage", "title": title,
            "description": desc,
            "body": body, "published": None, "faq": [], "js": []}

# ------------------------------------------------------------------ 博客（09-26 用户要求：参照 EasyNotes 官网补博客）
BLOG_SRC = ROOT / "tools/blog/posts.en.json"
BLOG = json.loads(BLOG_SRC.read_text(encoding="utf-8"))["posts"] if BLOG_SRC.exists() else []
APP_ORDER = {"countdown": 0, "invoiceqr": 1, "beforego": 2}
POST_SHOT = {  # 每篇配一张对应功能的插画（assets/art，编号同 features.en.json；09-28 起不用商店截图）
    "countdown-widget-iphone-home-lock-screen": ("countdown", "07"), "count-down-birthday-exam-trip-iphone": ("countdown", "09"),
    "payment-qr-code-on-invoice": ("invoiceqr", "08"), "invoice-vs-estimate-vs-quote": ("invoiceqr", "05", "Invoice, estimate and quote side by side"),
    "travel-post-screenshot-to-itinerary": ("beforego", "01"), "packing-list-by-destination": ("beforego", "04"),
}

def post_art(slug):
    return bp.art(*POST_SHOT[slug][:2]) if slug in POST_SHOT else None

def post_image(slug):
    pic = post_art(slug)
    return ORIGIN + pic[1] if pic else None

def post_figure(slug):
    pic = post_art(slug)
    if not pic:
        return ""
    key, num = POST_SHOT[slug][:2]; name = bp.store_of(BY_KEY[key])["name"]
    # 图注：没有对应功能块的图（05）在 POST_SHOT 第三项写明，别退回 app 名（09-28 评审：「Invoice Maker — Smart Invoice & Estimate Maker」重复）
    alt = POST_SHOT[slug][2] if len(POST_SHOT[slug]) > 2 else next(f["title"] for f in bp.FEAT_EN[key] if f["shot"] == num)
    return (f'<figure class="shot">{bp.art_img(pic, "280px", f"{alt} — {name}", ' loading="lazy" decoding="async"')}'
            f'<figcaption>{esc(alt)} — {esc(name)}</figcaption></figure>')

def blog_page(post):
    secs = "\n".join(f'<h2>{esc(x["h2"])}</h2>\n{x["html"]}' for x in post["sections"])
    body = f"""<h1>{esc(post["h1"])}</h1>
<p class="lede">{esc(post["intro"])}</p>
{post_figure(post["slug"])}
{secs}"""
    return {"path": f"/blog/{post['slug']}/", "lang": "en", "kind": "Article", "app": post["app"], "published": post.get("published", "2026-09-26"),
            "title": post["title"], "description": post["description"], "crumb": post["h1"] if len(post["h1"]) <= 60 else post["title"],
            "body": body, "faq": [(f["q"], f["a"]) for f in post.get("faq", [])], "js": [],
            "hub_title": post["title"], "hub_desc": post["description"], "headline": post["h1"], "image": post_image(post["slug"])}

def blog_hub():
    groups = []
    for key in sorted({p["app"] for p in BLOG}, key=lambda k: APP_ORDER.get(k, 9)):
        cards = "\n".join(f'  <a href="/blog/{p["slug"]}/"><b>{esc(p["title"])}</b><span>{esc(p["description"])}</span><small>{esc(BY_KEY[key]["home"]["label"])}</small></a>'
                          for p in BLOG if p["app"] == key)
        groups.append(f'<h2>{esc(BY_KEY[key]["home"]["label"])}</h2>\n<div class="hub">\n{cards}\n</div>')
    body = f"""<h1>Blog</h1>
<p class="lede">Plain how-to guides for the everyday things our apps do: countdown widgets, invoices and payment QR codes, trip plans and packing lists.</p>
{chr(10).join(groups)}"""
    return {"path": "/blog/", "lang": "en", "kind": "CollectionPage", "title": "Blog — guides for countdowns, invoices and trips | go ka",
            "description": "How-to guides from go ka: countdown widgets on iPhone, payment QR codes on invoices, estimates vs quotes, and trip plans and packing lists.",
            "body": body, "published": None, "faq": [], "js": []}

def main():
    manifest = []
    blog = [blog_page(p) for p in BLOG]
    for pg in PAGES + blog + [hub_page(l) for l in HUBS] + ([blog_hub()] if blog else []):
        out = ROOT / pg["path"].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(shell(pg, pg["body"]), encoding="utf-8")
        manifest.append({"path": pg["path"], "lang": pg["lang"], "kind": pg["kind"], "title": pg["title"], "description": pg["description"],
                         "faq": [{"q": q, "a": a} for q, a in pg.get("faq", [])], "published": pg.get("published"), "app": pg.get("app"),
                         "hubTitle": pg.get("hub_title", pg["title"]), "items": pg.get("items", []),
                         "headline": pg.get("headline"), "image": pg.get("image")})
        print(f"  {pg['path']}")
    (ROOT / "tools/tools.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"工具页 {len(manifest)} 页；接着跑 tools/build_seo.py")

if __name__ == "__main__":
    main()
