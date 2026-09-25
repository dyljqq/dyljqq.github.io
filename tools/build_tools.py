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
         "home": "Home", "other_lang": "Também em português (Brasil)", "other_lang_href": "/tools/pt-br/"},
  "pt-BR": {"tools": "Ferramentas", "hub_title": "Ferramentas e guias grátis", "hub_lede": "Pequenas, grátis, sem cadastro. Cada uma faz no navegador a mesma coisa do dia a dia que os nossos apps fazem.",
            "faq": "Perguntas frequentes", "published": "Publicado em", "updated": "Atualizado em", "get": "Leve para o seu iPhone",
            "ask": "Pergunte a uma IA sobre esta página", "days": "dias", "day": "dia", "weeks": "semanas", "today": "É hoje!", "passed": "dias atrás",
            "home": "Início", "other_lang": "Also in English", "other_lang_href": "/tools/"},
}
def ts(lang, k): return TS.get(lang, TS["en"])[k]
def fmt(d, lang):
    if lang == "pt-BR":
        wd = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"][d.weekday()]
        mo = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"][d.month - 1]
        return f"{wd}, {d.day} de {mo} de {d.year}"
    return d.strftime("%A, %-d %B %Y")
def days_to(d): return (d - TODAY).days

# 共用 JS：data-date 的元素按访问当天重算天数；data-until 的把整句里的数字替换
COUNT_JS = """
(function(){var T={en:['days','day','That\\'s today!','days ago'],'pt-BR':['dias','dia','É hoje!','dias atrás']}[document.documentElement.lang]||['days','day','Today','days ago'];
var now=new Date();now=new Date(now.getFullYear(),now.getMonth(),now.getDate());
document.querySelectorAll('[data-date]').forEach(function(el){var p=el.getAttribute('data-date').split('-');var d=new Date(+p[0],+p[1]-1,+p[2]);var n=Math.round((d-now)/864e5);
var num=el.querySelector('[data-n]'),unit=el.querySelector('[data-unit]');if(!num)return;
if(n===0){num.textContent='';unit.textContent=T[2];}else if(n<0){num.textContent=-n;unit.textContent=T[3];}else{num.textContent=n;unit.textContent=n===1?T[1]:T[0];}
var w=el.querySelector('[data-weeks]');if(w&&n>0){w.textContent=Math.floor(n/7)+' '+(document.documentElement.lang==='pt-BR'?'semanas':'weeks')+(n%7?' + '+(n%7)+' '+(n%7===1?T[1]:T[0]):'');}});})();
"""
CALC_JS = """
(function(){var f=document.getElementById('calc');if(!f)return;var out=document.getElementById('calc-out');var name=f.querySelector('[name=name]'),date=f.querySelector('[name=date]');
var q=new URLSearchParams(location.search);if(q.get('date'))date.value=q.get('date');if(q.get('name'))name.value=q.get('name');
function run(e){if(e)e.preventDefault();if(!date.value)return;var p=date.value.split('-');var d=new Date(+p[0],+p[1]-1,+p[2]);var now=new Date();now=new Date(now.getFullYear(),now.getMonth(),now.getDate());
var n=Math.round((d-now)/864e5);var label=name.value.trim()||'that day';var pretty=d.toLocaleDateString('en-GB',{weekday:'long',day:'numeric',month:'long',year:'numeric'});var s;
if(n===0)s='<strong>'+label+'</strong> is today ('+pretty+').';else if(n<0)s='<strong>'+label+'</strong> was <strong>'+(-n)+' day'+(n===-1?'':'s')+' ago</strong> ('+pretty+').';
else{var w=Math.floor(n/7),r=n%7;s='<strong>'+n+' day'+(n===1?'':'s')+'</strong> until <strong>'+label+'</strong> — '+pretty+'.'+(n>=7?' That\\'s '+w+' week'+(w===1?'':'s')+(r?' and '+r+' day'+(r===1?'':'s'):'')+'.':'');}
out.innerHTML='<p class="big">'+s+'</p><p class="share"><a href="?date='+date.value+'&name='+encodeURIComponent(name.value.trim())+'" id="share">Link to this countdown</a></p>';out.hidden=false;
var a=document.getElementById('share');a.addEventListener('click',function(ev){if(navigator.clipboard){ev.preventDefault();navigator.clipboard.writeText(location.origin+location.pathname+a.getAttribute('href'));a.textContent='Link copied';}});}
f.addEventListener('submit',run);if(date.value)run();})();
"""
INVOICE_JS = """
(function(){var t=document.getElementById('inv');if(!t)return;var body=t.querySelector('tbody');
function money(n){return n.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});}
function calc(){var sub=0;body.querySelectorAll('tr').forEach(function(tr){var q=parseFloat(tr.children[1].textContent)||0,p=parseFloat(tr.children[2].textContent.replace(/[^0-9.\\-]/g,''))||0;var a=q*p;tr.children[3].textContent=money(a);sub+=a;});
var rate=parseFloat(document.getElementById('taxrate').textContent)||0;var tax=sub*rate/100;document.getElementById('sub').textContent=money(sub);document.getElementById('tax').textContent=money(tax);document.getElementById('total').textContent=money(sub+tax);}
document.getElementById('addrow').addEventListener('click',function(){var tr=body.rows[0].cloneNode(true);tr.children[0].textContent='Item';tr.children[1].textContent='1';tr.children[2].textContent='0.00';body.appendChild(tr);calc();});
document.getElementById('print').addEventListener('click',function(){window.print();});
t.addEventListener('input',calc);document.getElementById('taxrate').addEventListener('input',calc);document.getElementById('today').textContent=new Date().toLocaleDateString();
var due=new Date();due.setDate(due.getDate()+30);document.getElementById('due').textContent=due.toLocaleDateString();calc();})();
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
.article{max-width:720px}.article h1{font-size:clamp(32px,5vw,50px)}.article .lede{font-size:18px}
.article h2{font:500 clamp(24px,3vw,32px)/1.2 var(--display);margin:44px 0 14px}.article h3{font:600 18px/1.4 var(--text);margin:26px 0 8px}
.article p,.article li{color:var(--muted)}.article ul,.article ol{padding-left:22px}.article li{margin:0 0 6px}
.article table{border-collapse:collapse;width:100%;font-size:15px;margin:12px 0}.article th,.article td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--rule);vertical-align:top}.article th{font-weight:700;color:var(--ink)}
.count{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:22px 0 6px;font:500 clamp(48px,9vw,96px)/1 var(--display);letter-spacing:-.04em}.count small{font:600 16px/1 var(--text);letter-spacing:.5px;color:var(--muted)}
.count-sub{margin:0 0 6px;color:var(--muted);font-size:15px}
.calc{display:grid;gap:12px;grid-template-columns:1fr 1fr auto;align-items:end;margin:22px 0;padding:22px;border:1.5px solid var(--ink);border-radius:20px;background:var(--cream)}
.calc label{display:grid;gap:6px;font:700 12px/1 var(--text);letter-spacing:1.2px;text-transform:uppercase;color:var(--muted)}
.calc input,.calc select{font:400 16px/1.3 var(--text);padding:12px 14px;border:1.5px solid var(--rule);border-radius:12px;background:#fff;color:var(--ink);min-width:0}
.calc button,.btn{font:700 14px/1 var(--text);padding:15px 20px;border:0;border-radius:999px;background:var(--ink);color:#fff;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:8px}
.calc button:hover,.btn:hover{background:var(--yellow);color:var(--ink)}.btn svg{width:18px;height:18px;flex:none;fill:currentColor}.appcard .btn{white-space:nowrap}.btn.ghost{background:transparent;color:var(--ink);border:1.5px solid var(--ink)}
#calc-out .big{font:500 clamp(22px,3.4vw,32px)/1.3 var(--display);letter-spacing:-.02em;margin:8px 0 6px;color:var(--ink)}#calc-out .share a{font-size:14px}
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
.inv-head{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap}.inv-head h2{margin:0;font:600 34px/1 var(--display);letter-spacing:-.02em}
.inv-parties{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:24px 0}.inv-parties h4,.inv-meta h4{margin:0 0 6px;font:700 11px/1 var(--text);letter-spacing:1.6px;text-transform:uppercase;color:var(--soft)}
.inv table{width:100%;border-collapse:collapse;margin:8px 0}.inv th{font:700 11px/1 var(--text);letter-spacing:1.4px;text-transform:uppercase;color:var(--soft);text-align:left;padding:8px 6px;border-bottom:1.5px solid var(--ink)}
.inv td{padding:9px 6px;border-bottom:1px solid var(--rule)}.inv td:nth-child(n+2),.inv th:nth-child(n+2){text-align:right;width:14%}
.inv .totals{margin-left:auto;width:min(100%,320px);margin-top:12px}.inv .totals div{display:flex;justify-content:space-between;padding:6px 0}.inv .totals .grand{border-top:1.5px solid var(--ink);font-weight:800;font-size:18px;margin-top:6px;padding-top:10px}
.inv .notes{margin-top:22px;color:var(--muted);font-size:14px}
.check{list-style:none;padding:0;margin:0 0 18px;columns:2;column-gap:32px}.check li{break-inside:avoid;margin:0 0 6px}.check label{display:flex;gap:10px;align-items:flex-start;color:var(--ink);cursor:pointer}.check input{margin-top:5px;accent-color:var(--ink)}
@media (max-width:760px){.calc{grid-template-columns:1fr}.inv{padding:20px}.inv-parties{grid-template-columns:1fr}.check{columns:1}.appcard{flex-direction:column;align-items:flex-start}}
@media print{header,.crumbs,.calc,.appcard,.ask,.meta,footer,#faq-section,.article>*:not(.inv-wrap):not(#pack-out):not(.pack-head){display:none!important}.inv{border:0;padding:0}.inv [contenteditable]{border:0}.inv-tools,#pack-actions{display:none!important}body{font-size:13px}}
"""

def app_card(app_key, lang):
    """页尾「去 iPhone 上做这件事」卡片：图标 + 商店名 + 一句话 + 商店按钮。"""
    p = BY_KEY[app_key]; s = bp.store_of({"variantOf": app_key, "lang": lang} if lang != "en" else p)
    page = bp.sibling_path(p, lang) if lang != "en" else p["path"]
    icon = bp.cdn(s["icon"], 256) if s.get("icon", "").startswith("http") else p["icon"]
    return (f'<aside class="appcard"><img src="{icon}" width="72" height="72" alt="" loading="lazy"><div>'
            f'<p class="label" style="margin:0 0 6px">{esc(ts(lang, "get"))}</p><b>{esc(s["name"])}</b><p>{esc(p["home"]["blurb"] if lang == "en" else s["description"].split(chr(10))[0][:160])}</p>'
            f'<a class="btn" href="{bp.store_link(p, s)}">{bp.APPLE}{esc(bp.t(lang, "cta_store"))}</a> &nbsp; <a href="{page}" style="font-size:14px">{esc(p["home"]["label"])} →</a></div></aside>')

def ask_ai(url, lang):
    q = f"Read {url} and summarise its key points in a few sentences." if lang == "en" else f"Leia {url} e resuma os pontos principais em poucas frases."
    from urllib.parse import quote
    return (f'<p class="ask">{esc(ts(lang, "ask"))}: <a href="https://chatgpt.com/?q={quote(q)}" rel="nofollow noopener">ChatGPT</a>'
            f'<a href="https://www.perplexity.ai/search?q={quote(q)}" rel="nofollow noopener">Perplexity</a>'
            f'<a href="https://claude.ai/new?q={quote(q)}" rel="nofollow noopener">Claude</a></p>')

def faq_html(faq, lang):
    rows = "\n".join(f'    <div class="card"><h3>{esc(q)}</h3><p>{esc(a)}</p></div>' for q, a in faq)
    return f'<section class="sec" id="faq-section"><h2 id="faq">{esc(ts(lang, "faq"))}</h2><div class="grid">\n{rows}\n</div></section>'

def counter(d, lang, label=""):
    n = days_to(d); unit = ts(lang, "today") if n == 0 else (ts(lang, "passed") if n < 0 else (ts(lang, "day") if n == 1 else ts(lang, "days")))
    w = f"{n // 7} {ts(lang, 'weeks')}" + (f" + {n % 7} {ts(lang, 'days') if n % 7 != 1 else ts(lang, 'day')}" if n % 7 else "") if n > 0 else ""
    return (f'<div class="count" data-date="{d.isoformat()}"><span data-n>{abs(n) if n else ""}</span><small data-unit>{esc(unit)}</small></div>'
            f'<p class="count-sub">{esc(label + " · " if label else "")}{esc(fmt(d, lang))}{f" · <span data-weeks>{esc(w)}</span>" if w else ""}</p>')

def shell(pg, body):
    lang = pg["lang"]; T = lambda k, **kw: bp.t(lang, k, **kw)
    hub = "/tools/pt-br/" if lang == "pt-BR" else "/tools/"
    crumbs = [(ts(lang, "home"), "/"), (ts(lang, "tools"), hub)] + ([(pg["crumb"], None)] if pg.get("crumb") else [])
    crumb_html = "".join(f'<li>{f"<a href={chr(34)}{h}{chr(34)}>{esc(l)}</a>" if h else esc(l)}</li>' for l, h in crumbs)
    meta = ""
    if pg.get("published"):
        meta = f'<p class="meta">{esc(ts(lang, "published"))} {pg["published"]} · {esc(ts(lang, "updated"))} {TODAY.isoformat()} · go ka</p>'
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
  <a class="brand" href="/">{bp.LOGO}<b>go ka</b></a>
  <nav class="nav" aria-label="Main">
    <a href="/">{esc(T("nav_all_apps"))}</a>
    <a href="{hub}">{esc(ts(lang, "tools"))}</a>
    <a href="mailto:{EMAIL}">{esc(T("nav_support"))}</a>
  </nav>
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
<p style="margin:28px 0 0;font-size:14px"><a href="{ts(lang, 'other_lang_href')}" hreflang="{'pt-BR' if lang == 'en' else 'en'}">{esc(ts(lang, 'other_lang'))} →</a></p>
</main>
<footer><div class="wrap"><p>go ka · <a href="mailto:{EMAIL}">{EMAIL}</a> · <a href="/">{esc(T("nav_all_apps"))}</a></p></div></footer>
{scripts}
</body>
</html>
"""

# ------------------------------------------------------------------ 内容
XMAS, NYE, HALLOWEEN, REV = dt.date(2026, 12, 25), dt.date(2027, 1, 1), dt.date(2026, 10, 31), dt.date(2026, 12, 31)
ENEM1, ENEM2 = dt.date(2026, 11, 8), dt.date(2026, 11, 15)
CARN_SAT, CARN_TUE, ASH = dt.date(2027, 2, 6), dt.date(2027, 2, 9), dt.date(2027, 2, 10)

def holiday_page(slug, name, d, lang, title, desc, h1, intro, glance, ideas, faq, next_dates):
    body = f"""<h1>{esc(h1)}</h1>
<p class="lede">{intro}</p>
{counter(d, lang, name)}
<h2>{esc(name)} at a glance</h2>
<table><tbody>{"".join(f"<tr><th>{esc(k)}</th><td>{v}</td></tr>" for k, v in glance)}</tbody></table>
<h2>Put the countdown on your Home Screen</h2>
<p>A countdown you have to open an app to see is a countdown you forget. With <a href="/countdown/">Countdown Widget: Any Event</a> you add the date once and it sits on the Home Screen or Lock Screen as a widget — every widget size is free, events are unlimited, and it can remind you on the day and as far ahead as you like.</p>
<ol><li>Install the app and tap <strong>+</strong>. Pick the template or type the name.</li><li>Set the date to {esc(fmt(d, lang))}. Turn on <strong>Repeat yearly</strong> if you want it back next year.</li><li>Long-press the Home Screen → <strong>Edit</strong> → <strong>Add Widget</strong> → Countdown. Choose the size you like.</li></ol>
<h2>Countdown ideas</h2>
<ul>{"".join(f"<li>{i}</li>" for i in ideas)}</ul>
<h2>{esc(name)} in the next few years</h2>
<table><thead><tr><th>Year</th><th>Date</th><th>Day of the week</th></tr></thead><tbody>{"".join(f"<tr><td>{y}</td><td>{esc(fmt(dd, lang))}</td><td>{dd.strftime('%A')}</td></tr>" for y, dd in next_dates)}</tbody></table>"""
    return {"path": f"/tools/{slug}/", "lang": lang, "title": title, "description": desc, "crumb": name, "kind": "Article",
            "app": "countdown", "faq": faq, "published": "2026-09-26", "js": [COUNT_JS], "body": body, "hub_title": h1, "hub_desc": desc}

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
   ("How do I put a Christmas countdown on my iPhone Home Screen?", "Add the date in Countdown Widget: Any Event, then long-press the Home Screen, tap Edit → Add Widget, and choose Countdown. The widgets are free in every size, and the event can repeat every year.")],
  [(2026, XMAS), (2027, dt.date(2027, 12, 25)), (2028, dt.date(2028, 12, 25)), (2029, dt.date(2029, 12, 25))]))

PAGES.append(holiday_page("days-until-halloween", "Halloween 2026", HALLOWEEN, "en",
  "How many days until Halloween 2026? Live countdown", "Halloween 2026 is on Saturday, 31 October 2026. Live countdown in days and weeks, plus a free Home Screen widget for your iPhone.",
  "How many days until Halloween 2026?",
  "Halloween 2026 falls on <strong>Saturday, 31 October 2026</strong> — a weekend Halloween, which last happened in 2020. The counter below updates every day.",
  [("Halloween", "Saturday, 31 October 2026"), ("All Saints' Day", "Sunday, 1 November 2026"), ("Día de los Muertos", "Monday, 2 November 2026"), ("Days from Halloween to Christmas", "55")],
  ["A countdown to the party with a reminder a week before, so the costume gets ordered in time.", "A trick-or-treat countdown on the kids' shared iPad.", "A Lock Screen widget with a pumpkin backdrop for October."],
  [("What day of the week is Halloween 2026?", "Saturday. Halloween 2026 is on Saturday, 31 October 2026, so parties and trick-or-treating fall on a weekend."),
   ("How many weeks until Halloween 2026?", f"On {TODAY.strftime('%-d %B %Y')} there were {days_to(HALLOWEEN)} days, about {days_to(HALLOWEEN)//7} weeks. The counter on this page recalculates when you open it."),
   ("When is Halloween 2027?", "Sunday, 31 October 2027. Halloween 2028 falls on a Tuesday."),
   ("How do I get a Halloween countdown widget on iPhone?", "Add 31 October as an event in Countdown Widget: Any Event and set it to repeat yearly, then add the widget from the Home Screen's Edit → Add Widget menu. Every widget size is free.")],
  [(2026, HALLOWEEN), (2027, dt.date(2027, 10, 31)), (2028, dt.date(2028, 10, 31)), (2029, dt.date(2029, 10, 31))]))

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
  "description": "As provas do ENEM 2026 são em 8 e 15 de novembro de 2026 (Edital nº 64 do Inep). Contagem regressiva ao vivo e widget grátis para a tela de início do iPhone.",
  "hub_title": "Quantos dias faltam para o ENEM 2026?", "hub_desc": "Contagem regressiva para os dois domingos de prova, 8 e 15 de novembro.",
  "js": [COUNT_JS], "faq": [
    ("Quando é o ENEM 2026?", "As provas serão aplicadas nos domingos 8 de novembro e 15 de novembro de 2026, conforme o Edital nº 64, publicado pelo Inep em 22 de maio de 2026."),
    ("Quando foram as inscrições do ENEM 2026?", "De 25 de maio a 12 de junho de 2026, pela Página do Participante do Inep."),
    ("O que cai em cada dia do ENEM 2026?", "No primeiro dia (8/11): Linguagens, Códigos e suas Tecnologias, Redação e Ciências Humanas e suas Tecnologias. No segundo dia (15/11): Ciências da Natureza e suas Tecnologias e Matemática e suas Tecnologias, com 90 questões objetivas."),
    ("Quando sai o gabarito do ENEM 2026?", "Segundo o edital, até o 10º dia útil após o segundo dia de prova."),
    ("Como coloco a contagem regressiva do ENEM na tela de início?", "Adicione 8 de novembro de 2026 no app Countdown: Contagem regressiva, depois segure a tela de início → Editar → Adicionar widget → Countdown. Todos os tamanhos de widget são grátis e você pode criar outro evento para o dia 15."),
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
<h2>A contagem na tela de início, sem abrir nada</h2>
<p>Uma contagem regressiva que você precisa abrir para ver é uma contagem que você esquece. Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na tela de início ou na tela de bloqueio como widget — todos os tamanhos são grátis, os eventos são ilimitados e o app avisa no dia e com a antecedência que você quiser.</p>
<ol><li>Instale o app e toque em <strong>+</strong>. Dê o nome "ENEM — 1º dia".</li><li>Coloque a data <strong>8 de novembro de 2026</strong>. Crie outro evento para o dia 15.</li><li>Segure a tela de início → <strong>Editar</strong> → <strong>Adicionar widget</strong> → Countdown. Escolha o tamanho.</li></ol>
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
    ("Como coloco a contagem do Réveillon na tela de bloqueio?", "Crie o evento 31 de dezembro de 2026 no Countdown: Contagem regressiva, marque repetir todo ano, e na tela de bloqueio segure → Personalizar → adicione o widget Countdown. Os widgets são grátis em todos os tamanhos."),
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
<h2>A contagem na tela de início</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na tela de início ou de bloqueio como widget — grátis em todos os tamanhos, eventos ilimitados, com lembrete no dia. Marque <strong>repetir todo ano</strong> e o Réveillon volta sozinho em 2027.</p>
<ol><li>Toque em <strong>+</strong>, escolha o modelo Réveillon ou digite o nome.</li><li>Data: 31 de dezembro de 2026, repetir todo ano.</li><li>Segure a tela de início → Editar → Adicionar widget → Countdown.</li></ol>
<h2>Ideias</h2>
<ul><li>Uma contagem para a viagem de Carnaval, com o endereço no verso do evento.</li><li>Uma contagem progressiva desde 1º de janeiro para a meta do ano — o widget mostra os dias de sequência.</li><li>Um evento para o primeiro dia de trabalho depois das festas, para o feriado ter começo e fim.</li></ul>"""})

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
<div class="inv-head"><div><h2>INVOICE</h2><p style="margin:6px 0 0"><span contenteditable="true">Your Business Name</span><br><span contenteditable="true">Street, City, Country</span><br><span contenteditable="true">you@example.com · +1 000 000 0000</span></p></div>
<div class="inv-meta"><h4>Invoice number</h4><p style="margin:0 0 10px"><span contenteditable="true">INV-0001</span></p><h4>Date</h4><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><h4>Due</h4><p style="margin:0"><span contenteditable="true" id="due"></span></p></div></div>
<div class="inv-parties"><div><h4>Bill to</h4><p style="margin:0"><span contenteditable="true">Client name</span><br><span contenteditable="true">Client address</span><br><span contenteditable="true">client@example.com</span></p></div>
<div><h4>Payment</h4><p style="margin:0"><span contenteditable="true">Bank transfer — IBAN / account number</span><br><span contenteditable="true">Or scan the QR code on your Smart Invoice PDF</span></p></div></div>
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
<p>If you send more than a few invoices a month, an app that remembers clients, items and tax rates, numbers the invoices for you and shows what is paid, unpaid and overdue saves real time. That is what <a href="/invoiceqr/">Smart Invoice &amp; Estimate Maker</a> does on iPhone — including a payment QR code on every invoice.</p>"""})

# 8. 如何写发票（指南）
PAGES.append({"path": "/tools/how-to-write-an-invoice/", "lang": "en", "kind": "Article", "app": "invoiceqr", "published": "2026-09-26",
  "title": "How to Write an Invoice (freelancers & small businesses) — 8 steps", "crumb": "How to write an invoice",
  "description": "How to write an invoice that gets paid: what to include, how to number it, payment terms that work, and the mistakes that delay payment. With a free template.",
  "hub_title": "How to write an invoice", "hub_desc": "The eight things every invoice needs, numbering, payment terms and the mistakes that delay payment.",
  "faq": [
    ("What should I put on an invoice?", "The word Invoice, a unique number, issue and due dates, your business details, the client's details, each item with quantity and price, subtotal, tax and total, and how to pay. Add your tax ID if your country requires it."),
    ("How do I number invoices?", "Sequentially and never reused: INV-0001, INV-0002… Many freelancers prefix the year (2026-001) so the sequence resets each January. Gaps are fine; duplicates are not."),
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
<p>Use the <a href="/tools/invoice-template/">free invoice template</a> on this site for a one-off. If you invoice regularly, <a href="/invoiceqr/">Smart Invoice &amp; Estimate Maker</a> on iPhone keeps clients, items and tax rates, numbers invoices for you, puts a payment QR code on each one and shows what's paid, unpaid and overdue.</p>"""})

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
   "free": "Unlimited events, every widget size on Home Screen and Lock Screen, reminders, repeats, iCloud sync — all free. Pro only sells backdrops.",
   "widgets": "Home Screen + Lock Screen, all sizes, free", "recur": "Yearly, monthly, weekly, every N days", "sync": "iCloud, no account", "ads": "None",
   "take": "The only app on this list where the widgets are not the paid feature. Every widget size, unlimited events, recurring dates, reminders and iCloud sync are free; the subscription is for decorative backdrops. It also keeps a daily on-device snapshot so an update or reinstall never loses the events. New in 2026, so it has few ratings yet — judge it by the free tier, which is the most generous here."},
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
<table><thead><tr><th>App</th><th>Free tier</th><th>Widgets</th><th>Repeats</th><th>Sync</th><th>US rating</th></tr></thead><tbody>{rows}</tbody></table>
<p class="meta">"Not stated" means the App Store description does not say. Ratings are the US storefront on 26 September 2026 and change daily.</p>
<h2>Which one to pick</h2>
<ul>
<li><strong>You want widgets without paying:</strong> Countdown Widget: Any Event (ours) — every widget size is free, and so are unlimited events, repeats, reminders and iCloud sync. Countdown: Event Countdown gives you one free Next Event widget.</li>
<li><strong>You want the longest track record:</strong> Countdown Star — 13 years and over 200,000 ratings, with an Apple Watch app and time zones per event.</li>
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

# ------------------------------------------------------------------ 目录页
def hub_page(lang):
    hub_path = "/tools/pt-br/" if lang == "pt-BR" else "/tools/"
    items = [p for p in PAGES if p["lang"] == lang]
    cards = "\n".join(f'  <a href="{p["path"]}"><b>{esc(p["hub_title"])}</b><span>{esc(p["hub_desc"])}</span><small>{esc(BY_KEY[p["app"]]["home"]["label"])}</small></a>' for p in items)
    body = f"""<h1>{esc(ts(lang, "hub_title"))}</h1>
<p class="lede">{esc(ts(lang, "hub_lede"))}</p>
<div class="hub">
{cards}
</div>"""
    return {"path": hub_path, "lang": lang, "kind": "CollectionPage", "title": ("Free tools & guides — go ka" if lang == "en" else "Ferramentas e guias grátis — go ka"),
            "description": ("Free, no-sign-up tools from go ka: days-until calculator and holiday countdowns, an invoice template and guide, and a packing list generator." if lang == "en"
                            else "Ferramentas grátis e sem cadastro da go ka: contagem regressiva para o ENEM 2026, Réveillon e Carnaval 2027, e mais."),
            "body": body, "published": None, "faq": [], "js": []}

def main():
    manifest = []
    for pg in PAGES + [hub_page("en"), hub_page("pt-BR")]:
        out = ROOT / pg["path"].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(shell(pg, pg["body"]), encoding="utf-8")
        manifest.append({"path": pg["path"], "lang": pg["lang"], "kind": pg["kind"], "title": pg["title"], "description": pg["description"],
                         "faq": [{"q": q, "a": a} for q, a in pg.get("faq", [])], "published": pg.get("published"), "app": pg.get("app"),
                         "hubTitle": pg.get("hub_title", pg["title"]), "items": pg.get("items", [])})
        print(f"  {pg['path']}")
    (ROOT / "tools/tools.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"工具页 {len(manifest)} 页；接着跑 tools/build_seo.py")

if __name__ == "__main__":
    main()
