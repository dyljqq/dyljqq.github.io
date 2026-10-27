#!/usr/bin/env python3
"""免费工具页 / 指南页（/tools/…）：吃 Google 长尾和 AI 引用的页面，每页挂对应 app 的入口。

  python3 tools/build_tools.py     # 生成全部工具页 + 目录页，并写 tools/tools.json 清单
                                   # 然后跑 tools/build_seo.py（head / sitemap / llms.txt 按清单补）

内容全在本文件里（PAGES），日期类数字在构建时算一次写进静态文本，页面上的 JS 再按访问当天更新。
"""
import datetime as dt, json, html, os, re, sys, time
from pathlib import Path

# 日期口径固定为越南时间，原因见 build_seo.py 开头。
os.environ["TZ"] = "Asia/Ho_Chi_Minh"; time.tzset()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_pages as bp

ROOT, CFG, APPS, BY_KEY, EMAIL = bp.ROOT, bp.CFG, bp.APPS, bp.BY_KEY, bp.EMAIL
ORIGIN = CFG["site"]["origin"]
TODAY = dt.date.today()
# 页面上写的「来源确认日」必须是真去核对官方来源的那一天，不能用构建日——每次构建都会变，等于谎称当天又核对过。
# 重新核对了官方来源（大学入試センター / 行政院人事行政總處 / 香港政府一站通）之后再改这个日期。
SOURCES_CHECKED = dt.date(2026, 9, 29)
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
  # 10-12：泰国线走 InvoiceQR（泰国是 InvoiceQR 唯一产出试用的市场）
  "th": {"tools": "เครื่องมือ", "hub_title": "เครื่องมือและคู่มือฟรี", "hub_lede": "เครื่องมือเล็ก ๆ ใช้ฟรี ไม่ต้องสมัคร ทำงานในเบราว์เซอร์ได้เหมือนที่แอป iPhone ของเราทำ",
         "faq": "คำถามที่พบบ่อย", "published": "เผยแพร่", "updated": "อัปเดต", "get": "ทำต่อบน iPhone", "ask": "ให้ AI สรุปหน้านี้",
         "days": "วัน", "day": "วัน", "weeks": "สัปดาห์", "today": "วันนี้!", "passed": "วันที่แล้ว",
         "home": "หน้าแรก", "other_lang": "Free tools & guides in English", "other_lang_href": "/tools/"},
  # 10-12：韩国线走 BeforeGo（트리플 11-03 停服，联想词有「트리플 대체 어플」「여행 일정 앱 추천」）
  "ko": {"tools": "도구", "hub_title": "무료 도구와 가이드", "hub_lede": "가입 없이 무료로 보는 가이드입니다. 우리 iPhone 앱으로 하는 일을 더 쉽게 하는 방법을 정리했습니다.",
         "faq": "자주 묻는 질문", "published": "게시", "updated": "업데이트", "get": "iPhone에서 계속하기", "ask": "이 페이지를 AI에게 요약 요청",
         "days": "일", "day": "일", "weeks": "주", "today": "오늘입니다!", "passed": "일 지남",
         "home": "홈", "other_lang": "Free tools & guides in English", "other_lang_href": "/tools/"},
  # 10-17：德国线走 InvoiceQR（用户定：IQ 瞄德国；10-16 首笔月付 7 天试用就是德国自然量）
  "de": {"tools": "Tools", "hub_title": "Kostenlose Vorlagen und Anleitungen", "hub_lede": "Kostenlos und ohne Anmeldung: Vorlagen, die du direkt im Browser ausfüllst und als PDF speicherst, und Anleitungen für unsere iPhone-App.",
         "faq": "Häufige Fragen", "published": "Veröffentlicht", "updated": "Aktualisiert", "get": "Auf dem iPhone weitermachen", "ask": "Diese Seite von einer KI zusammenfassen lassen",
         "days": "Tage", "day": "Tag", "weeks": "Wochen", "today": "Heute ist es so weit!", "passed": "Tage her",
         "home": "Startseite", "other_lang": "Free tools & guides in English", "other_lang_href": "/tools/"},
}
HUBS = {"en": "/tools/", "pt-BR": "/tools/pt-br/", "es-MX": "/tools/es-mx/", "zh-Hant": "/tools/zh-hant/", "ja": "/tools/ja/", "th": "/tools/th/", "ko": "/tools/ko/", "de": "/tools/de/"}
HOMES = {"en": "/", "pt-BR": "/pt-br/", "es-MX": "/es-mx/", "zh-Hant": "/zh-hant/", "ja": "/ja/", "th": "/th/", "ko": "/ko/", "de": "/de/"}
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
    if lang == "ko":
        return f"{d.year}년 {d.month}월 {d.day}일({'월화수목금토일'[d.weekday()]})"
    return d.strftime("%A, %-d %B %Y")
def days_to(d): return (d - TODAY).days
def en_days(n): return f"{n} day{'' if n == 1 else 's'}"
def en_weeks(n):   # 节日页 FAQ 的周数：13 → "1 week and 6 days"，不满一周 → "less than a week"（原来 n//7 + 固定 weeks，13 天写成 "about 1 weeks"）
    if n < 7: return "less than a week"
    w, r = divmod(n, 7)
    return f"{w} week{'' if w == 1 else 's'}" + (f" and {en_days(r)}" if r else "")
def pt_days(n): return f"{n} dia{'' if n == 1 else 's'}"
def pt_weeks(n):   # 葡语 FAQ 周数：13 → "1 semana e 6 dias"，不满一周 → "menos de uma semana"（原来 n//7 + 固定 semanas）
    if n < 7: return "menos de uma semana"
    w, r = divmod(n, 7)
    return f"{w} semana{'' if w == 1 else 's'}" + (f" e {pt_days(r)}" if r else "")
def pt_left(n, alvo, nome, com_artigo):   # 葡语 FAQ「Em <日期>, …」后半句；前 1 天 / 当天 / 过后不能写 "faltavam 1 dias" / 负数
    if n >= 2: return f"faltavam {n} dias para {alvo}"
    return f"faltava 1 dia para {alvo}" if n == 1 else f"já era {nome}" if n == 0 else f"{com_artigo} já tinha passado"
def zh_left(n, target):   # 繁中 FAQ「在<日期>，…」：原来「約 n//7 週」，前一週內會寫成「約 0 週」
    if n >= 7: return f"離{target}還有 {n} 天，也就是 {n // 7} 週" + (f"又 {n % 7} 天" if n % 7 else "")
    if n >= 2: return f"離{target}還有 {n} 天"
    return f"離{target}只剩 1 天，就是隔天" if n == 1 else f"這天就是{target}" if n == 0 else f"{target}已經過了"
def ja_left(n, target, past=None):   # 日文 FAQ「<日期>の時点で…」：同上，原来「約 n//7 週間」；past＝多日程考试过了第一天的说法
    if n >= 7: return f"{target}まで{n}日、" + (f"{n // 7}週と{n % 7}日です" if n % 7 else f"ちょうど{n // 7}週間です")
    if n >= 2: return f"{target}まで{n}日です"
    return f"{target}は翌日です" if n == 1 else f"{target}当日を迎えています" if n == 0 else past or f"{target}はすでに終わっています"
def en_weeks_left(n, name, sep):   # FAQ「On <日期> …」后半句；前 1 天 / 当天 / 过后不能写 "there were 1 day, or less than a week"
    if n >= 2: return f"there were {en_days(n)}{sep}{en_weeks(n)}"
    return f"{name} was the next day" if n == 1 else f"it was {name} itself" if n == 0 else f"{name} had already passed"
def fmt_us(d): return d.strftime("%A, %B %-d, %Y")   # 美区页用 November 26, 2026 写法

# 共用 JS：data-date 的元素按访问当天重算天数；data-until 的把整句里的数字替换
COUNT_JS = """
(function(){var T={en:['days','day','That\\'s today!','days ago'],'pt-BR':['dias','dia','É hoje!','dias atrás'],ja:['日','日','今日です！','日前'],'zh-Hant':['天','天','就是今天！','天前'],ko:['일','일','오늘입니다!','일 지남']}[document.documentElement.lang]||['days','day','Today','days ago'];
var now=new Date();now=new Date(now.getFullYear(),now.getMonth(),now.getDate());
document.querySelectorAll('[data-date]').forEach(function(el){var p=el.getAttribute('data-date').split('-');var d=new Date(+p[0],+p[1]-1,+p[2]);var n=Math.round((d-now)/864e5);
var num=el.querySelector('[data-n]'),unit=el.querySelector('[data-unit]');if(!num)return;
if(n===0){num.textContent='';unit.textContent=T[2];}else if(n<0){num.textContent=-n;unit.textContent=n===-1?T[3].replace(/^(dias|days)/,function(m){return m.slice(0,-1)}):T[3];}else{num.textContent=n;unit.textContent=n===1?T[1]:T[0];}
var w=el.querySelector('[data-weeks]')||(el.nextElementSibling&&el.nextElementSibling.querySelector('[data-weeks]')),L=document.documentElement.lang;if(w&&n<7)w.textContent='';if(w&&n>=7){w.textContent=L==='ja'?Math.floor(n/7)+(n%7?'週と'+(n%7)+'日':'週間'):L==='zh-Hant'?Math.floor(n/7)+' 週'+(n%7?'又 '+(n%7)+' 天':''):L==='ko'?Math.floor(n/7)+'주'+(n%7?' '+(n%7)+'일':''):Math.floor(n/7)+' '+(L==='pt-BR'?(n<14?'semana':'semanas'):(n<14?'week':'weeks'))+(n%7?(L==='pt-BR'?' e ':' + ')+(n%7)+' '+(n%7===1?T[1]:T[0]):'');}});})();
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
var L=document.documentElement.lang,loc=L==='en'?undefined:L,de=/^de/.test(L);function $(i){return document.getElementById(i);}
function num(x){x=x.replace(/[^0-9.,\\-]/g,'');x=de?(x.indexOf(',')<0&&/\\.\\d{1,2}$/.test(x)?x:x.replace(/\\./g,'').replace(',','.')):x.replace(/,/g,'');return parseFloat(x)||0;}
function money(n){return n.toLocaleString(de?'de-DE':undefined,{minimumFractionDigits:2,maximumFractionDigits:2});}
function put(i,v){var e=$(i);if(e)e.textContent=money(v);}
function calc(){var sub=0;body.querySelectorAll('tr').forEach(function(tr){var a=num(tr.children[1].textContent)*num(tr.children[2].textContent);tr.children[3].textContent=money(a);sub+=a;});
var r=$('taxrate'),tax=r?sub*num(r.textContent)/100:0;put('sub',sub);put('tax',tax);put('total',sub+tax);}
$('addrow').addEventListener('click',function(){var tr=body.rows[0].cloneNode(true);tr.children[0].textContent=t.getAttribute('data-newitem')||'Item';tr.children[1].textContent='1';tr.children[2].textContent=money(0);body.appendChild(tr);calc();});
$('print').addEventListener('click',function(){window.print();});
t.addEventListener('input',calc);if($('taxrate'))$('taxrate').addEventListener('input',calc);$('today').textContent=new Date().toLocaleDateString(loc);
var dd=$('due');if(dd){var due=new Date();due.setDate(due.getDate()+(+t.getAttribute('data-days')||30));dd.textContent=due.toLocaleDateString(loc);}calc();})();
"""
PACK_JS = """
(function(){var f=document.getElementById('pack');if(!f)return;var out=document.getElementById('pack-out');var L=JSON.parse(document.getElementById('pack-data').textContent);
var KEY='goka-packlist';var saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
function build(){var type=f.querySelector('[name=type]').value,days=+f.querySelector('[name=days]').value;var groups=[];
Object.keys(L.base).forEach(function(g){groups.push([g,L.base[g].slice()]);});(L.types[type]||[]).forEach(function(x){var g=groups.find(function(y){return y[0]===x[0]});if(g)g[1]=g[1].concat(x[1]);else groups.push([x[0],x[1].slice()]);});
var h='';groups.forEach(function(g){h+='<h3>'+g[0]+'</h3><ul class="check">';g[1].forEach(function(item){var it=item.replace(/\\{d\\}/g,String(days)).replace(/\\{n\\}/g,String(Math.max(1,Math.ceil(days*(/socks|underwear/i.test(item)?1:0.5)))));var id=type+'|'+it;
h+='<li><label><input type="checkbox" data-id="'+id.replace(/"/g,'&quot;')+'"'+(saved[id]?' checked':'')+'> '+it+'</label></li>';});h+='</ul>';});
out.innerHTML=h;out.hidden=false;document.getElementById('pack-actions').hidden=false;}
f.addEventListener('change',build);f.addEventListener('submit',function(e){e.preventDefault();build();});
out.addEventListener('change',function(e){if(e.target.type==='checkbox'){saved[e.target.getAttribute('data-id')]=e.target.checked;try{localStorage.setItem(KEY,JSON.stringify(saved))}catch(x){}}});
document.getElementById('pack-print').addEventListener('click',function(){window.print();});
document.getElementById('pack-copy').addEventListener('click',function(){var s='';out.querySelectorAll('h3,li').forEach(function(el){s+=(el.tagName==='H3'?'\\n'+el.textContent.toUpperCase()+'\\n':'- '+el.textContent.trim()+'\\n');});if(navigator.clipboard)navigator.clipboard.writeText(s.trim()).then(function(){document.getElementById('pack-copy').textContent='Copied';});});
build();})();
"""

CSS = bp.CSS + """
.crumbs{margin:24px 0 28px;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:6px 8px;font-size:13px;line-height:1.6;color:var(--soft)}.crumbs a{color:var(--soft);text-decoration:none}.crumbs a:hover{text-decoration:underline}
.crumbs li+li::before{content:"›";margin-right:8px}
html[lang^=th] *{letter-spacing:0!important}
.shot{margin:28px 0;display:flex;flex-direction:column;align-items:center;gap:10px}.shot img{width:min(100%,280px);height:auto;border-radius:24px;background:var(--cream)}.shot figcaption{font-size:13px;color:var(--soft);text-align:center}
@media (max-width:760px){.crumbs{margin:20px 0 24px}.crumbs li:last-child{display:none}}
.article{max-width:720px}.article h1{font-size:clamp(32px,5vw,50px);line-height:1.15;margin:0 0 20px}.article .lede{font-size:18px;margin:0 0 28px}
.article h2{font:500 clamp(24px,3vw,32px)/1.25 var(--display);margin:48px 0 18px}.article h3{font:600 18px/1.4 var(--text);margin:28px 0 12px}
.article p,.article li{color:var(--muted)}.article ul,.article ol{padding-left:22px}.article li{margin:0 0 6px}
.tbl{overflow-x:auto;max-width:100%;margin:12px 0;-webkit-overflow-scrolling:touch}.tbl.full{max-width:none;width:min(1032px,calc(100vw - 2 * var(--gutter)))}.article table{border-collapse:collapse;width:100%;font-size:15px;margin:0}.article table.cmp{min-width:720px}.article th,.article td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--rule);vertical-align:top}.article th{font-weight:700;color:var(--ink)}
.count{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:22px 0 6px;font:500 clamp(48px,9vw,96px)/1 var(--display);letter-spacing:-.04em}.count small{font:600 16px/1 var(--text);letter-spacing:.5px;color:var(--muted)}
.count-sub{margin:0 0 6px;color:var(--muted);font-size:15px}
.ios-cta{display:none;margin:16px 0 0}html.is-ios .ios-cta{display:block}
.more{max-width:720px}.more details{border-bottom:1px solid var(--rule);padding:0}.more summary{cursor:pointer;padding:14px 0;font:600 16px/1.5 var(--text);color:var(--ink)}.more details p{margin:0 0 14px;color:var(--muted)}
.countdown-result{margin:28px 0 36px;padding:28px;border:1px solid var(--rule);border-radius:20px;background:var(--cream)}.countdown-result .count{margin:0}.countdown-result .count-sub{margin:16px 0 0}.calc-note{font-size:14px;color:var(--muted);margin:12px 0 24px}
@media (max-width:760px){.countdown-result{padding:24px 20px}.article .lede{font-size:17px}}
.calc{display:grid;gap:12px;grid-template-columns:1fr 1fr auto;align-items:end;margin:22px 0;padding:22px;border:1.5px solid var(--ink);border-radius:20px;background:var(--cream)}
.calc label{display:grid;gap:6px;font:700 12px/1 var(--text);letter-spacing:1.2px;text-transform:uppercase;color:var(--muted)}
.calc input,.calc select{font:400 16px/1.3 var(--text);padding:12px 14px;border:1.5px solid var(--rule);border-radius:12px;background:#fff;color:var(--ink);min-width:0}
.calc button,.btn{font:700 14px/1 var(--text);padding:15px 20px;border:0;border-radius:999px;background:var(--ink);color:#fff;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:8px}
.calc button:hover,.btn:hover{background:var(--yellow);color:var(--ink)}.btn svg{width:18px;height:18px;flex:none;fill:currentColor}.appcard .btn{white-space:nowrap}.btn.ghost{background:transparent;color:var(--ink);border:1.5px solid var(--ink)}
#calc-out .big,.tool-out .big{font:500 clamp(22px,3.4vw,32px)/1.3 var(--display);letter-spacing:-.02em;margin:8px 0 6px;color:var(--ink)}#calc-out .share a,.tool-out .share a{font-size:14px}
.tool-out p{margin:6px 0}.tool-out ul{margin:10px 0 6px}.calc.c2{grid-template-columns:minmax(0,1fr) auto}.calc.c4{grid-template-columns:minmax(0,.8fr) minmax(0,1.3fr) minmax(0,1fr) auto}
.pop{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0 0}.pop a{text-decoration:none;border:1px solid var(--rule);border-radius:16px;padding:16px;display:block}.pop a:hover{background:var(--cream)}
.pop span span{display:inline;margin:0}.pop b{display:block;font:500 30px/1 var(--display);letter-spacing:-.03em}.pop span{display:block;color:var(--muted);font-size:14px;margin-top:6px}
.appcard{display:flex;gap:18px;align-items:center;margin:48px 0 0;padding:22px;border:1.5px solid var(--ink);border-radius:22px;background:#fff}
.appcard img{width:72px;height:72px;border-radius:16px;flex:none}.appcard b{display:block;font:600 18px/1.3 var(--text)}.appcard p{margin:4px 0 12px;color:var(--muted);font-size:15px}
.ask{margin:36px 0 0;padding-top:18px;border-top:1px solid var(--rule);font-size:14px;color:var(--muted)}.ask a{margin-right:14px;text-underline-offset:3px}
.meta{font-size:13px;color:var(--soft);margin:16px 0 0}.meta.meta-top{margin:-4px 0 14px}
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
.itin .days{display:grid;gap:14px;margin-top:18px}.itin .day{border-top:1.5px solid var(--ink);padding-top:10px;break-inside:avoid}.itin .day h3{margin:0 0 6px;font:600 17px/1.4 var(--text)}.itin .day h3 [contenteditable]{display:inline-block;min-width:8em}.itin .slot{display:grid;grid-template-columns:96px minmax(0,1fr);gap:10px;padding:6px 0;border-bottom:1px solid var(--rule)}.itin .slot b{font:700 11px/1.9 var(--text);letter-spacing:1.2px;text-transform:uppercase;color:var(--soft)}
.rcpt-line{margin:14px 0;font-size:17px;line-height:1.7}.rcpt-line strong{font-size:19px;letter-spacing:.06em}.rcpt-sign{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px 24px;margin-top:40px}
.check{list-style:none;padding:0;margin:0 0 18px;columns:2;column-gap:32px}.check li{break-inside:avoid;margin:0 0 6px}.check label{display:flex;gap:10px;align-items:flex-start;color:var(--ink);cursor:pointer}.check input{margin-top:5px;accent-color:var(--ink)}
html[lang=ja] .article table.cmp thead th{white-space:nowrap}html[lang=ja] .article table.cmp td:nth-child(4),html[lang=ja] .article table.cmp td:last-child{white-space:nowrap}
@media (max-width:760px){.calc,.calc.c2,.calc.c4{grid-template-columns:1fr}.inv{padding:20px}.inv th{letter-spacing:.4px}.inv td,.inv th{padding:8px 4px}.inv-parties{grid-template-columns:1fr}.check{columns:1}.appcard{flex-direction:column;align-items:flex-start}}
.print-title{display:none}
@media print{.print-title{display:block!important;font:600 22px/1.3 var(--display);margin:0 0 12px}.inv-wrap h3,#pack-out h3{break-after:avoid}header,.crumbs,.calc,.appcard,.ask,.meta,footer,#faq-section,.more,.article>*:not(.inv-wrap):not(#pack-out):not(.pack-head){display:none!important}.inv{border:0;padding:0}.inv [contenteditable]{border:0}.inv-tools,#pack-actions{display:none!important}body{font-size:13px}}
"""

def clip(t, n):   # 10-17 评审：商店描述按字符硬截会断在词中间；有空格就退到词边界，再加省略号
    if len(t) <= n: return t
    cut = t[:n - 1]; sp = cut.rfind(" ")
    return (cut[:sp] if sp > n * .6 else cut).rstrip(" ,;:–-") + "…"
APP_LINK = {"de": "Mehr zur App"}   # 卡片里去产品页的链接文字；其余语言沿用 app 短名
def app_card(app_key, lang):
    """页尾「去 iPhone 上做这件事」卡片：图标 + 商店名 + 一句话 + 商店按钮。"""
    p = BY_KEY[app_key]; s = bp.store_of({"variantOf": app_key, "lang": lang} if lang != "en" else p)
    page = bp.site_url(p, lang) if p.get("site") else bp.sibling_path(p, lang) if lang != "en" else p["path"]   # 有独立站（10-26 BeforeGo）去新站同语言页
    icon = bp.cdn(s["icon"], 256) if s.get("icon", "").startswith("http") else p["icon"]
    return (f'<aside class="appcard"><img src="{icon}" width="72" height="72" alt="" loading="lazy"><div>'
            f'<p class="label" style="margin:0 0 6px">{esc(ts(lang, "get"))}</p><b>{esc(s["name"])}</b><p>{esc(p["home"]["blurb"] if lang == "en" else clip(s["description"].split(chr(10))[0], 160))}</p>'
            f'<a class="btn" href="{esc(bp.store_link({"variantOf": app_key, "lang": lang} if lang != "en" else p, s, "tool"))}">{bp.APPLE}{esc(bp.t(lang, "cta_store"))}</a> &nbsp; <a href="{page}" style="font-size:14px">{esc(APP_LINK.get(lang, p["home"]["label"]))} →</a></div></aside>')

def ask_ai(url, lang):
    q = {"pt-BR": f"Leia {url} e resuma os pontos principais em poucas frases.",
         "es-MX": f"Lee {url} y resume sus puntos principales en pocas frases.",
         "zh-Hant": f"請閱讀 {url}，用幾句話摘要重點。",
         "ja": f"{url} を読んで、要点を数文でまとめてください。",
         "th": f"อ่าน {url} แล้วสรุปประเด็นสำคัญเป็นไม่กี่ประโยค",
         "ko": f"{url} 을(를) 읽고 핵심을 몇 문장으로 요약해 주세요.",
         "de": f"Lies {url} und fasse die wichtigsten Punkte in wenigen Sätzen zusammen."}.get(lang, f"Read {url} and summarise its key points in a few sentences.")
    from urllib.parse import quote
    return (f'<p class="ask">{esc(ts(lang, "ask"))}: <a href="https://chatgpt.com/?q={quote(q)}" rel="nofollow noopener">ChatGPT</a>'
            f'<a href="https://www.perplexity.ai/search?q={quote(q)}" rel="nofollow noopener">Perplexity</a>'
            f'<a href="https://claude.ai/new?q={quote(q)}" rel="nofollow noopener">Claude</a></p>')

def faq_html(faq, lang):
    rows = "\n".join(f'    <div class="card"><h3>{esc(q)}</h3><p>{esc(a)}</p></div>' for q, a in faq)
    return f'<section class="sec" id="faq-section"><h2 id="faq">{esc(ts(lang, "faq"))}</h2><div class="grid">\n{rows}\n</div></section>'

def counter(d, lang, label="", us=False):
    n = days_to(d); unit = ts(lang, "today") if n == 0 else (ts(lang, "passed") if n < 0 else (ts(lang, "day") if n == 1 else ts(lang, "days")))
    if n == -1: unit = unit.replace("dias", "dia").replace("days", "day")
    wk = {"pt-BR": "semana", "en": "week"}.get(lang) if n // 7 == 1 else None
    w = f"{n // 7} {wk or ts(lang, 'weeks')}" + (f"{' e ' if lang == 'pt-BR' else ' + '}{n % 7} {ts(lang, 'days') if n % 7 != 1 else ts(lang, 'day')}" if n % 7 else "") if n >= 7 else ""
    if lang == "ja" and n >= 7: w = f"{n // 7}週と{n % 7}日" if n % 7 else f"{n // 7}週間"
    if lang == "zh-Hant" and n >= 7: w = f"{n // 7} 週又 {n % 7} 天" if n % 7 else f"{n // 7} 週"
    if lang == "ko" and n >= 7: w = f"{n // 7}주 {n % 7}일" if n % 7 else f"{n // 7}주"
    return (f'<div class="count" data-date="{d.isoformat()}"><span data-n>{abs(n) if n else ""}</span><small data-unit>{esc(unit)}</small></div>'
            f'<p class="count-sub">{esc(label + " · " if label else "")}{esc(fmt_us(d) if us else fmt(d, lang))}{f" · <span data-weeks>{esc(w)}</span>" if w else ""}</p>')

# 首个倒数数字正下方的一行下载按钮：只对 iOS 访客显示（build_seo 的 DEVICE 给 <html> 打 is-ios）。
# 10-10 复盘：下载按钮原来只在页面靠后的位置，搜进来的人看完数字就走。ct=web-countdown-top，和页尾卡片的 -tool 分开计。
TOP_CTA = {"en": "Add it to your Home Screen — free", "pt-BR": "Colocar na Tela de Início — grátis",
           "ja": "ホーム画面・ロック画面に置く（無料）", "zh-Hant": "放到主畫面（免費）",
           "ko": "잠금 화면·홈 화면에 두기 (무료)"}   # 短到 375 宽一行放得下
def top_cta(app_key, lang, label=None):   # label：锁屏教程页说「放到锁屏」，其余页默认说主屏
    p = BY_KEY[app_key]; a = {"variantOf": app_key, "lang": lang} if lang != "en" else p
    return f'<p class="ios-cta"><a class="btn" href="{esc(bp.store_link(a, bp.store_of(a), "top"))}">{bp.APPLE}{esc(label or TOP_CTA[lang])}</a></p>'

# 「更多问题」：搜索词的其它问法（GSC 查询词 / 联想词），默认折叠、点开可见，正文真实存在——不做隐藏文字。不进 FAQPage 结构化数据。
MORE_H = {"en": "More questions", "pt-BR": "Mais perguntas", "ja": "そのほかの質問", "zh-Hant": "更多問題", "es-MX": "Más preguntas", "th": "คำถามเพิ่มเติม", "ko": "더 궁금한 점", "de": "Weitere Fragen"}
def more_html(items, lang):
    rows = "".join(f"<details><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in items)
    return f'<section class="sec more"><h2>{esc(MORE_H[lang])}</h2>{rows}</section>'

def live(d, lang="pt-BR"):
    """正文里的一小段实时天数（COUNT_JS 在访问当天重算）。"""
    n = days_to(d); u = ts(lang, "today") if n == 0 else (ts(lang, "passed") if n < 0 else (ts(lang, "day") if n == 1 else ts(lang, "days")))
    if n == -1: u = u.replace("dias", "dia").replace("days", "day")
    sep = "" if lang == "ko" else " "
    return f'<span data-date="{d.isoformat()}"><span data-n>{abs(n) if n else ""}</span>{sep}<span data-unit>{esc(u)}</span></span>'

def wrap_tables(body):
    """表格外包 .tbl（overflow-x:auto），手机上表格自己滚，不把页面撑宽。"""
    return body.replace("<table>", '<div class="tbl"><table>').replace('<table class="cmp">', '<div class="tbl full"><table class="cmp">').replace("</table>", "</table></div>")

def shell(pg, body):
    body = wrap_tables(body)
    lang = pg["lang"]; T = lambda k, **kw: bp.t(lang, k, **kw)
    if pg.get("app") == "countdown" and lang in TOP_CTA and '<p class="count-sub">' in body:
        body = re.sub(r'(<p class="count-sub">.*?</p>)', lambda m: m.group(1) + top_cta("countdown", lang), body, count=1, flags=re.S)
    hub, home = HUBS.get(lang, "/tools/"), HOMES.get(lang, "/")
    if pg.get("crumbs"):   # 不在 /tools/ 和 /blog/ 下的页（/about/）自带面包屑
        crumbs = pg["crumbs"]
    elif pg["path"].startswith("/blog/"):
        crumbs = [(ts(lang, "home"), "/"), ("Blog", "/blog/" if pg["path"] != "/blog/" else None)] + ([(pg["crumb"], None)] if pg.get("crumb") else [])
    else:
        crumbs = [(ts(lang, "home"), home), (ts(lang, "tools"), hub)] + ([(pg["crumb"], None)] if pg.get("crumb") else [])
    crumb_html = "".join(f'<li>{f"<a href={chr(34)}{h}{chr(34)}>{esc(l)}</a>" if h else esc(l)}</li>' for l, h in crumbs)
    meta = ""
    if pg.get("published"):
        meta = f'<p class="meta">{esc(ts(lang, "published"))} {pg["published"]} · {esc(ts(lang, "updated"))} {pg.get("updated", pg["published"])} · go ka</p>'
        # 10-16 GEO 实测：AI 要找「新鲜」的来源，日期放在标题下面比放在文末更容易被读到。先只开在两页教程上（meta_top）。
        if pg.get("meta_top") and "</h1>" in body:
            body = body.replace("</h1>", "</h1>\n" + meta.replace('class="meta"', 'class="meta meta-top"'), 1)
            meta = ""
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
<style>{CSS + pg.get('css', '')}</style>
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
{more_html(pg["more"], lang) if pg.get("more") else ""}
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

def holiday_page(slug, name, d, lang, title, desc, h1, intro, glance, ideas, faq, next_dates, moving=False, published="2026-09-26", extra="", repeat_note=None, us=False, lock_anchor="how to put a countdown on your iPhone Lock Screen", tail=""):
    # 10-16：步骤原来只讲主屏，加第 4 步锁屏并链到锁屏教程（锚文本按页换，别 7 页一个样）；tail 放在页尾，避免和「Still choosing」连成一串链接（评审 92）
    F = fmt_us if us else (lambda x: fmt(x, lang))
    # moving：按阴历 / 印度历定日子的节日（排灯节等）每年公历日期不同，「每年重复」会数错，改成提示明年另加
    repeat = repeat_note or ("The date moves every year, so add next year's date as a new event instead of turning on <strong>Repeat yearly</strong>."
              if moving else "Turn on <strong>Repeat yearly</strong> if you want it back next year.")
    body = f"""<h1>{esc(h1)}</h1>
<p class="lede">{intro}</p>
{counter(d, lang, name, us)}
<h2>{esc(name)} at a glance</h2>
<table><tbody>{"".join(f"<tr><th>{esc(k)}</th><td>{v}</td></tr>" for k, v in glance)}</tbody></table>
<h2>Put the countdown on your Home Screen</h2>
<p>A countdown you have to open an app to see is a countdown you forget. With <a href="/countdown/">Countdown Widget: Any Event</a> you add the date once and it sits on the Home Screen or Lock Screen as a widget — every widget size is free, events are unlimited, and it can remind you on the day and as far ahead as you like.</p>
<ol><li>Install the app and tap <strong>Add Event</strong> (or <strong>+</strong> once you already have events). Pick the template or type the name.</li><li>{'Set the date to' if repeat_note else 'If you typed the name yourself, set the date to'} {esc(F(d))}. {repeat}</li><li>Long-press the Home Screen → <strong>Edit</strong> → <strong>Add Widget</strong> (on iOS 17, tap <strong>+</strong>) → Countdown. Choose the size you like.</li><li>For the Lock Screen, touch and hold it → <strong>Customize</strong> → <strong>Add Widgets</strong> → Countdown. The full steps are in <a href="/blog/countdown-widget-iphone-home-lock-screen/">{esc(lock_anchor)}</a>.</li></ol>
{extra}<p>Still choosing an app? See <a href="/tools/best-countdown-widget-apps-iphone/">which countdown widget apps are free</a> — seven compared.</p>
<h2>Countdown ideas</h2>
<ul>{"".join(f"<li>{i}</li>" for i in ideas)}</ul>
<h2>{esc(re.sub(r'\s\d{4}$', '', name))} in the next few years</h2>
<table><thead><tr><th>Year</th><th>Date</th><th>Day of the week</th></tr></thead><tbody>{"".join(f"<tr><td>{y}</td><td>{esc(F(dd))}</td><td>{dd.strftime('%A')}</td></tr>" for y, dd in next_dates)}</tbody></table>
{tail}"""
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
<form class="calc" id="calc"><label>Event<input type="text" name="name" placeholder="Wedding, exam, trip…" maxlength="60"></label><label>Date<input type="date" name="date" required></label><button type="submit" data-track-id="calc-submit">Count the days</button></form>
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
<p>For a countdown you can see without opening anything, put it on your iPhone Home Screen or Lock Screen with the app below; the steps are in <a href="/blog/countdown-widget-iphone-home-lock-screen/">how to put a countdown on your iPhone Lock Screen</a>.</p>"""})

# 2–4. 节日页
PAGES.append(holiday_page("days-until-christmas", "Christmas 2026", XMAS, "en",
  "How many days until Christmas 2026? Live countdown", "Christmas Day 2026 is on Friday, December 25, 2026. Live countdown in days and weeks, plus a free Home Screen widget for your iPhone.",
  "How many days until Christmas 2026?",
  f"Christmas Day 2026 falls on <strong>Friday, December 25, 2026</strong>. Christmas Eve is Thursday the 24th and Boxing Day is Saturday the 26th. The counter below updates every day.",
  [("Christmas Day", "Friday, December 25, 2026"), ("Christmas Eve", "Thursday, December 24, 2026"), ("Boxing Day / St Stephen's Day", "Saturday, December 26, 2026"), ("First Sunday of Advent", "Sunday, November 29, 2026"), ("Twelve days of Christmas end", "Wednesday, January 6, 2027 (Epiphany)")],
  ["A countdown to Christmas Eve for the kids, with a reminder the morning before.", "One countdown per December event: the school play, the last working day, the flight home.", "A count-up from last Christmas to see how fast the year went."],
  [("What day of the week is Christmas 2026?", "Christmas Day 2026 is a Friday. That gives most people a long weekend from Friday, December 25 to Sunday, December 27, and many workplaces add Christmas Eve, Thursday, December 24."),
   ("How many weeks until Christmas 2026?", ("Divide the days by seven: on" if days_to(XMAS) >= 7 else "On") + f" {TODAY.strftime('%B %-d, %Y')}, {en_weeks_left(days_to(XMAS), 'Christmas', ', which is ')}. The counter at the top of this page recalculates it on the day you visit."),
   ("How many days between Halloween and Christmas?", "55 days. Halloween is October 31 and Christmas Day is December 25, so there are 55 days from one to the other in any year."),
   ("When is Christmas 2027?", "Saturday, December 25, 2027. Christmas 2028 is on a Monday, and Christmas 2029 on a Tuesday."),
   ("How do I put a Christmas countdown on my iPhone Home Screen?", "Add the date in Countdown Widget: Any Event, then long-press the Home Screen, tap Edit → Add Widget (on iOS 17, tap +), and choose Countdown. The widgets are free in every size, and the event can repeat every year.")],
  [(2026, XMAS), (2027, dt.date(2027, 12, 25)), (2028, dt.date(2028, 12, 25)), (2029, dt.date(2029, 12, 25))],
  tail='<p>The <a href="/tools/christmas-countdown-widget-iphone/">Christmas countdown widget for iPhone</a> guide covers the extra large size in iOS 27 and a few Christmas setups.</p>\n', us=True,
  lock_anchor="how to add a Lock Screen countdown widget"))

PAGES.append(holiday_page("days-until-halloween", "Halloween 2026", HALLOWEEN, "en",
  "How many days until Halloween 2026? Live countdown", "Halloween 2026 is on Saturday, October 31, 2026. Live countdown in days and weeks, plus a free Home Screen widget for your iPhone.",
  "How many days until Halloween 2026?",
  "Halloween 2026 falls on <strong>Saturday, October 31, 2026</strong> — a weekend Halloween, which last happened in 2021. The counter below updates every day.",
  [("Halloween", "Saturday, October 31, 2026"), ("All Saints' Day", "Sunday, November 1, 2026"), ("Día de los Muertos", "Monday, November 2, 2026"), ("Days from Halloween to Christmas", "55")],
  ["A countdown to the party with a reminder a week before, so the costume gets ordered in time.", "A trick-or-treat countdown on the kids' shared iPad.", "A Home Screen widget counting down the days to October 31."],
  [("What day of the week is Halloween 2026?", "Saturday. Halloween 2026 is on Saturday, October 31, 2026, so parties and trick-or-treating fall on a weekend."),
   ("How many weeks until Halloween 2026?", f"On {TODAY.strftime('%B %-d, %Y')}, {en_weeks_left(days_to(HALLOWEEN), 'Halloween', ', or ')}. The counter on this page recalculates when you open it."),
   ("When is Halloween 2027?", "Sunday, October 31, 2027. Halloween 2028 falls on a Tuesday."),
   ("How do I get a Halloween countdown widget on iPhone?", "Add October 31 as an event in Countdown Widget: Any Event and set it to repeat yearly, then add the widget from the Home Screen's Edit → Add Widget (on iOS 17, tap +) menu. Every widget size is free.")],
  [(2026, HALLOWEEN), (2027, dt.date(2027, 10, 31)), (2028, dt.date(2028, 10, 31)), (2029, dt.date(2029, 10, 31))], us=True,
  lock_anchor="the Lock Screen widget guide",
  tail='<p>After Halloween comes <a href="/tools/days-until-thanksgiving/">Thanksgiving</a> on November 26, and Christmas is 55 days after October 31. The <a href="/tools/christmas-countdown-widget-iphone/">Christmas countdown widget for iPhone</a> walks through the holiday setup.</p>\n'))

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
   ("How many weeks until Diwali 2026?", f"On {TODAY.strftime('%-d %B %Y')}, {en_weeks_left(days_to(DIWALI), 'Diwali', ', or ')}. The counter on this page recalculates when you open it."),
   ("Why does the date of Diwali change every year?", "Diwali follows the Hindu lunisolar calendar: it falls on the new-moon night (Amavasya) of the month of Kartik, so its date in the Gregorian calendar moves between mid-October and mid-November."),
   ("How do I get a Diwali countdown widget on iPhone?", "Add 8 November 2026 as an event in Countdown Widget: Any Event, then add the widget from the Home Screen's Edit → Add Widget (on iOS 17, tap +) menu. Because the date moves, add next year's Diwali as a new event rather than repeating it yearly. Every widget size is free.")],
  [(2026, DIWALI), (2027, dt.date(2027, 10, 29)), (2028, dt.date(2028, 10, 17))], moving=True, published="2026-09-28"))

PAGES.append(holiday_page("days-until-new-year", "New Year 2027", NYE, "en",
  "How many days until New Year 2027? Live countdown", "New Year's Day 2027 is on Friday, January 1, 2027; New Year's Eve is Thursday, December 31, 2026. Live countdown plus a free iPhone widget.",
  "How many days until New Year 2027?",
  "New Year's Day 2027 falls on <strong>Friday, January 1, 2027</strong>, so New Year's Eve is Thursday, December 31, 2026. The counter below updates every day.",
  [("New Year's Eve", "Thursday, December 31, 2026"), ("New Year's Day", "Friday, January 1, 2027"), ("Lunar New Year 2027", "Saturday, February 6, 2027 (Year of the Goat)"), ("Days left in 2026", f"{days_to(REV) + 1} (as of {TODAY.isoformat()})")],
  ["A countdown to midnight with the party address in the notes on the back of the event.", "A count-up from January 1 for a new habit — the widget shows the streak in days.", "One countdown for the first working day, so the holiday has a shape."],
  [("What day of the week is New Year's Day 2027?", "Friday. New Year's Eve 2026 is a Thursday and January 1, 2027 is a Friday, which makes a three-day weekend for many people."),
   ("How many days are left in 2026?", (f"As of {TODAY.strftime('%B %-d, %Y')}, there were {days_to(REV) + 1} days left in 2026, counting today." if days_to(REV) >= 1 else f"On {TODAY.strftime('%B %-d, %Y')}, there was 1 day left in 2026: today, New Year's Eve." if days_to(REV) == 0 else f"As of {TODAY.strftime('%B %-d, %Y')}, the year 2026 had already ended.") + " The counter on this page recalculates when you open it."),
   ("When is Lunar New Year 2027?", "Saturday, February 6, 2027. It begins the Year of the Goat."),
   ("How do I keep a New Year countdown on my Lock Screen?", "Add January 1, 2027 in Countdown Widget: Any Event, then on the Lock Screen long-press → Customize → add the Countdown widget. Lock Screen widgets are free, like every other size.")],
  [(2027, NYE), (2028, dt.date(2028, 1, 1)), (2029, dt.date(2029, 1, 1)), (2030, dt.date(2030, 1, 1))], us=True,
  lock_anchor="our guide to Lock Screen countdown widgets",
  tail='<p>New Year\'s Day is a week after Christmas, so you can keep both in one list widget: see the <a href="/tools/christmas-countdown-widget-iphone/">Christmas countdown widget for iPhone</a>.</p>\n'))

# 10-16：美区。用户 10-16「关注美国的内容，广告中心和用户重心在美国」。
# 感恩节：美国 = 11 月第四个星期四（2026-11-26）；Google US 联想词「thanksgiving countdown 2026 / clock / calendar / app」。商店描述的模板里有 Thanksgiving。
# 日期每年变（第四个星期四）：App 现成事件 thanksgiving = .yearly + nextNthWeekday(11,5,4)，每年自动落在第四个星期四（EventTemplate.swift）；手打名字的普通每年重复会固定月日 → repeat_note 分开说（10-16 评审）。
THANKS = dt.date(2026, 11, 26)
PAGES.append(holiday_page("days-until-thanksgiving", "Thanksgiving 2026", THANKS, "en",
  "How many days until Thanksgiving 2026? Live countdown (Nov 26)", "Thanksgiving 2026 in the US is on Thursday, November 26, 2026, with Black Friday on the 27th. Live countdown in days and weeks, plus a free iPhone widget.",
  "How many days until Thanksgiving 2026?",
  "Thanksgiving 2026 in the United States falls on <strong>Thursday, November 26, 2026</strong> — the fourth Thursday of November. Black Friday is the next day, November 27. The counter below updates every day.",
  [("Thanksgiving Day (US)", "Thursday, November 26, 2026"), ("Black Friday", "Friday, November 27, 2026"), ("Cyber Monday", "Monday, November 30, 2026"),
   ("Days from Thanksgiving to Christmas", "29"), ("Thanksgiving in Canada", "Monday, October 12, 2026 (second Monday of October)")],
  ["A countdown to the trip home, with the flight or the drive written on the back of the event.", "A countdown to Black Friday with a reminder the night before.",
   "A list widget with Thanksgiving, the first Sunday of Advent and Christmas Day, so the whole season sits on one screen."],
  [("What date is Thanksgiving 2026?", "Thursday, November 26, 2026. In the US, Thanksgiving is always the fourth Thursday of November, so the date moves between November 22 and 28."),
   ("How many weeks until Thanksgiving 2026?", f"On {TODAY.strftime('%B %-d, %Y')}, {en_weeks_left(days_to(THANKS), 'Thanksgiving', ': ')}. The counter on this page recalculates when you open it."),
   ("When is Thanksgiving 2027?", "Thursday, November 25, 2027. Thanksgiving 2028 is on November 23 and Thanksgiving 2029 on November 22."),
   ("How many days are there between Thanksgiving and Christmas 2026?", "29 days, from Thursday, November 26 to Friday, December 25, 2026."),
   ("How do I get a Thanksgiving countdown widget on iPhone?", "In Countdown Widget: Any Event, tap Add Event (or the + button once you already have events) and pick Thanksgiving from the ready-made events: it lands on the fourth Thursday of November and comes back on the right Thursday every year. Then long-press the Home Screen, tap Edit → Add Widget (on iOS 17, tap the + in the top-left corner) and choose Countdown. Every widget size is free.")],
  [(2026, THANKS), (2027, dt.date(2027, 11, 25)), (2028, dt.date(2028, 11, 23)), (2029, dt.date(2029, 11, 22))], published="2026-10-16", us=True,
  lock_anchor="the Lock Screen guide",
  tail='<p>Christmas is 29 days after Thanksgiving this year, and the same app can count down to it: see the <a href="/tools/christmas-countdown-widget-iphone/">Christmas countdown widget for iPhone</a>.</p>\n',
  repeat_note="Picked from the ready-made events, Thanksgiving already repeats on the fourth Thursday of November every year. If you typed the name yourself, add next year's date as a new event instead, because a plain yearly repeat keeps the same day of the month."))

# 10-16：美区「想把倒数放到手机上」——Google US 联想词「christmas countdown widget iphone」「countdown widget iphone free / lock screen free」
# 「free countdown widget iphone」。GSC 10-12 起有点击的全是这类词（待ち受け / 桌布 / tela de bloqueio）。
# 步骤依据 Apple 支持 iOS 27：Add, edit, and remove widgets（Add Widget、长按图标选尺寸）、Customize apps and widgets（sizes up to extra large）、
# Create a custom Lock Screen（Customize → Add Widgets → Done）、What's new in iOS 27（Extra-large widgets）。10-16 curl 读原文。
# app 说法只用 en-US 商店描述：EVERY WIDGET, FREE / Every widget size, Home + Lock / Unlimited / Recurring yearly / Reminders / 模板含 Christmas；
# 自己的照片、Lock Screen Live Activity 属于 Pro。超大尺寸：「Every widget size」+ App 代码 WidgetFamily+ExtraLarge（iOS 27 起）。
ADVENT1, XEVE = dt.date(2026, 11, 29), dt.date(2026, 12, 24)
PAGES.append({"path": "/tools/christmas-countdown-widget-iphone/", "iphone_only": True, "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-10-16",
  "meta_top": True, "title": "Free Christmas 2026 Countdown Widget for iPhone: Lock & Home", "crumb": "Christmas countdown widget",
  "description": "A free Christmas countdown widget for your iPhone Lock Screen or Home Screen, step by step, with the iOS 27 extra large size. Christmas 2026 is December 25.",
  "hub_title": "Christmas countdown widget for iPhone", "hub_desc": "Lock Screen and Home Screen steps, the iOS 27 extra large size, and a few Christmas setups.",
  "js": [COUNT_JS], "faq": [
    ("Is there a free Christmas countdown widget for iPhone?", "Yes. In Countdown Widget: Any Event every widget size is free, on the Home Screen and the Lock Screen, and you can keep as many countdowns as you like. Pro unlocks the Pro backdrops, your own photos, the Pro typefaces and the Lock Screen Live Activity; the widgets are not part of it."),
    ("Will the Christmas countdown come back next year?", "Yes. Christmas is always December 25, so with Repeat yearly on — the ready-made Christmas event already has it — the countdown starts toward Christmas 2027 the day after Christmas 2026."),
    ("Can I put a Christmas photo behind the countdown?", "Using your own photo behind a countdown is part of Countdown Pro. The free version has its own backdrops, and the widget works the same either way."),
    ("Is the Lock Screen widget the same as a Live Activity?", "No. The Lock Screen widget sits under the clock and is free. The Lock Screen Live Activity is a separate, Pro feature."),
    ("Can I make the widget bigger than large?", "On iOS 27, yes: touch and hold the Countdown app icon or widget on the Home Screen and choose the extra large size. Earlier versions of iOS stop at large."),
    ("Does it work on Android?", "No. Countdown is an app for iPhone and iPad. On Android, look on Google Play for a countdown app with a Home Screen widget."),
  ],
  "body": f"""<h1>Christmas countdown widget for iPhone</h1>
<p class="lede">Add Christmas — <strong>Friday, December 25, 2026</strong> — as an event in a countdown app, then put its widget on the Lock Screen (<strong>Customize</strong> → <strong>Add Widgets</strong>) or the Home Screen (<strong>Edit</strong> → <strong>Add Widget</strong>). In Countdown Widget: Any Event every widget size is free, and the widget counts down by itself every day.</p>
{counter(XMAS, "en", "Christmas Day", us=True)}
<h2>On the Lock Screen</h2>
<ol><li>Install <a href="/countdown/">Countdown Widget: Any Event</a>, tap <strong>Add Event</strong> (or <strong>+</strong> once you already have events) and pick Christmas from the ready-made events, or type a name and set the date to December 25, 2026.</li>
<li>Touch and hold the Lock Screen until the <strong>Customize</strong> button appears at the bottom, then tap it.</li>
<li>Tap <strong>Add Widgets</strong> under the clock, or tap the widgets that are already there.</li>
<li>Choose Countdown, then tap <strong>Done</strong>.</li></ol>
<h2>On the Home Screen</h2>
<ol><li>Touch and hold an empty area until the apps jiggle.</li>
<li>Tap <strong>Edit</strong> → <strong>Add Widget</strong> (on iOS 17, tap <strong>+</strong>), search for Countdown and swipe through the sizes.</li>
<li>Tap <strong>Add Widget</strong>, drag it into place, then tap <strong>Done</strong>.</li></ol>
<p>You can also touch and hold the Countdown app icon and pick a size at the bottom of the menu. iOS 27 adds a bigger size: Apple says extra-large widgets “let you see more information from your favorite apps right on the Home Screen” (<a href="https://support.apple.com/guide/iphone/whats-new-in-ios-27-iphfed2c4091/ios" rel="noopener">What’s new in iOS 27</a>). Countdown offers that size too, and every size is free.</p>
<h2>Wallpaper or widget?</h2>
<table><thead><tr><th></th><th>Number on a wallpaper</th><th>Widget</th></tr></thead><tbody>
<tr><th>The number</th><td>Stays as you made it</td><td>Goes down by one every day</td></tr>
<tr><th>Work</th><td>Make a new image each day</td><td>Set the date once</td></tr>
<tr><th style="white-space:nowrap">Where</th><td>Behind everything</td><td>Under the Lock Screen clock, or anywhere on the Home Screen</td></tr>
</tbody></table>
<p>Prefer the number on a picture? The <a href="/tools/countdown-wallpaper-maker/">countdown wallpaper maker</a> puts it on your own photo; make a new one when you want a fresh count. For a number that stays current, use the widget with a plain photo behind it.</p>
<h2>Christmas setups that work well</h2>
<ul><li><strong>One big number:</strong> a single countdown to Christmas Day on the Lock Screen, set to repeat yearly so it is back on December 26.</li>
<li><strong>The whole season in a list:</strong> the first Sunday of Advent ({fmt_us(ADVENT1)}), Christmas Eve ({fmt_us(XEVE)}), Christmas Day and New Year's Eve, shown together in the list widget.</li>
<li><strong>The trip home:</strong> a countdown to the flight, with a reminder a week before and the booking written on the back of the event.</li>
<li><strong>For the kids:</strong> a countdown to Christmas Eve on a shared iPad, with a reminder the morning before.</li></ul>
<p>Just want the number? <a href="/tools/days-until-christmas/">How many days until Christmas 2026</a> has the live count and the dates for the next few years. Full Lock Screen and Home Screen steps for any event are in <a href="/blog/countdown-widget-iphone-home-lock-screen/">how to put a countdown on your iPhone Lock Screen</a>, and if you are still choosing an app, see <a href="/tools/best-countdown-widget-apps-iphone/">which countdown widget apps are free</a>.</p>"""})

# 10-12：GSC 显示有点击的是「想把倒数放到手机上」的词（锁屏 / 待ち受け），所以每页的手机一节先讲 Tela Bloqueada，再讲 Tela de Início，
# 并链到锁屏教程页。原来这里只写了 Tela de Início 的步骤。
PT_WIDGET_STEP = ("<li>Na Tela Bloqueada: toque e segure → <strong>Personalizar</strong> → Tela Bloqueada → <strong>Adicionar widgets</strong> → Countdown.</li>"
                  "<li>Na Tela de Início: segure a tela → <strong>Editar</strong> → <strong>Adicionar widget</strong> (no iOS 17, toque em <strong>+</strong>) → Countdown.</li>")
PT_LOCK_LINK = ('<p>Passo a passo, e a diferença entre papel de parede e widget: <a href="/tools/pt-br/contagem-regressiva-tela-de-bloqueio-iphone/">'
                'como colocar contagem regressiva na tela de bloqueio do iPhone</a>.</p>')

# 5. ENEM 2026（pt-BR）
PAGES.append({"path": "/tools/pt-br/dias-para-o-enem-2026/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-26",
  "title": "Quantos dias faltam para o ENEM 2026? (8 e 15 de novembro)", "crumb": "ENEM 2026",
  "description": "As provas do ENEM 2026 são em 8 e 15 de novembro de 2026 (Edital nº 64 do Inep). Contagem regressiva ao vivo e widget grátis para a tela de bloqueio do iPhone.",
  "hub_title": "Quantos dias faltam para o ENEM 2026?", "hub_desc": "Contagem regressiva para os dois domingos de prova, 8 e 15 de novembro.",
  "js": [COUNT_JS], "faq": [
    ("Quando é o ENEM 2026?", "As provas serão aplicadas nos domingos 8 de novembro e 15 de novembro de 2026, conforme o Edital nº 64, publicado pelo Inep em 22 de maio de 2026."),
    ("Quando foram as inscrições do ENEM 2026?", "De 25 de maio a 12 de junho de 2026, pela Página do Participante do Inep."),
    ("O que cai em cada dia do ENEM 2026?", "No primeiro dia (8/11): Linguagens, Códigos e suas Tecnologias, Redação e Ciências Humanas e suas Tecnologias. No segundo dia (15/11): Ciências da Natureza e suas Tecnologias e Matemática e suas Tecnologias, com 90 questões objetivas."),
    ("Quando sai o gabarito do ENEM 2026?", "Segundo o edital, até o 10º dia útil após o segundo dia de prova."),
    ("Como coloco a contagem regressiva do ENEM na tela de bloqueio do iPhone?", "Adicione 8 de novembro de 2026 no app Countdown: Contagem regressiva e, na Tela Bloqueada, toque e segure → Personalizar → Tela Bloqueada → Adicionar widgets → Countdown. Todos os tamanhos de widget são grátis e você pode criar outro evento para o dia 15."),
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
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Uma contagem regressiva que você precisa abrir para ver é uma contagem que você esquece. Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — todos os tamanhos são grátis, os eventos são ilimitados e o app avisa no dia e com a antecedência que você quiser.</p>
<ol><li>Instale o app e toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos). Dê o nome "ENEM — 1º dia".</li><li>Coloque a data <strong>8 de novembro de 2026</strong>. Crie outro evento para o dia 15.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<h2>Ideias para a reta final</h2>
<ul><li>Um evento por simulado, com lembrete na véspera.</li><li>Uma contagem progressiva desde o primeiro dia de estudo — o widget mostra a sequência em dias.</li><li>Depois da prova, uma contagem para a divulgação do resultado.</li></ul>"""})

# 6. Réveillon + Carnaval 2027（pt-BR）
PAGES.append({"path": "/tools/pt-br/contagem-regressiva-reveillon-2027/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-26",
  "title": "Quantos dias faltam para o Réveillon 2027? (quinta, 31/12)", "crumb": "Réveillon 2027",
  "description": "Réveillon: quinta-feira, 31/12/2026. Carnaval 2027: sábado, 6, a terça, 9 de fevereiro. Contagem ao vivo e widget grátis para a tela de bloqueio do iPhone.",
  "hub_title": "Quantos dias faltam para o Réveillon 2027?", "hub_desc": "Réveillon e Ano-Novo com contagem ao vivo, mais as datas do Carnaval 2027.",
  "more": [
    ('Quantos dias faltam para acabar o ano?', f'O ano termina na quinta-feira, 31 de dezembro de 2026. Contagem de hoje: {live(REV)}.'),
    ('Quantas semanas faltam para o fim do ano?', 'A linha abaixo do contador mostra as semanas e os dias que faltam para 31 de dezembro de 2026.'),
    ('Quantos dias faltam para 2027?', 'Um a mais que o contador do Réveillon: 2027 começa na sexta-feira, 1º de janeiro.'),
    ('Quantos dias faltam para a virada do ano?', 'A virada é na noite de quinta-feira, 31 de dezembro de 2026, para sexta-feira, 1º de janeiro de 2027; o contador desta página conta até o dia 31.'),
  ],
  "js": [COUNT_JS], "faq": [
    ("Em que dia da semana cai o Réveillon 2026/2027?", "A virada é na quinta-feira, 31 de dezembro de 2026, e o Ano-Novo, 1º de janeiro de 2027, cai numa sexta-feira — emenda com o fim de semana."),
    ("Quando é o Carnaval 2027?", "A terça-feira de Carnaval é 9 de fevereiro de 2027; os desfiles e blocos vão do sábado 6 à terça 9, e a Quarta-feira de Cinzas é 10 de fevereiro. A data vem da Páscoa (28 de março de 2027): o Carnaval é sempre 47 dias antes."),
    ("Quantos dias faltam para o Ano-Novo?", (f"Em {TODAY.strftime('%d/%m/%Y')}, faltavam {days_to(NYE)} dias para 1º de janeiro de 2027." if days_to(NYE) >= 2 else f"Em {TODAY.strftime('%d/%m/%Y')}, véspera de Ano-Novo, faltava 1 dia para 1º de janeiro de 2027." if days_to(NYE) == 1 else f"Em {TODAY.strftime('%d/%m/%Y')}, já era Ano-Novo de 2027." if days_to(NYE) == 0 else f"Em {TODAY.strftime('%d/%m/%Y')}, o Ano-Novo de 2027 já tinha passado.") + " O contador desta página recalcula no dia em que você abre."),
    ("Como coloco a contagem do Réveillon na Tela Bloqueada?", "Crie o evento 31 de dezembro de 2026 no Countdown: Contagem regressiva, marque repetir todo ano, e na Tela Bloqueada toque e segure → Personalizar → Tela Bloqueada → Adicionar widgets → Countdown. Os widgets são grátis em todos os tamanhos."),
  ],
  "body": f"""<h1>Quantos dias faltam para o Réveillon 2027?</h1>
<p class="lede">A virada do ano é na <strong>quinta-feira, 31 de dezembro de 2026</strong>, e o Ano-Novo, 1º de janeiro de 2027, cai numa sexta. O Carnaval 2027 vai de <strong>sábado, 6</strong> a <strong>terça-feira, 9 de fevereiro</strong>. Contadores ao vivo abaixo.</p>
<h2>Réveillon — 31 de dezembro de 2026</h2>
{counter(REV, "pt-BR", "Réveillon")}
<h2>Carnaval 2027 — de 6 a 9 de fevereiro</h2>
{counter(CARN_SAT, "pt-BR", "Sábado de Carnaval")}
<p>O Carnaval tem a sua própria página: <a href="/tools/pt-br/quantos-dias-faltam-para-o-carnaval-2027/">quantos dias faltam para o Carnaval 2027</a>, com as datas de cada dia e dos próximos anos.</p>
<h2>Todas as datas</h2>
<table><tbody>
<tr><th>Réveillon</th><td>quinta-feira, 31 de dezembro de 2026</td></tr>
<tr><th>Ano-Novo</th><td>sexta-feira, 1º de janeiro de 2027</td></tr>
<tr><th>Sábado de Carnaval</th><td>6 de fevereiro de 2027</td></tr>
<tr><th>Terça-feira de Carnaval</th><td>9 de fevereiro de 2027</td></tr>
<tr><th>Quarta-feira de Cinzas</th><td>10 de fevereiro de 2027</td></tr>
<tr><th>Páscoa 2027</th><td>domingo, 28 de março de 2027</td></tr>
<tr><th>Dias que restam em 2026</th><td>{days_to(REV) + 1} (em {TODAY.strftime('%d/%m/%Y')}, contando hoje)</td></tr>
</tbody></table>
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — grátis em todos os tamanhos, eventos ilimitados, com lembrete no dia. Marque <strong>repetir todo ano</strong> e o Réveillon volta sozinho em 2027.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e dê o nome “Réveillon”.</li><li>Data: 31 de dezembro de 2026, repetir todo ano.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<h2>Ideias</h2>
<ul><li>Uma contagem para a viagem de Carnaval, com o endereço no verso do evento.</li><li>Uma contagem progressiva desde 1º de janeiro para a meta do ano — o widget mostra os dias de sequência.</li><li>Um evento para o primeiro dia de trabalho depois das festas, para o feriado ter começo e fim.</li></ul>"""})

# 6a. Carnaval 2027（pt-BR）——10-10 从 Réveillon 页拆出。日期只用历法能算出来的（复活节前 47 天）；
# 各城市游行 / bloco 的日程每年由市政府另行公布，不写。「是不是假日」只写通则（联邦 ponto facultativo，州 / 市法另定）。
def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7; m = (a + 11 * h + 22 * l) // 451
    return dt.date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)
assert easter(2027) == dt.date(2027, 3, 28) and easter(2027) - dt.timedelta(days=47) == CARN_TUE
CARN_NEXT = [(y, easter(y) - dt.timedelta(days=47)) for y in (2027, 2028, 2029, 2030)]
PT_DM = lambda d: f"{'1º' if d.day == 1 else d.day} de {['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'][d.month - 1]}"
PAGES.append({"path": "/tools/pt-br/quantos-dias-faltam-para-o-carnaval-2027/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-10-10",
  "title": "Quantos dias faltam para o Carnaval 2027? (6 a 9 de fevereiro)", "crumb": "Carnaval 2027",
  "description": "Carnaval 2027: de sábado, 6, a terça-feira, 9 de fevereiro (Cinzas, dia 10). Contagem ao vivo e widget grátis para a tela de bloqueio do iPhone.",
  "hub_title": "Quantos dias faltam para o Carnaval 2027?", "hub_desc": "De sábado, 6, a terça-feira, 9 de fevereiro de 2027, com contagem ao vivo e as datas dos próximos anos.",
  "js": [COUNT_JS], "faq": [
    ("Quando é o Carnaval 2027?", "De sábado, 6 de fevereiro, a terça-feira, 9 de fevereiro de 2027. A Quarta-feira de Cinzas é 10 de fevereiro."),
    ("Quantos dias faltam para o Carnaval 2027?", f"Em {TODAY.strftime('%d/%m/%Y')}, {pt_left(days_to(CARN_SAT), 'o sábado de Carnaval, 6 de fevereiro de 2027', 'sábado de Carnaval', 'o sábado de Carnaval de 2027')}. O contador desta página recalcula no dia em que você abre."),
    ("O Carnaval é feriado nacional?", "Não. O Carnaval não está entre os feriados nacionais: nos órgãos federais, a segunda e a terça-feira costumam ser ponto facultativo, e o dia só é feriado onde uma lei estadual ou municipal determina. Vale conferir com a empresa ou a prefeitura."),
    ("Quando é o Carnaval 2028?", f"A terça-feira de Carnaval de 2028 é {PT_DM(CARN_NEXT[1][1])}, e o sábado de Carnaval é {PT_DM(CARN_NEXT[1][1] - dt.timedelta(days=3))}."),
    ("Como coloco a contagem do Carnaval na tela de bloqueio do iPhone?", "Crie o evento 6 de fevereiro de 2027 no Countdown: Contagem regressiva e, na Tela Bloqueada, toque e segure → Personalizar → Tela Bloqueada → Adicionar widgets → Countdown. A data do Carnaval muda todo ano, então para 2028 crie um evento novo em vez de repetir. Os widgets são grátis em todos os tamanhos."),
  ],
  "body": f"""<h1>Quantos dias faltam para o Carnaval 2027?</h1>
<p class="lede">O Carnaval 2027 começa no <strong>sábado, 6 de fevereiro</strong>, e a terça-feira de Carnaval é <strong>9 de fevereiro</strong>. A contagem abaixo é refeita todo dia.</p>
{counter(CARN_SAT, "pt-BR", "Sábado de Carnaval")}
<h2>Datas do Carnaval 2027</h2>
<table><tbody>
<tr><th>Sábado de Carnaval</th><td>{PT_DM(CARN_SAT)} de 2027</td></tr>
<tr><th>Domingo de Carnaval</th><td>{PT_DM(CARN_SAT + dt.timedelta(days=1))} de 2027</td></tr>
<tr><th>Segunda-feira de Carnaval</th><td>{PT_DM(CARN_SAT + dt.timedelta(days=2))} de 2027</td></tr>
<tr><th>Terça-feira de Carnaval</th><td>{PT_DM(CARN_TUE)} de 2027</td></tr>
<tr><th>Quarta-feira de Cinzas</th><td>{PT_DM(ASH)} de 2027</td></tr>
</tbody></table>
<h2>Por que a data muda todo ano</h2>
<p>O Carnaval acompanha a Páscoa: a terça-feira de Carnaval é sempre 47 dias antes do domingo de Páscoa. Em 2027 a Páscoa é em 28 de março, então a terça-feira de Carnaval cai em 9 de fevereiro.</p>
<h2>O Carnaval é feriado?</h2>
<p>O Carnaval não está entre os feriados nacionais. Nos órgãos federais, a segunda e a terça-feira costumam ser ponto facultativo, e o dia só é feriado onde uma lei estadual ou municipal determina. Vale conferir com a empresa ou a prefeitura antes de marcar a viagem.</p>
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — grátis em todos os tamanhos, eventos ilimitados, com lembrete no dia e com a antecedência que você quiser.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e dê o nome “Carnaval”.</li><li>Data: 6 de fevereiro de 2027. A data muda todo ano, então para 2028 crie um evento novo em vez de repetir.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<h2>O Carnaval nos próximos anos</h2>
<table><thead><tr><th>Ano</th><th>Sábado de Carnaval</th><th>Terça-feira de Carnaval</th></tr></thead><tbody>{"".join(f"<tr><td>{y}</td><td>{PT_DM(t - dt.timedelta(days=3))}</td><td>{PT_DM(t)}</td></tr>" for y, t in CARN_NEXT)}</tbody></table>
<p>Antes do Carnaval vem o fim do ano: veja <a href="/tools/pt-br/contagem-regressiva-reveillon-2027/">quantos dias faltam para o Réveillon</a> e <a href="/tools/pt-br/quantos-dias-faltam-para-o-natal-2026/">para o Natal</a>.</p>"""})

# 6b. Black Friday + Natal 2026（pt-BR）——09-28 借势：巴西是 Countdown 唯一有付费 + 五星的市场，节前 4–6 周要被收录
# 13º 日期依据 Lei 4.749/1965（1ª parcela até 30/11，2ª até 20/12；pt.wikipedia「Décimo terceiro salário」09-28 核对）。
# 2026 年 20/12 是周日 → 付款提前到前一个工作日 18/12（周五）：Contábeis 09-13、O Povo 两处 09-28 核对（评审第 5 轮指出）
BF26, CYBER26, BF27, BF28 = dt.date(2026, 11, 27), dt.date(2026, 11, 30), dt.date(2027, 11, 26), dt.date(2028, 11, 24)
DEC13_1, DEC13_2, DEC13_2_PAY = dt.date(2026, 11, 30), dt.date(2026, 12, 20), dt.date(2026, 12, 18)
PAGES.append({"path": "/tools/pt-br/contagem-regressiva-black-friday-2026/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-28",
  "title": "Quantos dias faltam para a Black Friday 2026? (27 de novembro)", "crumb": "Black Friday 2026",
  "description": "Black Friday 2026: contagem regressiva até 27 de novembro. Veja quantos dias faltam, a Cyber Monday e como pôr a contagem na tela de bloqueio do iPhone.",
  "hub_title": "Quantos dias faltam para a Black Friday 2026?", "hub_desc": "Black Friday e Cyber Monday com contagem ao vivo, mais a 1ª parcela do 13º.",
  "more": [
    ('Faltam quantos dias para a Black Friday?', f'A Black Friday 2026 é sexta-feira, 27 de novembro. Contagem de hoje: {live(BF26)}.'),
    ('Quantas semanas faltam para a Black Friday?', 'A linha abaixo do contador mostra as semanas e os dias que faltam para 27 de novembro de 2026.'),
    ('Quando é a Black Friday 2027?', 'Sexta-feira, 26 de novembro de 2027.'),
    ('A Black Friday é sempre na última sexta-feira de novembro?', 'Nem sempre. Ela é a sexta-feira seguinte ao Dia de Ação de Graças dos Estados Unidos, que cai na quarta quinta-feira de novembro; quando a última sexta-feira do mês é dia 30, como em 2029, a Black Friday é a penúltima. Em 2026 é dia 27; em 2027, dia 26.'),
  ],
  "js": [COUNT_JS], "faq": [
    ("Quando é a Black Friday 2026?", "Na sexta-feira, 27 de novembro de 2026. A Black Friday é sempre a sexta-feira depois do Dia de Ação de Graças dos Estados Unidos, que em 2026 cai na quinta-feira, 26 de novembro."),
    ("Quando é a Cyber Monday 2026?", "Na segunda-feira, 30 de novembro de 2026 — a segunda-feira logo depois da Black Friday."),
    ("Quantos dias faltam para a Black Friday?", f"Em {TODAY.strftime('%d/%m/%Y')}, {pt_left(days_to(BF26), '27 de novembro de 2026', 'Black Friday', 'a Black Friday de 2026')}. O contador desta página recalcula no dia em que você abre."),
    ("Até quando sai a 1ª parcela do 13º salário?", "Pela Lei 4.749/1965, a primeira parcela do 13º deve ser paga até 30 de novembro — em 2026, uma segunda-feira, três dias depois da Black Friday. A segunda parcela tem prazo legal em 20 de dezembro; como em 2026 esse dia é um domingo, o pagamento vai para o dia útil anterior, sexta-feira, 18 de dezembro."),
    ("Como coloco a contagem da Black Friday na tela de bloqueio do iPhone?", "Com o widget do Countdown: Contagem regressiva — o passo a passo está na seção sobre a tela de bloqueio, logo acima. Os widgets são grátis em todos os tamanhos."),
  ],
  "body": f"""<h1>Quantos dias faltam para a Black Friday 2026?</h1>
<p class="lede">A Black Friday 2026 é na <strong>sexta-feira, 27 de novembro</strong>. Veja abaixo quantos dias e semanas faltam: a contagem atualiza conforme a data do seu aparelho.</p>
<div class="countdown-result" aria-label="Contagem regressiva para a Black Friday 2026">
{counter(BF26, "pt-BR", "Black Friday")}
</div>
<h2>Cyber Monday — 30 de novembro de 2026</h2>
{counter(CYBER26, "pt-BR", "Cyber Monday")}
<h2>Todas as datas</h2>
<table><tbody>
<tr><th>Black Friday 2026</th><td>{fmt(BF26, "pt-BR")}</td></tr>
<tr><th>Cyber Monday 2026</th><td>{fmt(CYBER26, "pt-BR")}</td></tr>
<tr><th>1ª parcela do 13º (prazo legal)</th><td>até {fmt(DEC13_1, "pt-BR")}</td></tr>
<tr><th>2ª parcela do 13º</th><td>até {fmt(DEC13_2_PAY, "pt-BR")} (o prazo legal, 20/12, cai num domingo)</td></tr>
<tr><th>Da Black Friday ao Natal</th><td>{(XMAS - BF26).days} dias</td></tr>
</tbody></table>
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — todos os tamanhos são grátis, os eventos são ilimitados e o app avisa no dia e com a antecedência que você quiser.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e dê o nome “Black Friday”.</li><li>Data: 27 de novembro de 2026. Como a data muda todo ano, não marque repetir — em 2027 crie um evento novo para 26 de novembro.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<h2>A Black Friday nos próximos anos</h2>
<table><thead><tr><th>Ano</th><th>Data</th></tr></thead><tbody>
<tr><td>2026</td><td>{fmt(BF26, "pt-BR")}</td></tr>
<tr><td>2027</td><td>{fmt(BF27, "pt-BR")}</td></tr>
<tr><td>2028</td><td>{fmt(BF28, "pt-BR")}</td></tr>
</tbody></table>
<h2>Ideias</h2>
<ul><li>Uma contagem para a Black Friday com a lista do que você quer comprar escrita no verso do evento.</li><li>Um lembrete uma semana antes, para acompanhar os preços antes da data e saber se o desconto é real.</li><li>Logo em seguida, a contagem para o <a href="/tools/pt-br/quantos-dias-faltam-para-o-natal-2026/">Natal 2026</a> — são {(XMAS - BF26).days} dias entre uma data e outra.</li></ul>"""})

PAGES.append({"path": "/tools/pt-br/quantos-dias-faltam-para-o-natal-2026/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-28",
  "title": "Quantos dias faltam para o Natal 2026? (sexta-feira, 25/12)", "crumb": "Natal 2026",
  "description": "O Natal 2026 é na sexta-feira, 25 de dezembro, e a véspera na quinta, 24. Contagem regressiva ao vivo e widget grátis para a tela de bloqueio do iPhone.",
  "hub_title": "Quantos dias faltam para o Natal 2026?", "hub_desc": "Contagem ao vivo para 25 de dezembro, com a véspera e o prazo da 2ª parcela do 13º (18/12 em 2026).",
  "more": [
    ('Faltam quantos dias para o Natal?', f'O Natal 2026 é sexta-feira, 25 de dezembro. Contagem de hoje: {live(XMAS)}.'),
    ('Quando é a véspera de Natal 2026?', 'Quinta-feira, 24 de dezembro de 2026.'),
    ('Quantos dias faltam para a véspera de Natal?', 'Um a menos que o contador desta página, que conta até 25 de dezembro.'),
  ],
  "js": [COUNT_JS], "faq": [
    ("Em que dia da semana cai o Natal 2026?", "Numa sexta-feira: 25 de dezembro de 2026. A véspera, 24 de dezembro, é uma quinta-feira, e o Natal emenda com o fim de semana."),
    ("Quantas semanas faltam para o Natal?", f"Em {TODAY.strftime('%d/%m/%Y')}, " + (f"faltavam {days_to(XMAS)} dias, ou {pt_weeks(days_to(XMAS))}." if days_to(XMAS) >= 2 else f"{pt_left(days_to(XMAS), 'o Natal', 'Natal', 'o Natal de 2026')}.") + f" O contador desta página recalcula no dia em que você abre."),
    ("Até quando sai a 2ª parcela do 13º salário?", "Pela Lei 4.749/1965, o prazo legal da segunda parcela do 13º é 20 de dezembro. Em 2026 esse dia cai num domingo, então o pagamento vai para o dia útil anterior: sexta-feira, 18 de dezembro, uma semana antes do Natal. A primeira parcela vai até 30 de novembro."),
    ("Quando é o Natal 2027?", "Num sábado, 25 de dezembro de 2027. Em 2028, o Natal cai numa segunda-feira."),
    ("Como coloco a contagem do Natal na Tela Bloqueada?", "Crie o evento 25 de dezembro de 2026 no Countdown: Contagem regressiva, marque repetir todo ano e, na Tela Bloqueada, toque e segure → Personalizar → Tela Bloqueada → Adicionar widgets → Countdown. Os widgets são grátis em todos os tamanhos."),
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
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> você cria o evento uma vez e ele fica na Tela de Início ou na Tela Bloqueada como widget — grátis em todos os tamanhos, eventos ilimitados, com lembrete no dia. Marque <strong>repetir todo ano</strong> e o Natal volta sozinho em 2027.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e dê o nome “Natal”.</li><li>Data: 25 de dezembro de 2026, repetir todo ano.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<h2>O Natal nos próximos anos</h2>
<table><thead><tr><th>Ano</th><th>Dia da semana</th></tr></thead><tbody>
<tr><td>2026</td><td>{fmt(XMAS, "pt-BR")}</td></tr>
<tr><td>2027</td><td>{fmt(dt.date(2027, 12, 25), "pt-BR")}</td></tr>
<tr><td>2028</td><td>{fmt(dt.date(2028, 12, 25), "pt-BR")}</td></tr>
</tbody></table>
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
<form class="calc" id="calc"><label>Evento<input type="text" name="name" placeholder="Aniversário, casamento, viagem…" maxlength="60"></label><label>Data<input type="date" name="date" required></label><button type="submit" data-track-id="calc-submit">Contar os dias</button></form>
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
<p>O resultado é a quantidade de dias corridos entre hoje e a data escolhida, no fuso horário do seu aparelho — do jeito que a gente fala “faltam 12 dias”. Se a data é hoje, a resposta é 0. Uma data no passado mostra quantos dias se passaram, o que serve para aniversário de namoro, dias sem fumar ou o tempo no emprego novo.</p>
<h2>Contadores prontos</h2>
<ul><li><a href="/tools/pt-br/quantos-dias-faltam-para-o-meu-aniversario/">Quantos dias faltam para o meu aniversário</a> — com os anos que você vai fazer</li><li><a href="/tools/pt-br/quantos-dias-faltam-para-as-ferias/">Quantos dias faltam para as férias</a> — com os dias úteis</li><li><a href="/tools/pt-br/contador-de-dias-de-namoro/">Contador de dias de namoro</a> — há quantos dias vocês estão juntos</li></ul>
<p>Para ver a contagem sem abrir nada, coloque-a na Tela de Início do iPhone com o app abaixo.</p>"""})
_first_pt = next(i for i, p in enumerate(PAGES) if p["lang"] == "pt-BR")
PAGES.insert(_first_pt, PAGES.pop())   # 计算器排在葡语工具目录第一个

# 6d. 葡语场景页（09-29，Google 巴西联想词）：
#   aniversário — quantos dias faltam para o meu aniversário / … do meu filho, da minha filha, do meu amor / frases / instagram / dias e horas
#   férias      — quantos dias faltam para as férias (de julho, de dezembro, escolares, acabarem)；学校假期各州不同，10-10 起首屏列出核对过官方文件的网络（FERIAS_2026）
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

# 巴西学校假期：2026 学年结束日。只收直接读过官方文件的教育网络（10-10 核对）；没核到官方原文的州（RJ、BA 等）不列。
# 依据：GSC 10-02~10-06 这页 747 次曝光 0 点击，查询词大半是「férias escolares」，要的是现成答案。
# ⚠ 12-18 之后这些日期都过了：届时换成 2027 学年（开学日 / 7 月假期），并改 FERIAS_CHECKED。
FERIAS_CHECKED = dt.date(2026, 10, 10)
FERIAS_2026 = [
    ("São Paulo — rede estadual", dt.date(2026, 12, 18), "Seduc-SP",
     "https://www.agenciasp.sp.gov.br/calendario-2026-sp-define-para-2-de-fevereiro-inicio-do-proximo-ano-letivo-nas-escolas-estaduais/"),
    ("São Paulo (capital) — rede municipal", dt.date(2026, 12, 22), "Prefeitura de São Paulo",
     "https://prefeitura.sp.gov.br/w/ano-letivo-na-rede-municipal-da-capital-come%C3%A7a-em-4-de-fevereiro-veja-o-calend%C3%A1rio-de-2026"),
    ("Minas Gerais — rede estadual", dt.date(2026, 12, 18), "SEE-MG",
     "https://www.agenciaminas.mg.gov.br/noticia/secretaria-de-educacao-e-undime-anunciam-calendario-escolar-2026-128101"),
    ("Paraná — rede estadual", dt.date(2026, 12, 18), "Seed-PR, Resolução n.º 6.494/2025",
     "https://www.educacao.pr.gov.br/Pagina/Calendario-Escolar"),
    ("Rio Grande do Sul — rede estadual", dt.date(2026, 12, 18), "Seduc-RS, Portaria n.º 704/2025",
     "https://educacao.rs.gov.br/calendario-escolar-de-2026"),
    ("Pernambuco — rede estadual", dt.date(2026, 12, 23), "SEE-PE, Instrução Normativa n.º 19/2025",
     "https://portal.educacao.pe.gov.br/calendario-escolar-2026/"),
]
FERIAS_MAIN = dt.date(2026, 12, 18)   # 四个州立网络共同的结课日，首屏大数字数到这一天
if TODAY > FERIAS_MAIN:
    raise SystemExit("FERIAS_2026 已过期：把假期页换成 2027 学年的日期（开学日 / 7 月假期），并更新 FERIAS_CHECKED。")
PT_WD = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
def ferias_rows():
    out = []
    for rede, d, fonte, url in FERIAS_2026:
        n = days_to(d)
        left = (f'<span data-n>{abs(n) if n else ""}</span> <span data-unit>'
                f'{"É hoje!" if n == 0 else ("dias atrás" if n < 0 else ("dia" if n == 1 else "dias"))}</span>')
        out.append(f'<tr><td>{esc(rede)}<br><small>Fonte: <a href="{url}" rel="noopener">{esc(fonte)}</a></small></td>'
                   f'<td>{d.day} de {PT_MONTHS[d.month - 1]} ({PT_WD[d.weekday()]})</td><td data-date="{d.isoformat()}" style="white-space:nowrap">{left}</td></tr>')
    return "".join(out)

SCENES = [
 {"path": "/tools/pt-br/quantos-dias-faltam-para-o-meu-aniversario/", "lang": "pt-BR", "kind": "WebApplication", "app": "countdown", "published": "2026-09-29",
  "title": "Quantos dias faltam para o meu aniversário? Contagem regressiva", "crumb": "Meu aniversário",
  "description": "Escolha o dia e o mês do seu aniversário e veja quantos dias, meses e horas faltam, em que dia da semana ele cai e quantos anos você vai fazer.",
  "hub_title": "Quantos dias faltam para o meu aniversário?", "hub_desc": "Dias, meses e horas até o próximo aniversário — e quantos anos você vai fazer.",
  "more": [
    ("Como colocar a contagem do aniversário na tela de bloqueio do iPhone?", "Crie o evento com o modelo de aniversário no Countdown: Contagem regressiva e, na Tela Bloqueada, toque e segure → Personalizar → Tela Bloqueada → Adicionar widgets → Countdown. O widget é grátis e a contagem se repete sozinha todo ano."),
    ("Como fazer contagem regressiva de aniversário no Instagram?", "No story, use a figurinha de contagem regressiva do próprio Instagram e escolha a data. As frases desta página servem de legenda; para ver os dias no celular todo dia, use o widget."),
  ],
  "js": [SCENE_JS], "faq": [
    ("Como a conta é feita?", "São dias corridos entre hoje e o próximo aniversário, no fuso horário do seu aparelho. Se o aniversário deste ano já passou, a conta vai para o do ano que vem; se é hoje, a página diz que é hoje."),
    ("E quem nasceu em 29 de fevereiro?", "Nos anos que não são bissextos, a página conta até 28 de fevereiro. O próximo 29 de fevereiro é em 2028."),
    ("Dá para contar os dias para o aniversário do meu filho?", "Sim: escolha o dia e o mês em que ele nasceu. No Countdown dá para ter um evento para cada pessoa da família, porque os eventos são ilimitados, e cada um pode aparecer num widget."),
    ("Quantos dias e horas faltam?", "Depois de contar, a página mostra também as horas que faltam até a meia-noite em que o aniversário começa, no seu fuso horário."),
    ("Existe um app com a contagem do aniversário no celular?", "O Countdown: Contagem regressiva é o nosso app grátis para iPhone: widgets em todos os tamanhos na Tela de Início e na Tela Bloqueada, eventos ilimitados, repetição todo ano e lembretes no dia e com a antecedência que você quiser."),
  ],
  "body": f"""<h1>Quantos dias faltam para o meu aniversário?</h1>
<p class="lede">Escolha o dia e o mês em que você nasceu e veja quantos dias faltam para o próximo aniversário e em que dia da semana ele cai. Informe o ano, se quiser, para ver quantos anos vai fazer. Serve também para o aniversário do filho, da filha ou do amor.</p>
<form class="calc c4" id="bday"><label>Dia<select name="dia" required>{"".join(f'<option value="{d}">{d}</option>' for d in range(1, 32))}</select></label><label>Mês<select name="mes" required>{"".join(f'<option value="{i}">{m}</option>' for i, m in enumerate(PT_MONTHS, 1))}</select></label><label>Ano (opcional)<input type="number" name="ano" min="1900" max="{TODAY.year}" placeholder="1995" inputmode="numeric"></label><button type="submit" data-track-id="bday-submit">Contar</button></form>
<div id="bday-out" class="tool-out" hidden aria-live="polite"></div>
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> o aniversário fica na Tela de Início ou na Tela Bloqueada como widget, grátis em todos os tamanhos. O app tem modelos prontos, entre eles o de aniversário, que já vêm com a repetição e os lembretes certos. Os eventos são ilimitados: cabem o seu, o dos filhos e o de quem mais você quiser.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e escolha o modelo de aniversário.</li><li>Informe a data de nascimento.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<p>Quando a contagem chega a um marco — cem dias, uma semana, a manhã do dia —, o app abre o número em tela cheia e prepara um cartão para compartilhar.</p>
<h2>Frases para a contagem regressiva</h2>
<p>Para o story ou a legenda do Instagram:</p>
<ul><li>“Contagem regressiva oficialmente aberta: falta uma semana para o meu dia.”</li><li>“Faltam 10 dias para mais um ano de história.”</li><li>“3, 2, 1… faltam só 3 dias!”</li><li>“Falta 1 dia. Amanhã é festa.”</li><li>“Faltam 30 dias para o aniversário do meu pequeno, e ele já pergunta todo dia quanto falta.”</li><li>“Um mês para o aniversário do meu amor — a surpresa já está sendo preparada.”</li></ul>
<p>Para qualquer outra data, use o <a href="/tools/pt-br/quantos-dias-faltam/">contador de dias</a>.</p>"""},
 {"path": "/tools/pt-br/quantos-dias-faltam-para-as-ferias/", "lang": "pt-BR", "kind": "WebApplication", "app": "countdown", "published": "2026-09-29",
  "updated": FERIAS_CHECKED.isoformat(),
  "title": "Quantos dias faltam para as férias escolares 2026? SP, MG, PR, RS e PE", "crumb": "Férias",
  "description": "As aulas de 2026 vão até 18/12 na rede estadual de SP, MG, PR e RS e até 23/12 em PE. Veja quantos dias faltam ou conte os dias até as suas férias do trabalho.",
  "hub_title": "Quantos dias faltam para as férias?", "hub_desc": "Fim das aulas de 2026 em SP, MG, PR, RS e PE, com os dias que faltam hoje — e um contador com dias úteis para as suas férias.",
  "more": [
    ("Quantos dias faltam para as férias de dezembro?", "Nas redes da tabela acima, as aulas de 2026 terminam entre 18 e 23 de dezembro, e a tabela mostra quantos dias faltam em cada uma. Para as férias do trabalho, use o contador com a data combinada com a empresa."),
    ("Quantos dias faltam para as férias de julho?", "O recesso de julho de 2026 já passou: foi de 7 a 23 de julho na rede estadual de São Paulo, de 20 a 31 de julho em Minas Gerais, de 13 a 22 de julho no Paraná, de 10 a 26 de julho em Pernambuco e de 27 de julho a 2 de agosto no Rio Grande do Sul. Para julho de 2027, digite no contador a data do calendário de 2027 da sua rede."),
    ("Quantas semanas faltam para as férias?", "A contagem no alto da página mostra também as semanas e os dias que faltam para 18 de dezembro. No contador, o resultado vem em dias, em dias úteis e em semanas."),
    ("Como colocar a contagem regressiva das férias na tela de bloqueio?", "No iPhone, crie o evento “Férias” no Countdown: Contagem regressiva com a data do último dia de aula ou do primeiro dia de férias e, na Tela Bloqueada, toque e segure → Personalizar → Tela Bloqueada → Adicionar widgets → Countdown. O widget é grátis e o número diminui sozinho todo dia."),
    ("Quantos dias faltam para as férias do fim do ano no trabalho?", "Depende da data combinada com a empresa. Digite o primeiro dia das férias no contador para ver os dias corridos e os dias úteis que faltam."),
  ],
  "js": [SCENE_JS, COUNT_JS], "faq": [
    ("Como os dias úteis são contados?", "São os dias de segunda a sexta entre amanhã e a véspera do primeiro dia de férias. Os feriados não são descontados, porque mudam de cidade para cidade: se houver feriado de segunda a sexta no período, tire um dia por feriado."),
    ("Quando começam as férias escolares de fim de ano em 2026?", "Depende do estado, da cidade e da rede de ensino. Pelos calendários oficiais, as aulas de 2026 terminam em 18 de dezembro nas redes estaduais de São Paulo, Minas Gerais, Paraná e Rio Grande do Sul, em 22 de dezembro na rede municipal da cidade de São Paulo e em 23 de dezembro na rede estadual de Pernambuco. Para outras redes, confira o calendário da secretaria de educação ou da escola."),
    ("Em quantas partes posso dividir as férias pela CLT?", "Em até três, se você concordar: um período de pelo menos 14 dias corridos e os outros de pelo menos 5 dias corridos cada (art. 134, § 1º, da CLT)."),
    ("Quanto falta para as minhas férias acabarem?", "Informe o primeiro e o último dia. Se hoje estiver dentro desse intervalo, a página mostra quantos dias faltam para acabarem."),
    ("Dá para ver a contagem das férias no celular?", "Sim. No Countdown: Contagem regressiva, grátis para iPhone, a contagem fica num widget da Tela de Início ou da Tela Bloqueada, com lembretes no dia e com antecedência. Os eventos são ilimitados e sincronizam pelo iCloud, sem criar conta."),
  ],
  "body": f"""<h1>Quantos dias faltam para as férias?</h1>
<p class="lede">Em 2026, as aulas das redes estaduais de São Paulo, Minas Gerais, Paraná e Rio Grande do Sul vão até sexta-feira, 18 de dezembro. Veja quantos dias faltam em cada rede — ou informe a data das suas férias, da escola ou do trabalho, e conte até lá.</p>
{counter(FERIAS_MAIN, "pt-BR", "Fim das aulas na rede estadual de SP, MG, PR e RS")}
<h2>Férias escolares: quando acabam as aulas em 2026</h2>
<table><thead><tr><th>Rede de ensino</th><th>Último dia de aula</th><th>Faltam</th></tr></thead><tbody>{ferias_rows()}</tbody></table>
<p>Para os alunos, as férias começam depois do último dia de aula. Quem fica de recuperação pode ter atividades depois dessa data: em Pernambuco, por exemplo, a recuperação final está marcada para 24, 28 e 29 de dezembro.</p>
<p class="meta">Datas dos calendários oficiais de 2026 de cada rede, conferidas em {FERIAS_CHECKED.day} de {PT_MONTHS[FERIAS_CHECKED.month - 1]} de {FERIAS_CHECKED.year}. A escola pode ajustar o calendário (reposição de aulas, feriados municipais), e as redes municipais e particulares têm datas próprias: confirme com a sua escola.</p>
<p>O calendário completo de cada rede, com o recesso de julho e a volta às aulas, está <a href="#calendarios">mais abaixo nesta página</a>.</p>
<p>O seu estado não está na tabela? O calendário é publicado pela secretaria de educação do estado ou pela escola: digite o primeiro dia das férias no contador abaixo.</p>
<h2>Conte os dias até as suas férias</h2>
<p>Informe o primeiro dia das férias para contar os dias que faltam. Adicione o último dia para ver a duração ou quanto falta para acabarem.</p>
<form class="calc" id="ferias"><label>Primeiro dia<input type="date" name="inicio" required></label><label>Último dia (opcional)<input type="date" name="fim"></label><button type="submit" data-track-id="ferias-submit">Contar</button></form>
<p class="calc-note">Dias úteis: de segunda a sexta, sem descontar feriados.</p>
<div id="ferias-out" class="tool-out" hidden aria-live="polite"></div>
<!--ESCOLAS-->
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> a contagem das férias fica na Tela de Início ou na Tela Bloqueada como widget, grátis em todos os tamanhos, com lembretes no dia e com a antecedência que você quiser.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e dê o nome “Férias”.</li><li>Data: o primeiro dia das férias. Adicione um lembrete uma semana antes, para arrumar as malas com calma.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<h2>Férias do trabalho (CLT)</h2>
<ul><li>São 30 dias corridos a cada 12 meses de trabalho para quem teve até 5 faltas injustificadas no período (art. 130).</li><li>Com a sua concordância, podem ser divididas em até três períodos: um de pelo menos 14 dias e os outros de pelo menos 5 dias cada (art. 134, § 1º).</li><li>A empresa comunica as férias por escrito com pelo menos 30 dias de antecedência (art. 135), e o pagamento sai até 2 dias antes do início (art. 145).</li></ul>
<p>Para saber até quando o salário do mês precisa ser pago, veja <a href="/tools/pt-br/quinto-dia-util/">quando é o quinto dia útil</a> de cada mês.</p>
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
<form class="calc c2" id="namoro"><label>Começamos a namorar em<input type="date" name="desde" max="{TODAY.isoformat()}" required></label><button type="submit" data-track-id="namoro-submit">Contar os dias</button></form>
<div id="namoro-out" class="tool-out" hidden aria-live="polite"></div>
<h2>Quantos dias têm os meses de namoro</h2>
<p>Os meses não têm o mesmo tamanho, então “7 meses de namoro” dá um número de dias diferente conforme o mês em que vocês começaram. A tabela mostra o mínimo e o máximo:</p>
<table><thead><tr><th>Tempo de namoro</th><th>Dias</th></tr></thead><tbody>{"".join(f"<tr><td>{n} {'mês' if n == 1 else 'meses'}</td><td>{lo} a {hi} dias</td></tr>" for n, (lo, hi) in ((n, month_span(n)) for n in range(1, 12)))}<tr><td>1 ano</td><td>365 ou 366 dias</td></tr></tbody></table>
<h2>Marcos para comemorar</h2>
<ul><li><strong>Mesversário</strong>: todo mês, no mesmo dia em que começaram; quando o mês não tem esse dia, no último dia do mês.</li><li><strong>100 dias</strong>: dá 3 meses e mais {M3_LO} a {M3_HI} dias, conforme o mês de início. Depois vêm os 200, os 500 e os 1.000 dias.</li><li><strong>Aniversário de namoro</strong>: 365 dias, ou 366 quando o ano passa por um 29 de fevereiro.</li></ul>
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>No <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> um evento pode contar a partir de uma data: crie o dia em que vocês começaram e ele mostra há quantos dias estão juntos num widget grátis da Tela Bloqueada ou da Tela de Início. No verso do evento dá para escrever algumas linhas, guardar fotos e gravar uma voz — a história do dia fica junto com o dia.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos), dê um nome e escolha a data em que começaram.</li><li>Escolha contar a partir dessa data.</li><li>Para o mesversário, crie outro evento que se repete todo mês.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<p>Quer dar a contagem de presente em QR code? Copie o link gerado acima e transforme em QR code com qualquer gerador — o nosso é o <a href="/qrcodestudio/" hreflang="en">QR Studio</a>, para iPhone (página em inglês).</p>"""},
 # 10-12：锁屏教程页（pt-BR，Countdown）。依据 10-12 GSC：「quantos dias faltam…」这类词被 Google AI 概览直接答掉，排第 8 也 0 点击；
 # 全站唯一有点击的查询是日语「共通テストカウントダウン 待ち受け」（想把倒数放到手机上）。Google 巴西联想词：
 # 「como colocar contagem regressiva na tela de bloqueio do iphone / … do celular / … android / … samsung」「widget contagem regressiva iphone gratuito」
 # 「contagem regressiva iphone foto」「contador de dias widget iphone」「como colocar contagem regressiva no calendário do celular」。
 # app 说法只用 pt-BR 商店 1.4.16 描述：widgets 全尺寸免费（Tela de Início / Tela Bloqueada）、eventos ilimitados、repetição、importar de calendário；
 # fotos próprias como fundo、Atividade ao Vivo na Tela Bloqueada 属于 Pro；「Suas contagens, lembretes e widgets funcionam igual, assinando ou não」。
 {"path": "/tools/pt-br/contagem-regressiva-tela-de-bloqueio-iphone/", "iphone_only": True, "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-10-12",
  "title": "Contagem regressiva na tela de bloqueio do iPhone: widget gratuito", "crumb": "Na tela de bloqueio",
  "description": "Como colocar a contagem regressiva na tela de bloqueio e na Tela de Início do iPhone com um widget gratuito, passo a passo. O número de dias diminui sozinho.",
  "hub_title": "Como colocar contagem regressiva na tela de bloqueio do iPhone", "hub_desc": "Widget grátis na Tela Bloqueada e na Tela de Início: o número de dias muda sozinho, sem refazer papel de parede.",
  "more": [
    ("Como colocar contagem regressiva na tela do celular?", "No iPhone, com um widget: crie o evento no app e adicione o widget na Tela Bloqueada ou na Tela de Início, como nos passos acima. No Android, o caminho depende do aparelho e do app que você usar."),
    ("Como fazer uma contagem regressiva de dias no celular?", 'Dê um nome ao evento e escolha a data: o widget mostra quantos dias faltam e o número diminui sozinho a cada dia. Se você só quer saber o número de hoje, use o <a href="/tools/pt-br/quantos-dias-faltam/">contador de dias</a>.'),
    ("Dá para usar os eventos do calendário do iPhone?", "Dá: o Countdown importa eventos do calendário e mostra quantos dias faltam no widget."),
  ],
  "js": [COUNT_JS], "faq": [
    ("O widget de contagem regressiva é grátis?", "Sim. No Countdown: Contagem regressiva, todos os widgets são grátis em todos os tamanhos, na Tela de Início e na Tela Bloqueada, e não há limite de eventos."),
    ("Posso colocar o número no papel de parede?", "Pode, mas o papel de parede é uma imagem: o número fica parado no dia em que você fez a imagem. Para um número que muda sozinho, use o widget da Tela Bloqueada, que fica abaixo do relógio."),
    ("Dá para usar uma foto minha na contagem?", "No Countdown, usar uma foto sua como fundo faz parte do Countdown Pro. As contagens, os lembretes e os widgets funcionam igual, assinando ou não."),
    ("Funciona no Android, Samsung ou Xiaomi?", "Não: o Countdown é um app para iPhone e iPad. No Android, procure na Google Play um app de contagem regressiva com widget para a tela inicial."),
    ("O widget é a mesma coisa que a Atividade ao Vivo?", "Não. O widget da Tela Bloqueada fica abaixo do relógio e é grátis. A Atividade ao Vivo na Tela Bloqueada é um recurso do Countdown Pro."),
    ("A contagem se repete todo ano?", "Se você quiser: o evento pode repetir todo ano, todo mês, toda semana ou a cada poucos dias. Aniversários e o Natal voltam sozinhos; datas que mudam todo ano, como o Carnaval e a Black Friday, pedem um evento novo."),
  ],
  "body": f"""<h1>Como colocar contagem regressiva na tela de bloqueio do iPhone</h1>
<p class="lede">Para ver quantos dias faltam para as férias, o Natal ou um aniversário sem abrir nada, deixe a contagem na tela de bloqueio (a Tela Bloqueada) ou na Tela de Início do iPhone. Um papel de parede com o número precisa ser refeito todo dia; um widget recebe a data uma vez e o número diminui sozinho.</p>
{top_cta("countdown", "pt-BR", "Colocar na tela de bloqueio — grátis")}
<h2>Papel de parede ou widget?</h2>
<table><thead><tr><th></th><th>Papel de parede com o número</th><th>Widget</th></tr></thead><tbody>
<tr><th>Número</th><td>fica como no dia em que você fez a imagem</td><td>muda sozinho todo dia</td></tr>
<tr><th>Trabalho</th><td>refazer a imagem todo dia</td><td>informar a data uma vez</td></tr>
<tr><th style="white-space:nowrap">Onde fica</th><td>no fundo da Tela Bloqueada e da Tela de Início</td><td>abaixo do relógio, na Tela Bloqueada, e na Tela de Início</td></tr>
</tbody></table>
<h2>Na tela de bloqueio, passo a passo</h2>
<ol><li>Instale o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a>, toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e informe o nome (por exemplo, “Férias”) e a data.</li><li>Na Tela Bloqueada, toque e segure até aparecer <strong>Personalizar</strong>, e toque nele.</li><li>Escolha a Tela Bloqueada e toque em <strong>Adicionar widgets</strong>.</li><li>Escolha Countdown e toque no widget que você quer. A contagem passa a aparecer abaixo do relógio.</li></ol>
<p>Todos os widgets são grátis, em todos os tamanhos, e os eventos são ilimitados: dá para ter as férias, o aniversário e o Natal ao mesmo tempo.</p>
<h2>Na Tela de Início</h2>
<ol><li>Toque e segure um espaço vazio da Tela de Início.</li><li>Toque em <strong>Editar</strong> → <strong>Adicionar widget</strong> (no iOS 17, toque em <strong>+</strong> no canto superior esquerdo).</li><li>Escolha Countdown e o tamanho, e toque em <strong>Adicionar widget</strong>.</li></ol>
<h2>As datas que mais se contam</h2>
<div class="pop">
<a href="/tools/pt-br/quantos-dias-faltam-para-as-ferias/" data-date="{FERIAS_MAIN.isoformat()}"><b data-n>{days_to(FERIAS_MAIN)}</b><span><span data-unit>dias</span> para o fim das aulas (rede estadual de SP, MG, PR e RS)</span></a>
<a href="/tools/pt-br/contagem-regressiva-black-friday-2026/" data-date="{BF26.isoformat()}"><b data-n>{days_to(BF26)}</b><span><span data-unit>dias</span> para a Black Friday 2026</span></a>
<a href="/tools/pt-br/quantos-dias-faltam-para-o-natal-2026/" data-date="{XMAS.isoformat()}"><b data-n>{days_to(XMAS)}</b><span><span data-unit>dias</span> para o Natal 2026</span></a>
</div>
<p class="meta">Os números acima foram calculados em {TODAY.strftime("%d/%m/%Y")} e se atualizam quando a página abre.</p>
<h2>Quando a contagem chega a um marco</h2>
<p>Cem dias, uma semana, a manhã do dia: quando a contagem chega a um marco, o app abre o número em tela cheia e prepara um cartão para compartilhar. Para saber o número de qualquer outra data, use o <a href="/tools/pt-br/quantos-dias-faltam/">contador de dias</a>.</p>"""},
]
_ci = next(i for i, p in enumerate(PAGES) if p["path"] == "/tools/pt-br/quantos-dias-faltam/")
PAGES[_ci + 1:_ci + 1] = SCENES   # 场景页紧跟在计算器后面（常青页排在节日页前面）

# ------------------------------------------------------------------ 8. 10-10 第三轮：巴西分州校历页 + 「quinto dia útil」
# 依据：10-10 Google 巴西联想词「quando começam as férias escolares em são paulo / no paraná / em minas gerais」「volta as aulas 2027 rs」
# 「quinto dia útil de <mês> 2026」「quantos dias úteis tem <mês> de 2026」。写页规矩同假期页：标题和首屏先给答案。
# 每个州只写亲自读过官方文件的日期（10-10）：
#   SP  Seduc-SP 服务门户 SED-08404（Resolução Seduc 125/2025）+ Agência SP；市立见 prefeitura.sp.gov.br
#   MG  Agência Minas 128101（2025-11-05）   PR  Seed-PR Resolução 6.494/2025 附件日历（逐格读过颜色图例）
#   RS  educacao.rs.gov.br（Portaria 704/2025）；2027 预告见 estado.rs.gov.br 2026-10-02 稿   PE  DOE 2025-12-12 的 IN SEE/PE 19/2025
# ⚠ 和 FERIAS_2026 一起在 12-18 过期（上面的 SystemExit 会拦住构建）。
PT_DMW = lambda d: f"{PT_DM(d)} ({PT_WD[d.weekday()]})"
ESC_2027_PADRAO = "O calendário de 2026 foi {verbo} em {pub}; o de 2027 ainda não foi conferido para esta página. Como referência, em 2026 as aulas começaram em {inicio}."
ESCOLAS = [
 {"slug": "ferias-escolares-sao-paulo-2026", "pub": "setembro de 2025", "hub_desc": "Aulas até 18 de dezembro na rede estadual e até 22 na rede municipal da capital, com a contagem dos dias.", "nome": "São Paulo", "em": "em São Paulo", "da": "de São Paulo",
  "title": "Quando começam as férias escolares em São Paulo? Aulas até 18/12/2026",
  "inicio": dt.date(2026, 2, 2), "fim": dt.date(2026, 12, 18),
  "rows": [("Início das aulas", "2 de fevereiro"), ("1º bimestre", "2 de fevereiro a 22 de abril"), ("2º bimestre", "23 de abril a 6 de julho"),
           ("Férias de julho dos alunos", "7 a 23 de julho"), ("3º bimestre", "24 de julho a 2 de outubro"), ("4º bimestre", "5 de outubro a 18 de dezembro"),
           ("Último dia de aula", "18 de dezembro (sexta-feira)"), ("Recesso escolar de fim de ano", "19 a 31 de dezembro")],
  "julho": "As férias de julho dos alunos foram de 7 a 23 de julho, com volta às aulas em 24 de julho.",
  "fontes": [("Seduc-SP, calendário escolar 2026 (Resolução Seduc n.º 125/2025)", "https://atendimento.educacao.sp.gov.br/knowledgebase/article/SED-08404/pt-br"),
             ("Agência SP", "https://www.agenciasp.sp.gov.br/calendario-2026-sp-define-para-2-de-fevereiro-inicio-do-proximo-ano-letivo-nas-escolas-estaduais/")],
  "desc_extra": "as datas da rede municipal da capital",
  "extra": ('<h2>E na rede municipal da capital?</h2>'
            '<p>Na rede municipal da cidade de São Paulo o calendário é outro: o ano letivo de 2026 começou em 4 de fevereiro e vai até <strong>terça-feira, 22 de dezembro</strong> '
            '(contagem de hoje: <span data-date="2026-12-22"><span data-n>{n_cap}</span> <span data-unit>{u_cap}</span></span>), e o recesso do meio do ano foi de 6 a 17 de julho. '
            'Fonte: <a href="https://prefeitura.sp.gov.br/w/ano-letivo-na-rede-municipal-da-capital-come%C3%A7a-em-4-de-fevereiro-veja-o-calend%C3%A1rio-de-2026" rel="noopener">Prefeitura de São Paulo</a>.</p>')},
 {"slug": "ferias-escolares-minas-gerais-2026", "pub": "novembro de 2025", "pub_verbo": "anunciado", "hub_desc": "Aulas até 18 de dezembro na rede estadual; recesso da Semana do Professor de 13 a 16 de outubro.", "nome": "Minas Gerais", "em": "em Minas Gerais", "da": "de Minas Gerais",
  "title": "Quando começam as férias escolares em Minas Gerais? Aulas até 18/12",
  "inicio": dt.date(2026, 2, 4), "fim": dt.date(2026, 12, 18),
  "rows": [("Início do ano letivo", "4 de fevereiro"), ("Recesso de julho", "20 a 31 de julho"), ("Recesso da Semana do Professor", "13 a 16 de outubro"),
           ("Término do ano letivo", "18 de dezembro (sexta-feira)")],
  "julho": "O recesso de julho, para professores e estudantes, foi de 20 a 31 de julho.",
  "fontes": [("Agência Minas, calendário escolar 2026 (SEE-MG e Undime)", "https://www.agenciaminas.mg.gov.br/noticia/secretaria-de-educacao-e-undime-anunciam-calendario-escolar-2026-128101")],
  "desc_extra": "os recessos de julho e de outubro",
  "extra": ('<h2>Recesso de outubro</h2>'
            '<p>Além do recesso de julho, o calendário de Minas Gerais tem o recesso da Semana do Professor, de 13 a 16 de outubro de 2026. '
            'Como 12 de outubro, segunda-feira, é feriado nacional, a semana inteira fica sem aula.</p>'
            '<h2>Um calendário para a rede estadual e as municipais</h2>'
            '<p>O calendário de 2026 foi elaborado pela Secretaria de Estado de Educação em parceria com a Undime-MG e alinha as agendas da rede estadual e das redes municipais. '
            'Os sábados letivos passam a ser dedicados a ações de mobilização familiar e comunitária.</p>')},
 {"slug": "ferias-escolares-parana-2026", "pub": "novembro de 2025", "hub_desc": "Aulas até 18 de dezembro na rede estadual, com os trimestres e o recesso de julho.", "nome": "Paraná", "em": "no Paraná", "da": "do Paraná",
  "title": "Quando começam as férias escolares no Paraná? Aulas até 18/12/2026",
  "inicio": dt.date(2026, 2, 5), "fim": dt.date(2026, 12, 18),
  "rows": [("Início das aulas", "5 de fevereiro"), ("1º trimestre", "5 de fevereiro a 14 de maio"), ("2º trimestre", "18 de maio a 4 de setembro"),
           ("Recesso de julho", "13 a 22 de julho"), ("Volta às aulas no 2º semestre", "27 de julho"), ("3º trimestre", "8 de setembro a 18 de dezembro"), ("Recesso do Dia do Professor", "13 de outubro (terça-feira)"),
           ("Último dia de aula", "18 de dezembro (sexta-feira)"), ("Dias letivos no ano", "201")],
  "julho": "O recesso escolar de julho foi de 13 a 22 de julho; os dias 23 e 24 foram de estudo e planejamento dos profissionais, e as aulas voltaram em 27 de julho.",
  "fontes": [("Seed-PR, Calendário Escolar 2026 (anexo da Resolução n.º 6.494/2025)", "https://www.educacao.pr.gov.br/Pagina/Calendario-Escolar")],
  "desc_extra": "os trimestres e o recesso de julho",
  "extra": ('<h2>Depois do último dia de aula</h2>'
            '<p>No calendário oficial, o sábado, 19 de dezembro, está marcado como conselho de classe e fechamento do ano letivo; 21 e 22 de dezembro, como recesso escolar; '
            'e o período de férias começa em 23 de dezembro.</p>')},
 {"slug": "ferias-escolares-rio-grande-do-sul-2026", "nome": "Rio Grande do Sul", "em": "no Rio Grande do Sul", "da": "do Rio Grande do Sul",
  "title": "Férias escolares no Rio Grande do Sul: aulas até 18/12/2026",
  "inicio": dt.date(2026, 2, 18), "fim": dt.date(2026, 12, 18),
  "rows": [("Início do ano letivo", "18 de fevereiro"), ("1º trimestre", "18 de fevereiro a 22 de maio"), ("2º trimestre", "25 de maio a 4 de setembro"),
           ("Recesso escolar", "27 de julho a 2 de agosto"), ("3º trimestre", "8 de setembro a 18 de dezembro"),
           ("Encerramento do ano letivo", "18 de dezembro (sexta-feira)"), ("Dias letivos no ano", "202")],
  "julho": "O recesso escolar de estudantes e professores foi de 27 de julho a 2 de agosto, com volta às aulas em 3 de agosto.",
  "fontes": [("Seduc-RS, Calendário Escolar de 2026 (Portaria n.º 704/2025)", "https://educacao.rs.gov.br/calendario-escolar-de-2026")],
  "desc_extra": "a previsão de volta às aulas em 2027",
  "y2027": ('O governo do estado informou, em 2 de outubro de 2026, que o calendário letivo de 2027 da rede estadual está previsto para começar em 15 de fevereiro e terminar em 17 de dezembro.',
            ' Fonte: <a href="https://www.estado.rs.gov.br/aberto-periodo-de-inscricoes-para-ingresso-na-rede-estadual-de-educacao" rel="noopener">Governo do Rio Grande do Sul</a>.'),
  "hub_desc": "Aulas até 18 de dezembro na rede estadual; a volta às aulas de 2027 está prevista para 15 de fevereiro.",
  "extra": ('<h2>EJA e cursos técnicos</h2>'
            '<p>Os trimestres da tabela valem para o Ensino Fundamental e o Ensino Médio. Na EJA, nos cursos técnicos subsequentes e concomitantes e no Curso Normal – Aproveitamento de Estudos, '
            'o ano é dividido em semestres: de 18 de fevereiro a 24 de julho e de 3 de agosto a 18 de dezembro.</p>')},
 {"slug": "ferias-escolares-pernambuco-2026", "pub": "dezembro de 2025", "hub_desc": "Aulas até 23 de dezembro na rede estadual; recuperação final em 24, 28 e 29 de dezembro.", "nome": "Pernambuco", "em": "em Pernambuco", "da": "de Pernambuco",
  "title": "Quando começam as férias escolares em Pernambuco? Aulas até 23/12/2026",
  "inicio": dt.date(2026, 2, 3), "fim": dt.date(2026, 12, 23),
  "rows": [("Início do ano letivo", "3 de fevereiro"), ("1º trimestre", "3 de fevereiro a 19 de maio"), ("2º trimestre", "21 de maio a 11 de setembro"),
           ("Recesso escolar", "10 a 26 de julho"), ("3º trimestre", "14 de setembro a 23 de dezembro"), ("Término do ano letivo", "23 de dezembro (quarta-feira)"),
           ("Recuperação final", "24, 28 e 29 de dezembro"), ("Dias letivos no ano", "202")],
  "julho": "O recesso escolar foi de 10 a 26 de julho, e o 2º semestre começou em 27 de julho.",
  "fontes": [("SEE-PE, Instrução Normativa n.º 19/2025", "https://portal.educacao.pe.gov.br/calendario-escolar-2026/")],
  "desc_extra": "as datas da recuperação final",
  "extra": ('<h2>Recuperação final</h2>'
            '<p>Depois do término do ano letivo, o calendário de Pernambuco reserva 24, 28 e 29 de dezembro para novas oportunidades de aprendizagem e recuperação final. '
            'Quem não fica de recuperação entra de férias depois de 23 de dezembro.</p>')},
]
def escola_page(e):
    fim, rede, wd = e["fim"], f"rede estadual {e['da']}", PT_WD[e["fim"].weekday()]
    path = f"/tools/pt-br/{e['slug']}/"
    n_cap = days_to(dt.date(2026, 12, 22))
    extra = e["extra"].replace("{n_cap}", str(abs(n_cap)) if n_cap else "").replace("{u_cap}", "É hoje!" if n_cap == 0 else ("dias atrás" if n_cap < 0 else ("dia" if n_cap == 1 else "dias")))
    y27, y27_src = e.get("y2027", (ESC_2027_PADRAO.format(verbo=e.get("pub_verbo", "publicado"), pub=e.get("pub", ""), inicio=PT_DM(e["inicio"])), ""))
    rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in e["rows"])
    fontes = " e ".join(f'<a href="{u}" rel="noopener">{esc(t)}</a>' for t, u in e["fontes"])
    _o = [f'{o["da"].split()[0]} <a href="/tools/pt-br/{o["slug"]}/">{esc(o["nome"])}</a>' for o in ESCOLAS if o is not e]
    outros = ", ".join(_o[:-1]) + " e " + _o[-1]
    title = e["title"]; assert len(title) <= 70, (len(title), title)
    desc = f"As aulas de 2026 na {rede} vão até {wd}, {PT_DM(fim)}. Veja quantos dias faltam e {e['desc_extra']}."
    assert len(desc) <= 165, (len(desc), desc)
    body = f"""<h1>Quando começam as férias escolares {e['em']}?</h1>
<p class="lede">Na {rede}, as aulas de 2026 vão até <strong>{wd}, {PT_DM(fim)}</strong>. As férias de fim de ano dos alunos começam depois desse dia. A contagem abaixo é refeita todo dia.</p>
{counter(fim, "pt-BR", f"Último dia de aula na {rede}")}
<h2>Calendário escolar 2026 da {rede}</h2>
<table><tbody>{rows}</tbody></table>
<p class="meta">Fonte: {fontes}. Datas conferidas em {FERIAS_CHECKED.day} de {PT_MONTHS[FERIAS_CHECKED.month - 1]} de {FERIAS_CHECKED.year}. A escola pode ajustar o calendário (reposição de aulas, feriados municipais), e as redes municipais e particulares têm datas próprias: confirme com a sua escola.</p>
{extra}
<h2>Volta às aulas em 2027</h2>
<p>{esc(y27)}{y27_src}</p>
<h2>Outros estados</h2>
<p>Veja também o calendário {outros}. A página <a href="/tools/pt-br/quantos-dias-faltam-para-as-ferias/">quantos dias faltam para as férias</a> compara as redes lado a lado e tem um contador com dias úteis para as férias do trabalho.</p>
<h2>A contagem na tela de bloqueio do iPhone</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> a contagem das férias fica na Tela de Início ou na Tela Bloqueada como widget, grátis em todos os tamanhos, com lembretes no dia e com a antecedência que você quiser.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e dê o nome “Férias”.</li><li>Data: {PT_DM(fim)} de 2026, o último dia de aula. Adicione um lembrete uma semana antes.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}"""
    return {"path": path, "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-10-10",
            "title": title, "crumb": f"Férias escolares: {e['nome']}", "description": desc,
            "hub_title": f"Férias escolares {e['em']} (2026)", "hub_desc": e["hub_desc"],
            "js": [COUNT_JS], "body": body,
            "faq": [
              (f"Quando começam as férias escolares {e['em']} em 2026?", f"Na {rede}, o último dia de aula de 2026 é {wd}, {PT_DM(fim)}; as férias dos alunos começam depois desse dia. Redes municipais e escolas particulares têm calendário próprio."),
              (f"Quando foram as férias de julho de 2026 na {rede}?", e["julho"]),
              *([(f"Quando voltam as aulas em 2027 {e['em']}?", y27)] if "y2027" in e else []),
              ("Dá para ver a contagem das férias no celular?", "Sim. No Countdown: Contagem regressiva, grátis para iPhone, a contagem fica num widget da Tela de Início ou da Tela Bloqueada, com lembretes no dia e com antecedência. Os eventos são ilimitados e sincronizam pelo iCloud, sem criar conta."),
            ],
            "more": [
              (f"Quantos dias faltam para as férias escolares {e['em']}?", f"O contador no alto da página mostra quantos dias faltam hoje para {PT_DM(fim)} de 2026, o último dia de aula da {rede}."),
              (f"Quando acabam as aulas {e['em']} em 2026?", f"Na {wd}, {PT_DM(fim)} de 2026, na {rede}."),
              ("As escolas particulares seguem o mesmo calendário?", "Não necessariamente. Cada escola particular define o seu calendário, respeitando o mínimo de 200 dias letivos da Lei de Diretrizes e Bases da Educação; confirme as datas com a escola."),
            ]}
# 10-25：5 个分州页并回假期页，旧网址在 vercel.json 301 到这里。依据：claude-seo 的程序化页面门槛——这 5 页独有内容只有 28~32%
# （同一模板只换州名），10-18 起 Google 把它们全放进「已抓取未收录」。数据和来源原样保留，变成假期页里的一节 + 「更多问题」。
# escola_page() 留着不删：2027 学年要是再拆页，从这里接着改。
def escola_anchor(e): return e["slug"].replace("ferias-escolares-", "").replace("-2026", "")
def escolas_html():
    out, toc = [], []
    for e in ESCOLAS:
        fim, wd, a = e["fim"], PT_WD[e["fim"].weekday()], escola_anchor(e)
        rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in e["rows"])
        fontes = " e ".join(f'<a href="{u}" rel="noopener">{esc(t)}</a>' for t, u in e["fontes"])
        n_cap = days_to(dt.date(2026, 12, 22))
        extra = (e["extra"].replace("{n_cap}", str(abs(n_cap)) if n_cap else "")
                 .replace("{u_cap}", "É hoje!" if n_cap == 0 else ("dias atrás" if n_cap < 0 else ("dia" if n_cap == 1 else "dias")))
                 .replace("<h2>", "<p><strong>").replace("</h2>", "</strong></p>"))
        y27, y27_src = e.get("y2027", (ESC_2027_PADRAO.format(verbo=e.get("pub_verbo", "publicado"), pub=e.get("pub", ""), inicio=PT_DM(e["inicio"])), ""))
        toc.append(f'<a href="#{a}">{esc(e["nome"])}</a>')
        out.append(f'<h3 id="{a}">{esc(e["nome"])}: rede estadual</h3>\n'
                   f'<p>Último dia de aula de 2026: <strong>{wd}, {PT_DM(fim)}</strong>. {esc(e["julho"])}</p>\n'
                   f'<table><tbody>{rows}</tbody></table>\n<p class="meta">Fonte: {fontes}.</p>\n{extra}\n'
                   f'<p><strong>Volta às aulas em 2027:</strong> {esc(y27)}{y27_src}</p>')
    return (f'<h2 id="calendarios">Calendário escolar 2026 de cada rede estadual</h2>\n'
            f'<p>Ir para: {" · ".join(toc)}. Datas conferidas em {FERIAS_CHECKED.day} de {PT_MONTHS[FERIAS_CHECKED.month - 1]} de {FERIAS_CHECKED.year} '
            f'nos calendários oficiais; a escola pode ajustar as datas, e as redes municipais e particulares têm calendário próprio.</p>\n' + "\n".join(out))
_fi = next(i for i, p in enumerate(PAGES) if p["path"] == "/tools/pt-br/quantos-dias-faltam-para-as-ferias/")
PAGES[_fi]["body"] = PAGES[_fi]["body"].replace("<!--ESCOLAS-->", escolas_html())
PAGES[_fi]["more"] = PAGES[_fi]["more"] + [
    (f"Quando começam as férias escolares {e['em']} em 2026?",
     f"Na rede estadual {e['da']}, o último dia de aula de 2026 é {PT_WD[e['fim'].weekday()]}, {PT_DM(e['fim'])}; "
     f'as férias dos alunos começam depois desse dia. O calendário completo está <a href="#{escola_anchor(e)}">nesta página</a>.')
    for e in ESCOLAS]

# 8b. Quinto dia útil（工资最迟发放日）+ 每月工作日数
# 规则：CLT art. 459 § 1º（次月第 5 个工作日前发）；Instrução Normativa MTP n.º 2/2021 art. 14, I（数的时候周六算、周日和节假日不算，含市级节日）、
#       II（走银行的，钱要在第 5 个工作日前到账可用）——10-10 读过 gov.br 上的 PDF 原文。
# 全国性节日按法律固定日期（Lei 662/1949、6.802/1980、10.607/2002、14.759/2023）+ Paixão de Cristo；Carnaval 和 Corpus Christi 不是全国节日，不算。
def br_feriados(y):
    return {dt.date(y, 1, 1): "Confraternização Universal", easter(y) - dt.timedelta(days=2): "Paixão de Cristo", dt.date(y, 4, 21): "Tiradentes",
            dt.date(y, 5, 1): "Dia do Trabalho", dt.date(y, 9, 7): "Independência", dt.date(y, 10, 12): "Nossa Senhora Aparecida", dt.date(y, 11, 2): "Finados",
            dt.date(y, 11, 15): "Proclamação da República", dt.date(y, 11, 20): "Consciência Negra", dt.date(y, 12, 25): "Natal"}
def quinto_dia_util(y, m):
    fer, d, k = br_feriados(y), dt.date(y, m, 1), 0
    while True:
        if d.weekday() != 6 and d not in fer: k += 1
        if k == 5: return d
        d += dt.timedelta(days=1)
def dias_uteis_mes(y, m):
    fer, d, k = br_feriados(y), dt.date(y, m, 1), 0
    while d.month == m:
        if d.weekday() < 5 and d not in fer: k += 1
        d += dt.timedelta(days=1)
    return k
assert quinto_dia_util(2026, 10) == dt.date(2026, 10, 6) and quinto_dia_util(2026, 11) == dt.date(2026, 11, 7) and quinto_dia_util(2027, 1) == dt.date(2027, 1, 7)
QDU_MESES = [(y, m) for y in (2026, 2027) for m in range(1, 13) if (y, m) >= (TODAY.year, TODAY.month)]
QDU = [(y, m, quinto_dia_util(y, m), dias_uteis_mes(y, m)) for y, m in QDU_MESES]
QDU_NEXT = [q for q in QDU if q[2] >= TODAY][:3]
QDU_LBL = lambda q: f"Quinto dia útil de {PT_MONTHS[q[1] - 1]} de {q[0]} · {PT_WD[q[2].weekday()]}, {PT_DM(q[2])}"
# 首屏大数字要自己跳到「下一个」：把后面每个月的日期放进 data-list，访问当天挑第一个没过的，再交给 COUNT_JS 算天数
NEXT_JS = """
(function(){document.querySelectorAll('[data-list]').forEach(function(el){var L=JSON.parse(el.getAttribute('data-list')),n=new Date();n=new Date(n.getFullYear(),n.getMonth(),n.getDate());
for(var i=0;i<L.length;i++){var p=L[i][0].split('-');if(new Date(+p[0],+p[1]-1,+p[2])>=n||i===L.length-1){el.setAttribute('data-date',L[i][0]);var s=document.getElementById(el.id+'-sub');if(s)s.textContent=L[i][1];break;}}});})();
"""
def next_counter(el_id, items, lang):
    """items: [(date, 说明文字)]，按时间升序。静态先渲染第一个没过的；NEXT_JS 在访问当天改成当时的下一个。"""
    d, label = next((x for x in items if x[0] >= TODAY), items[-1]); n = days_to(d)
    unit = ts(lang, "today") if n == 0 else (ts(lang, "day") if n == 1 else ts(lang, "days"))
    lst = esc(json.dumps([[x[0].isoformat(), x[1]] for x in items], ensure_ascii=False))
    return (f'<div class="count" id="{el_id}" data-date="{d.isoformat()}" data-list="{lst}"><span data-n>{n if n else ""}</span><small data-unit>{esc(unit)}</small></div>'
            f'<p class="count-sub"><span id="{el_id}-sub">{esc(label)}</span></p>')
def _qdu_obs(y, m, q):
    fer = br_feriados(y); early = [f"{PT_DM(d)} é feriado ({n})" for d, n in sorted(fer.items()) if d.year == y and d.month == m and d <= q and d.weekday() != 6]
    return "; ".join(early)
_q1, _q2 = QDU_NEXT[0], QDU_NEXT[1]
PAGES.insert(_fi + 1 + len(ESCOLAS), {"path": "/tools/pt-br/quinto-dia-util/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-10-10",
  "title": "Quinto dia útil 2026 e 2027: a data do pagamento em cada mês", "crumb": "Quinto dia útil",
  "description": f"O quinto dia útil de {PT_MONTHS[_q1[1] - 1]} de {_q1[0]} é {PT_WD[_q1[2].weekday()]}, {_q1[2].day}; o de {PT_MONTHS[_q2[1] - 1]}, {PT_WD[_q2[2].weekday()]}, {_q2[2].day}. Veja todos os meses até dezembro de 2027 e como contar: o sábado entra.",
  "hub_title": "Quando é o quinto dia útil do mês?", "hub_desc": "A data-limite do pagamento do salário em cada mês de 2026 e 2027, com a contagem dos dias — e quantos dias úteis cada mês tem.",
  "js": [NEXT_JS, COUNT_JS],
  "faq": [
    ("O sábado conta como dia útil para o pagamento do salário?", "Conta. Pela Instrução Normativa MTP n.º 2/2021 (art. 14, I), na contagem dos dias entra o sábado e ficam de fora o domingo e o feriado, inclusive o municipal."),
    ("E se o quinto dia útil cair no sábado?", "O prazo termina nesse sábado. Quando o pagamento é feito pelo banco, o valor precisa estar à disposição do empregado até o quinto dia útil (art. 14, II, da mesma instrução normativa)."),
    ("Feriado municipal ou estadual muda o quinto dia útil?", "Muda. O feriado local não entra na contagem, então, se ele cair nos primeiros dias do mês, o quinto dia útil passa para o dia útil seguinte na sua cidade. A tabela desta página considera só os feriados nacionais."),
    ("De onde vem a regra do quinto dia útil?", "Do art. 459, § 1º, da CLT: quando o pagamento é mensal, ele deve ser feito, o mais tardar, até o quinto dia útil do mês seguinte ao trabalhado."),
    ("Como coloco o dia do pagamento na tela de bloqueio do iPhone?", "Crie no Countdown: Contagem regressiva um evento com a data do quinto dia útil deste mês e, na Tela Bloqueada, toque e segure → Personalizar → Tela Bloqueada → Adicionar widgets → Countdown. Como a data muda de mês para mês, atualize o evento no mês seguinte; se a sua empresa paga sempre no mesmo dia, use a repetição mensal. Os widgets são grátis em todos os tamanhos."),
  ],
  "more": [(f"Quando é o quinto dia útil de {PT_MONTHS[m - 1]} de {y}?", f"É {PT_WD[q.weekday()]}, {PT_DM(q)} de {y}, contando o sábado e sem contar domingos e feriados nacionais.") for y, m, q, _ in QDU_NEXT[:2]]
        + [("Quando cai o pagamento este mês?", "Depende da empresa: a lei fixa só a data-limite, que é o quinto dia útil do mês. Muitas empresas pagam antes, em dia fixo, por acordo ou convenção coletiva.")],
  "body": f"""<h1>Quando é o quinto dia útil do mês?</h1>
<p class="lede">O salário do mês precisa ser pago até o quinto dia útil do mês seguinte. Na contagem o sábado entra; o domingo e os feriados, não. Em {PT_MONTHS[_q1[1] - 1]} de {_q1[0]}, o quinto dia útil é <strong>{PT_WD[_q1[2].weekday()]}, {PT_DM(_q1[2])}</strong>.</p>
{next_counter("qdu", [(q[2], QDU_LBL(q)) for q in QDU], "pt-BR")}
<h2>Quinto dia útil de cada mês</h2>
<table><thead><tr><th>Mês</th><th>Quinto dia útil</th><th>Dias úteis no mês</th></tr></thead><tbody>{"".join(f'<tr><td>{PT_MONTHS[m - 1].capitalize()} de {y}</td><td>{q.day} ({PT_WD[q.weekday()]}){"<br><small>" + esc(_qdu_obs(y, m, q)) + "</small>" if _qdu_obs(y, m, q) else ""}</td><td>{u}</td></tr>' for y, m, q, u in QDU)}</tbody></table>
<p class="meta">A coluna “Quinto dia útil” conta de segunda a sábado; a coluna “Dias úteis no mês” conta de segunda a sexta. As duas descontam só os feriados nacionais: um feriado estadual ou municipal nos primeiros dias do mês empurra o quinto dia útil para o dia útil seguinte na sua cidade.</p>
<h2>Como contar o quinto dia útil</h2>
<ul><li><strong>A regra</strong>: quando o salário é mensal, o pagamento deve ser feito, o mais tardar, até o quinto dia útil do mês seguinte ao trabalhado (CLT, art. 459, § 1º).</li>
<li><strong>O sábado entra</strong>: na contagem dos dias inclui-se o sábado e excluem-se o domingo e o feriado, inclusive o municipal (Instrução Normativa MTP n.º&nbsp;2/2021, art. 14, I).</li>
<li><strong>Pagamento pelo banco</strong>: o valor precisa estar à disposição do empregado até o quinto dia útil (art. 14, II).</li></ul>
<p>Um exemplo: em novembro de 2026, o dia 1º é domingo e o dia 2, segunda-feira, é feriado (Finados). Contam terça, 3, quarta, 4, quinta, 5, sexta, 6, e sábado, 7 — o quinto dia útil é sábado, 7 de novembro.</p>
<h2>Quantos dias úteis tem cada mês?</h2>
<p>Para o trabalho de segunda a sexta, a conta é outra: os dias de segunda a sexta do mês, menos os feriados nacionais que caem nesses dias. É a terceira coluna da tabela. Os feriados nacionais considerados são 1º de janeiro, Paixão de Cristo, 21 de abril, 1º de maio, 7 de setembro, 12 de outubro, 2, 15 e 20 de novembro e 25 de dezembro. Carnaval e Corpus Christi não são feriados nacionais — são ponto facultativo ou feriado local —, por isso não foram descontados.</p>
<h2>O dia do pagamento na tela de bloqueio e na Tela de Início</h2>
<p>Com o <a href="/countdown/pt-br/">Countdown: Contagem regressiva</a> a contagem até o pagamento fica na Tela de Início ou na Tela Bloqueada como widget, grátis em todos os tamanhos, com lembrete no dia.</p>
<ol><li>Toque em <strong>Adicionar evento</strong> (ou em <strong>+</strong>, se já tiver eventos) e dê o nome “Pagamento”.</li><li>Data: o quinto dia útil deste mês. Como ele muda de mês para mês, atualize a data no mês seguinte; se a empresa paga sempre no mesmo dia, ligue a repetição mensal.</li>{PT_WIDGET_STEP}</ol>
{PT_LOCK_LINK}
<p>Para contar até qualquer outra data, use o <a href="/tools/pt-br/quantos-dias-faltam/">contador de dias</a>; para as férias, veja <a href="/tools/pt-br/quantos-dias-faltam-para-as-ferias/">quantos dias faltam para as férias</a>.</p>"""})

# 7. 发票模板
PAGES.append({"path": "/tools/invoice-template/", "lang": "en", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-09-26", "updated": "2026-10-24",
  "title": "Free Online Invoice Maker — No Sign-up, No Watermark", "crumb": "Invoice maker",
  "description": "Create an invoice online for free. No sign-up, watermark or credit card. Edit your details, calculate totals and tax, then print or save as PDF.",
  "hub_title": "Free online invoice maker", "hub_desc": "Create an invoice and save it as a PDF. No sign-up or watermark.",
  "css": (ROOT / "tools/invoice_editor.css").read_text(encoding="utf-8"),
  "js": [(ROOT / "tools/invoice_editor.js").read_text(encoding="utf-8")], "faq": [
    ("Is this invoice template really free?", "Yes. Your invoice details stay in your browser and are not sent to us. There is no account or watermark. Fill in the fields, then print or save as PDF."),
    ("What must an invoice include?", "The word Invoice, a unique invoice number, the issue date and due date, your business name and contact details, the client's name and address, a description of each item with quantity and price, the subtotal, any tax with its rate, the total due, and how to pay."),
    ("How do I save the invoice as a PDF?", "Click Save PDF / Print. In the print dialog choose 'Save as PDF' as the destination. Only the invoice is printed — the rest of the page is hidden."),
    ("Does it calculate tax?", "Yes. Type a tax rate in the Tax field and the tax amount and total update. Leave it at 0 if you do not charge tax."),
    ("Is there an app that keeps invoices, clients and payments?", "Smart Invoice & Estimate Maker is our iPhone app for exactly that: 100+ templates, estimates and quotes that turn into invoices, a payment QR code on every invoice, and paid / unpaid / overdue tracking. Your first document is free, with no account."),
  ],
  "body": f"""<h1>Free online invoice maker</h1>
<p class="lede">Create, edit and save a PDF invoice. Your invoice details stay in your browser.</p>
<p class="invoice-assurance">No sign-up · No watermark · No credit card</p>
{(ROOT / "tools/invoice_editor.html").read_text(encoding="utf-8")}
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
# 依据：tools/store/invoiceqr.json es-MX 描述（primer documento gratis sin cuenta（1.1.22 起）；cotización → nota de venta con un toque；CLABE / QR de pago；
# 「No emite CFDI ni facturas fiscales ante el SAT」）。IVA 只写「tasa general 16 %」（LIVA art. 1）；边境 8 % 是否延续没核实，不写。
# ⛔ 不把我们的单据叫 factura（墨西哥 factura = CFDI）
MX_NOTE = ('<p class="meta" style="margin-top:18px"><strong>Importante:</strong> una cotización o una nota de venta no es una factura. '
           'En México, la factura es un CFDI: un comprobante fiscal digital que se emite a través del SAT o de un proveedor autorizado (PAC). '
           'Ni este formato ni nuestra app emiten CFDI ni facturas fiscales ante el SAT.</p>')
MX_APP = ('Nota de Venta, Cotización, nuestra app para iPhone, hace esto mismo y guarda tus clientes y conceptos: envía primero la cotización y conviértela en nota de venta con un toque, '
          'agrega tus datos de transferencia (CLABE) o un código QR de pago, y comparte el PDF por WhatsApp. Tu primer documento es gratis, sin cuenta ni registro.')

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

# 7b2. 墨西哥：用 iPhone 做报价单 + Invoice Simple 替代对比（es-MX，InvoiceQR）——10-12
# 依据：10-12 Google 墨西哥联想词「app para hacer cotizaciones gratis / en iphone / en iphone gratis / mejor app para hacer cotizaciones」
# 「invoice simple gratis / app / factura」。app 说法只用 tools/store/invoiceqr.json es-MX 描述（1.1.23 与 1.1.22 描述相同）。
# Invoice Simple 只用它墨西哥商店页的描述（iTunes lookup id=694831622&country=mx&lang=es_mx，10-12 取）：名称「Invoice Simple: Facturas」、
# Zenvoice Inc.、「tus dos primeras facturas/presupuestos/recibos gratis」、datos bancarios、correo/SMS/WhatsApp/PDF、avisos al abrirse/pagarse/vencer、
# 评分 4.85（860）。我们 5.0（2）。⛔ 官网不写具体价格（两边都不写）；描述里没写的功能一律写「su descripción no lo menciona」，不替对方下结论。
COMPARED_ON = dt.date(2026, 10, 12)
PAGES.append({"path": "/tools/es-mx/app-para-hacer-cotizaciones-iphone/", "lang": "es-MX", "kind": "Article", "app": "invoiceqr", "published": "2026-10-12",
  "title": "App para hacer cotizaciones en iPhone: paso a paso, la primera gratis", "crumb": "Cotizaciones en el iPhone",
  "description": "Cómo hacer una cotización en el iPhone y mandarla en PDF por WhatsApp: cliente, conceptos, IVA, retenciones y CLABE; luego pásala a nota de venta.",
  "hub_title": "App para hacer cotizaciones en el iPhone", "hub_desc": "Paso a paso: de la cotización en PDF por WhatsApp a la nota de venta, con CLABE o QR de pago.",
  "more": [
    ("¿Hay una app para hacer cotizaciones gratis?", "Nota de Venta, Cotización te deja hacer tu primer documento gratis, sin cuenta ni registro. Es uno en total, no uno al mes; para más documentos está Pro. Si solo necesitas una cotización de vez en cuando, el <a href=\"/tools/es-mx/formato-de-cotizacion/\">formato de cotización</a> de esta página es gratis y se llena en el navegador."),
    ("¿Hay app para hacer cotizaciones en Android?", "Nota de Venta, Cotización es para iPhone y iPad. Desde un teléfono Android puedes usar el <a href=\"/tools/es-mx/formato-de-cotizacion/\">formato de cotización en línea</a> y guardarlo en PDF."),
    ("¿Cuál es la mejor app para hacer cotizaciones?", 'Depende de cómo trabajes. Si cotizas en México y cobras por transferencia, conviene una que hable de cotización y nota de venta, ponga tu CLABE y calcule retenciones. Comparamos la nuestra con Invoice Simple, que tiene 860 calificaciones en la App Store de México, en <a href="/tools/es-mx/alternativa-a-invoice-simple/">alternativa a Invoice Simple</a>.'),
  ],
  "faq": [
    ("¿Cuánto cuesta?", "Tu primer documento es gratis, sin cuenta ni registro: uno en total, sea cotización o nota de venta; las remisiones no lo consumen. Se cuenta una sola vez al crearlo, así que editarlo o reenviarlo no gasta nada. Con Pro los documentos son ilimitados; el precio aparece en la App Store antes de comprar."),
    ("¿Puedo mandar la cotización por WhatsApp?", "Sí. La cotización se comparte en PDF por WhatsApp, por correo o impresa."),
    ("¿La app emite factura (CFDI)?", "No. Crea cotizaciones, notas de venta, remisiones y recibos comerciales. Guarda el RFC, el código postal, el régimen y el uso CFDI de tu cliente para que tu contador facture con ellos."),
    ("¿Calcula retenciones?", "Sí: retención de ISR (10 % o 1.25 % RESICO) e IVA (dos terceras partes) con un interruptor, y el documento termina en «Total a pagar»."),
    ("¿Necesito internet o una cuenta?", "No. Funciona sin conexión y sin cuenta ni registro; tus documentos y clientes se sincronizan en privado con tu propio iCloud."),
  ],
  "body": f"""<h1>App para hacer cotizaciones en el iPhone</h1>
<p class="lede">Si cotizas en la calle o con el cliente enfrente, hazlo desde el iPhone: eliges una plantilla, agregas al cliente y los conceptos, y mandas el PDF por WhatsApp. Cuando el cliente acepta, la misma cotización se convierte en nota de venta con un toque.</p>
{top_cta("invoiceqr", "es-MX", "Descargar en el iPhone — el primero es gratis")}
<h2>Cómo hacer una cotización en el iPhone, paso a paso</h2>
<p>Con <a href="/invoiceqr/es-mx/">Nota de Venta, Cotización</a>, nuestra app:</p>
<ol><li>Elige una plantilla (en Pro hay más de 100). Tu logo, color y fuente se configuran una sola vez y se aplican a todos tus documentos; el kit de marca completo es parte de Pro.</li><li>Agrega al cliente. Queda guardado para la próxima vez, igual que tus artículos e impuestos.</li><li>Agrega los conceptos con cantidad y precio. Puedes sumar descuentos y envío, y activar las retenciones de ISR (10 % o 1.25 % RESICO) e IVA (dos terceras partes) con un interruptor; el documento termina en «Total a pagar».</li><li>Pon tus datos de transferencia (banco, CLABE, beneficiario) o un código QR con tu link de pago.</li><li>Comparte el PDF por WhatsApp, por correo o imprímelo.</li><li>Cuando el cliente acepte, convierte la cotización en nota de venta con un toque. Si entregas mercancía, la remisión lleva la firma de quien recibe.</li></ol>
<p>También puedes firmar a mano alzada en la pantalla, y si tienes un documento en papel, tómale una foto: se convierte en un borrador editable.</p>
<h2>Después de mandarla</h2>
<ul><li>Ves de un vistazo qué está pagado, pendiente, parcial o vencido.</li><li>Registras los pagos y el saldo pendiente se mantiene exacto.</li><li>Cuando te pagan completo, compartes el mismo documento como recibo, marcado como pagado y con la fecha de cobro.</li><li>Un widget en la pantalla de inicio te muestra lo que te deben.</li></ul>
<h2>Qué es gratis y qué es Pro</h2>
<table><thead><tr><th>Gratis</th><th>Pro</th></tr></thead><tbody>
<tr><td>Tu primer documento, sin cuenta ni registro (uno en total, no uno al mes; las remisiones no lo consumen)</td><td>Documentos y exportaciones QR ilimitados</td></tr>
<tr><td>4 de los 16 diseños QR listos</td><td>Más de 100 plantillas de documento, todos los estilos y diseños QR</td></tr>
<tr><td>Los archivos llevan al pie una línea pequeña con el nombre de la app</td><td>Kit de marca completo y sin la línea con el nombre de la app</td></tr>
</tbody></table>
<h2>¿Sin el iPhone a la mano?</h2>
<p>Llena el <a href="/tools/es-mx/formato-de-cotizacion/">formato de cotización</a> en el navegador: el importe, el IVA y el total se calculan solos y lo guardas en PDF. Cuando el cliente acepte, usa el <a href="/tools/es-mx/nota-de-venta/">formato de nota de venta</a>.</p>
{MX_NOTE}"""})

PAGES.append({"path": "/tools/es-mx/alternativa-a-invoice-simple/", "lang": "es-MX", "kind": "Article", "app": "invoiceqr", "published": "2026-10-12",
  "title": "Alternativa a Invoice Simple en México: cotización y nota de venta", "crumb": "Alternativa a Invoice Simple",
  "description": "Invoice Simple y Nota de Venta, Cotización lado a lado según la App Store de México: documentos, CFDI, cuántos son gratis, CLABE, retenciones y envío.",
  "hub_title": "Alternativa a Invoice Simple en México", "hub_desc": "Las dos apps lado a lado según la App Store de México: documentos, CFDI, gratis, CLABE y retenciones.",
  "more": [
    ("¿Invoice Simple es gratis?", "Se descarga gratis. Según su descripción en la App Store de México, tus dos primeras facturas, presupuestos o recibos son gratis; la descripción no dice cuánto cuesta seguir, así que revisa su página en la App Store."),
    ("¿Invoice Simple hace facturas para el SAT?", "Su descripción en la App Store de México no menciona el CFDI ni el SAT. En México, una factura fiscal es un CFDI emitido a través del SAT o de un proveedor autorizado (PAC)."),
  ],
  "faq": [
    ("¿Cuál es mejor, Invoice Simple o Nota de Venta, Cotización?", "Depende de cómo trabajes. Invoice Simple tiene muchas más calificaciones y te manda una notificación cuando se abre, se paga o vence un documento. Nota de Venta, Cotización usa los nombres de documentos de México (cotización, nota de venta, remisión), pone tu CLABE o un QR de pago y calcula retenciones de ISR e IVA."),
    ("¿Alguna de las dos emite CFDI?", "Nota de Venta, Cotización no emite CFDI: guarda el RFC, el código postal, el régimen y el uso CFDI del cliente para que tu contador facture. La descripción de Invoice Simple en la App Store de México no menciona el CFDI."),
    ("¿Cuántos documentos puedo hacer gratis?", "Según cada descripción: dos en Invoice Simple y uno en Nota de Venta, Cotización (uno en total; las remisiones no lo consumen). Para hacer más, revisa en la App Store lo que ofrece cada una."),
    ("¿Puedo pasar mis clientes a otra app?", "En Nota de Venta, Cotización los clientes, artículos e impuestos se guardan para reutilizarlos y se sincronizan con tu iCloud. Si cambias de app, cuenta con capturar de nuevo los datos de tus clientes."),
  ],
  "body": f"""<h1>Alternativa a Invoice Simple en México</h1>
<p class="lede">Invoice Simple es una app para hacer facturas, presupuestos y recibos, y en la App Store de México tiene 860 calificaciones. Si trabajas en México, a lo mejor buscas otra cosa: documentos que se llamen como aquí se llaman, tu CLABE en cada PDF y las retenciones ya calculadas. Esta es la comparación, con lo que dice cada app en su página de la App Store de México.</p>
<table class="cmp"><thead><tr><th></th><th>Invoice Simple: Facturas</th><th>Nota de Venta, Cotización (nuestra)</th></tr></thead><tbody>
<tr><th>Documentos</th><td>Facturas, presupuestos y recibos</td><td>Cotizaciones, notas de venta, remisiones y recibos</td></tr>
<tr><th>CFDI ante el SAT</th><td>Su descripción no lo menciona</td><td>No emite CFDI; guarda RFC, código postal, régimen y uso CFDI del cliente para tu contador</td></tr>
<tr><th>Gratis para empezar</th><td>Tus dos primeros documentos</td><td>Tu primer documento (uno en total; las remisiones no lo consumen)</td></tr>
<tr><th>Datos de pago</th><td>Tus datos bancarios</td><td>Banco, CLABE y beneficiario, o un QR con tu link de pago</td></tr>
<tr><th>Retenciones de ISR e IVA</th><td>Su descripción no lo menciona (sí permite ajustar impuestos y descuentos)</td><td>ISR 10 % o 1.25 % RESICO e IVA (dos terceras partes) con un interruptor</td></tr>
<tr><th>De cotización a venta</th><td>Su descripción no lo menciona</td><td>La cotización se convierte en nota de venta con un toque</td></tr>
<tr><th>Envío</th><td>Correo, SMS, WhatsApp o PDF</td><td>WhatsApp, correo o impresión (PDF)</td></tr>
<tr><th>Notificaciones</th><td>Te avisa cuando se abre, se paga o vence un documento</td><td>Nuestra descripción no lo menciona; ves de un vistazo qué está pagada, pendiente, parcial o vencida</td></tr>
<tr><th>Cuenta y conexión</th><td>Su descripción no lo menciona</td><td>Sin cuenta ni registro; funciona sin conexión y sincroniza con tu iCloud</td></tr>
<tr><th>Calificación en la App Store de México</th><td>4.9 (860 calificaciones)</td><td>5.0 (2 calificaciones)</td></tr>
</tbody></table>
<p class="meta">Datos tomados de la página de cada app en la App Store de México el {COMPARED_ON.day} de {['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'][COMPARED_ON.month - 1]} de {COMPARED_ON.year}. Las dos se descargan gratis; lo que cuesta seguir después de los documentos gratis aparece en la página de cada app en la App Store. Invoice Simple es una marca de Zenvoice Inc.; no tenemos relación con ellos.</p>
<h2>Cuándo conviene cada una</h2>
<ul><li><strong>Invoice Simple</strong>: si quieres recibir una notificación cuando se abra, se pague o venza un documento, o si te importa elegir una app con cientos de calificaciones.</li><li><strong>Nota de Venta, Cotización</strong>: si cotizas y luego vendes en México, cobras por transferencia con CLABE, necesitas retenciones de ISR o IVA, o quieres trabajar sin cuenta y sin conexión.</li></ul>
<h2>Una palabra sobre «factura»</h2>
<p>En México, factura quiere decir CFDI: un comprobante fiscal digital que se emite a través del SAT o de un proveedor autorizado (PAC). Por eso nuestra app no llama factura a lo que crea: hace cotizaciones, notas de venta, remisiones y recibos, y guarda los datos fiscales de tu cliente para que tu contador facture.</p>
<p>¿Quieres probar sin instalar nada? Llena el <a href="/tools/es-mx/formato-de-cotizacion/">formato de cotización</a> en el navegador. Y si ya decidiste, aquí está <a href="/tools/es-mx/app-para-hacer-cotizaciones-iphone/">cómo hacer una cotización en el iPhone, paso a paso</a>.</p>"""})

# 7b3. 泰国：ใบเสนอราคา / ใบเสร็จรับเงิน 模板（th，InvoiceQR）——10-12
# 依据：泰国是 InvoiceQR 唯一产出试用的市场（见 invoiceqr-th-* 记忆）。10-12 Google 泰国联想词：「ใบเสนอราคา ตัวอย่าง / ฟอร์ม / excel ฟรี / บุคคลธรรมดา / ฟรี / word」
# 「ใบเสร็จรับเงิน ภาษาอังกฤษ / (excel ฟรี) / บุคคลธรรมดา / ไฟล์ word / ฟอร์ม」。app 说法只用 tools/store/invoiceqr.json th 描述：
# เอกสารใบแรกฟรี ไม่ต้องสมัครบัญชี（ฟรีใบเดียวทั้งหมด）；เริ่มจากใบเสนอราคา แล้วแปลงเป็นใบแจ้งหนี้ได้ในแตะเดียว；คิวอาร์โค้ดชำระเงิน；
# ใบแจ้งหนี้ที่ชำระครบแล้ว แชร์เป็นใบเสร็จได้；ลายเซ็นเขียนมือ；ไม่ต้องสมัครบัญชี ใช้งานออฟไลน์ได้。
# 法规只写一句通则：ใบกำกับภาษี 由 VAT 登记的经营者开具（ประมวลรัษฎากร มาตรา 86）；税率不写死（默认 0，用户自己填）。⛔ 不说我们开 ใบกำกับภาษี。
TH_NOTE = ('<p class="meta" style="margin-top:18px"><strong>หมายเหตุ:</strong> แบบฟอร์มนี้เป็นใบเสนอราคาและใบเสร็จรับเงินทั่วไป ไม่ใช่ใบกำกับภาษี '
           'ใบกำกับภาษีออกโดยผู้ประกอบการที่จดทะเบียนภาษีมูลค่าเพิ่มตามมาตรา 86 แห่งประมวลรัษฎากร และต้องมีรายการตามที่กฎหมายกำหนด '
           'ถ้าคุณจดทะเบียนภาษีมูลค่าเพิ่ม โปรดตรวจรายการกับกรมสรรพากรก่อนใช้</p>')
TH_APP = ('ทำใบแจ้งหนี้ ใบเสนอราคา ง่ายๆ คือแอป iPhone ของเรา ทำเรื่องเดียวกันนี้ได้ในไม่กี่นาที และจำลูกค้ากับรายการไว้ใช้ซ้ำ: '
          'เริ่มจากใบเสนอราคา แล้วแปลงเป็นใบแจ้งหนี้ได้ในแตะเดียว ใส่คิวอาร์โค้ดชำระเงินให้ลูกค้าสแกนจ่าย '
          'และเมื่อชำระครบแล้ว แชร์เอกสารเดิมเป็นใบเสร็จได้เลย เอกสารใบแรกฟรี ไม่ต้องสมัครบัญชี')
# 10-25：ใบเสร็จรับเงิน 页并进 ใบเสนอราคา 页（同一张表单，上方切换文档类型），旧网址在 vercel.json 301 到 ?doc=receipt。
# 依据：claude-seo 程序化门槛——两页共用同一套表单和说明，独有内容只有 24% / 32%；泰国也已不是 IQ 的目标市场（10-17 用户定 IQ 瞄德国）。
# 切换只改还没被用户改过的默认文字（data-q / data-r），已填的客户、条目、金额都留着。
TH_DOC_JS = r"""
(function(){var t=document.getElementById('inv'),sw=document.getElementById('doc-switch');if(!t||!sw)return;
function set(mode){var r=mode==='receipt';t.setAttribute('data-doc',mode);
t.querySelectorAll('[data-q]').forEach(function(el){var q=el.getAttribute('data-q'),rc=el.getAttribute('data-r'),cur=el.textContent.trim();if(!el.isContentEditable||!cur||cur===q||cur===rc)el.textContent=r?rc:q});
t.querySelectorAll('.only-q').forEach(function(el){el.hidden=r});t.querySelectorAll('.only-r').forEach(function(el){el.hidden=!r});
sw.querySelectorAll('button[data-doc]').forEach(function(b){var on=b.getAttribute('data-doc')===mode;b.setAttribute('aria-pressed',on?'true':'false');b.classList.toggle('ghost',!on)})}
sw.addEventListener('click',function(e){var b=e.target.closest('button[data-doc]');if(b)set(b.getAttribute('data-doc'))});
if(new URLSearchParams(location.search).get('doc')==='receipt')set('receipt')})();
"""
PAGES.append({"path": "/tools/th/bai-sanoe-rakha/", "lang": "th", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-10-12",
  "title": "ใบเสนอราคา ใบเสร็จรับเงิน ฟรี — กรอกออนไลน์ บุคคลธรรมดาใช้ได้", "crumb": "ใบเสนอราคา / ใบเสร็จรับเงิน",
  "description": "แบบฟอร์มใบเสนอราคาและใบเสร็จรับเงินฟรี สำหรับบุคคลธรรมดาและฟรีแลนซ์ กรอกบนหน้าเว็บ สลับประเภทเอกสารได้ ยอดรวมคำนวณให้เอง พิมพ์หรือบันทึก PDF ไม่ต้องสมัคร",
  "hub_title": "ใบเสนอราคา และใบเสร็จรับเงิน ฟรี", "hub_desc": "ฟอร์มเดียว สลับเป็นใบเสนอราคาหรือใบเสร็จรับเงินได้ ยอดรวมคำนวณให้เอง พิมพ์หรือบันทึกเป็น PDF",
  "js": [INVOICE_JS, TH_DOC_JS], "css": ".doc-switch{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}.doc-switch .btn{padding:12px 18px}.doc-switch .btn[aria-pressed=true]{background:var(--yellow);color:var(--ink);box-shadow:inset 0 0 0 1.5px var(--ink)}.inv [hidden]{display:none!important}@media print{.doc-switch{display:none!important}}",
  "more": [
    ("ใบเสนอราคา excel ฟรี มีไหม", "หน้านี้ไม่ต้องโหลด Excel: กรอกบนหน้าเว็บได้เลย ยอดของแต่ละรายการและยอดรวมคำนวณให้เอง แล้วกด «พิมพ์ / บันทึก PDF»"),
    ("ใบเสนอราคา word ใช้แทนได้ไหม", "ได้ บันทึกเป็น PDF จากหน้านี้แล้วส่งให้ลูกค้า ไฟล์ PDF เปิดได้ทุกเครื่องและแก้ไขไม่ได้โดยไม่ตั้งใจ"),
    ("ใบเสร็จรับเงิน excel ฟรี มีไหม", "กดปุ่ม «ใบเสร็จรับเงิน» เหนือฟอร์ม แล้วกรอกบนหน้าเว็บได้เลย ยอดรวมคำนวณให้เอง ไม่ต้องโหลด Excel"),
    ("ใบเสร็จรับเงิน ภาษาอังกฤษ เรียกว่าอะไร", "ภาษาอังกฤษเรียกว่า Receipt ส่วนใบเสนอราคาเรียกว่า Quotation และใบแจ้งหนี้เรียกว่า Invoice"),
  ],
  "faq": [
    ("ฟอร์มนี้ฟรีจริงไหม", "ฟรี ทุกอย่างทำงานในเบราว์เซอร์ของคุณ ไม่มีการอัปโหลด ไม่ต้องสมัคร และไม่มีลายน้ำ กรอกเสร็จแล้วพิมพ์หรือบันทึกเป็น PDF ได้เลย"),
    ("บุคคลธรรมดาออกใบเสนอราคาได้ไหม", "ได้ ใบเสนอราคาคือเอกสารเสนอราคาก่อนตกลงซื้อขาย ฟรีแลนซ์และบุคคลธรรมดาออกได้ ใส่ชื่อ ที่อยู่ และช่องทางติดต่อของคุณแทนชื่อบริษัท"),
    ("บุคคลธรรมดาออกใบเสร็จรับเงินได้ไหม", "ได้ ใบเสร็จรับเงินคือหลักฐานว่าได้รับเงินแล้ว บุคคลธรรมดาและฟรีแลนซ์ออกให้ลูกค้าได้ ใส่ชื่อ ที่อยู่ และลงลายมือชื่อผู้รับเงิน"),
    ("ต้องใส่ภาษีมูลค่าเพิ่มไหม", "ถ้าคุณไม่ได้จดทะเบียนภาษีมูลค่าเพิ่ม ให้ปล่อยช่องภาษีเป็น 0 ถ้าจดทะเบียนแล้ว ให้ใส่อัตราที่ใช้อยู่ ยอดภาษีและยอดรวมจะคำนวณให้เอง"),
    ("ใบเสนอราคาควรมีกำหนดยืนราคาไหม", "ควรมี เพื่อบอกว่าราคานี้ใช้ได้ถึงวันไหน ในฟอร์มนี้จะตั้งไว้ให้ 15 วันนับจากวันนี้ แก้เป็นวันอื่นได้"),
    ("ใบเสร็จรับเงินกับใบกำกับภาษีต่างกันอย่างไร", "ใบเสร็จรับเงินยืนยันว่าได้รับเงินแล้ว ส่วนใบกำกับภาษีเป็นเอกสารภาษีมูลค่าเพิ่ม ออกโดยผู้ประกอบการที่จดทะเบียนภาษีมูลค่าเพิ่ม ฟอร์มในหน้านี้ไม่ใช่ใบกำกับภาษี"),
    ("บันทึกเป็น PDF อย่างไร", "กด «พิมพ์ / บันทึก PDF» แล้วในหน้าต่างพิมพ์ เลือกปลายทางเป็น «บันทึกเป็น PDF» จะพิมพ์ออกมาเฉพาะตัวเอกสาร"),
    ("มีแอปทำใบเสนอราคาและใบเสร็จบน iPhone ไหม", TH_APP),
  ],
  "body": f"""<h1>ใบเสนอราคา และใบเสร็จรับเงิน ฟรี</h1>
<p class="lede">กรอกได้บนหน้านี้เลย เลือกว่าจะทำใบเสนอราคาหรือใบเสร็จรับเงิน แล้วคลิกช่องที่มีเส้นประเพื่อแก้ไข ยอดของแต่ละรายการ ภาษี และยอดรวมคำนวณให้เอง จากนั้นพิมพ์หรือบันทึกเป็น PDF ข้อมูลไม่ออกจากเบราว์เซอร์ของคุณ</p>
<div class="inv-wrap">
<div class="doc-switch" id="doc-switch" role="group" aria-label="เลือกเอกสาร"><button class="btn" type="button" data-doc="quote" aria-pressed="true" data-track-id="th-doc-quote">ใบเสนอราคา</button><button class="btn ghost" type="button" data-doc="receipt" aria-pressed="false" data-track-id="th-doc-receipt">ใบเสร็จรับเงิน</button></div>
<div class="inv-tools"><button class="btn" id="print" type="button">พิมพ์ / บันทึก PDF</button><button class="btn ghost" id="addrow" type="button">+ เพิ่มรายการ</button></div>
<div class="inv" id="inv" data-newitem="รายการ" data-days="15" data-doc="quote">
<div class="inv-head"><div><div class="inv-title" data-q="ใบเสนอราคา" data-r="ใบเสร็จรับเงิน">ใบเสนอราคา</div><p style="margin:6px 0 0"><span contenteditable="true">ชื่อของคุณหรือชื่อร้าน</span><br><span contenteditable="true">ที่อยู่</span><br><span contenteditable="true">อีเมล · 08x-xxx-xxxx</span></p></div>
<div class="inv-meta"><div class="k">เลขที่</div><p style="margin:0 0 10px"><span contenteditable="true" data-q="QT-0001" data-r="RC-0001">QT-0001</span></p><div class="k">วันที่</div><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><div class="only-q"><div class="k">ยืนราคาถึง</div><p style="margin:0"><span contenteditable="true" id="due"></span></p></div></div></div>
<div class="inv-parties"><div><div class="k" data-q="เสนอราคาให้" data-r="ได้รับเงินจาก">เสนอราคาให้</div><p style="margin:0"><span contenteditable="true">ชื่อลูกค้า</span><br><span contenteditable="true">ที่อยู่ลูกค้า</span><br><span contenteditable="true">อีเมลหรือเบอร์โทรลูกค้า</span></p></div>
<div class="only-q"><div class="k">เงื่อนไข</div><p style="margin:0"><span contenteditable="true">มัดจำ 50% ส่วนที่เหลือชำระเมื่อส่งงาน</span><br><span contenteditable="true">โอนเข้าบัญชี ธนาคาร … เลขที่ …</span></p></div>
<div class="only-r" hidden><div class="k">ชำระโดย</div><p style="margin:0"><span contenteditable="true">เงินสด / โอนเงิน / พร้อมเพย์</span></p></div></div>
<table><thead><tr><th>รายการ</th><th>จำนวน</th><th>ราคาต่อหน่วย</th><th>จำนวนเงิน</th></tr></thead>
<tbody><tr><td contenteditable="true">ออกแบบโลโก้</td><td contenteditable="true">1</td><td contenteditable="true">5000.00</td><td>5,000.00</td></tr>
<tr><td contenteditable="true">ออกแบบนามบัตร</td><td contenteditable="true">1</td><td contenteditable="true">1500.00</td><td>1,500.00</td></tr></tbody></table>
<div class="totals"><div><span>รวม</span><span id="sub">6,500.00</span></div><div><span>ภาษีมูลค่าเพิ่ม (<span contenteditable="true" id="taxrate">0</span>%)</span><span id="tax">0.00</span></div><div class="grand"><span>รวมทั้งสิ้น</span><span id="total">6,500.00</span></div></div>
<p class="notes only-q" contenteditable="true">ราคาเป็นเงินบาท ใบเสนอราคานี้มีผลถึงวันที่ยืนราคา</p>
<p class="notes only-r" contenteditable="true" hidden>ได้รับเงินถูกต้องครบถ้วนแล้ว ขอบคุณที่ใช้บริการ<br><br>ลงชื่อ ................................ ผู้รับเงิน</p>
</div></div>
<h2>ใบเสนอราคาควรมีอะไรบ้าง</h2>
<ul><li><strong>คำว่า «ใบเสนอราคา»</strong> และเลขที่เอกสาร</li><li><strong>วันที่</strong> และ <strong>วันยืนราคา</strong>: ราคานี้ใช้ได้ถึงวันไหน</li><li><strong>ข้อมูลของคุณ</strong>: ชื่อหรือชื่อร้าน ที่อยู่ และช่องทางติดต่อ</li><li><strong>ข้อมูลลูกค้า</strong>: ชื่อ ที่อยู่ หรืออีเมล</li><li><strong>รายการ</strong>: รายละเอียด จำนวน ราคาต่อหน่วย และจำนวนเงิน</li><li><strong>ยอดรวม</strong> ภาษี (ถ้ามี) และ <strong>ยอดรวมทั้งสิ้น</strong></li><li><strong>เงื่อนไข</strong>: การชำระเงิน มัดจำ และระยะเวลาส่งงาน</li></ul>
<h2>ใบเสร็จรับเงินควรมีอะไรบ้าง</h2>
<ul><li><strong>คำว่า «ใบเสร็จรับเงิน»</strong> และเลขที่เรียงกันไป</li><li><strong>วันที่</strong> ได้รับเงิน</li><li><strong>ชื่อผู้รับเงิน</strong>: ชื่อของคุณหรือชื่อร้าน และที่อยู่</li><li><strong>ชื่อผู้จ่ายเงิน</strong>: ชื่อลูกค้า</li><li><strong>รายการ</strong>: รายละเอียด จำนวน ราคาต่อหน่วย และจำนวนเงิน</li><li><strong>ยอดรวมทั้งสิ้น</strong> และวิธีชำระ</li><li><strong>ลายมือชื่อผู้รับเงิน</strong></li></ul>
<h2>บุคคลธรรมดาออกใบเสร็จรับเงินได้ไหม</h2>
<p>ได้ ใบเสร็จรับเงินเป็นหลักฐานว่าคุณได้รับเงินจากลูกค้าแล้ว ฟรีแลนซ์ แม่ค้าออนไลน์ และร้านเล็ก ๆ ที่ยังไม่ได้จดทะเบียนภาษีมูลค่าเพิ่ม ใช้ฟอร์มนี้ออกให้ลูกค้าได้ ปล่อยช่องภาษีเป็น 0 แล้วลงลายมือชื่อผู้รับเงิน</p>
<h2>ใบเสนอราคา ใบแจ้งหนี้ ใบเสร็จรับเงิน ต่างกันอย่างไร</h2>
<table><thead><tr><th>เอกสาร</th><th>ออกเมื่อไร</th><th>ใช้ทำอะไร</th></tr></thead><tbody>
<tr><td>ใบเสนอราคา</td><td>ก่อนตกลงซื้อขาย</td><td>เสนอราคาที่ยืนให้จนถึงวันยืนราคา</td></tr>
<tr><td>ใบแจ้งหนี้</td><td>เมื่อส่งงานหรือส่งของ</td><td>แจ้งยอดที่ลูกค้าต้องชำระและกำหนดชำระ</td></tr>
<tr><td>ใบเสร็จรับเงิน</td><td>เมื่อได้รับเงินแล้ว</td><td>ยืนยันว่าได้รับเงินจำนวนนั้นแล้ว</td></tr>
</tbody></table>
<p>ลูกค้าตกลงและจ่ายเงินแล้ว? กดปุ่ม «ใบเสร็จรับเงิน» เหนือฟอร์ม รายการและยอดเงินที่กรอกไว้ยังอยู่ครบ ถ้าทำเอกสารหลายใบต่อเดือน <a href="/invoiceqr/th/">ทำใบแจ้งหนี้ ใบเสนอราคา ง่ายๆ</a> บน iPhone จำลูกค้าและรายการไว้ให้ แปลงใบเสนอราคาเป็นใบแจ้งหนี้ได้ในแตะเดียว และเมื่อชำระครบแล้ว แชร์เอกสารเดิมเป็นใบเสร็จได้ทันที</p>
{TH_NOTE}"""})

# 7c. 港台：報價單範本 / 收據範本（zh-Hant，InvoiceQR）——09-29
# 依据：Google HK / TW 联想词（報價單範本 excel/word/下載/pdf、報價單產生器；收據範本 word/excel/茲收到/數字/香港、免用統一發票 收據格式）；
# app 说法全部出自 tools/store/invoiceqr.json zh-Hant 描述（商店名「開單、報價單、收據、送貨單產生器」；先寄報價單，確認後一鍵轉帳單；
# 收款 QR Code；手寫簽名；結清後同一份帳單當收據分享；第一份免費免註冊（1.1.22 起）；「不用於開立稅務發票」）。
# ⛔ 台灣的「發票」＝統一發票（稅務憑證），我們不開——同墨西哥 CFDI 的口径。營業稅只写一般稅率 5%；香港無營業稅。
ZH_NOTE = ('<p class="meta" style="margin-top:18px"><strong>提醒：</strong>報價單和收據都不是稅務發票。在台灣，營業人依法開立的是統一發票；'
           '這個範本和我們的 App 都不開立統一發票或其他稅務發票。</p>')
ZH_APP = ('「開單、報價單、收據、送貨單產生器」是我們的 iPhone App，做的就是這件事，還會記住客戶與項目：先寄報價單，客戶確認後一鍵轉成帳單；'
          '每份帳單都可以附上收款 QR Code，簽名直接在 iPhone 上手寫；收款結清後，同一份帳單可以直接當作收據分享。第一份免費，免註冊帳號。')
RECEIPT_JS = r"""
(function(){var r=document.getElementById('rcpt');if(!r)return;
function amount(){var m=(a.textContent||'').trim().match(/^((?:\d+|\d{1,3}(?:,\d{3})+))(?:\.(\d{1,2}))?$/);
 if(!m)return null;var yuan=Number(m[1].replace(/,/g,''));if(yuan>=1e12)return null;
 return yuan*100+Number((m[2]||'').padEnd(2,'0'));}
function cnUpper(cents){var n=Math.floor(cents/100),part=cents%100;
 var D='零壹貳參肆伍陸柒捌玖',U=['','拾','佰','仟'],S=['','萬','億'],s=String(n),L=s.length,out=n===0?'零':'',zero=false;
 for(var i=0;i<L;i++){var d=+s[i],p=L-1-i,u=p%4,g=Math.floor(p/4);
  if(d===0)zero=true;else{if(zero){out+='零';zero=false;}out+=D[d]+U[u];}
  if(u===0&&g>0&&+s.substring(Math.max(0,i-3),i+1)>0){out+=S[g];zero=false;}}
 var jiao=Math.floor(part/10),fen=part%10;
 return out+'元'+(!part?'整':(jiao?D[jiao]+'角':(n?'零':''))+(fen?D[fen]+'分':'整'));}
var a=document.getElementById('amt'),o=document.getElementById('amt-cn'),error=document.getElementById('amount-error');
function upd(){var cents=amount(),valid=cents!==null;
 a.setAttribute('aria-invalid',String(!valid));error.hidden=valid;
 if(valid)r.removeAttribute('data-invalid');else r.setAttribute('data-invalid','true');
 o.textContent=valid?cnUpper(cents):'（金額格式有誤）';return valid;}
function format(){if(!upd())return false;var cents=amount(),part=cents%100;
 a.textContent=Math.floor(cents/100).toLocaleString('en-US')+(part?'.'+String(part).padStart(2,'0'):'');return true;}
a.addEventListener('input',upd);upd();
a.addEventListener('blur',format);
var t=document.getElementById('today');if(t)t.textContent=new Date().toLocaleDateString('zh-Hant');
window.addEventListener('beforeprint',format);
document.getElementById('print').addEventListener('click',function(){if(format())window.print();else a.focus();});})();
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
  # 10-15：GSC「茲收到 / 茲收到收款證明 / 茲收到範本」等約 30 次曝光、排名 6.5–12；Google TW 联想词「茲收到意思 / 用法 / 現金範本 / 手寫收據範本 / 英文」
  "more": [
    ("茲收到的英文怎麼說？", "英文收據常寫「Received from（付款人）the sum of（金額）for（事由）」，例如 Received from Wang Xiao-Ming the sum of NT$15,000 for October rent."),
    ("手寫收據也可以用這個格式嗎？", "可以。照「茲收到、付款人、事由、大寫金額」的順序寫，最後簽名或蓋章。寫錯了不要塗改，重開一張比較保險。"),
  ],
  "title": "收據範本（免費）— 茲收到格式，金額自動轉大寫", "crumb": "收據範本",
  "description": "免費收據範本：線上填寫「茲收到」格式的收據，輸入金額就自動寫出中文大寫，再列印或存成 PDF。不用註冊，港台都適用。",
  "hub_title": "收據範本", "hub_desc": "「茲收到」格式，輸入金額自動寫出大寫；列印或存成 PDF。",
  "js": [RECEIPT_JS], "faq": [
    ("這個收據範本免費嗎？", "是。整份在你的瀏覽器裡填寫，不會上傳，不用帳號，也沒有浮水印。填好後列印或存成 PDF。"),
    ("收據金額為什麼要寫大寫？", "大寫數字筆畫多、不容易被塗改，例如「壹萬貳仟參佰元整」；最後的「整」表示沒有零頭。在範本裡輸入數字，大寫會自動寫出來。"),
    ("「茲收到」是什麼意思？", "「茲」是「此、現在」的意思，「茲收到」就是「現在確實收到」。這是收據開頭的固定用語，表示收款人確認已經收到這筆錢。"),
    ("「茲收到」後面要寫什麼？", "寫付款人的姓名或公司名稱，接著寫「繳付」與款項的事由，例如「茲收到 王小明 繳付 十月份房租 款項」。"),
    ("金額有小數怎麼辦？", "支援最多兩位小數，數字與中文大寫會一起保留角、分，例如 123.45 會寫成「壹佰貳拾參元肆角伍分」。超過兩位小數、負數、空白或一兆元以上的金額會提示修正，不會自動捨去或列印。"),
    ("收據可以當發票用嗎？", "不行。收據證明你收到了款項；在台灣，營業人依法要開的是統一發票。在香港，「發票」通常指請款用的單據（invoice），不是稅務憑證。這個範本和我們的 App 都不開立稅務發票。"),
    ("有 App 可以在 iPhone 上開收據嗎？", "有。在我們的「開單、報價單、收據、送貨單產生器」裡，收款結清後，同一份帳單可以直接當作收據分享：標記為已付，並附上結清日期。帳單可以附收款 QR Code，也能在 iPhone 上手寫簽名。第一份免費，免註冊帳號。"),
  ],
  "body": f"""<style>@media print{{#rcpt[data-invalid="true"]{{display:none!important}}}}</style>
<h1>收據範本</h1>
<p class="lede">直接在這裡填：點任何虛線欄位就能修改。輸入金額，下面會自動寫出中文大寫；填好後列印或存成 PDF。資料不會離開你的瀏覽器。</p>
<div class="inv-wrap">
<div class="inv-tools"><button class="btn" id="print" type="button">列印／存成 PDF</button></div>
<p id="amount-error" role="alert" hidden>請輸入 0 至未滿一兆元的金額，最多兩位小數，例如 123.45；修正前無法列印有效收據。</p>
<div class="inv" id="rcpt">
<div class="inv-head"><div><div class="inv-title">收據</div><p style="margin:6px 0 0"><span contenteditable="true">收款人或公司名稱</span><br><span contenteditable="true">地址 · 電話</span></p></div>
<div class="inv-meta"><div class="k">收據編號</div><p style="margin:0 0 10px"><span contenteditable="true">R-0001</span></p><div class="k">日期</div><p style="margin:0"><span contenteditable="true" id="today"></span></p></div></div>
<p class="rcpt-line">茲收到 <span contenteditable="true">付款人姓名／公司</span> 繳付 <span contenteditable="true">網站設計費用</span> 款項</p>
<p class="rcpt-line">金額：<span contenteditable="true">新台幣</span> <strong id="amt-cn">參萬元整</strong></p>
<p class="rcpt-line">（<span contenteditable="true">NT$</span> <span contenteditable="true" id="amt" role="textbox" aria-label="收據金額" aria-describedby="amount-error" inputmode="decimal">30,000</span>）</p>
<p class="rcpt-line">付款方式：<span contenteditable="true">銀行轉帳</span></p>
<div class="rcpt-sign"><div>收款人簽名：＿＿＿＿＿＿</div><div>蓋章：</div></div>
<p class="notes" contenteditable="true">此據。</p>
</div></div>
<h2>收據要寫什麼</h2>
<ul><li><strong>「收據」字樣</strong>與收據編號。</li><li><strong>日期</strong>：收到款項的那一天。</li><li><strong>「茲收到 某某 繳付 某某款項」</strong>：付款人與事由。</li><li><strong>金額</strong>：中文大寫加阿拉伯數字，整數元以「元整」結尾，有小數則寫出角、分。香港填港幣時，把「新台幣」和「NT$」改成「港幣」和「HK$」。</li><li><strong>付款方式</strong>：現金、轉帳、支票。</li><li><strong>收款人簽名或蓋章</strong>。</li></ul>
<h2>「茲收到」的寫法</h2>
<p>「茲」是「此、現在」，「茲收到」就是「現在確實收到」。後面依序寫付款人、事由和金額，最後寫「此據」。</p>
<table><thead><tr><th>情況</th><th>寫法</th></tr></thead><tbody>
<tr><td>現金</td><td>茲收到 王小明 交來 現金 新台幣參仟元整</td></tr>
<tr><td>房租</td><td>茲收到 王小明 繳付 十月份房租 新台幣壹萬伍仟元整</td></tr>
<tr><td>訂金</td><td>茲收到 陳大華 繳付 婚禮攝影訂金 新台幣伍仟元整</td></tr>
<tr><td>英文收據</td><td>Received from Wang Xiao-Ming the sum of NT$15,000 for October rent.</td></tr>
</tbody></table>
<p>手寫收據也照這個順序寫。寫錯了不要塗改，重開一張比較保險；大寫金額和阿拉伯數字要一致。</p>
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
  "more": [
    ('離過年還有幾天？', '2027 年農曆新年（初一）是 2 月 6 日星期六。頁面最上方的數字會在你打開的當天重新計算。'),
    ('2027 除夕是哪一天？', '2027 年除夕是 2 月 5 日星期五。'),
    ('2027 過年是什麼時候？', '除夕是 2 月 5 日（五），初一是 2 月 6 日（六）。台灣的春節假期從 2 月 4 日放到 2 月 10 日。'),
    ('2027 年還有哪些連假？', '台灣 2027 年 3 天以上的連假有 9 個，日期和倒數整理在 <a href="/tools/zh-hant/2027-lian-jia-xing-shi-li/">2027 連假行事曆</a>。'),
  ],
  "js": [COUNT_JS], "faq": [
    ("2027 年農曆新年是哪一天？", f"大年初一是{fmt(CNY, 'zh-Hant')}，除夕是{fmt(CNY_EVE, 'zh-Hant')}。"),
    ("2027 年台灣過年放幾天？", f"依行政院人事行政總處公布的 116 年辦公日曆表，春節假期共 7 天，從{fmt(dt.date(2027, 2, 4), 'zh-Hant')}放到{fmt(dt.date(2027, 2, 10), 'zh-Hant')}；初一、初二逢週末，於2月9日、10日補假。"),
    ("2027 年香港農曆新年有哪幾天公眾假期？", f"年初一是{CNY_MD(CNY)}、年初三是{CNY_MD(dt.date(2027, 2, 8))}、年初四是{CNY_MD(dt.date(2027, 2, 9))}。年初二是星期日，所以年初四定為補假。"),
    ("2027 年是什麼生肖？", "羊年，天干地支是丁未。"),
    ("過年還有幾天？", f"在{TODAY.year}年{TODAY.month}月{TODAY.day}日，{zh_left(days_to(CNY), '大年初一')}。本頁的倒數會在你打開當天重新計算。"),
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
<p class="meta">資料來源：行政院人事行政總處新聞稿、香港政府一站通「2027 年公眾假期」（{SOURCES_CHECKED.year}年{SOURCES_CHECKED.month}月{SOURCES_CHECKED.day}日確認）。公司與學校的假期可能不同。</p>
<h2>把過年倒數放在鎖定畫面</h2>
<p>不想每次打開網頁，可以把倒數放在 iPhone 的主畫面或鎖定畫面。<a href="/countdown/zh-hant/">倒數計時 Widget：紀念日提醒</a>的小工具全部尺寸都免費，事件數量不限；倒數走到一百天、一週、當天早上這些節點時，App 會以整螢幕的數字打開，並給你一張可以分享的卡片。</p>
<ol><li>點「新增事件」（已經有事件時點「＋」），輸入「過年」。</li><li>日期設為2027年2月6日。農曆新年的國曆日期每年都不同，所以不要開「每年重複」；明年再另外加一個新日期。</li><li>長按鎖定畫面 →「自訂」→ 鎖定畫面 → 加入小工具 → Countdown。主畫面則是長按 →「編輯」→「加入小工具」（iOS 17 是長按後點左上角的「＋」）。</li></ol>
<p>點一下事件，它會翻到自己的背面：可以寫下年貨清單、放幾張照片，這一天的故事就留在這一天裡。桌布和小工具差在哪裡，見 <a href="/tools/zh-hant/iphone-zhu-hua-mian-dao-shu/">iPhone 主畫面與鎖定畫面倒數教學</a>。</p>"""})

# 7c2. 台灣：2027 連假行事曆（zh-Hant，Countdown）——10-10
# 依據：10-10 Google 台灣聯想詞「2027 連假行事曆 / 2027 連假 / 2027 春節 連假 / 2027 過年 連假 / 過年 還有幾天」。
# 日期出自行政院人事行政總處新聞稿（115.05.21「行政院核定116年政府行政機關辦公日曆表」：9 個連假與各自日數、春節與兒童節補假；
# 114.06.13 稿：115 年國慶 / 光復 / 行憲各 3 日、處理要點刪除補行上班）——10-10 直接讀官網原文；起迄日按「逢六前補、逢日後補」逐個核對過星期。
# 端午 6/9、中秋 9/15 是農曆固定日換算；教師節 9/28。App 說法只用 zh-Hant 商店描述裡免費的部分。⛔ 不用「倒數日」（APP280001-B）。
TW_CHECKED = dt.date(2026, 10, 10)
_tw = lambda y, m, d: dt.date(y, m, d)
TW_2026 = [("臺灣光復暨金門古寧頭大捷紀念日", _tw(2026, 10, 24), _tw(2026, 10, 26), "10/25 是星期日，10/26（一）補假"),
           ("行憲紀念日", _tw(2026, 12, 25), _tw(2026, 12, 27), "12/25 是星期五")]
TW_2027 = [("元旦（開國紀念日）", _tw(2027, 1, 1), _tw(2027, 1, 3), "1/1 是星期五"),
           ("農曆春節", _tw(2027, 2, 4), _tw(2027, 2, 10), "初一、初二是週六、週日，2/9、2/10 補假"),
           ("和平紀念日（228）", _tw(2027, 2, 27), _tw(2027, 3, 1), "2/28 是星期日，3/1（一）補假"),
           ("兒童節及清明節", _tw(2027, 4, 3), _tw(2027, 4, 6), "4/4 兒童節是星期日，4/6（二）補假"),
           ("勞動節", _tw(2027, 4, 30), _tw(2027, 5, 2), "5/1 是星期六，4/30（五）補假"),
           ("國慶日", _tw(2027, 10, 9), _tw(2027, 10, 11), "10/10 是星期日，10/11（一）補假"),
           ("臺灣光復暨金門古寧頭大捷紀念日", _tw(2027, 10, 23), _tw(2027, 10, 25), "10/25 是星期一"),
           ("行憲紀念日", _tw(2027, 12, 24), _tw(2027, 12, 26), "12/25 是星期六，12/24（五）補假"),
           ("2028 年元旦", _tw(2027, 12, 31), _tw(2028, 1, 2), "2028/1/1 是星期六，12/31（五）補假")]
assert [(a.weekday(), b.weekday()) for _, a, b, _ in TW_2027] == [(4, 6), (3, 2), (5, 0), (5, 1), (4, 6), (5, 0), (5, 0), (4, 6), (4, 6)]
assert [(a.weekday(), b.weekday()) for _, a, b, _ in TW_2026] == [(5, 0), (4, 6)]
TW_WD = lambda d: "一二三四五六日"[d.weekday()]
TW_MD = lambda d: f"{d.month}/{d.day}（{TW_WD(d)}）"
def tw_rows(items):
    out = []
    for name, a, b, note in items:
        n = days_to(a); left = f'<span data-n>{abs(n) if n else ""}</span> <span data-unit>{"就是今天！" if n == 0 else ("天前" if n < 0 else "天")}</span>'
        nb = "border-bottom:0;padding-bottom:4px"
        out.append(f'<tr><td style="{nb}">{esc(name)}</td><td style="{nb}"><span style="white-space:nowrap">{TW_MD(a)}</span>–<span style="white-space:nowrap">{TW_MD(b)}</span></td>'
                   f'<td style="white-space:nowrap;{nb}">{(b - a).days + 1} 天</td><td data-date="{a.isoformat()}" style="white-space:nowrap;{nb}">{left}</td></tr>'
                   f'<tr><td colspan="4" style="padding-top:0"><small>{esc(note)}</small></td></tr>')
    return "".join(out)
PAGES.append({"path": "/tools/zh-hant/2027-lian-jia-xing-shi-li/", "lang": "zh-Hant", "kind": "Article", "app": "countdown", "published": "2026-10-10",
  "title": "2027 連假行事曆（民國 116 年）：9 個連假與請假攻略，還有幾天？", "crumb": "2027 連假行事曆",
  "description": "2027 年（民國 116 年）3 天以上的連假有 9 個：元旦 1/1–1/3、春節 2/4–2/10 共 7 天，還有 228、清明、勞動節、國慶、光復節、行憲紀念日。每個連假還有幾天，每天更新。",
  "hub_title": "2027 連假行事曆：下一個連假還有幾天？", "hub_desc": "民國 116 年的 9 個連假、補假日與請假攻略，每個連假都有每天更新的倒數。",
  "js": [NEXT_JS, COUNT_JS],
  "faq": [
    ("2027 年有幾個連假？", "依行政院核定的 116 年政府行政機關辦公日曆表，3 天以上的連假有 9 個：元旦、農曆春節、和平紀念日、兒童節及清明節、勞動節、國慶日、臺灣光復暨金門古寧頭大捷紀念日、行憲紀念日，以及 2028 年元旦補假形成的跨年連假。全年放假 121 天。"),
    ("2027 年春節放幾天？", "從 2 月 4 日（四）放到 2 月 10 日（三），共 7 天。初一、初二（2 月 6 日、7 日）是週六、週日，所以在 2 月 9 日、10 日補假。"),
    ("2027 年有補班日嗎？", "沒有。現行的補假規定已經刪除「調整放假、補行上班」的做法：放假日遇到星期六，在前一個上班日補假；遇到星期日，在後一個上班日補假。"),
    ("民間企業也照這份行事曆放假嗎？", "這份日曆表適用於政府行政機關，公營事業原則上比照辦理；學校和警察、消防、軍事等機關另有規定。民間企業的放假依勞動基準法和勞動部的規定辦理。"),
    ("怎麼把連假倒數放在 iPhone 主畫面？", "在「倒數計時 Widget：紀念日提醒」裡點「新增事件」（已經有事件時點「＋」），輸入連假名稱和第一天的日期，再長按主畫面 → 編輯 → 加入小工具 → Countdown。小工具全部尺寸都免費，事件數量不限。"),
  ],
  "more": [
    ("2027 過年連假是哪幾天？", "2 月 4 日（四）到 2 月 10 日（三），共 7 天；除夕是 2 月 5 日，初一是 2 月 6 日。"),
    ("2027 清明連假是哪幾天？", "4 月 3 日（六）到 4 月 6 日（二），共 4 天。4 月 4 日兒童節是星期日，改在 4 月 6 日補假。"),
    ("2027 國慶連假是哪幾天？", "10 月 9 日（六）到 10 月 11 日（一），共 3 天。"),
    ("2027 中秋節是哪一天？有連假嗎？", "2027 年中秋節是 9 月 15 日星期三，放假 1 天，沒有形成連假。"),
    ("2027 端午節是哪一天？", "2027 年端午節是 6 月 9 日星期三，放假 1 天，沒有形成連假。"),
    ("2026 年還有連假嗎？", "還有兩個：光復節連假 10 月 24 日（六）到 10 月 26 日（一），行憲紀念日連假 12 月 25 日（五）到 12 月 27 日（日）。"),
  ],
  "body": f"""<h1>2027 連假行事曆：下一個連假還有幾天？</h1>
<p class="lede">依行政院核定的 116 年（2027 年）政府行政機關辦公日曆表，2027 年 3 天以上的連假有 <strong>9 個</strong>，春節連放 <strong>7 天</strong>，全年沒有補班日。下面的數字會在你打開頁面的當天重新計算。</p>
{next_counter("lj", [(a, f"下一個連假：{name} · {TW_MD(a)}–{TW_MD(b)}，共 {(b - a).days + 1} 天") for name, a, b, _ in TW_2026 + TW_2027], "zh-Hant")}
<h2>2027 年的 9 個連假</h2>
<table><thead><tr><th>連假</th><th>日期</th><th style="white-space:nowrap">天數</th><th style="white-space:nowrap">還有幾天</th></tr></thead><tbody>{tw_rows(TW_2027)}</tbody></table>
<h2>2026 年底前還有的連假</h2>
<table><thead><tr><th>連假</th><th>日期</th><th style="white-space:nowrap">天數</th><th style="white-space:nowrap">還有幾天</th></tr></thead><tbody>{tw_rows(TW_2026)}</tbody></table>
<h2>沒有連假的國定假日</h2>
<ul><li>端午節：6 月 9 日（三）</li><li>中秋節：9 月 15 日（三）</li><li>孔子誕辰紀念日／教師節：9 月 28 日（二）</li></ul>
<h2>請假攻略</h2>
<ul><li><strong>春節</strong>：2 月 11 日（四）、12 日（五）請 2 天，從 2 月 4 日連休到 2 月 14 日，共 11 天。</li>
<li><strong>端午節</strong>：6 月 7 日（一）、8 日（二）請 2 天，從 6 月 5 日連休到 6 月 9 日，共 5 天。</li>
<li><strong>中秋節</strong>：9 月 13 日（一）、14 日（二）請 2 天，從 9 月 11 日連休到 9 月 15 日，共 5 天。</li>
<li><strong>教師節</strong>：9 月 27 日（一）請 1 天，從 9 月 25 日連休到 9 月 28 日，共 4 天。</li></ul>
<h2>補假怎麼算</h2>
<p>放假的紀念日或節日遇到星期六，在前一個上班日補假；遇到星期日，在後一個上班日補假。除夕和春節遇到例假日，可以在前一個或後一個上班日補假。現行規定已經沒有「先放假、再補班」的做法。</p>
<p>這份日曆表適用於政府行政機關，公營事業原則上比照辦理；學校和警察、消防、軍事等機關另有規定，民間企業則依勞動基準法和勞動部的規定辦理。</p>
<p class="meta">資料來源：<a href="https://www.dgpa.gov.tw/information?pid=12983&amp;uid=82" rel="noopener">行政院人事行政總處新聞稿</a>（115 年 5 月 21 日、114 年 6 月 13 日）與 116 年政府行政機關辦公日曆表（{TW_CHECKED.year} 年 {TW_CHECKED.month} 月 {TW_CHECKED.day} 日確認）。公司與學校的假期可能不同。</p>
<h2>把連假倒數放在主畫面</h2>
<p>不想每次打開網頁，可以把倒數放在 iPhone 的主畫面或鎖定畫面。「<a href="/countdown/zh-hant/">倒數計時 Widget：紀念日提醒</a>」的小工具全部尺寸都免費，事件數量不限。</p>
<ol><li>點「新增事件」（已經有事件時點「＋」），輸入連假的名稱，例如「春節連假」。</li><li>日期設為連假的第一天，例如 2027 年 2 月 4 日。</li><li>長按主畫面 →「編輯」→「加入小工具」→ Countdown。</li></ol>
<p>農曆新年的日期和香港的公眾假期，見 <a href="/tools/zh-hant/nong-li-xin-nian-2027/">2027 農曆新年倒數</a>；放到鎖定畫面的完整步驟，見 <a href="/tools/zh-hant/iphone-zhu-hua-mian-dao-shu/">iPhone 主畫面與鎖定畫面倒數教學</a>。</p>"""})

# 7c3. 台灣：116 學測 / 116 會考倒數 + iPhone 主畫面倒數教學（zh-Hant，Countdown）——10-12
# 依据：10-12 GSC——「…まであと何日 / いつ」「quantos dias faltam…」這類問日期、問天數的詞被 Google AI 概覽直接答掉，排第 8 也 0 點擊；
# 全站唯一有點擊的是「共通テストカウントダウン 待ち受け」（想把考試倒數放到手機上）。Google 台灣聯想詞：「會考 倒數 桌布 / 116 會考 倒數 桌布 /
# 學 測 倒數 桌布 / 分科 倒數 桌布」「iphone 倒數 計時 桌面」「倒數 app 桌面」「iphone 倒數 widget」「考試倒數 app」。
# 日期只用 10-12 讀過的官方原文：大考中心「116學年度考試重要試務日期」PDF（ceec.edu.tw 首頁「重要日程」）；
# 教育部 115-09-11 臺教授國部字第1155404304號函「116學年度國中教育會考及全國高級中等學校與專科學校五年制適性入學重要日程表」PDF（cap.rcpet.edu.tw）。
# app 說法只用 zh-Hant 商店 1.4.16 描述：小工具全部尺寸免費（主畫面和鎖定畫面）、事件數量無限制、節點整螢幕；
# 自己的照片做背景、鎖定畫面即時動態屬於 Pro；「無論訂不訂閱，倒數、提醒和小工具都照常能用」。⛔ 不用「倒數日」三個字（APP280001-B）。
EXAMS_CHECKED = dt.date(2026, 10, 12)
XC1, XC3, XC_REG1, XC_REG2, XC_ROOM, XC_SCORE, XC_MAIL = (dt.date(2027, 1, 22), dt.date(2027, 1, 24), dt.date(2026, 10, 27), dt.date(2026, 11, 10),
                                                          dt.date(2027, 1, 5), dt.date(2027, 2, 25), dt.date(2027, 2, 26))
FK1, FK2, FK_SCORE = dt.date(2027, 7, 10), dt.date(2027, 7, 11), dt.date(2027, 7, 29)
HK1, HK2, HK_REG1, HK_REG2, HK_TICKET, HK_SCORE = dt.date(2027, 5, 15), dt.date(2027, 5, 16), dt.date(2027, 3, 4), dt.date(2027, 3, 6), dt.date(2027, 4, 9), dt.date(2027, 6, 4)
ZH_LOCK_PATH = "/tools/zh-hant/iphone-zhu-hua-mian-dao-shu/"
ZH_LOCK_STEPS = ('<li>鎖定畫面：長按鎖定畫面 →「自訂」→ 鎖定畫面 →「加入小工具」→ 選 Countdown。</li>'
                 '<li>主畫面：長按主畫面 →「編輯」→「加入小工具」（iOS 17 是長按後點左上角的「＋」）→ 選 Countdown，挑一個尺寸。</li>')
def zh_nodes(d):
    return "".join(f"<tr><td>{k}</td><td>{fmt(d - dt.timedelta(days=n), 'zh-Hant')}</td></tr>"
                   for k, n in (("100 天前", 100), ("50 天前", 50), ("30 天前", 30), ("1 週前", 7), ("前一天", 1)))

# 10-20 用户：学测 / 会考 / 共通テスト / 都立入試 / 旅行計画アプリ 5 页标题按 Google 桌面标题 20px Arial 实测缩到 580px 内，搜索词留在开头
PAGES.append({"path": "/tools/zh-hant/116-xue-ce-dao-shu/", "lang": "zh-Hant", "kind": "Article", "app": "countdown", "published": "2026-10-12",
  "title": "116 學測倒數桌布？iPhone 鎖定畫面小工具（1/22–24）", "crumb": "116 學測倒數",
  "description": "116 學年度學測在 2027 年 1 月 22 日（五）到 24 日（日），2 月 25 日公布成績。想要學測倒數桌布？用 iPhone 鎖定畫面的免費小工具，天數每天自動更新；另附報名與分科測驗日期。",
  "hub_title": "116 學測倒數", "hub_desc": "1 月 22 日到 24 日考試，報名、成績公布與分科測驗日期，每天更新的倒數。",
  "more": [
    ("有學測倒數桌布嗎？", f'桌布是一張圖片，上面的數字會停在做圖那一天。想讓桌面上的「還有幾天」每天自己變，就用鎖定畫面或主畫面的小工具：日期設 2027 年 1 月 22 日，數字每天自動減一。步驟見本頁「學測倒數桌布？改用 iPhone 鎖定畫面小工具」一節。'),
    ("學測還有幾週？", "頁面最上方的數字下面，會寫還有幾週又幾天，打開當天重新計算。"),
    ("學測倒數 100 天是哪一天？", f"{fmt(XC1 - dt.timedelta(days=100), 'zh-Hant')}。其他節點見「倒數的節點」表。"),
  ],
  "js": [COUNT_JS], "faq": [
    ("116 學測是哪幾天？", f"{fmt(XC1, 'zh-Hant')}到{fmt(XC3, 'zh-Hant')}，一共三天。"),
    ("116 學測什麼時候報名？", f"{fmt(XC_REG1, 'zh-Hant')}到{fmt(XC_REG2, 'zh-Hant')}。"),
    ("學測成績什麼時候公布？", f"{fmt(XC_SCORE, 'zh-Hant')}公布成績並開放查詢，隔天寄發成績通知單。"),
    ("116 分科測驗是哪一天？", f"{fmt(FK1, 'zh-Hant')}和{fmt(FK2, 'zh-Hant')}，成績在{fmt(FK_SCORE, 'zh-Hant')}公布。"),
    ("學測還有幾天？", f"在{TODAY.year}年{TODAY.month}月{TODAY.day}日，{zh_left(days_to(XC1), '學測第一天')}。本頁的倒數會在你打開當天重新計算。"),
    ("怎麼把學測倒數放在 iPhone 鎖定畫面？", "在「倒數計時 Widget：紀念日提醒」建立 2027 年 1 月 22 日的事件，然後長按鎖定畫面 →「自訂」→ 鎖定畫面 → 加入小工具 → 選 Countdown。小工具全部尺寸都免費。"),
  ],
  "body": f"""<h1>116 學測倒數</h1>
<p class="lede">116 學年度學科能力測驗在 <strong>2027 年 1 月 22 日（星期五）到 24 日（星期日）</strong>。下面的倒數每天更新；想每天在手機上看到，可以把它放到 iPhone 的主畫面或鎖定畫面。</p>
{counter(XC1, "zh-Hant", "學測第一天")}
<h2>116 學年度考試日程</h2>
<table><thead><tr><th>項目</th><th>日期</th></tr></thead><tbody>
<tr><td>學測報名</td><td>{fmt(XC_REG1, "zh-Hant")}～{fmt(XC_REG2, "zh-Hant")}</td></tr>
<tr><td>開放查詢應試號碼、考試地點</td><td>{fmt(XC_ROOM, "zh-Hant")}</td></tr>
<tr><td>學測考試</td><td>{fmt(XC1, "zh-Hant")}～{fmt(XC3, "zh-Hant")}</td></tr>
<tr><td>學測公布成績</td><td>{fmt(XC_SCORE, "zh-Hant")}</td></tr>
<tr><td>寄發學測成績通知單</td><td>{fmt(XC_MAIL, "zh-Hant")}</td></tr>
<tr><td>分科測驗</td><td>{fmt(FK1, "zh-Hant")}～{fmt(FK2, "zh-Hant")}</td></tr>
<tr><td>分科測驗公布成績</td><td>{fmt(FK_SCORE, "zh-Hant")}</td></tr>
</tbody></table>
<p class="meta">資料來源：<a href="https://www.ceec.edu.tw/" rel="noopener">大學入學考試中心</a>「116學年度考試重要試務日期」（{EXAMS_CHECKED.year}年{EXAMS_CHECKED.month}月{EXAMS_CHECKED.day}日確認）。各科的考試時間與應考規定，以大考中心公告的簡章為準。</p>
<h2>學測倒數桌布？改用 iPhone 鎖定畫面小工具</h2>
<p>很多人會找「學測倒數桌布」，但桌布是一張圖片，數字停在做圖那一天。<a href="/countdown/zh-hant/">倒數計時 Widget：紀念日提醒</a>的小工具會每天自己把數字減一；主畫面和鎖定畫面的小工具全部尺寸都免費，事件數量也沒有上限。</p>
<ol><li>點「新增事件」（已經有事件時點「＋」），輸入「學測」，日期設為 2027 年 1 月 22 日。想一起倒數分科測驗，就再加一個 7 月 10 日的事件。</li>{ZH_LOCK_STEPS}</ol>
<p>倒數走到一百天、一週、當天早上這些節點時，App 會以整螢幕的數字打開，並給你一張可以分享的卡片。桌布和小工具差在哪裡、還有更完整的步驟，見 <a href="{ZH_LOCK_PATH}">iPhone 主畫面與鎖定畫面倒數教學</a>。</p>
<h2>倒數的節點</h2>
<table><thead><tr><th>節點</th><th>日期</th></tr></thead><tbody>{zh_nodes(XC1)}</tbody></table>
<p>國中教育會考的倒數，見 <a href="/tools/zh-hant/116-hui-kao-dao-shu/">116 會考倒數</a>。</p>"""})

PAGES.append({"path": "/tools/zh-hant/116-hui-kao-dao-shu/", "lang": "zh-Hant", "kind": "Article", "app": "countdown", "published": "2026-10-12",
  "title": "116 會考倒數桌布？iPhone 鎖定畫面小工具（5/15–16）", "crumb": "116 會考倒數",
  "description": "116 年國中教育會考在 2027 年 5 月 15 日（六）、16 日（日），6 月 4 日寄發成績通知單。想要會考倒數桌布？用 iPhone 鎖定畫面的免費小工具，天數每天自動更新；另附報名與准考證日期。",
  "hub_title": "116 會考倒數", "hub_desc": "5 月 15 日、16 日考試，報名、准考證與成績日期，每天更新的倒數。",
  "more": [
    ("有會考倒數桌布嗎？", '桌布是一張圖片，上面的數字會停在做圖那一天。想讓桌面上的「還有幾天」每天自己變，就用鎖定畫面或主畫面的小工具：日期設 2027 年 5 月 15 日，數字每天自動減一。步驟見本頁「會考倒數桌布？改用 iPhone 鎖定畫面小工具」一節。'),
    ("會考還有幾週？", "頁面最上方的數字下面，會寫還有幾週又幾天，打開當天重新計算。"),
    ("會考倒數 100 天是哪一天？", f"{fmt(HK1 - dt.timedelta(days=100), 'zh-Hant')}。其他節點見「倒數的節點」表。"),
  ],
  "js": [COUNT_JS], "faq": [
    ("116 會考是哪幾天？", f"{fmt(HK1, 'zh-Hant')}和{fmt(HK2, 'zh-Hant')}。"),
    ("116 會考什麼時候報名？", f"{fmt(HK_REG1, 'zh-Hant')}到{fmt(HK_REG2, 'zh-Hant')}。"),
    ("會考准考證什麼時候寄？", f"{fmt(HK_TICKET, 'zh-Hant')}寄發准考證。"),
    ("會考成績什麼時候公布？", f"{fmt(HK_SCORE, 'zh-Hant')}寄發成績通知單，並開放網路查詢。"),
    ("會考還有幾天？", f"在{TODAY.year}年{TODAY.month}月{TODAY.day}日，{zh_left(days_to(HK1), '會考第一天')}。本頁的倒數會在你打開當天重新計算。"),
    ("怎麼把會考倒數放在 iPhone 鎖定畫面？", "在「倒數計時 Widget：紀念日提醒」建立 2027 年 5 月 15 日的事件，然後長按鎖定畫面 →「自訂」→ 鎖定畫面 → 加入小工具 → 選 Countdown。小工具全部尺寸都免費。"),
  ],
  "body": f"""<h1>116 會考倒數</h1>
<p class="lede">116 年國中教育會考在 <strong>2027 年 5 月 15 日（星期六）、16 日（星期日）</strong>。下面的倒數每天更新；想每天在手機上看到，可以把它放到 iPhone 的主畫面或鎖定畫面。</p>
{counter(HK1, "zh-Hant", "會考第一天")}
<h2>116 年會考日程</h2>
<table><thead><tr><th>項目</th><th>日期</th></tr></thead><tbody>
<tr><td>會考報名</td><td>{fmt(HK_REG1, "zh-Hant")}～{fmt(HK_REG2, "zh-Hant")}</td></tr>
<tr><td>寄發准考證</td><td>{fmt(HK_TICKET, "zh-Hant")}</td></tr>
<tr><td>會考考試</td><td>{fmt(HK1, "zh-Hant")}～{fmt(HK2, "zh-Hant")}</td></tr>
<tr><td>寄發成績通知單、開放網路查詢</td><td>{fmt(HK_SCORE, "zh-Hant")}</td></tr>
</tbody></table>
<p class="meta">資料來源：教育部 115 年 9 月 11 日臺教授國部字第 1155404304 號函「116學年度國中教育會考及全國高級中等學校與專科學校五年制適性入學重要日程表」，刊於<a href="https://cap.rcpet.edu.tw/" rel="noopener">國中教育會考網站</a>（{EXAMS_CHECKED.year}年{EXAMS_CHECKED.month}月{EXAMS_CHECKED.day}日確認）。報名方式和考試時間表，以會考簡章為準。</p>
<h2>會考倒數桌布？改用 iPhone 鎖定畫面小工具</h2>
<p>很多人會找「會考倒數桌布」，但桌布是一張圖片，數字停在做圖那一天。<a href="/countdown/zh-hant/">倒數計時 Widget：紀念日提醒</a>的小工具會每天自己把數字減一；主畫面和鎖定畫面的小工具全部尺寸都免費，事件數量也沒有上限。</p>
<ol><li>點「新增事件」（已經有事件時點「＋」），輸入「會考」，日期設為 2027 年 5 月 15 日。</li>{ZH_LOCK_STEPS}</ol>
<p>倒數走到一百天、一週、當天早上這些節點時，App 會以整螢幕的數字打開，並給你一張可以分享的卡片。桌布和小工具差在哪裡、還有更完整的步驟，見 <a href="{ZH_LOCK_PATH}">iPhone 主畫面與鎖定畫面倒數教學</a>。</p>
<h2>倒數的節點</h2>
<table><thead><tr><th>節點</th><th>日期</th></tr></thead><tbody>{zh_nodes(HK1)}</tbody></table>
<p>大學學測的倒數，見 <a href="/tools/zh-hant/116-xue-ce-dao-shu/">116 學測倒數</a>。</p>"""})

PAGES.append({"path": ZH_LOCK_PATH, "iphone_only": True, "lang": "zh-Hant", "kind": "Article", "app": "countdown", "published": "2026-10-12",
  "title": "iPhone 桌面倒數怎麼放？主畫面、鎖定畫面倒數小工具教學", "crumb": "iPhone 桌面倒數",
  "description": "把「還有幾天」放到 iPhone 主畫面和鎖定畫面的步驟。和寫上數字的桌布不同，小工具只要設定一次日期，數字每天自動更新；學測、會考、過年、連假都適用。",
  "hub_title": "iPhone 桌面倒數教學", "hub_desc": "在主畫面和鎖定畫面放「還有幾天」的步驟，學測、會考、過年都適用。",
  "js": [COUNT_JS], "faq": [
    ("桌面倒數小工具要錢嗎？", "不用。「倒數計時 Widget：紀念日提醒」的小工具全部尺寸都免費，主畫面和鎖定畫面都能放，事件數量也沒有上限。"),
    ("桌布可以直接寫上倒數天數嗎？", "可以，但桌布是一張圖片，數字會停在做圖那一天。想讓「還有幾天」每天自己變，要用鎖定畫面或主畫面的小工具。"),
    ("可以用自己的照片當背景嗎？", "可以，用你自己的照片做背景屬於 Countdown Pro。無論訂不訂閱，倒數、提醒和小工具都照常能用。"),
    ("鎖定畫面小工具和即時動態一樣嗎？", "不一樣。鎖定畫面的小工具在時間下方，免費；鎖定畫面的即時動態是 Countdown Pro 的功能。"),
    ("Android 手機可以用嗎？", "這個 App 只有 iPhone 和 iPad 版，沒有 Android 版。Android 手機請到 Google Play 找支援桌面小工具的倒數計時 App。"),
  ],
  "body": f"""<h1>iPhone 桌面倒數怎麼放？</h1>
<p class="lede">學測、會考、過年、旅行……想不打開任何東西就看到「還有幾天」，可以把倒數放到 iPhone 的鎖定畫面或主畫面。寫上數字的桌布每天都得重做一張；小工具只要設定一次日期，數字就會每天自動減一。</p>
{top_cta("countdown", "zh-Hant", "放到鎖定畫面（免費）")}
<h2>桌布和小工具差在哪裡</h2>
<table><thead><tr><th></th><th>寫上數字的桌布</th><th>小工具</th></tr></thead><tbody>
<tr><th>數字</th><td>停在做圖那一天</td><td>每天自動更新</td></tr>
<tr><th>要做的事</th><td>每天重做一張</td><td>設定一次日期</td></tr>
<tr><th style="white-space:nowrap">位置</th><td>鎖定畫面、主畫面的背景</td><td>鎖定畫面的時間下方、主畫面</td></tr>
</tbody></table>
<h2>放到鎖定畫面</h2>
<ol><li>安裝<a href="/countdown/zh-hant/">倒數計時 Widget：紀念日提醒</a>，點「新增事件」（已經有事件時點「＋」），輸入名稱（例如「學測」）和日期。</li><li>長按鎖定畫面，等「自訂」出現後點一下，選擇鎖定畫面。</li><li>點「加入小工具」，選 Countdown，再點想用的小工具。倒數就會出現在時間下方。</li></ol>
<p>小工具全部尺寸都免費，事件數量沒有上限：學測、分科測驗和過年可以同時倒數。</p>
<h2>放到主畫面</h2>
<ol><li>長按主畫面的空白處。</li><li>點左上角的「編輯」→「加入小工具」（iOS 17 是點左上角的「＋」）。</li><li>選 Countdown 和尺寸，再點「加入小工具」。</li></ol>
<h2>大家常倒數的日子</h2>
<div class="pop">
<a href="/tools/zh-hant/116-xue-ce-dao-shu/" data-date="{XC1.isoformat()}"><b data-n>{days_to(XC1)}</b><span><span data-unit>天</span>（116 學測）</span></a>
<a href="/tools/zh-hant/116-hui-kao-dao-shu/" data-date="{HK1.isoformat()}"><b data-n>{days_to(HK1)}</b><span><span data-unit>天</span>（116 會考）</span></a>
<a href="/tools/zh-hant/nong-li-xin-nian-2027/" data-date="{CNY.isoformat()}"><b data-n>{days_to(CNY)}</b><span><span data-unit>天</span>（2027 農曆新年）</span></a>
</div>
<p class="meta">上面的數字是 {TODAY.year}年{TODAY.month}月{TODAY.day}日算的，打開頁面時會重新計算。2027 年的連假日期見 <a href="/tools/zh-hant/2027-lian-jia-xing-shi-li/">2027 連假行事曆</a>。</p>
<h2>倒數走到節點時</h2>
<p>倒數走到一百天、一週、當天早上這些節點時，App 會以整螢幕的數字打開，並給你一張可以分享的卡片。點一下事件，它會翻到自己的背面，可以寫幾句話、放照片、錄一段聲音。</p>"""})

# 7d. 日本：あと何日（日数計算）+ 共通テスト2027（ja，Countdown）——09-29
# 依据：Google JP 联想词（共通テスト まであと何日 2027 / カウントダウン 待ち受け / あと何日 アプリ / 共通テスト 100日前 いつ；
# あと何日 計算 / 今日 入れる / あと何日で今年終わる、日数計算 / 営業日）。
# 日期出自大学入試センター「令和9年度試験」「令和10年度試験」页（09-29 取）：本試験 2027-01-16/17，追・再試験 01-23/24；2028-01-15/16。
# app 说法只用 ja 商店描述里「免费」那部分（ウィジェットはすべて無料 / ホーム画面・ロック画面 / 節目の全画面 / 裏面 / カウントアップ）；
# jp 商店 10-10 已是 1.4.16（Pro＝背景 / 自分の写真 / Pro フォント / ロック画面のライブアクティビティ / 招待）。
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
<form class="calc" id="calc"><label>イベント<input type="text" name="name" placeholder="誕生日、旅行、試験…" maxlength="60"></label><label>日付<input type="date" name="date" required></label><button type="submit" data-track-id="calc-submit">日数を数える</button></form>
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
  "more": [
    ("共通テスト2027の追・再試験はいつですか？", f"{fmt(KTM1, 'ja')}・{KTM2.day}日（{'月火水木金土日'[KTM2.weekday()]}）です。"),
    ("共通テストまであと1か月になるのはいつですか？", f"1か月前は{fmt(dt.date(2026, 12, 16), 'ja')}、30日前は{fmt(KT1 - dt.timedelta(days=30), 'ja')}です。"),
  ],
  "title": "共通テスト2027 カウントダウン・待ち受け（1/16・17）", "crumb": "共通テスト2027",
  "description": f"2027年の大学入学共通テストは1月16日（土）・17日（日）。本試験まであと何日かを毎日更新でカウントダウンし、100日前・1週間前の日付と、iPhoneのロック画面に置く方法をまとめました。",
  "hub_title": "共通テスト2027まであと何日？", "hub_desc": "本試験（1月16日・17日）までのカウントダウンと、100日前・30日前・1週間前の日付。",
  "js": [COUNT_JS], "faq": [
    ("共通テスト2027はいつですか？", f"本試験は{fmt(KT1, 'ja')}と{fmt(KT2, 'ja')}です。追・再試験は{fmt(KTM1, 'ja')}と{fmt(KTM2, 'ja')}です（大学入試センター「令和9年度試験」）。"),
    ("共通テストまであと何週間ですか？", f"{TODAY.year}年{TODAY.month}月{TODAY.day}日の時点で{ja_left(days_to(KT1), '本試験', '本試験の初日はすでに過ぎています')}。このページのカウントダウンは、開いた日に合わせて再計算されます。"),
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
<p class="meta">出典：大学入試センター「令和9年度試験」「令和10年度試験」（{SOURCES_CHECKED.year}年{SOURCES_CHECKED.month}月{SOURCES_CHECKED.day}日に確認）。出願の手続きや時間割は、大学入試センターの案内で確認してください。</p>
<h2>節目の日付</h2>
<table><thead><tr><th>節目</th><th>日付</th></tr></thead><tbody>{"".join(f"<tr><td>{k}</td><td>{fmt(KT1 - dt.timedelta(days=n), 'ja')}</td></tr>" for k, n in (("100日前", 100), ("50日前", 50), ("30日前", 30), ("1週間前", 7), ("前日", 1)))}</tbody></table>
<h2>ロック画面・待ち受けに置く</h2>
<p>毎回サイトを開かなくても残り日数が見えるように、iPhone のロック画面やホーム画面にウィジェットとして置けます。<a href="/countdown/ja/">カウントダウン ウィジェット: 記念日</a>なら、すべてのサイズのウィジェットが無料です。100日前・1週間前・当日の朝といった節目に達すると、アプリが全画面の数字で開き、共有できるカードを用意します。</p>
<ol><li>アプリで「イベントを追加」（すでにイベントがある場合は「＋」）をタップし、「共通テスト」と入力します。</li><li>日付を{fmt(KT1, "ja")}に設定します。通知は当日のほか、何日前でも好きなだけ追加できます。</li><li>ロック画面を長押し →「カスタマイズ」→ ロック画面 → ウィジェットを追加 → Countdown。ホーム画面なら、長押し →「編集」→「ウィジェットを追加」です（iOS 17 では長押しして左上の「＋」）。</li></ol>
<h2>カウントダウンの使い方</h2>
<ul><li>イベントの裏面に、科目ごとの目標や模試の結果を書いておく。</li><li>追・再試験や二次試験、私立大学の入試日も別のイベントにして、「次の予定リスト」のウィジェットで並べる。</li><li>過ぎた日は削除されず、振り返れるタイムラインとして残ります。</li></ul>
<p>ほかの日付は<a href="/tools/ja/ato-nannichi/">あと何日？（日数計算）</a>で数えられます。</p>
<p>ロック画面に置く手順は<a href="/tools/ja/countdown-machiuke-iphone/">カウントダウンを待ち受けにする方法（iPhone）</a>にくわしくまとめました。</p>"""})

# 7d2. 日本：都立入試2027 カウントダウン（ja，Countdown）——10-15
# 依据：Google JP 联想词「都立入試 2027 / 2027 日程 / 2027年度 都立入試」「都立入試 カウントダウン」「都立入試 あと何日」「2027 都立 入試 カウントダウン」；
# 全站点击最多的是共通テスト页（「共通テストカウントダウン 待ち受け」），本页照它的结构做（首屏答案 + 待ち受け）。
# 日期只用 10-15 读过的官方原文：東京都教育委員会「令和９年度東京都立高等学校入学者選抜実施要綱・同細目について」（2026-09-17 更新）「1 主な日程」。
# app 说法同共通テスト页（ja 商店描述：ウィジェットは全サイズ無料、イベント無制限；ロック画面のライブアクティビティは Pro）。
TOKYO_CHECKED = dt.date(2026, 10, 15)
TR_S_APP1, TR_S_APP2, TR_S1, TR_S2, TR_S_RES = dt.date(2027, 1, 8), dt.date(2027, 1, 18), dt.date(2027, 1, 26), dt.date(2027, 1, 27), dt.date(2027, 2, 2)
TR_APP1, TR_APP2, TR1, TR_RES = dt.date(2027, 1, 29), dt.date(2027, 2, 4), dt.date(2027, 2, 21), dt.date(2027, 3, 1)
TR2_APP, TR2, TR2_RES, TR_NET = dt.date(2027, 3, 4), dt.date(2027, 3, 9), dt.date(2027, 3, 12), dt.date(2026, 12, 18)
TOKYO_SRC = "https://www.kyoiku.metro.tokyo.lg.jp/admission/high_school/exam/release20260917_r9yoko"
def md_ja(d): return f"{d.month}月{d.day}日（{'月火水木金土日'[d.weekday()]}）"
def nw_ja(d): return f'<span style="white-space:nowrap">{md_ja(d)}</span>'   # 日期和曜日不拆行
PAGES.append({"path": "/tools/ja/toritsu-nyushi-2027/", "lang": "ja", "kind": "Article", "app": "countdown", "published": "2026-10-15",
  "title": "都立入試2027 カウントダウン・待ち受け（2月21日）", "crumb": "都立入試2027",
  "description": "令和9年度（2027年）の都立高校入試は、学力検査（第一次募集）が2月21日（日）、推薦入試が1月26日（火）・27日（水）。あと何日かを毎日更新でカウントダウンし、出願期間と合格発表日、iPhoneのロック画面に置く方法をまとめました。",
  "hub_title": "都立入試2027まであと何日？", "hub_desc": "学力検査（2月21日）と推薦入試（1月26日・27日）までのカウントダウン、出願期間と合格発表日。",
  "more": [
    ("都立高校の推薦入試まであと何日ですか？", f"推薦に基づく選抜の検査日は{fmt(TR_S1, 'ja')}・{md_ja(TR_S2)}です。{TODAY.year}年{TODAY.month}月{TODAY.day}日の時点で{days_to(TR_S1)}日です。"),
    ("都立入試の合格発表はいつですか？", f"推薦に基づく選抜は{fmt(TR_S_RES, 'ja')}、学力検査に基づく選抜（第一次募集）は{fmt(TR_RES, 'ja')}です。"),
    ("都立入試まであと1か月になるのはいつですか？", f"1か月前は{fmt(dt.date(2027, 1, 21), 'ja')}、30日前は{fmt(TR1 - dt.timedelta(days=30), 'ja')}です。"),
  ],
  "js": [COUNT_JS], "faq": [
    ("都立入試2027の学力検査はいつですか？", f"学力検査に基づく選抜（第一次募集）の学力検査は{fmt(TR1, 'ja')}です。出願は{fmt(TR_APP1, 'ja')}から{md_ja(TR_APP2)}まで、合格発表は{fmt(TR_RES, 'ja')}です（東京都教育委員会「令和9年度東京都立高等学校入学者選抜実施要綱・同細目について」）。"),
    ("都立高校の推薦入試はいつですか？", f"推薦に基づく選抜の検査日は{fmt(TR_S1, 'ja')}・{md_ja(TR_S2)}、合格発表は{fmt(TR_S_RES, 'ja')}です。出願は{fmt(TR_S_APP1, 'ja')}から{md_ja(TR_S_APP2)}までです。"),
    ("都立入試まであと何日ですか？", f"{TODAY.year}年{TODAY.month}月{TODAY.day}日の時点で{ja_left(days_to(TR1), '学力検査')}。このページのカウントダウンは、開いた日に合わせて再計算されます。"),
    ("都立入試の100日前はいつですか？", f"学力検査の100日前は{fmt(TR1 - dt.timedelta(days=100), 'ja')}です。50日前は{fmt(TR1 - dt.timedelta(days=50), 'ja')}、1週間前は{fmt(TR1 - dt.timedelta(days=7), 'ja')}です。"),
    ("インフルエンザなどで学力検査を受けられなかったときは？", f"インフルエンザ等追検査は第二次募集と同じ日程で、出願は{md_ja(TR2_APP)}、検査は{md_ja(TR2)}、合格発表は{md_ja(TR2_RES)}です。追検査の対象や手続きは、東京都教育委員会の実施要綱で確認してください。"),
    ("iPhone の待ち受け（ロック画面）に都立入試のカウントダウンを置くには？", "カウントダウン ウィジェット: 記念日で「都立入試」を2027年2月21日に作り、ロック画面を長押し →「カスタマイズ」→ ロック画面 → ウィジェットを追加 → Countdown、の順に進みます。ウィジェットはすべて無料です。"),
  ],
  "body": f"""<h1>都立入試2027まであと何日？</h1>
<p class="lede">令和9年度（2027年）の東京都立高校入試は、学力検査に基づく選抜（第一次募集）の学力検査が<strong>{fmt(TR1, "ja")}</strong>、推薦に基づく選抜の検査が<strong>{md_ja(TR_S1)}・{md_ja(TR_S2)}</strong>です。下のカウントダウンは毎日更新されます。</p>
{counter(TR1, "ja", "学力検査")}
<p>推薦入試の検査日、{md_ja(TR_S1)}まではあと {live(TR_S1, "ja")}です。</p>
<h2>日程（いずれも2027年）</h2>
<table><thead><tr><th>選抜</th><th>項目</th><th>日付</th></tr></thead><tbody>
<tr><th rowspan="3" style="min-width:7em">推薦に基づく選抜</th><td>出願</td><td>{nw_ja(TR_S_APP1)}～{nw_ja(TR_S_APP2)}</td></tr>
<tr><td>検査</td><td>{nw_ja(TR_S1)}・{nw_ja(TR_S2)}</td></tr>
<tr><td style="white-space:nowrap">合格発表</td><td>{nw_ja(TR_S_RES)}</td></tr>
<tr><th rowspan="3">学力検査に基づく選抜（第一次募集）</th><td>出願</td><td>{nw_ja(TR_APP1)}～{nw_ja(TR_APP2)}</td></tr>
<tr><td>学力検査</td><td>{nw_ja(TR1)}</td></tr>
<tr><td style="white-space:nowrap">合格発表</td><td>{nw_ja(TR_RES)}</td></tr>
<tr><th rowspan="3">第二次募集（インフルエンザ等追検査）</th><td>出願</td><td>{nw_ja(TR2_APP)}</td></tr>
<tr><td>検査</td><td>{nw_ja(TR2)}</td></tr>
<tr><td style="white-space:nowrap">合格発表</td><td>{nw_ja(TR2_RES)}</td></tr>
</tbody></table>
<p>推薦と第一次募集は、{TR_NET.year}年{md_ja(TR_NET)}から各選抜の願書受付期間の最終日までに、インターネット上の専用サイトに必要事項を入力します。そのほかの出願書類は、受付期間内に届くよう志望する都立高校に郵送します。</p>
<p class="meta">出典：<a href="{TOKYO_SRC}" rel="noopener">東京都教育委員会「令和９年度東京都立高等学校入学者選抜実施要綱・同細目について」</a>（2026年9月17日更新、{TOKYO_CHECKED.year}年{TOKYO_CHECKED.month}月{TOKYO_CHECKED.day}日に確認）。分割募集やチャレンジスクールなどの日程、出願の細かな手続きは、同ページの実施要綱で確認してください。</p>
<h2>節目の日付</h2>
<table><thead><tr><th>節目</th><th>日付</th></tr></thead><tbody>{"".join(f"<tr><td>{k}</td><td>{fmt(TR1 - dt.timedelta(days=n), 'ja')}</td></tr>" for k, n in (("100日前", 100), ("50日前", 50), ("30日前", 30), ("1週間前", 7), ("前日", 1)))}</tbody></table>
<h2>ロック画面・待ち受けに置く</h2>
<p>毎回サイトを開かなくても残り日数が見えるように、iPhone のロック画面やホーム画面にウィジェットとして置けます。<a href="/countdown/ja/">カウントダウン ウィジェット: 記念日</a>なら、すべてのサイズのウィジェットが無料です。100日前・1週間前・当日の朝といった節目に達すると、アプリが全画面の数字で開き、共有できるカードを用意します。</p>
<ol><li>アプリで「イベントを追加」（すでにイベントがある場合は「＋」）をタップし、「都立入試」と入力します。</li><li>日付を{fmt(TR1, "ja")}に設定します。推薦入試を受ける人は、{md_ja(TR_S1)}のイベントも作っておくと便利です。</li><li>ロック画面を長押し →「カスタマイズ」→ ロック画面 → ウィジェットを追加 → Countdown。ホーム画面なら、長押し →「編集」→「ウィジェットを追加」です（iOS 17 では長押しして左上の「＋」）。</li></ol>
<h2>カウントダウンの使い方</h2>
<ul><li>イベントの裏面に、教科ごとの目標や模試の結果を書いておく。</li><li>推薦入試、学力検査、合格発表、私立高校の入試日を別々のイベントにして、「次の予定リスト」のウィジェットで並べる。</li><li>過ぎた日は削除されず、振り返れるタイムラインとして残ります。</li></ul>
<p>ほかの日付は<a href="/tools/ja/ato-nannichi/">あと何日？（日数計算）</a>で数えられます。ロック画面に置く手順は<a href="/tools/ja/countdown-machiuke-iphone/">カウントダウンを待ち受けにする方法（iPhone）</a>にくわしくまとめました。大学入学共通テストのカウントダウンは<a href="/tools/ja/kyotsu-test-2027/">共通テスト2027まであと何日？</a>へ。</p>"""})

# 7e. 日本：カウントダウンを待ち受けにする方法（ja，Countdown）——10-10
# 依据：GSC 10-06 前「共通テストカウントダウン 待ち受け」16 次曝光排名 8.8、「…待ち受け iphone」排名 13；
# Google JP 联想词「カウントダウン 待ち受け iphone / アプリ / にする方法 / android」「受験 カウントダウン ロック画面」。
# app 说法只用 ja 商店 1.4.16 描述：ウィジェットは全サイズ無料（ホーム画面・ロック画面）、イベント無制限；ロック画面のライブアクティビティは Pro。
PAGES.append({"path": "/tools/ja/countdown-machiuke-iphone/", "iphone_only": True, "lang": "ja", "kind": "Article", "app": "countdown", "published": "2026-10-10",
  "title": "カウントダウンを待ち受け（ロック画面）にする方法｜iPhone", "crumb": "待ち受けにカウントダウン",
  "description": "iPhoneの待ち受け（ロック画面）やホーム画面に「あと何日」を表示する手順です。数字入りの壁紙画像と違い、ウィジェットなら日付を一度入れるだけで数字が毎日自動で減ります。",
  "hub_title": "カウントダウンを待ち受けにする方法（iPhone）", "hub_desc": "ロック画面とホーム画面に「あと何日」を出す手順。受験・ライブ・記念日に。",
  "js": [COUNT_JS], "faq": [
    ("待ち受け（ロック画面）のカウントダウンは無料で使えますか？", "はい。カウントダウン ウィジェット: 記念日 のウィジェットは、ロック画面用もホーム画面用もすべてのサイズが無料です。イベントの数にも上限はありません。"),
    ("壁紙そのものに数字を入れることはできますか？", "壁紙は画像なので、入れた数字はその日のまま変わりません。毎日変わる「あと何日」を待ち受けに出したいときは、ロック画面のウィジェットを使います。"),
    ("受験までのカウントダウンにも使えますか？", "使えます。大学入学共通テスト2027なら、イベントの日付を2027年1月16日にします。残りの日数は、このサイトの共通テスト2027のカウントダウンでも毎日確認できます。"),
    ("ライブアクティビティとは違いますか？", "違います。ロック画面のウィジェットは無料で、時計の下に表示されます。ロック画面のライブアクティビティは Countdown Pro の機能です。"),
    ("Android でも使えますか？", "このアプリは iPhone・iPad 用です。Android では、ホーム画面ウィジェットに対応したカウントダウンアプリを Google Play で探してください。"),
  ],
  "body": f"""<h1>カウントダウンを待ち受けにする方法（iPhone）</h1>
<p class="lede">受験日やライブ、記念日までの「あと何日」を、iPhone の待ち受け（ロック画面）に出しておく方法です。数字を書き込んだ壁紙画像は毎日作り直すことになりますが、ウィジェットなら日付を一度入れるだけで、数字が毎日自動で減っていきます。</p>
{top_cta("countdown", "ja")}
<h2>壁紙画像とウィジェットの違い</h2>
<table><thead><tr><th></th><th>数字入りの壁紙画像</th><th>ウィジェット</th></tr></thead><tbody>
<tr><th>数字</th><td>作った日のまま</td><td>毎日自動で変わる</td></tr>
<tr><th>手間</th><td>毎日作り直す</td><td>日付を一度入れるだけ</td></tr>
<tr><th style="white-space:nowrap">場所</th><td>ロック画面・ホーム画面の背景</td><td>ロック画面の時計の下、ホーム画面</td></tr>
</tbody></table>
<h2>ロック画面に置く手順</h2>
<ol><li>App Store で<a href="/countdown/ja/">カウントダウン ウィジェット: 記念日</a>を入れ、「イベントを追加」（すでにイベントがある場合は「＋」）をタップしてイベント名（例：共通テスト）と日付を入れます。</li><li>ロック画面を長押しして「カスタマイズ」をタップし、ロック画面を選びます。</li><li>「ウィジェットを追加」から Countdown を選び、置きたいウィジェットをタップします。</li><li>右上の「完了」をタップします。</li></ol>
<p>ウィジェットはすべてのサイズが無料で、イベントはいくつでも作れます。</p>
<h2>ホーム画面に置く手順</h2>
<ol><li>ホーム画面を長押しします。</li><li>左上の「編集」→「ウィジェットを追加」をタップします（iOS 17 では左上の「＋」）。</li><li>Countdown を選び、サイズを決めて「ウィジェットを追加」をタップします。</li></ol>
<h2>よくカウントダウンされる日</h2>
<div class="pop">
<a href="/tools/ja/kyotsu-test-2027/" data-date="{KT1.isoformat()}"><b data-n>{days_to(KT1)}</b><span><span data-unit>日</span>（共通テスト2027まで）</span></a>
<a href="/tools/ja/toritsu-nyushi-2027/" data-date="{TR1.isoformat()}"><b data-n>{days_to(TR1)}</b><span><span data-unit>日</span>（都立入試2027まで）</span></a>
<a href="/tools/ja/ato-nannichi/?date={XMAS.isoformat()}&amp;name=%E3%82%AF%E3%83%AA%E3%82%B9%E3%83%9E%E3%82%B9" data-date="{XMAS.isoformat()}"><b data-n>{days_to(XMAS)}</b><span><span data-unit>日</span>（クリスマスまで）</span></a>
</div>
<p>ほかの日付は<a href="/tools/ja/ato-nannichi/">あと何日？（日数計算）</a>で数えられます。</p>
<h2>節目を迎えたとき</h2>
<p>カウントダウンが100日、1週間、当日の朝といった節目を迎えると、アプリが数字を全画面で表示し、共有できるカードを用意します。</p>"""})

# 7f. 韩国：아이폰 디데이 위젯 설정 방법（ko，Countdown）——10-15
# 依据：Google KR 联想词「디데이 위젯 아이폰 / 잠금 화면 / 추천 / 설정」「수능 디데이 2027」；ja / zh-Hant / pt-BR 同主题教程页上线后
# 有搜索点击和商店点击（Vercel 10-10~15：待ち受け页 3 次 ~out）。
# 수능：교육부 2024-08-16 발표、평가원 2026-03-31 시행 기본계획——2026-11-19(목) 시행、12-11(금) 성적 통지。설날 = 农历初一 2027-02-06（同 CNY）。
# app 说法只用 ko 商店 1.4.18 描述：모든 위젯 무료（홈 화면과 잠금 화면의 모든 크기）、이벤트 개수 무제한、세어 올라가기；잠금 화면 실시간 현황은 Pro。
# 小组件列表里 app 名是 Countdown（ko.lproj 的 CFBundleDisplayName）。
SUNEUNG, SUNEUNG_SCORE = dt.date(2026, 11, 19), dt.date(2026, 12, 11)
KO_DAYS = [("2027학년도 수능", SUNEUNG), ("크리스마스", XMAS), ("2027년 새해", NYE), ("2027년 설날", CNY)]
PAGES.append({"path": "/tools/ko/iphone-didei-wijet/", "iphone_only": True, "lang": "ko", "kind": "Article", "app": "countdown", "published": "2026-10-15",
  "title": "아이폰 디데이 위젯 설정 방법 (잠금 화면·홈 화면)", "crumb": "아이폰 디데이 위젯",
  "description": "아이폰 잠금 화면과 홈 화면에 디데이를 띄우는 방법입니다. 숫자를 넣은 배경화면과 달리, 위젯은 날짜를 한 번만 입력하면 남은 날이 매일 자동으로 줄어듭니다.",
  "hub_title": "아이폰 디데이 위젯 설정 방법", "hub_desc": "잠금 화면과 홈 화면에 D-day를 띄우는 순서. 수능·전역·기념일에.",
  "more": [
    ("수능 D-30, D-7은 언제인가요?", f"D-30은 {fmt(SUNEUNG - dt.timedelta(days=30), 'ko')}, D-7은 {fmt(SUNEUNG - dt.timedelta(days=7), 'ko')}, D-1은 {fmt(SUNEUNG - dt.timedelta(days=1), 'ko')}입니다."),
    ("위젯 목록에 Countdown이 안 보여요.", "앱을 한 번 열어 이벤트를 하나 만든 뒤 다시 ‘위젯 추가’를 눌러 보세요. Countdown은 iOS 17 이상에서 쓸 수 있습니다."),
  ],
  "js": [COUNT_JS], "faq": [
    ("아이폰 디데이 위젯은 무료인가요?", "네. ‘카운트다운 위젯: 디데이’ 앱의 위젯은 잠금 화면용과 홈 화면용 모두 모든 크기가 무료이고, 이벤트 개수에도 제한이 없습니다."),
    ("배경화면에 디데이 숫자를 넣으면 안 되나요?", "배경화면은 이미지라서 넣은 숫자가 만든 날 그대로 멈춰 있습니다. 매일 바뀌는 디데이를 보려면 잠금 화면 위젯을 쓰세요."),
    ("수능 디데이는 며칠로 맞추면 되나요?", f"2027학년도 수능은 {fmt(SUNEUNG, 'ko')}입니다. 이벤트 날짜를 그날로 정하면 위젯이 매일 남은 날을 보여 줍니다. 성적 통지는 {fmt(SUNEUNG_SCORE, 'ko')}입니다(교육부 발표)."),
    ("지나간 날부터도 셀 수 있나요?", "네. 지나간 날짜를 넣으면 그날부터 며칠이 지났는지 세어 올라갑니다."),
    ("잠금 화면 실시간 현황과는 다른가요?", "다릅니다. 잠금 화면 위젯은 무료이고 시계 아래에 표시됩니다. 잠금 화면 실시간 현황은 Countdown Pro 기능입니다."),
    ("갤럭시(안드로이드)에서도 쓸 수 있나요?", "이 앱은 iPhone·iPad 전용입니다. 갤럭시에서는 Google Play에서 홈 화면 위젯을 지원하는 디데이 앱을 찾아보세요."),
  ],
  "body": f"""<h1>아이폰 디데이 위젯 설정 방법</h1>
<p class="lede">수능, 전역, 기념일까지 남은 날을 아이폰 잠금 화면에 띄워 두는 방법입니다. 숫자를 써 넣은 배경화면은 매일 새로 만들어야 하지만, 위젯은 날짜를 한 번만 넣으면 남은 날이 매일 자동으로 줄어듭니다.</p>
{top_cta("countdown", "ko")}
<h2>배경화면과 위젯의 차이</h2>
<table><thead><tr><th></th><th>숫자를 넣은 배경화면</th><th>위젯</th></tr></thead><tbody>
<tr><th>숫자</th><td>만든 날 그대로</td><td>매일 자동으로 바뀜</td></tr>
<tr><th>번거로움</th><td>매일 새로 만들기</td><td>날짜를 한 번만 입력</td></tr>
<tr><th style="white-space:nowrap">위치</th><td>잠금 화면·홈 화면 배경</td><td>잠금 화면 시계 아래, 홈 화면</td></tr>
</tbody></table>
<h2>잠금 화면에 두는 방법</h2>
<ol><li>App Store에서 <a href="/countdown/ko/">카운트다운 위젯: 디데이</a>를 설치하고, ‘이벤트 추가’(이미 이벤트가 있으면 ‘+’)를 눌러 이벤트 이름(예: 수능)과 날짜를 입력합니다.</li><li>잠금 화면을 길게 누른 뒤 ‘사용자화’를 누르고 잠금 화면을 고릅니다.</li><li>‘위젯 추가’에서 Countdown을 고르고, 넣고 싶은 위젯을 누릅니다.</li><li>오른쪽 위의 ‘완료’를 누릅니다.</li></ol>
<p>위젯은 모든 크기가 무료이고, 이벤트는 몇 개든 만들 수 있습니다.</p>
<h2>홈 화면에 두는 방법</h2>
<ol><li>홈 화면의 빈 곳을 길게 누릅니다.</li><li>왼쪽 위의 ‘편집’ → ‘위젯 추가’를 누릅니다(iOS 17에서는 왼쪽 위의 ‘+’).</li><li>Countdown을 고르고 크기를 정한 뒤 ‘위젯 추가’를 누릅니다.</li></ol>
<h2>많이 찾는 디데이</h2>
<table><thead><tr><th>날</th><th>날짜</th><th>남은 날</th></tr></thead><tbody>{"".join(f"<tr><td>{k}</td><td>{fmt(d, 'ko')}</td><td>{live(d, 'ko')}</td></tr>" for k, d in KO_DAYS)}</tbody></table>
<p class="meta">남은 날은 {TODAY.year}년 {TODAY.month}월 {TODAY.day}일 기준으로 계산했고, 페이지를 열 때 다시 계산됩니다. 수능 날짜는 교육부 발표 기준입니다.</p>
<h2>이정표에 닿았을 때</h2>
<p>디데이가 100일, 일주일, 당일 아침 같은 이정표에 닿으면 앱이 숫자를 전체 화면으로 보여 주고, 공유할 만한 카드를 만들어 줍니다. 지나간 날도 지워지지 않고 되돌아볼 수 있는 타임라인으로 남습니다.</p>
<p>여행을 준비하고 있다면 <a href="/tools/ko/yeohaeng-iljeong-aep/">여행 일정 앱 추천</a>도 참고하세요.</p>"""})


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

# 9. 打包清单（10-26 已搬到 beforegotech.com，本站不再生成，见 BG_MOVED）
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
<label>Length<select name="days"><option value="3">Weekend (3 days)</option><option value="7" selected>One week</option><option value="14">Two weeks</option></select></label><button type="submit" data-track-id="pack-submit">Make my list</button></form>
<div class="inv-wrap"><p class="print-title">Packing list</p><div id="pack-out" hidden></div></div>
<p id="pack-actions" hidden><button class="btn ghost" id="pack-print" type="button">Print</button> <button class="btn ghost" id="pack-copy" type="button">Copy as text</button></p>
<script type="application/json" id="pack-data">{json.dumps(PACK)}</script>
<h2>The three-day rule</h2>
<p>Documents and bookings a week before. Clothes and toiletries three days before, so there is time to buy what's missing. The night before, only the six things that cannot be replaced at the destination: passport, tickets, wallet, phone, charger, keys.</p>
<h2>What people forget</h2>
<ul><li>The <strong>power adapter</strong> for the destination's sockets — the plug type matters more than the voltage.</li><li><strong>Medication</strong> for the whole trip plus a couple of days.</li><li>A <strong>photo of the passport</strong> on the phone.</li><li><strong>Sunscreen</strong> — pricey at resorts, hard to find in cities.</li><li>The thing you forgot last time. That is the one to write down now.</li></ul>
<p>For a list built for your actual destination and dates — plugs, currency, entry rules, transit apps, and reminders before departure — that is what <a href="/beforego/">BeforeGo</a> does on iPhone, and it carries the forgotten items over to the next trip.</p>
<p>Packing for a particular trip? There is a <a href="/tools/japan-travel-checklist/">Japan travel checklist</a> and a <a href="/tools/disney-world-packing-list/">Disney World packing list</a>.</p>"""})


# 10. 榜单：iPhone 倒数日 app（含竞品；数据来自 09-26 美区 App Store 查询，只写商店描述里写明的事）
BEST = [
  {"name": "Countdown Widget: Any Event", "by": "go ka (that's us)", "id": 6799846628, "rating": (4.8, 13), "since": 2026, "ours": True,
   "free": "Unlimited events, every widget size on Home Screen and Lock Screen, reminders, repeats, iCloud sync — all free. Pro adds the Pro backdrops, your own photos, typefaces, the Live Activity and counting down with someone you invite.",
   "widgets": "Home Screen + Lock Screen, all sizes, free", "recur": "Yearly, monthly, weekly, every N days", "sync": "iCloud, no account", "ads": "None",
   "take": "Here the widgets are not the paid feature: every widget size, unlimited events, recurring dates, reminders and iCloud sync are free; the subscription adds the Pro backdrops, your own photos behind a countdown, the Pro typefaces, the Lock Screen Live Activity and inviting someone to count down with you. It also keeps a daily on-device snapshot so an update or reinstall never loses the events. New in 2026, so it has few ratings yet — judge it by what the free tier covers."},
  {"name": "Countdown Star", "by": "Joseph Merrill", "id": 576177593, "rating": (4.8, 216173), "since": 2012,
   "free": "Free version with ads and an optional Remove Ads purchase (there is also a paid ad-free version); add as many events as you like, with iCloud sync, repeating events and Home Screen widgets listed as features.",
   "widgets": "Home Screen (small, medium, large) + Apple Watch", "recur": "Annual events advance automatically", "sync": "iCloud across iPhone, iPad, Apple Watch", "ads": "In the free version",
   "take": "The veteran: on the App Store since 2012 with over 200,000 ratings. Strong on the countdown itself — time-zone support, a slider that flips between seconds and years, celebration animations at zero, and an Apple Watch app. The listing does not describe Lock Screen widgets."},
  {"name": "Countdown", "by": "Find Appiness LLC", "id": 1403367428, "rating": (4.8, 188720), "since": 2018,
   "free": "Unlimited events, count-up, iCloud sync and reminders 1 day / 1 week before. Home Screen widget, Lock Screen widget, StandBy and calendar auto-import are Premium.",
   "widgets": "Home Screen, Lock Screen, StandBy — Premium", "recur": "Yearly, monthly, weekly, daily", "sync": "iCloud", "ads": "Not stated",
   "take": "Very popular and easy to use, with sharing and a StandBy widget. The catch for widget fans: the listing marks the Home Screen widget, the Lock Screen widget and calendar auto-import as Premium features, so the free version is mostly the in-app list."},
  {"name": "Countdown: Event Countdown", "by": "ROOT38 LIMITED", "id": 983258067, "rating": (4.7, 23889), "since": 2015,
   "free": "Unlimited countdowns, counting up or down, and a Next Event Home Screen widget are free; the ticking, multi-event, Lock Screen and StandBy widgets, repeats and sync are Premium.",
   "widgets": "Next Event widget free; live, multi-event, Lock Screen, StandBy paid", "recur": "Premium (shows ages on birthdays)", "sync": "Premium, across Apple devices", "ads": "Ad-free is Premium",
   "take": "The prettiest calendar view of the group: every event on a month grid, color-coded, with Live Activities in the Dynamic Island as the moment approaches and countdowns you can export as a video — the listing puts the calendar view and Live Activities under Premium. Unlimited events are free; most widget sizes are not."},
  {"name": "DayCount", "by": "Zaminiti Pty Ltd", "id": 1121088244, "rating": (4.7, 26263), "since": 2016,
   "free": "Event counters, categories, notes, streaks; reminders before or after events; widgets with custom fonts and textures (the listing does not state a free limit).",
   "widgets": "Home Screen + Lock Screen, custom filters and textures", "recur": "Daily, weekly, fortnightly, monthly, yearly, custom", "sync": "Backup and sync across iPhone, iPad and Mac", "ads": "Not stated",
   "take": "For people who count in both directions: counters track time before and after the date, streaks sit next to events, and reminders can fire minutes to years before or after. Widgets are unusually configurable — filters, fonts, textures, borders — on both Home and Lock Screen, and events can be imported from your calendar."},
  {"name": "Countdown Buddy", "by": "Taptics Ltd.", "id": 1534850579, "rating": (4.6, 26138), "since": 2020,
   "free": "One countdown widget with the basic design; 11 widget styles and more widgets are paid.",
   "widgets": "Home Screen + Lock Screen, small and medium, 11 styles", "recur": "Not stated; weekend exclusion for deadlines", "sync": "Not stated", "ads": "Not stated",
   "take": "A widget designer more than an event list: you build a countdown or count-up widget from 11 styles and drop it on the Home or Lock Screen, and work deadlines can skip weekends. The free version is one basic widget, so it is best if you only ever need one countdown."},
  {"name": "Days • Countdown & Widgets", "by": "MD Apps LTD", "id": 939368917, "rating": (4.8, 12658), "since": 2015,
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
<p class="lede">Seven countdown apps that put a widget on your Home Screen or Lock Screen, compared on the things that actually differ: what the free tier includes, which widgets cost money, repeats, reminders and sync. Data comes from each app's US App Store listing, first read on September 26, 2026 and checked again on October 16, 2026. One of the seven is ours; it is marked, and it is judged by the same table as the rest.</p>
<h2>The comparison</h2>
<table class="cmp"><thead><tr><th>App</th><th>Free tier</th><th>Widgets</th><th>Repeats</th><th>Sync</th><th>US rating</th></tr></thead><tbody>{rows}</tbody></table>
<p class="meta">"Not stated" means the App Store description does not say. Ratings are the US storefront on October 16, 2026 and change daily.</p>
<h2>Which one to pick</h2>
<ul>
<li><strong>You want widgets without paying:</strong> Countdown Widget: Any Event (ours) — every widget size is free, and so are unlimited events, repeats, reminders and iCloud sync. Countdown: Event Countdown gives you one free Next Event widget.</li>
<li><strong>You want the longest track record:</strong> Countdown Star — on the App Store since 2012, with over 200,000 ratings, with an Apple Watch app and time zones per event.</li>
<li><strong>You count streaks and time since:</strong> DayCount — counters run before and after the date, with reminders on either side.</li>
<li><strong>You want the prettiest calendar:</strong> Countdown: Event Countdown — month grid, Live Activities, countdown videos (the calendar view and Live Activities are Premium).</li>
<li><strong>You only need one widget and want to design it:</strong> Countdown Buddy — 11 widget styles, one free.</li>
<li><strong>You want full-screen photos:</strong> Days • Countdown & Widgets.</li>
</ul>
<p>If you go with ours, the Home Screen and Lock Screen steps are in <a href="/blog/countdown-widget-iphone-home-lock-screen/">how to put a countdown on your iPhone Lock Screen</a>, and the <a href="/tools/christmas-countdown-widget-iphone/">Christmas countdown widget guide</a> covers a holiday setup.</p>
<h2>The seven apps</h2>
{entries}
<h2>How we chose</h2>
<p>We searched the US App Store for "countdown widget", "days until countdown" and "countdown app", took the countdown-specific apps with the most ratings, and read each listing for what it says about the free tier, widgets, repeats, reminders and sync. Apps that are general widget makers (Widgetsmith) or visual timers for kids were left out. We did not test paid tiers, and we did not rank by rating — the list is grouped by what each app is best at. We make one of these apps; it is included because it is a countdown widget app for iPhone, and it is described with the same fields as everyone else.</p>"""
    return {"path": "/tools/best-countdown-widget-apps-iphone/", "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-09-26",
            "title": "Best Countdown Widget Apps for iPhone (2026): Which Ones Are Free", "crumb": "Best countdown widget apps",
            "description": "Seven iPhone countdown widget apps compared on what is free, which widgets cost money, repeats and sync — from their US App Store listings, October 2026.",
            "hub_title": "Best countdown widget apps for iPhone (2026)", "hub_desc": "Seven apps compared on free tier, widgets, repeats, reminders and sync.",
            "items": [{"name": b["name"], "url": ("https://apps.apple.com/us/app/id%d" % b["id"])} for b in BEST],
            "faq": [
              ("Which countdown app has free Lock Screen widgets on iPhone?", "Countdown Widget: Any Event (ours) makes every widget size free, on both the Home Screen and the Lock Screen. In Countdown by Find Appiness and Countdown: Event Countdown, the Lock Screen widget is part of the paid tier according to their listings; DayCount and Days list Lock Screen widgets without stating a limit."),
              ("Which countdown apps allow unlimited events for free?", "Countdown Widget: Any Event, Countdown Star ('add as many events as you like'), Countdown by Find Appiness ('create as many events as you'd like') and Countdown: Event Countdown ('unlimited countdowns') all state unlimited events in their free version."),
              ("Do these apps sync between iPhone and iPad?", "Countdown Widget: Any Event, Countdown Star and Countdown by Find Appiness list iCloud sync, and DayCount lists backup and sync across iPhone, iPad and Mac. Countdown: Event Countdown lists sync across Apple devices as a Premium feature. Countdown Buddy and Days do not state it."),
              ("Can I count up from a past date?", "Yes in Countdown Widget: Any Event, Countdown Star, Countdown by Find Appiness, Countdown: Event Countdown, DayCount, Countdown Buddy and Days — all list count-up from a past date."),
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
<p class="meta">“Não informado” quer dizer que a descrição na App Store não diz. As avaliações são da App Store do Brasil em 29/09/2026 e mudam todo dia.</p>
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
<p>Pesquisamos na App Store do Brasil “contagem regressiva” e “countdown widget”, ficamos com os apps feitos para contagem com mais avaliações no Brasil e lemos a descrição de cada um em português para ver o que ela diz sobre a versão grátis, os widgets, a repetição, a sincronização e os anúncios. Criadores de widget em geral (como o Widgetsmith) ficaram de fora. Não testamos as versões pagas e não ordenamos por nota: o nosso vem primeiro porque somos nós que fazemos a lista, e os outros seguem pelo número de avaliações no Brasil. Nós fazemos um desses apps; ele entra porque é um app de contagem regressiva com widget para iPhone e é descrito com os mesmos campos que os outros. A <a href="/tools/best-countdown-widget-apps-iphone/" hreflang="en">versão em inglês desta lista</a> usa a App Store dos Estados Unidos, por isso os apps não são os mesmos.</p>"""
    return {"path": "/tools/pt-br/melhores-apps-contagem-regressiva/", "lang": "pt-BR", "kind": "Article", "app": "countdown", "published": "2026-09-29",
            "title": "Melhores apps de contagem regressiva para iPhone (2026) com widget", "crumb": "Melhores apps",
            "description": "Sete apps de contagem regressiva para iPhone comparados: o que é grátis, quais widgets são pagos, repetição e anúncios. Dados da App Store Brasil, set. 2026.",
            "hub_title": "Melhores apps de contagem regressiva para iPhone (2026)", "hub_desc": "Sete apps comparados: versão grátis, widgets, repetição, sincronização e anúncios.",
            "items": [{"name": b["name"], "url": ("https://apps.apple.com/br/app/id%d" % b["id"])} for b in BEST_PT],
            "faq": [
              ("Qual app de contagem regressiva tem widget grátis na tela bloqueada?", "O Countdown: Contagem regressiva (o nosso) deixa todos os tamanhos de widget grátis, na Tela de Início e na Tela Bloqueada. No Contagem Regressiva ◎, o widget da tela bloqueada é recurso Premium, segundo a descrição; os outros da lista não dizem se o widget da tela bloqueada é grátis."),
              ("Quais apps deixam criar eventos ilimitados de graça?", "Pela descrição na App Store do Brasil: o Countdown: Contagem regressiva (“eventos ilimitados”), o Contagens (“um número ilimitado de timers” na versão gratuita) e o Contagem Regressiva ◎ (“crie quantos eventos quiser”, sem marcar como Premium). O Countdown Star diz “adicione quantos eventos quiser”, sem separar o que é grátis e o que é pago. Os outros não dizem."),
              ("Qual é o melhor app para contar os dias de namoro?", "O Widget Casal é feito para isso: dias juntos, diário do casal e lembretes de 10 e 100 dias. O Countdown: Contagem regressiva também conta a partir de uma data e guarda texto, fotos e voz no verso do evento."),
              ("Algum desses apps tem anúncios?", "O Countdown Star tem anúncios na versão grátis, com uma compra para removê-los. O Countdown: Contagem regressiva não tem anúncios. Os outros não dizem na descrição."),
              ("Esta lista é independente?", "Não: nós fazemos o Countdown: Contagem regressiva. Tudo na tabela vem das páginas públicas na App Store do Brasil, os campos são os mesmos para todos os apps e cada concorrente tem link para você conferir. Não testamos as versões pagas."),
            ], "js": [], "body": body}
_ci = next(i for i, p in enumerate(PAGES) if p["path"] == "/tools/pt-br/contador-de-dias-de-namoro/")
PAGES.insert(_ci + 1, best_page_pt())   # 常青页一组：计算器 → 场景页 → 榜单 → 节日页

# 10c. BeforeGo「行程规划 App 推荐」三语榜单（zh-Hant / ja / ko；10-26 繁中、日语两版已搬到 beforegotech.com，只剩韩语，见 BG_MOVED）——10-12
# 依据：10-12 Google 联想词「行程規劃 app 推薦 / dcard / ptt / 日本 / ai」「旅行 計画 アプリ おすすめ / 無料 / 海外 / 共有」
# 「여행 계획 앱 추천」「여행 일정 앱 추천 / 디시」「트리플 종료 / 트리플 앱 종료 / 트리플 대체 어플」。
# 选法同 Countdown 榜单：各国商店搜「行程規劃」「旅行 計画」「여행 계획」，去掉订房订票平台、行事历、地图，留下专门排行程的 app，
# 只写各自本地商店描述（iTunes lookup，10-12）里写明的事；没写的格子写「说明没写」。我们的 app 说法只用 tools/store/beforego.json 对应语言。
# 트리플：其韩国商店描述写「11월 3일 서비스 종료, NOL로 통합；기존 일정 그대로 불러오고」——只引用它自己的说法。
LISTED_ON = dt.date(2026, 10, 12)
BG_L10N = {
    "zh-Hant": {"ours": "（我們的）", "none": "尚無評分", "see": "在 App Store 查看", "our_page": "我們的產品頁", "unit": " 則評分", "page": "/beforego/zh-hant/", "cc": "tw"},
    "ja": {"ours": "（自社）", "none": "評価なし", "see": "App Store で見る", "our_page": "製品ページ", "unit": "件", "page": "/beforego/ja/", "cc": "jp"},
    "ko": {"ours": " (우리 앱)", "none": "평점 없음", "see": "App Store에서 보기", "our_page": "제품 페이지", "unit": "개", "page": "/beforego/ko/", "cc": "kr"},
}
def bg_rate(b, L):
    return f"★ {b['rating'][0]:.1f} · {format(b['rating'][1], ',')}{L['unit']}" if b.get("rating") else L["none"]   # 日韩写成「数字+单位」，繁中单位自带前导空格
def bg_list_page(spec):
    lang = spec["lang"]; L = BG_L10N[lang]; apps = spec["apps"]
    link = lambda b: L["page"] if b.get("ours") else f"https://apps.apple.com/{L['cc']}/app/id{b['id']}"
    rows = "".join(f"<tr><th>{esc(b['name'])}{esc(L['ours']) if b.get('ours') else ''}</th>" + "".join(f"<td>{esc(c)}</td>" for c in b["t"]) + f"<td>{esc(bg_rate(b, L))}</td></tr>" for b in apps)
    entries = "".join(f"""<h3>{i}. {esc(b['name'])} <span style="font-weight:400;color:var(--soft)">— {esc(b['by'])}</span></h3>
<p>{esc(b['take'])}</p>
<p><a href="{link(b)}"{'' if b.get('ours') else ' rel="nofollow noopener"'}>{esc(L['our_page'] if b.get('ours') else L['see'])} →</a></p>""" for i, b in enumerate(apps, 1))
    head = "".join(f"<th>{esc(h)}</th>" for h in spec["cols"])
    body = f"""<h1>{esc(spec['h1'])}</h1>
<p class="lede">{spec['lede']}</p>
{spec.get('pre', '')}<h2>{esc(spec['h_cmp'])}</h2>
<table class="cmp"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>
<p class="meta">{spec['note']}</p>
<h2>{esc(spec['h_pick'])}</h2>
<ul>{''.join(f'<li>{x}</li>' for x in spec['pick'])}</ul>
<h2>{esc(spec['h_apps'])}</h2>
{entries}
<h2>{esc(spec['h_method'])}</h2>
<p>{spec['method']}</p>"""
    return {"path": spec["path"], "lang": lang, "kind": "Article", "app": "beforego", "published": "2026-10-12",
            "title": spec["title"], "crumb": spec["crumb"], "description": spec["description"],
            "hub_title": spec["hub_title"], "hub_desc": spec["hub_desc"], "more": spec.get("more", []),
            "items": [{"name": b["name"], "url": f"https://apps.apple.com/{L['cc']}/app/id{b['id']}"} for b in apps],
            "faq": spec["faq"], "js": [], "body": body}

PAGES.append(bg_list_page({
  "lang": "zh-Hant", "path": "/tools/zh-hant/xing-cheng-gui-hua-app/",
  "title": "行程規劃 App 推薦 2026：7 款 iPhone 旅遊行程 App 比較", "crumb": "行程規劃 App 推薦",
  "description": "7 款 iPhone 行程規劃 App 比較：行程怎麼排、能不能共同編輯、離線、行前清單。資料取自台灣 App Store 頁面（2026 年 10 月 12 日）。",
  "hub_title": "行程規劃 App 推薦（2026）", "hub_desc": "7 款旅遊行程 App 比較：怎麼排行程、共同編輯、離線與行前清單。",
  "h1": "行程規劃 App 推薦（2026）",
  "lede": "7 款能在 iPhone 上排旅遊行程的 App，比較真正有差的地方：行程怎麼排出來、能不能和旅伴共同編輯、沒網路能不能看、有沒有行前清單。資料來自各 App 在台灣 App Store 的頁面（2026 年 10 月 12 日）。其中一款是我們做的，已標出，並用同樣的欄位描述。",
  "h_cmp": "比較表", "h_pick": "怎麼選", "h_apps": "7 款 App", "h_method": "我們怎麼選",
  "cols": ["App", "行程怎麼排", "共同編輯", "離線", "行前清單", "台灣評分"],
  "note": "「說明沒寫」表示 App Store 說明裡沒有提到，不代表一定沒有這個功能。評分是 2026 年 10 月 12 日台灣 App Store 的數字，每天都會變。",
  "apps": [
    {"name": "BeforeGo：AI行程規劃·行前清單", "by": "go ka", "id": 6786561175, "rating": None, "ours": True,
     "t": ("截圖攻略、貼連結或打字，整理成每天的行程", "說明沒寫", "說明沒寫", "依目的地自動生成，出發前 7 天到 3 小時提醒"),
     "take": "把看到的攻略直接變成行程：截圖一篇攻略、貼上連結，或隨手打幾句計畫，就整理成每天的行程，連同值得去的地方和出發前要辦的事；機票或訂單確認一掃就進行程。行李清單依目的地與日期自動生成（插座、貨幣、入境準備、交通 App），一天的行程會自動排成最短步行路線。免費開始、無廣告、無需帳號；Premium 可以訂閱，也可以一次買斷。"},
    {"name": "Funliday -全球旅遊行程規劃平台", "by": "Funliday Inc.", "id": 905768387, "rating": (4.48, 10517),
     "t": ("搜全球景點，拖拉排行程，自動規劃路徑", "可以", "可以（不含地圖）", "說明沒寫"),
     "take": "在台灣有一萬多則評分，也是旅遊社群：可以看別人的遊記，掃部落客文章裡的 Funliday QR Code 就能拿到對方排好的行程。景點不用自己填地址電話，拖拉就能排，路徑自動規劃；登入後行程存在雲端同步，離線也能看行程與景點資訊（不含地圖）。"},
    {"name": "去趣 chicTrip", "by": "HOTAI MOTOR CO., Ltd.", "id": 6443825385, "rating": (4.6, 5177),
     "t": ("加景點後 AI 一鍵排出順路路線，可複製他人行程", "可以", "說明沒寫", "有行李清單，另有共同記帳"),
     "take": "社群和工具都有：大量旅人上傳的公開行程可以直接複製，加入想去的景點後 AI 一鍵排序成最順的路線。多人共編、共同記帳、行李清單都在裡面，也能預訂台灣、日本等地的住宿與旅遊 eSIM，台灣和日本有叫車、租車、機場接送。"},
    {"name": "Japan Travel – 乘換案內與日本旅遊規劃", "by": "NAVITIME JAPAN CO.,LTD.", "id": 686373726, "rating": (4.81, 2101),
     "t": ("把收藏的日本景點排到時間軸，可參考編輯推薦行程", "說明沒寫（可分享行程）", "離線地點搜尋、離線查看路線紀錄", "說明沒寫"),
     "take": "專做日本：日本的電車、計程車、飛機、渡輪路線查詢和行程規劃在同一個 App，還能在離線時搜尋免費 Wi-Fi、換匯、ATM 和車站。從收藏的景點排出時間軸行程，也能參考編輯推薦行程。電車誤點時更新路線、語音導航等是付費功能。"},
    {"name": "Tripiday - 最佳旅行規劃App", "by": "Hsin Jung Huang", "id": 1450106361, "rating": (4.76, 481),
     "t": ("搜尋景點加入行程，依日期排序，可複製公開行程", "可以", "說明沒寫", "說明沒寫"),
     "take": "搜尋世界知名景點加進行程，依日期排好；可以邀請朋友一起規劃、複製別人公開的行程再自己改，預算支援多國幣別。"},
    {"name": "TripHugger - 旅遊規劃 | 行程討論分享", "by": "TripHugger Inc.", "id": 882313848, "rating": (4.5549, 337),
     "t": ("用 Google 地圖資料加景點，地圖與行程同一畫面拖拉", "可以，另有私密討論區", "可以，離線也能改", "說明沒寫"),
     "take": "適合一群人邊討論邊排：內建共同編輯器、Google 地圖和行程專屬的私密討論區，拖拉行程時地圖路線跟著變。看過的行程會存在手機裡，離線也能調整，連線後自動同步給所有旅伴。"},
    {"name": "Pathly 旅遊行程規劃・多人共同編輯分享與自由行工具", "by": "Mono Incorporated", "id": 6753792428, "rating": (4.96, 27),
     "t": ("跟 AI 說目的地與想做的事，AI 排時間與路線", "可以", "說明沒寫", "說明沒寫"),
     "take": "另一種 AI 做法：跟 AI 說「台南 3 天 2 夜，主攻古蹟和小吃」，時間分配和路線就排好，再和旅伴一起微調。旅途中一張地圖看景點順序與路線，回來後行程變成相簿。"},
  ],
  "pick": [
    "<strong>想把看到的攻略直接變成行程：</strong>BeforeGo（我們的），截圖、貼連結或打字就整理成每天的行程；Pathly 則是跟 AI 說目的地與天數。",
    "<strong>想和旅伴一起排：</strong>Funliday、去趣、Tripiday、TripHugger、Pathly 的說明都寫了共同編輯；TripHugger 還有行程專屬的討論區。",
    "<strong>想拿別人排好的行程來改：</strong>去趣與 Tripiday 可以複製公開行程，Funliday 可以掃部落客的 QR Code。",
    "<strong>只去日本：</strong>Japan Travel（NAVITIME），行程、乘換查詢與離線地點搜尋在同一個 App。",
    "<strong>在意出發前的準備：</strong>BeforeGo 依目的地自動生成行李清單並在出發前提醒；去趣有行李清單與共同記帳。",
  ],
  "method": "我們在台灣 App Store 搜尋「行程規劃」，排除訂房訂票平台、一般行事曆與地圖，留下專門排旅遊行程、在台灣評分較多的 App，再加上一款用 AI 排行程的新 App（Pathly），逐一讀它們的繁體中文說明，看說明怎麼寫行程的排法、共同編輯、離線與行前清單。我們沒有測試付費版，也不是按評分排名：我們的放第一，因為這份清單是我們做的，其餘依台灣評分數排列。Wanderlog 在台灣 App Store 的說明是英文，所以沒有放進來。",
  "more": [
    ("有用 AI 排行程的 App 嗎？", "有。BeforeGo 把截圖、連結或文字整理成每天的行程；Pathly 是跟 AI 說目的地與天數；去趣是加入景點後由 AI 一鍵排序路線。"),
    ("去日本用哪個行程規劃 App？", "只去日本的話，Japan Travel（NAVITIME）把行程、乘換查詢與離線地點搜尋放在一起。其他幾款也都能排日本行程。"),
  ],
  "faq": [
    ("哪個行程規劃 App 可以把截圖或貼文變成行程？", "BeforeGo 的說明寫：截圖一篇攻略、貼上連結或隨手打幾句計畫，就整理成每天的行程，機票或訂單確認一掃也會進行程。"),
    ("哪些 App 可以和朋友共同編輯行程？", "依台灣 App Store 的說明：Funliday、去趣、Tripiday、TripHugger、Pathly。"),
    ("出國沒網路能看行程嗎？", "Funliday（不含地圖）和 TripHugger 的說明寫了離線瀏覽；Japan Travel 可以離線搜尋地點、離線查看路線紀錄。其他 App 的說明沒寫。"),
    ("這些 App 要錢嗎？", "7 款都可以免費下載。說明裡寫了付費功能的有 Japan Travel（誤點更新路線、語音導航等）和 BeforeGo（Premium 訂閱或一次買斷）；其他 App 的說明沒寫付費內容。"),
    ("這份清單是中立的嗎？", "不是：BeforeGo 是我們做的。表格內容全部來自公開的 App Store 說明，欄位對每款都一樣，每款都附連結可以查證。"),
  ],
}))

PAGES.append(bg_list_page({
  "lang": "ja", "path": "/tools/ja/ryoko-keikaku-app/",
  "title": "旅行計画アプリおすすめ7選（2026）旅のしおり・共同編集", "crumb": "旅行計画アプリ",
  "description": "iPhoneの旅行計画アプリ7つを、プランの作り方・共同編集・オフライン・持ち物リスト・有料機能で比較。日本のApp Storeの掲載内容（2026年10月12日）から。",
  "hub_title": "旅行計画アプリおすすめ7選（2026）", "hub_desc": "旅のしおり・共同編集・オフライン・持ち物リストを比べました。",
  "h1": "旅行計画アプリおすすめ7選（2026）",
  "lede": "iPhoneで旅行の計画や旅のしおりを作れるアプリ7つを、実際に違いが出るところで比べました。プランの作り方、同行者との共同編集、オフラインで見られるか、持ち物リストの有無、説明に書かれた有料機能です。データは各アプリの日本のApp Storeのページ（2026年10月12日）から取りました。7つのうち1つは私たちのアプリで、同じ項目で書いています。",
  "h_cmp": "比較表", "h_pick": "選び方", "h_apps": "7つのアプリ", "h_method": "選び方の基準",
  "cols": ["アプリ", "プランの作り方", "共同編集", "オフライン", "持ち物リスト", "日本の評価"],
  "note": "「記載なし」は App Store の説明に書かれていないという意味で、その機能がないとは限りません。評価は2026年10月12日の日本の App Store の数字で、毎日変わります。",
  "apps": [
    {"name": "BeforeGo：AI旅行計画・旅行チェックリスト", "by": "go ka", "id": 6786561175, "rating": None, "ours": True,
     "t": ("旅の投稿のスクショ・リンク・テキストから日ごとのプランに", "記載なし", "記載なし", "行き先と日程から自動作成、出発7日前〜3時間前にリマインド"),
     "take": "旅の投稿をそのままプランに：スクショやリンク、打ち込んだ予定から、行きたい場所・出発前にやること・一日ごとの流れまでまとめます。航空券や予約確認はスキャンでプランへ。持ち物リストは行き先と日程から自動で作られ（プラグ、通貨、入国準備、交通アプリ）、1日の予定は最短ルートに並び替えます。無料で開始、広告なし、アカウント不要。プレミアムはサブスクのほか買い切りもあります。"},
    {"name": "-tabiori- 共有できる旅のしおり", "by": "Gotaru,Co.,Ltd.", "id": 1193502519, "rating": (4.51, 61153),
     "t": ("スケジュール・持ち物・位置情報・写真をまとめたしおり", "できる", "できる", "あり（共有の持ち物も）"),
     "take": "日本で6万件以上の評価がある旅のしおりアプリ。スケジュール、持ち物、位置情報、写真をリアルタイムで同期し、同行者を追加すれば共同編集できます。オフライン閲覧に対応し、しおりは提携コンビニで印刷も可能。月額のプレミアムでは広告除去や動画共有などが使えます。"},
    {"name": "旅のしおり", "by": "NORIHIKO HAYASAKA", "id": 976004299, "rating": (4.43, 18325),
     "t": ("スケジュール・持ち物・お土産リストを作る", "共有コードで送れる", "記載なし", "あり（初期リストを保存できる）"),
     "take": "シンプルに管理したい人向け。スケジュール（アラーム付き）、持ち物リスト、お土産リスト、メモを一冊のしおりにまとめ、共有コードで友達に送れます。プレミアムで広告削除としおり保存数の上限拡張。"},
    {"name": "ニコディ-旅のしおり作成・観光スポット検索・計画立て・マップ", "by": "ANY TRAVEL Inc.", "id": 1515379808, "rating": (4.55, 11852),
     "t": ("しおり作成と観光スポット検索、ホテル予約", "できる（LINEで招待、希望を一か所にまとめられる）", "記載なし", "記載なし"),
     "take": "旅行準備に特化したアプリ。ホテルスタッフが作った「ホテリエしおり」でローカルな穴場情報が読めます。広告非表示、海外旅行対応、経路時間計算、定休日アラートなどは月額会員（ニコディサポーターズ）向けの機能です。"},
    {"name": "ホリデー 国内・韓国旅行の計画やしおりを共同編集できる", "by": "Holiday Inc.", "id": 962231929, "rating": (4.56, 7170),
     "t": ("保存した「行きたい場所」を組み合わせて行程に", "できる", "記載なし", "記載なし"),
     "take": "Instagramやテレビで見つけた行きたい場所を保存しておき、組み合わせて旅行プランに。国内約1万エリアのおでかけ情報と韓国のスポットが探せて、友達を招待して共同編集で旅のしおりを作れます。韓国のテーマパークのチケット予約も。"},
    {"name": "旅のしおり作成・旅行計画 - NAVITIME Travel", "by": "NAVITIME JAPAN CO.,LTD.", "id": 1279724919, "rating": (4.38, 7126),
     "t": ("スポットを登録すると移動ルート・所要時間・交通費を自動計算", "プレミアム（1人の入会で最大10人）", "記載なし", "記載なし"),
     "take": "移動の計算をまかせたい人向け。行きたいスポットを登録するだけで、移動ルート・所要時間・交通費を自動計算してスケジュールを組みます。航空券・新幹線・ホテル・レンタカーの予約もアプリ内で。複数人での共同編集はプレミアムコースの機能です。"},
    {"name": "アバトラベル - 旅行計画・旅のしおり・AI旅行アプリ", "by": "AVA Intelligence, inc.", "id": 6470335943, "rating": (4.14, 207),
     "t": ("行き先やスポットをスワイプで選ぶとAIが旅程に", "できる（リアルタイム）", "記載なし", "あり（VISA・現地通貨などの準備情報も）"),
     "take": "AIと一緒に作るタイプ。気になる行き先やスポットをスワイプで選ぶと、移動時間をふまえた旅程にAIがまとめます。航空券・ホテル予約から、持ち物リスト、VISA、現地通貨などの出発前の準備情報までひとつに。"},
  ],
  "pick": [
    "<strong>旅の投稿をそのままプランにしたい：</strong>BeforeGo（自社）。スクショ・リンク・テキストから日ごとのプランに。",
    "<strong>みんなで旅のしおりを作りたい：</strong>tabiori（共同編集・オフライン・コンビニ印刷）、ホリデー（行きたい場所の保存と共同編集）。",
    "<strong>移動時間や交通費まで自動で：</strong>NAVITIME Travel（共同編集はプレミアム）。",
    "<strong>AIにおまかせしたい：</strong>アバトラベル（スワイプで選ぶとAIが旅程に）。",
    "<strong>持ち物とお土産をシンプルに管理：</strong>旅のしおり。",
    "<strong>国内のローカル情報が欲しい：</strong>ニコディ（ホテリエしおり。海外旅行対応は月額会員向け）。",
  ],
  "method": "日本の App Store で「旅行 計画」と検索し、宿や航空券の予約サイト、地図アプリを除いて、旅行計画・旅のしおり専用で日本の評価が多いアプリと、AIで旅程を作る新しいアプリ（アバトラベル）を選び、日本語の説明に書かれていることだけを同じ項目で並べました。有料版は試していません。評価順のランキングではなく、私たちのアプリを先頭に、残りは日本の評価数の順です。",
  "more": [
    ("無料で使える旅行計画アプリは？", "7つともダウンロードは無料です。説明に有料機能が書かれているのは tabiori（広告除去など）、旅のしおり（広告削除・保存数の上限拡張）、ニコディ（広告非表示・海外旅行対応など）、NAVITIME Travel（共同編集など）、BeforeGo（プレミアム）です。"),
    ("海外旅行の計画に使えるアプリは？", "BeforeGo は行き先に合わせてプラグ・通貨・入国準備・交通アプリまで持ち物リストを作ります。アバトラベルは VISA や現地通貨などの準備情報を案内します。ニコディの海外旅行対応は月額会員向けの機能です。"),
  ],
  "faq": [
    ("旅の投稿から旅行プランを作れるアプリは？", "BeforeGo の説明では、旅の投稿のスクショやリンク、打ち込んだ予定から、日ごとの旅行プランにまとめます。航空券や予約確認もスキャンでプランに加わります。"),
    ("友達と共同編集できる旅行計画アプリは？", "日本の App Store の説明では、tabiori、ニコディ、ホリデー、アバトラベルが共同編集に対応し、NAVITIME Travel はプレミアムで最大10人まで共同編集できます。旅のしおりは共有コードでしおりを送れます。"),
    ("電波がなくても旅のしおりを見られる？", "tabiori の説明にはオフライン閲覧が書かれています。ほかのアプリの説明には記載がありません。"),
    ("持ち物リストがあるアプリは？", "BeforeGo（行き先と日程から自動作成）、tabiori、旅のしおり、アバトラベルの説明に持ち物リストがあります。"),
    ("このランキングは中立ですか？", "いいえ。BeforeGo は私たちのアプリです。表の内容はすべて公開されている App Store の説明から取り、全アプリ同じ項目で書き、確かめられるようにそれぞれリンクを付けています。"),
  ],
}))

PAGES.append({
  "lang": "ko", "path": "/tools/ko/yeohaeng-iljeong-aep/", "kind": "Article", "app": None,
  "published": "2026-10-12", "updated": "2026-10-27", "meta_top": True,
  "title": "트리플 대체 앱 비교: NOL 이전·체크리스트·여행 경비 | BeforeGo", "crumb": "트리플 대체 앱",
  "description": "트리플 11월 3일 서비스 종료 전 확인할 NOL 일정 이전과 가계부 CSV 백업. 체크리스트, 출발 알림, 여행 경비, 캡처 정리 기준으로 대체 앱을 비교하세요.",
  "hub_title": "트리플 대체 앱 비교", "hub_desc": "공식 NOL 이전부터 체크리스트, 여행 경비, 캡처 정리까지 필요한 기능으로 선택하세요.",
  "items": [{"name": name, "url": f"https://apps.apple.com/kr/app/id{app_id}"} for name, app_id in [
    ("NOL", 436731843), ("BeforeGo", 6786561175), ("Wanderlog", 1476732439), ("트립노트", 6740430211), ("Funliday", 905768387)]],
  "faq": [
    ("트리플은 언제 서비스를 종료하나요?", "트리플의 한국 App Store 안내에 따르면 2026년 11월 3일 서비스를 종료하고 NOL로 통합됩니다. 이 페이지는 2026년 10월 27일 확인한 안내를 기준으로 작성했습니다."),
    ("11월 3일까지 NOL로 일정을 옮겨야 하나요?", "공식 안내는 서비스 종료 후에도 일정 이관을 12개월간 제공할 예정이라고 설명합니다. 일정은 자동으로 옮겨지지 않습니다. NOL 계정 전환과 최신 버전 앱이 필요하며, 가계부 CSV는 서비스 종료 전에 별도로 저장해야 합니다."),
    ("체크리스트와 가계부도 NOL로 옮겨지나요?", "2026년 10월 27일 확인한 공식 안내에서 체크리스트와 가계부는 제공되지 않는 기능으로 안내됩니다. 가계부 내역은 이관되지 않으며 종료 전 CSV로 보관할 수 있습니다. 일부 기능은 순차적으로 추가될 수 있으니 최신 공지를 확인하세요."),
    ("BeforeGo로 트리플 일정이나 CSV를 바로 가져올 수 있나요?", "트리플 원본 일정이나 가계부 CSV를 직접 가져오는 호환 기능은 확인하지 않았습니다. BeforeGo는 여행 게시물 캡처·링크·입력한 계획을 날짜별로 정리하는 앱입니다. 캡처 정리는 원본 데이터의 완전한 이전을 보장하지 않습니다."),
    ("친구와 함께 일정을 편집하려면 어떤 앱을 보나요?", "한국 App Store 설명 기준으로 Wanderlog는 실시간 협업을, 트립노트는 일행 초대와 함께 편집을, Funliday는 동행자와 공동 편집을 안내합니다. BeforeGo의 실시간 공동 편집은 이 비교에서 지원 기능으로 확인하지 않았습니다."),
    ("이 비교는 독립적인가요?", "BeforeGo는 우리가 만든 앱입니다. 공식 NOL 이전을 먼저 안내하고, 다른 앱도 같은 작업 기준으로 비교했습니다. 공개된 공식 안내와 한국 App Store 설명을 확인했으며, 실제 가져오기 호환성을 테스트한 비교는 아닙니다."),
  ], "js": [],
  "body": """<h1>트리플 종료 후, 어떤 여행 앱을 쓰면 좋을까요?</h1>
<p class="lede">트리플은 2026년 11월 3일 서비스를 종료하고 NOL로 통합됩니다. <strong>기존 일정을 이어 쓰려면 공식 NOL 이전부터 확인하세요.</strong> 그다음 체크리스트, 출발 알림, 경비 기록, 캡처 정리 중 필요한 기능을 골라 보세요. BeforeGo는 우리가 만든 앱입니다.</p>
<p><a href="https://triple.guide/content/articles/1b62be09-5cc2-4ff2-a73f-afee9b3d2c9a">트리플 공식 일정 이전 안내 →</a> · <a href="https://apps.apple.com/kr/app/id1225499481">트리플 App Store 종료 안내 →</a></p>
<h2>먼저, 트리플 일정을 NOL로 옮기기</h2>
<p>공식 안내는 <strong>서비스 종료 후에도 일정 이관 기능을 12개월간 제공할 예정</strong>이라고 설명합니다. 일정은 자동으로 옮겨지지 않습니다. 트리플 계정을 NOL 계정으로 전환하고 최신 버전 앱(안내 기준 7.23.0 이상)에서 원하는 여행을 선택해야 합니다. 계정이 여러 개라면 옮길 일정이 있는 계정을 먼저 확인하세요. 계정 전환은 취소하거나 다른 계정으로 바꿀 수 없다고 안내합니다.</p>
<p>한 번 옮긴 일정은 다시 옮길 수 없고 두 서비스의 일정이 서로 동기화되지 않습니다. 옮긴 뒤에는 NOL에서 내용을 확인하고 수정하세요. 2026년 10월 27일 확인한 안내에서는 <strong>체크리스트·가계부·일행 초대가 제공되지 않으며, 가계부 내역도 이관되지 않는다</strong>고 설명합니다. 일부 기능은 순차적으로 추가될 수 있으므로 이용 전 최신 공지를 확인하세요.</p>
<h2>필요한 작업부터 고르세요</h2>
<table><thead><tr><th>하려는 일</th><th>먼저 볼 선택지</th><th>확인할 점</th></tr></thead><tbody>
<tr><th>기존 트리플 일정 유지</th><td>NOL 공식 일정 이전</td><td>계정 전환과 여행별 선택이 필요합니다. 모든 기능·정보가 그대로 이어지지는 않습니다.</td></tr>
<tr><th>준비물 체크와 출발 알림</th><td>BeforeGo, 트립노트</td><td>BeforeGo는 목적지·날짜에 맞춘 목록과 출발 알림, 트립노트는 가방별 준비물 관리를 안내합니다.</td></tr>
<tr><th>여행 경비와 분담 기록</th><td>BeforeGo, Wanderlog, 트립노트</td><td>BeforeGo와 Wanderlog는 비용 분담을, 트립노트는 가계부·예산 관리를 안내합니다. 기존 CSV 보관과 새 앱에 기록하는 일은 별개입니다.</td></tr>
<tr><th>캡처·링크에서 새 일정 정리</th><td>BeforeGo, Wanderlog</td><td>BeforeGo는 캡처·링크·텍스트 입력을, Wanderlog는 링크·릴스 가져오기를 안내합니다. 트리플 원본을 완전히 옮기는 기능으로 확인한 것은 아닙니다.</td></tr>
<tr><th>동행자와 함께 일정 수정</th><td>Wanderlog, 트립노트, Funliday</td><td>각 앱의 공동 편집 설명을 확인하세요. BeforeGo의 실시간 공동 편집은 확인하지 않았습니다.</td></tr>
</tbody></table>
<h2>같은 기준으로 본 여행 일정 앱 5가지</h2>
<table class="cmp"><thead><tr><th>앱</th><th>일정 정리</th><th>체크리스트·출발 알림</th><th>여행 경비</th></tr></thead><tbody>
<tr><th><a href="https://apps.apple.com/kr/app/id436731843">NOL</a></th><td>트리플 공식 일정 이전</td><td>공식 안내에서 체크리스트 미제공; 출발 알림은 해당 안내에 없음</td><td>가계부 미제공·내역 이관 불가; 종료 전 CSV 보관</td></tr>
<tr><th><a href="https://beforegotech.com/ko/">BeforeGo (우리 앱)</a></th><td>캡처·링크·텍스트를 날짜별로 정리</td><td>목적지·날짜별 목록, 출발 7일·3일·24시간·3시간 전 알림</td><td>결제자·참여자별 분담, 영수증 입력</td></tr>
<tr><th><a href="https://apps.apple.com/kr/app/id1476732439">Wanderlog</a></th><td>지도·장소 순서 정리, 링크·릴스 가져오기, 실시간 협업</td><td>일반 목록 작성 안내; 출발 알림은 설명에 없음</td><td>비용 추적·그룹 비용 분할</td></tr>
<tr><th><a href="https://apps.apple.com/kr/app/id6740430211">트립노트</a></th><td>장소·동선·숙소·항공편 정리, 함께 편집</td><td>가방별 체크리스트; 출발 알림은 설명에 없음</td><td>가계부·현지 통화의 원화 환산·예산 비교</td></tr>
<tr><th><a href="https://apps.apple.com/kr/app/id905768387">Funliday</a></th><td>명소·경로 정리, 공동 편집, 오프라인 일정 보기(지도 제외)</td><td>설명에 없음</td><td>설명에 없음</td></tr>
</tbody></table>
<p class="meta">확인일: 2026년 10월 27일. 공식 이전 안내와 각 앱의 한국 App Store 설명 기준입니다. ‘설명에 없음’은 기능이 없다는 뜻이 아닙니다. 평점과 가격으로 순위를 매기지 않았으며, 유료 기능이나 가져오기 호환성을 직접 테스트하지 않았습니다.</p>
<h2>서비스 종료 전, 짧은 백업 체크리스트</h2>
<ol>
<li><strong>계정과 일정 확인:</strong> 이전할 일정이 어느 계정에 있는지 확인하고 공식 안내에 따라 NOL 계정 전환을 진행하세요. 옮긴 뒤 여행 날짜·장소·메모를 대조하세요.</li>
<li><strong>일정 이미지 저장:</strong> 트리플의 내 여행 일정 → 공유 → 일정 이미지로 저장하기에서 전체 또는 일별 이미지를 보관하세요.</li>
<li><strong>가계부 CSV 저장:</strong> 서비스 종료 전에 내 여행 일정 → 가계부 → 우측 상단 메뉴(···) → 가계부 내보내기(CSV)를 이용하세요. 저장한 파일이 열리는지도 확인하세요.</li>
<li><strong>중요한 정보 별도 보관:</strong> 공식 안내에 따르면 장소별 지정 시간과 트리플 구매 상품의 예약번호는 NOL 일정에 표기되지 않습니다. 필요한 시간을 메모하고 예약 확인서는 따로 보관하세요. 이전 전 메모·사진 속 여권·신분증 등 개인정보도 점검하세요.</li>
</ol>
<p>백업은 보관용입니다. 일정 이미지나 CSV를 저장했다고 해서 다른 앱으로 모든 항목을 자동 복원할 수 있다는 뜻은 아닙니다. 자세한 순서는 <a href="https://triple.guide/content/articles/1b62be09-5cc2-4ff2-a73f-afee9b3d2c9a">트리플 공식 안내</a>를 따르세요.</p>
<h2>BeforeGo로 출발 준비와 새 계획 정리하기</h2>
<p>BeforeGo는 캡처·링크·텍스트를 날짜별 계획으로 정리하고, 목적지와 날짜에 맞춘 체크리스트와 출발 알림을 제공합니다. 여행 경비는 결제자와 참여자를 골라 나누고, 영수증을 찍어 지출을 입력할 수 있습니다. 트리플 일정·CSV의 직접 가져오기는 확인하지 않았으며, 캡처 정리도 원본의 모든 필드를 보존하는 이전을 보장하지 않습니다.</p>
<h3>텍스트 예시: 오사카 2박 3일 준비</h3>
<p><strong>사용 흐름을 설명하기 위한 예시이며 실제 가져오기 테스트 결과가 아닙니다.</strong> ‘1일 차 난바, 2일 차 우메다’처럼 계획을 입력하거나 본인이 만든 여행 메모를 캡처해 정리한 뒤, 장소명과 날짜를 원본과 대조하세요. 예약 시간·금액·통화는 직접 확인하고, 목적지와 출발일을 설정해 준비물과 알림을 점검하세요. 공동 지출을 추가할 때는 결제자와 실제 참여자를 확인하세요.</p>
<p>캡처의 문자 인식은 기기에서 처리하고, 일정 구조화에는 요청 시 클라우드 AI를 사용합니다. 일정을 구조화할 때 인터넷 연결이 필요합니다.</p>
<p><a class="btn" href="https://beforegotech.com/ko/">캡처한 여행 계획과 출발 준비를 한곳에 정리하기 →</a></p>
<p><a href="https://apps.apple.com/kr/app/id6786561175?pt=128309253&amp;ct=web-triple-alternatives-ko&amp;mt=8">BeforeGo App Store에서 보기 →</a></p>
<h2>비교 기준과 개발자 공개</h2>
<p>우리는 BeforeGo 개발자입니다. NOL을 공식 이전 경로로 먼저 안내하고, 다른 앱은 체크리스트·경비·입력 방식·공동 편집처럼 실제 할 일을 기준으로 비교했습니다. BeforeGo 기능은 현재 제품 설명을, 다른 앱은 위에 연결한 한국 App Store 개발자 설명을 확인했습니다. 새 공지나 앱 업데이트에 따라 기능이 달라질 수 있습니다.</p>""",
})

# 7d. 美区：Countdown 三页 + BeforeGo 一页（BeforeGo 那页 10-26 已搬到 beforegotech.com，见 BG_MOVED）——10-17（用户：「Countdown 跟 BeforeGo 瞄准美国」，选题与证据见 App 数据仓库 reports/aso/site-us-topics-2026-10-17.md）
# 证据：Google 美国联想词（shared countdown app for couples / long distance relationship countdown widget / birthday countdown app / disney countdown app (widget, for iphone)
# / disney itinerary template）；App Store 美区广告：birthday countdown 780 展示 / 54 安装、shared countdown widget 点击率 24%。
# App 说法只用 tools/store/countdown.json en-US（1.4.20）与 beforego.json en-US（1.2.6），外加 Countdown 源码核实的：
# 列表长按菜单 / 详情页邀请按钮叫「Invite Someone」（共享后变「Manage Sharing」）；对方只读、改日期两边同步、对方删除只是退出共享；
# 发起邀请是 Pro、接受免费（SPEC-共享倒计时 09-29）；Birthday 模板：每年重复，提前一周 / 前一天 / 当天早上提醒；Vacation 模板：30 / 7 / 1 天和当天的里程碑。
# Disney：只作描述性使用、写明非官方、不放 logo / 角色图。订餐与 Lightning Lane 的开放时间 10-17 在 disneyworld.disney.go.com 读过原文：
# 「Make reservations for your entire length of stay (for up to a 10-night stay) up to 60 days in advance of your arrival」（各度假酒店的 dining 页），
# 「Guests of Disney Resort hotels and other select hotels can purchase passes up to 7 days in advance of their stay—and other Guests … up to 3 days in advance of their park visit」。
DISNEY_NOTE = ('<p class="meta" style="margin-top:18px">go ka is not affiliated with, endorsed by or sponsored by Disney. Disney, Walt Disney World, Magic Kingdom, EPCOT, '
               'Disney’s Hollywood Studios, Disney’s Animal Kingdom, Disney Springs, Lightning Lane, Disneyland and related names are trademarks of Disney. The booking windows above were checked on disneyworld.disney.go.com on October 17, 2026; '
               'Disney can change them, so check there before you plan around them.</p>')
EN_WIDGET_STEPS = ('<li>Lock Screen: touch and hold the Lock Screen, tap <strong>Customize</strong>, choose the Lock Screen, tap <strong>Add Widgets</strong> under the clock, choose Countdown and tap <strong>Done</strong>.</li>'
                   '<li>Home Screen: touch and hold an empty area, tap <strong>Edit</strong> → <strong>Add Widget</strong> (on iOS 17, tap <strong>+</strong>), search for Countdown, pick a size and tap <strong>Add Widget</strong>.</li>')
LL_URL = "https://disneyworld.disney.go.com/lightning-lane-passes/"
DINE_URL = "https://disneyworld.disney.go.com/resorts/contemporary-resort/dining/"   # 10-17 评审读过原文：「Guests with a Valid Disney Resort Hotel Reservation … up to 60 days in advance of your arrival」「All Other Guests: Make reservations up to 60 days in advance.」

PAGES.append({"path": "/tools/shared-countdown-app-couples/", "iphone_only": True, "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-10-17",
  "meta_top": True, "title": "Shared Countdown App for Couples: Same Countdown on Both iPhones", "crumb": "Shared countdown for couples",
  "description": "Count down to your next visit together: one of you sends an invite, the other taps the link, and the same countdown and widget show up on both iPhones.",
  "hub_title": "Shared countdown for couples", "hub_desc": "One countdown on both iPhones: invite, tap the link, and the date and widget stay in sync.",
  "faq": [
    ("Is there a free shared countdown app?", "In Countdown Widget: Any Event, joining a countdown someone shares with you is free, and so is every widget. Sending the invitation is part of Countdown Pro, so one of you needs Pro and the other doesn't."),
    ("Can both of us change the date?", "No. Only the person who created the countdown can change it. When they move the date, the countdown and its widget change on the other iPhone too."),
    ("Do we need the same Apple ID?", "No. Each of you uses your own iPhone with your own iCloud account."),
    ("Does it work with Android?", "No. Countdown is an app for iPhone and iPad, so both of you need one of those."),
    ("How do I stop sharing a countdown?", "Touch and hold the countdown in your list and tap Manage Sharing. If someone shared it with you, deleting it from your list takes you out of the share without touching their copy."),
  ],
  "body": f"""<h1>A shared countdown for couples</h1>
<p class="lede">Whether you live apart or are just counting the days to a trip, one of you sets up the countdown and taps <strong>Invite Someone</strong>, the other taps the link, and the same countdown appears on both iPhones, widget and all. Move the date and it moves on both.</p>
{top_cta("countdown", "en", "Get Countdown — joining is free")}
<h2>How to share a countdown</h2>
<ol><li>Both of you install <a href="/countdown/">Countdown Widget: Any Event</a>.</li>
<li>One of you taps <strong>Add Event</strong> (or <strong>+</strong> once you already have events), names it — “Next visit”, “Moving day” — and sets the date.</li>
<li>Touch and hold the countdown in your list and tap <strong>Invite Someone</strong> (the countdown’s own page has the same invite button). Send the link the way you send any link, for example in Messages.</li>
<li>The other person taps the link, and the countdown is in their list.</li>
<li>Each of you puts it on your own screen:<ul>{EN_WIDGET_STEPS}</ul></li></ol>
<h2>Who can do what</h2>
<table><thead><tr><th></th><th>The one who invites</th><th>The one who joins</th></tr></thead><tbody>
<tr><th>Needs</th><td>Countdown Pro</td><td>Nothing: joining is free</td></tr>
<tr><th>Changes the date or name</th><td>Yes, and it updates on both phones</td><td>No, it’s view-only</td></tr>
<tr><th>Widgets</th><td>Free, every size</td><td>Free, every size</td></tr>
<tr><th>Stops sharing</th><td>Manage Sharing</td><td>Deletes it from their own list</td></tr>
</tbody></table>
<h2>Countdowns worth sharing</h2>
<ul><li><strong>The next visit.</strong> The one long-distance couples check most. Change it once when the flight moves, and the other phone follows.</li>
<li><strong>Moving to the same city.</strong> The big one, on both Lock Screens.</li>
<li><strong>Your anniversary.</strong> Set it to repeat yearly and it starts again the day after.</li>
<li><strong>A trip together.</strong> Start from the <a href="/tools/vacation-countdown-widget-iphone/">vacation countdown</a>; the <a href="/tools/disney-countdown-widget-iphone/">Disney trip countdown</a> shows how to add the booking dates as countdowns too.</li></ul>
<p>Counting up rather than down? Countdown also counts up from a date, like the day you met. For a birthday, see the <a href="/tools/birthday-countdown-widget-iphone/">birthday countdown widget</a>.</p>"""})

PAGES.append({"path": "/tools/birthday-countdown-widget-iphone/", "iphone_only": True, "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-10-17",
  "meta_top": True, "title": "Birthday Countdown Widget for iPhone: Free, Repeats Every Year", "crumb": "Birthday countdown widget",
  "description": "Put a birthday countdown on your iPhone Lock Screen or Home Screen with a free widget. The Birthday template repeats yearly and reminds you a week before.",
  "hub_title": "Birthday countdown widget for iPhone", "hub_desc": "Set it once: it repeats every year, reminds you a week before, and sits on the Lock Screen.",
  "faq": [
    ("Is there a free birthday countdown widget for iPhone?", "Yes. In Countdown Widget: Any Event every widget size is free, on the Home Screen and the Lock Screen, with no limit on how many birthdays you add and no ads."),
    ("Does the birthday countdown start again next year?", "Yes. The ready-made Birthday event repeats every year, so the day after the birthday it counts down to the next one."),
    ("Will it remind me before the birthday?", "Yes. The Birthday event comes with reminders a week before, the day before and on the morning itself. You can change them or add more."),
    ("Can I see several birthdays in one widget?", "Yes. One of the four widgets shows the next few countdowns in a list, so the closest birthdays sit together."),
    ("Can I put the birthday person's photo behind the countdown?", "Using your own photo behind a countdown is part of Countdown Pro. The free version has its own backdrops, and the widget works the same either way."),
    ("Does it work on Android?", "No. Countdown is an app for iPhone and iPad."),
  ],
  "body": f"""<h1>Birthday countdown widget for iPhone</h1>
<p class="lede">Add the birthday once with the ready-made <strong>Birthday</strong> event: it repeats every year by itself and reminds you a week before, the day before and that morning. Then put its widget on your Lock Screen or Home Screen. In Countdown Widget: Any Event every widget size is free.</p>
{top_cta("countdown", "en", "Add a birthday countdown — free")}
<h2>Step by step</h2>
<ol><li>Install <a href="/countdown/">Countdown Widget: Any Event</a> and tap <strong>Add Event</strong> (or <strong>+</strong> once you already have events).</li>
<li>Pick <strong>Birthday</strong> from the ready-made events. It is already set to repeat yearly, with the three reminders.</li>
<li>Type the name and the date of the next birthday.</li>
<li>Put it on your screen:<ul>{EN_WIDGET_STEPS}</ul></li></ol>
<p>More detail on both screens, and what to do if a widget looks stuck, is in <a href="/blog/countdown-widget-iphone-home-lock-screen/">how to put a countdown on your iPhone Lock Screen</a>.</p>
<h2>Keeping track of several birthdays</h2>
<ul><li><strong>No limit.</strong> Add every birthday you want to remember; each one repeats on its own.</li>
<li><strong>The next few in one widget.</strong> The list widget shows the closest countdowns together, so you see whose birthday is coming up first.</li>
<li><strong>One big number.</strong> The single-countdown widget on the Lock Screen keeps your own birthday, or a big one like a 30th, in view.</li></ul>
<h2>When the day comes</h2>
<p>A week out, the day before and on the morning itself, the app opens on the number, full screen, with a card worth sharing. Tap an event and it turns over to a page of its own, where you can write a few lines and add photos.</p>
<p>Planning a surprise with someone? One of you can invite the other, and the countdown shows up on both iPhones; see the <a href="/tools/shared-countdown-app-couples/">shared countdown</a> page. Just want the number of days? Use the <a href="/tools/days-until/">days until calculator</a>.</p>"""})

PAGES.append({"path": "/tools/disney-countdown-widget-iphone/", "iphone_only": True, "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-10-17",
  "meta_top": True, "title": "Disney Trip Countdown Widget for iPhone: On Your Lock Screen", "crumb": "Disney trip countdown",
  "description": "Put the days until your Disney World trip on your iPhone Lock Screen or Home Screen with a free widget, plus countdowns to when dining and Lightning Lane open.",
  "hub_title": "Disney trip countdown widget", "hub_desc": "The days until your trip on the Lock Screen, plus the dates dining and Lightning Lane open.",
  "faq": [
    ("Is there a free Disney countdown widget for iPhone?", "Countdown Widget: Any Event is not a Disney app, but it counts down to any trip, and every widget size is free on the Home Screen and the Lock Screen, with no limit on countdowns."),
    ("Can I put a photo from my last trip behind the countdown?", "Using your own photo behind a countdown is part of Countdown Pro. The free version has its own backdrops, with no Disney characters."),
    ("When can I book dining at Walt Disney World?", "Disney’s resort dining pages say Disney Resort hotel guests can make reservations for their whole stay, up to 10 nights, up to 60 days before arrival, and all other guests up to 60 days in advance."),
    ("When can I buy Lightning Lane passes?", "Disney says guests of Disney Resort hotels and other select hotels can buy them up to 7 days before their stay, and other guests up to 3 days before their park visit."),
    ("Does this work for Disneyland too?", "The countdown works for any date. The booking windows on this page are the ones Walt Disney World publishes; Disneyland has its own rules."),
  ],
  "body": f"""<h1>Disney trip countdown widget for iPhone</h1>
<p class="lede">Add your arrival day as a countdown and put its widget on your Lock Screen or Home Screen; the number goes down by itself every day. Then add the dates that matter before you go — when dining opens, when Lightning Lane opens — so none of them sneaks up on you. In Countdown Widget: Any Event every widget size is free.</p>
{top_cta("countdown", "en", "Start your trip countdown — free")}
<h2>Step by step</h2>
<ol><li>Install <a href="/countdown/">Countdown Widget: Any Event</a> and tap <strong>Add Event</strong> (or <strong>+</strong> once you already have events).</li>
<li>Pick <strong>Vacation</strong> from the ready-made events, name it “Disney World” and set the arrival date. It marks 30 days, a week, the day before and the morning itself.</li>
<li>Choose a backdrop, or <a href="/tools/countdown-widget-with-your-own-photo-iphone/">your own photo</a> with Pro.</li>
<li>Put it on your screen:<ul>{EN_WIDGET_STEPS}</ul></li></ol>
<h2>Dates worth their own countdown</h2>
<table><thead><tr><th>Countdown</th><th>When it opens</th><th>Who</th></tr></thead><tbody>
<tr><td>Dining reservations</td><td>60 days before arrival, for the whole stay (up to 10 nights)</td><td>Disney Resort hotel guests</td></tr>
<tr><td>Dining reservations</td><td>60 days before the meal</td><td>Everyone else</td></tr>
<tr><td>Lightning Lane passes</td><td>7 days before the first day of your stay</td><td>Guests of Disney Resort hotels and other select hotels</td></tr>
<tr><td>Lightning Lane passes</td><td>3 days before your park visit</td><td>Everyone else</td></tr>
</tbody></table>
<p>Work out each date from your arrival or park day, add it as its own countdown, and the list widget shows them in order: dining first, then Lightning Lane, then the trip. Disney’s own wording is on its <a href="{LL_URL}" rel="noopener">Lightning Lane passes</a> page and on each resort’s <a href="{DINE_URL}" rel="noopener">dining page</a>.</p>
<h2>Counting down as a family</h2>
<p>With Pro you can invite someone to the countdown, and it shows up on their iPhone too; joining is free. Change the date once and it changes on every phone. See the <a href="/tools/shared-countdown-app-couples/">shared countdown</a> page for how it works.</p>
<p>Planning the days themselves? Fill in the <a href="/tools/disney-world-itinerary-template/">Disney World itinerary template</a>, and pack with the <a href="/tools/disney-world-packing-list/">Disney World packing list</a>.</p>
{DISNEY_NOTE}"""})

# 7d3. 美区 GEO：自己的照片当背景 + 度假倒数——10-18（App 数据仓库 reports/aso/geo-baseline-2026-10-18-countdown-us.md：
# ChatGPT 未登录 8 题 ×2，这两题官网没有对应页；赢家是名字带场景的小 App 或开发者自己域名上的专题页）。
# 照片：源码核实——编辑页 Backdrop → Custom → Add Photo → Photo adjustments（Detail / Small / Medium / Large 四个预览各自取景，只能拖动；
# Opacity / Blur / Text Contrast 三个滑块）→ Done；自己的照片属于 Pro（商店 1.4.21 原文）。锁屏三种小组件按系统单色渲染，不画背景（CountdownWidgetView isAccessory）。
# 背景 159 张、Pro 107 张 → 免费 52 张（商店原文）。度假：EventTemplate vacation 全天、提醒 30 / 7 / 1 天和当天（milestoneTiers 就是提醒通知），默认背景 Beach Pup 免费；
# Road trip 全天 7 / 1 / 当天；Flight 定时（默认 9:00，改成起飞时间），提醒前一天和当天。
PAGES.append({"path": "/tools/countdown-widget-with-your-own-photo-iphone/", "iphone_only": True, "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-10-18",
  "meta_top": True, "title": "Countdown Widget With Your Own Photo on iPhone: Home Screen Setup", "crumb": "Countdown widget with your photo",
  "description": "Put your own photo behind a countdown widget on your iPhone Home Screen, framed for each widget size. Lock Screen widgets can't show photos; use your wallpaper.",
  "hub_title": "Countdown widget with your own photo", "hub_desc": "Your photo behind the number, framed for each Home Screen size, and how to get it on the Lock Screen.",
  "faq": [
    ("Can I use my own photo as a countdown widget background on iPhone?", "Yes. In Countdown Widget: Any Event you can put your own photo behind any countdown, and it shows on its Home Screen widgets in every size when the Home Screen uses the Default or Dark look. Using your own photo is part of Countdown Pro."),
    ("Why doesn't my photo show in the Lock Screen widget?", "iOS draws Lock Screen widgets in a single tint over your wallpaper, so a photo can’t appear inside them. Set the photo as your Lock Screen wallpaper and put the countdown widget over it."),
    ("Is the countdown widget free?", "Yes. Every widget size on the Home Screen and the Lock Screen is free, with unlimited events and no ads. Of the 159 built-in backdrops, 52 are free; your own photo, the other 107 backdrops and the Pro typefaces are part of Countdown Pro."),
    ("Can each widget size show a different part of the photo?", "Yes. You frame the photo separately for the countdown's page and for the small, medium and large widgets, so a face isn't cut in half in the wide one."),
    ("What if the number is hard to read on my photo?", "Photo adjustments has three sliders: Opacity fades the photo, Blur softens the detail behind the digits, and Text Contrast adds a shade behind the number."),
    ("Does it work on Android?", "No. Countdown is an app for iPhone and iPad."),
  ],
  "body": f"""<h1>Your own photo behind a countdown widget</h1>
<p class="lede">In Countdown Widget: Any Event you can put your own photo behind any countdown and frame it separately for the small, medium and large Home Screen widgets. Opacity, Blur and Text Contrast keep the number readable. The widgets are free; using your own photo is part of Countdown Pro. Lock Screen widgets are drawn in a single tint, so a photo can’t appear inside them; the workaround is below.</p>
{top_cta("countdown", "en", "Get Countdown — every widget is free")}
<h2>Step by step</h2>
<ol><li>Install <a href="/countdown/">Countdown Widget: Any Event</a>, tap <strong>Add Event</strong> (or <strong>+</strong> once you already have events) and pick a ready-made event or <strong>Blank Event</strong>. For a countdown you already have, open it and tap the pencil to edit it.</li>
<li>Tap <strong>Backdrop</strong>, choose <strong>Custom</strong>, then <strong>Add Photo</strong>, and pick the photo.</li>
<li>In <strong>Photo adjustments</strong>, switch between the <strong>Detail</strong>, <strong>Small</strong>, <strong>Medium</strong> and <strong>Large</strong> previews and drag the frame in each one until it sits right; drag its corners to make it bigger or smaller.</li>
<li>Move the <strong>Opacity</strong>, <strong>Blur</strong> and <strong>Text Contrast</strong> sliders until the number stands out, then tap <strong>Done</strong>.</li>
<li>Home Screen: touch and hold an empty area, tap <strong>Edit</strong> → <strong>Add Widget</strong> (on iOS 17, tap <strong>+</strong>), search for Countdown, pick a size and tap <strong>Add Widget</strong>.</li></ol>
<h2>Where the photo shows</h2>
<table><thead><tr><th>Place</th><th>Your photo</th></tr></thead><tbody>
<tr><td>The countdown’s own page in the app</td><td>Yes, framed in the Detail preview</td></tr>
<tr><td>Home Screen widgets</td><td>Yes, every size, each framed on its own, with the Home Screen set to the Default or Dark look</td></tr>
<tr><td>Home Screen widgets on a Tinted or Clear Home Screen</td><td>No. iOS removes widget backgrounds in those looks</td></tr>
<tr><td>Lock Screen widgets</td><td>No. iOS draws them in one tint over the wallpaper, for every app</td></tr>
</tbody></table>
<h2>Want the photo on the Lock Screen too?</h2>
<p>Use the photo as the wallpaper and put the number on top of it:</p>
<ol><li>Touch and hold the Lock Screen, tap <strong>+</strong>, choose <strong>Photos</strong> and pick the photo.</li>
<li>Tap <strong>Add Widgets</strong> under the clock, choose Countdown and close the widget panel.</li>
<li>Tap <strong>Add</strong>, then <strong>Set as Wallpaper Pair</strong>.</li></ol>
<p>Want the date written on the photo as well? The <a href="/tools/countdown-wallpaper-maker/">countdown wallpaper maker</a> puts your title, the days left and the date on your photo, sized for the Lock Screen. More on both screens, and what to do if a widget looks stuck, is in <a href="/blog/countdown-widget-iphone-home-lock-screen/">how to put a countdown on your iPhone Lock Screen</a>.</p>
<h2>Photos that work well</h2>
<ul><li><strong>A trip.</strong> Last year’s beach behind this year’s <a href="/tools/vacation-countdown-widget-iphone/">vacation countdown</a>.</li>
<li><strong>The two of you.</strong> Behind the next visit, on a countdown you <a href="/tools/shared-countdown-app-couples/">share with your partner</a>.</li>
<li><strong>The birthday person.</strong> Behind a <a href="/tools/birthday-countdown-widget-iphone/">birthday countdown</a> that repeats every year.</li></ul>
<p>Rather not use a photo? The 52 free backdrops include drawn scenes and patterns, and they work in every widget the same way.</p>"""})

PAGES.append({"path": "/tools/vacation-countdown-widget-iphone/", "iphone_only": True, "lang": "en", "kind": "Article", "app": "countdown", "published": "2026-10-18",
  "meta_top": True, "title": "Vacation Countdown Widget for iPhone: Free, on Your Lock Screen", "crumb": "Vacation countdown widget",
  "description": "Put the days until your vacation on your iPhone Lock Screen or Home Screen with a free widget. The Vacation event reminds you 30 days, a week and a day before.",
  "hub_title": "Vacation countdown widget for iPhone", "hub_desc": "The days until your trip on the Lock Screen, with reminders 30 days, a week and a day before.",
  "faq": [
    ("Is there a free vacation countdown widget for iPhone?", "Yes. In Countdown Widget: Any Event the ready-made Vacation event is free, and so is every widget size on the Home Screen and the Lock Screen, with unlimited countdowns and no ads."),
    ("Can it count down to the hour for my flight?", "Yes. The Flight event is timed rather than all-day: set the departure time and it counts down to the hour, with a reminder the day before and on the day."),
    ("Will it remind me before the trip?", "The Vacation event reminds you 30 days out, a week out, the day before and on the morning itself. You can change those reminders or add your own."),
    ("Can I put a photo of the beach behind the countdown?", "The Vacation event starts on a free beach backdrop. Using your own photo, say from last year’s trip, is part of Countdown Pro."),
    ("Can my travel partner see the same countdown?", "Yes. With Pro you can invite them and the countdown shows up on their iPhone too; joining is free. When you change the date, it changes on both phones."),
    ("Does it work on Android?", "No. Countdown is an app for iPhone and iPad."),
  ],
  "body": f"""<h1>Vacation countdown widget for iPhone</h1>
<p class="lede">Add your trip with the ready-made <strong>Vacation</strong> event, then put its widget on your Lock Screen or Home Screen; the number goes down by itself every day. The Vacation event reminds you 30 days out, a week out, the day before and that morning. In Countdown Widget: Any Event every widget size is free, with unlimited countdowns and no ads.</p>
{top_cta("countdown", "en", "Start your vacation countdown — free")}
<h2>Step by step</h2>
<ol><li>Install <a href="/countdown/">Countdown Widget: Any Event</a> and tap <strong>Add Event</strong> (or <strong>+</strong> once you already have events).</li>
<li>Pick <strong>Vacation</strong> from the ready-made events, name it after the place and set the first day of the trip.</li>
<li>Keep the beach backdrop it starts with, pick another, or use <a href="/tools/countdown-widget-with-your-own-photo-iphone/">your own photo</a> with Pro.</li>
<li>Put it on your screen:<ul>{EN_WIDGET_STEPS}</ul></li></ol>
<h2>Pick the right ready-made event</h2>
<table><thead><tr><th>Event</th><th>Counts</th><th>Reminds you</th></tr></thead><tbody>
<tr><td>Vacation</td><td>Days (all-day)</td><td>30 days, a week and a day before, and that morning</td></tr>
<tr><td>Road trip</td><td>Days (all-day)</td><td>A week and a day before, and that morning</td></tr>
<tr><td>Flight</td><td>Down to the hour (set the departure time)</td><td>The day before and on the day</td></tr>
</tbody></table>
<h2>One widget for the whole trip</h2>
<p>Most trips come with more than one date: when you need to book something, the flight, then the first day away. Add each as its own countdown, and the list widget shows the next few in order, so the closest one is always on top. The <a href="/tools/disney-countdown-widget-iphone/">Disney trip countdown</a> shows this with dining and Lightning Lane dates.</p>
<h2>Counting down with someone</h2>
<p>With Pro you can invite your travel partner to the countdown, and it shows up on their iPhone too; joining is free. See the <a href="/tools/shared-countdown-app-couples/">shared countdown</a> page for how it works.</p>
<h2>After the trip</h2>
<p>Days that have passed aren’t deleted. They collect into a timeline you can look back through. Tap an event and it turns over to a page of its own, where you can write a few lines and add photos from the trip.</p>
<p>Getting ready to go? Make a <a href="/tools/packing-list/">packing list</a> for the trip.</p>"""})

ITIN_JS = """
(function(){var d=document.getElementById('days');if(!d)return;
function renum(){d.querySelectorAll('.day .dn').forEach(function(e,i){e.textContent='Day '+(i+1);});}
document.getElementById('addday').addEventListener('click',function(){var s=d.lastElementChild.cloneNode(true);s.querySelectorAll('[contenteditable]').forEach(function(e){e.textContent='';});d.appendChild(s);renum();var f=s.querySelector('[contenteditable]');if(f)f.focus();});
document.getElementById('print').addEventListener('click',function(){window.print();});renum();})();
"""
def itin_day(title, slots):
    rows = "".join(f'<div class="slot"><b>{k}</b><span contenteditable="true">{v}</span></div>' for k, v in slots)
    return f'<section class="day"><h3><span class="dn"></span> · <span contenteditable="true">{title}</span></h3>{rows}</section>'
DISNEY_DAYS = "\n".join([
    itin_day("Arrive · Disney Springs", [("Morning", "Fly in, check in, drop the bags"), ("Afternoon", "Pool"), ("Evening", "Disney Springs"), ("Dining", "Dinner at Disney Springs")]),
    itin_day("Magic Kingdom", [("Morning", "At the gate before opening"), ("Afternoon", "Back to the hotel for a break"), ("Evening", "Fireworks"), ("Dining", "Quick-service lunch; dinner booked for 5:30")]),
    itin_day("EPCOT", [("Morning", "Rides first, while lines are short"), ("Afternoon", "World Showcase"), ("Evening", "Nighttime show"), ("Dining", "Snacks around the World Showcase")]),
    itin_day("Animal Kingdom", [("Morning", "Safari first thing"), ("Afternoon", "Break: hotel pool"), ("Evening", "Early night"), ("Dining", "Character breakfast")]),
    itin_day("Hollywood Studios", [("Morning", "At the gate before opening"), ("Afternoon", "Shows"), ("Evening", "Pack for tomorrow"), ("Dining", "Dinner reservation")]),
])
PAGES.append({"path": "/tools/disney-world-itinerary-template/", "lang": "en", "kind": "WebApplication", "app": "beforego", "published": "2026-10-17",
  "title": "Disney World Itinerary Template: Free, Fill In Online, Save as PDF", "crumb": "Disney World itinerary template",
  "description": "A free Disney World itinerary template you fill in on the page: one block per day with park, morning, afternoon, evening and dining. Print it or save as PDF.",
  "hub_title": "Disney World itinerary template", "hub_desc": "One block per park day, filled in on the page. Print it or save as PDF; no sign-up.",
  "js": [ITIN_JS], "faq": [
    ("Is this Disney itinerary template free?", "Yes. You fill it in right on the page; nothing is uploaded and there is no sign-up or watermark. Print it or save it as a PDF when you are done."),
    ("How do I add more days?", "Tap “+ Add a day” under the title. A new empty day appears at the end, numbered for you."),
    ("How do I save it as a PDF?", "Tap “Print / Save as PDF” and choose Save as PDF in the print window. Only the itinerary is printed; the rest of the page is hidden."),
    ("When do dining and Lightning Lane open?", "Disney’s resort dining pages say Disney Resort hotel guests can book dining for their whole stay, up to 10 nights, up to 60 days before arrival, and all other guests up to 60 days in advance. Lightning Lane passes open 7 days before the stay for guests of Disney Resort hotels and other select hotels, and 3 days before the park visit for everyone else."),
    ("Is there an app for planning a Disney trip on iPhone?", "BeforeGo, our iPhone app, turns a screenshot of a guide, a pasted link or your own notes into a day-by-day plan, adds a scanned ticket or booking confirmation to it, and writes a packing list from your destination and dates. It is a general trip planner, not a Disney app."),
  ],
  "body": f"""<h1>Disney World itinerary template</h1>
<p class="lede">Fill in your trip right here: tap any dotted line to type, one block per day for the park, the morning, the afternoon, the evening and where you eat. Add days as you need them, then print the itinerary or save it as a PDF. Nothing leaves your browser.</p>
<div class="inv-wrap">
<div class="inv-tools"><button class="btn" id="print" type="button">Print / Save as PDF</button><button class="btn ghost" id="addday" type="button">+ Add a day</button></div>
<div class="inv itin" id="itin">
<div class="inv-head"><div><div class="inv-title">OUR DISNEY WORLD TRIP</div><p style="margin:6px 0 0"><span contenteditable="true">The Rivera family · 4 guests</span><br><span contenteditable="true">Hotel: your resort or hotel</span><br><span contenteditable="true">Tickets: 4 days, one park per day</span></p></div>
<div class="inv-meta"><div class="k">Arrive</div><p style="margin:0 0 10px"><span contenteditable="true">Sat, Mar 13, 2027</span></p><div class="k">Fly home</div><p style="margin:0"><span contenteditable="true">Thu, Mar 18, 2027</span></p></div></div>
<div class="days" id="days">
{DISNEY_DAYS}
</div>
<p class="notes" contenteditable="true">Book by: dining, 60 days ahead (Disney Resort hotel guests: the whole stay, 60 days before arrival) · Lightning Lane, 7 days before the stay (Disney Resort and select hotels) or 3 days before the park day</p>
</div></div>
<h2>How to plan the days</h2>
<ul><li><strong>Start with the parks.</strong> Write one park per day first; everything else fits around them.</li>
<li><strong>Give long trips a rest day.</strong> A pool morning in the middle keeps the last park days fun, especially with kids.</li>
<li><strong>Write down the booking dates.</strong> Dining and Lightning Lane open on set days before the trip; the note at the bottom of the template has them.</li>
<li><strong>Keep confirmation numbers on the plan.</strong> Type them next to the meal or the hotel, so they print with the day.</li></ul>
<p>Packing next? The <a href="/tools/disney-world-packing-list/">Disney World packing list</a> has the park rules on strollers, coolers and food.</p>
<h2>Dates to put on the calendar</h2>
<table><thead><tr><th>What</th><th>Opens</th><th>Who</th></tr></thead><tbody>
<tr><td>Dining reservations</td><td>60 days before arrival, for the whole stay (up to 10 nights)</td><td>Disney Resort hotel guests</td></tr>
<tr><td>Dining reservations</td><td>60 days before the meal</td><td>Everyone else</td></tr>
<tr><td>Lightning Lane passes</td><td>7 days before the first day of the stay</td><td>Guests of Disney Resort hotels and other select hotels</td></tr>
<tr><td>Lightning Lane passes</td><td>3 days before the park visit</td><td>Everyone else</td></tr>
</tbody></table>
<p>Disney’s own wording is on its <a href="{LL_URL}" rel="noopener">Lightning Lane passes</a> page and on each resort’s <a href="{DINE_URL}" rel="noopener">dining page</a>. To keep these dates in front of you, put them on your Lock Screen with the <a href="/tools/disney-countdown-widget-iphone/">Disney trip countdown widget</a>.</p>
<h2>On your iPhone</h2>
<p><a href="/beforego/">BeforeGo</a>, our trip planner app, turns a screenshot of a guide, a pasted link or your own notes into a day-by-day plan, and a scanned ticket or booking confirmation lands on the plan too. It writes the <a href="/tools/packing-list/">packing list</a> from your destination and dates, with reminders 7 days, 3 days, 24 hours and 3 hours before you leave. Free to start, no account.</p>
{DISNEY_NOTE.replace("The booking windows above", "The booking windows on this page")}"""})


# 7d2. 美区 BeforeGo 第一批内容页（10-26 已搬到 beforegotech.com，本站不再生成，见 BG_MOVED）——10-19（用户批「日本出发前清单 + Disney 打包清单」，选题与证据见 App 数据仓库
# reports/aso/beforego-us-content-topics-2026-10-19.md）。依据：Google 美国联想词 japan trip / travel checklist（pdf / 2026 / reddit）、
# things to do before traveling to japan（from usa）、medications banned in japan、can i bring sudafed to japan；disney packing list
# （printable / with kids / with toddlers / 2026）、disney prohibited items。
# 页面上的每条规定都在 10-19 读过官方原文：外务省免签国名单（美国、90 天）；厚生劳动省麻药取缔部 application2.html（安非他命 / Adderall 禁止、
# lisdexamfetamine 与 pseudoephedrine 属兴奋剂原料要事先许可、至少提前 14 天申请、精神药品按限量）；厚生劳动省药品进口 Q&A（一个月内的
# 普通处方药不用手续，超过要先办 Import Confirmation，几个工作日）；数字厅 Visit Japan Web 说明页 + 海关 2026-05-28 假网站警告（不收费）；
# 日本国家旅游局插头页（100 V、东 50 / 西 60 Hz）与 FAQ（Type A）、海关页（肉制品禁止）、免税改退税新闻（2026-11-01 起、出境前在海关办、
# 90 天内带出）；观光厅传单（2026-07-01 起出境税 ¥3,000，06-30 前出票按 ¥1,000，2 岁以下免）；JR 东日本 Welcome Suica Mobile 页（iOS、
# App 里开卡充值、部分国家入境后才能开）。Disney：disneyworld.disney.go.com/park-rules/（Prohibited Items、Attire）与 outside-food-and-drink FAQ。
# App 说法只用商店描述里的：按目的地生成打包清单（插头、货币、入境规定、交通 App）、7 天 / 3 天 / 24 小时 / 3 小时提醒。
CHECK_JS = """
(function(){var box=document.getElementById('chk');if(!box)return;var KEY=box.getAttribute('data-key');var saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
box.querySelectorAll('input[type=checkbox]').forEach(function(c){if(saved[c.getAttribute('data-id')])c.checked=true;});
box.addEventListener('change',function(e){if(e.target.type==='checkbox'){saved[e.target.getAttribute('data-id')]=e.target.checked;try{localStorage.setItem(KEY,JSON.stringify(saved))}catch(x){}}});
var p=document.getElementById('chk-print');if(p)p.addEventListener('click',function(){window.print();});
var c=document.getElementById('chk-copy');if(c)c.addEventListener('click',function(){var s='';box.querySelectorAll('h3,li').forEach(function(el){s+=(el.tagName==='H3'?'\\n'+el.textContent.toUpperCase()+'\\n':'- '+el.textContent.trim()+'\\n');});if(navigator.clipboard)navigator.clipboard.writeText(s.trim()).then(function(){c.textContent='Copied';});});})();
"""
def chk_groups(key, groups):
    out = ""
    for g, items in groups:
        lis = "".join(f'<li><label><input type="checkbox" data-id="{esc(key + "|" + re.sub(r"<[^>]+>", "", it)[:60])}"> <span>{it}</span></label></li>' for it in items)
        out += f'<h3>{g}</h3><ul class="check" style="columns:1">{lis}</ul>'
    return out
NCD_URL = "https://www.ncd.mhlw.go.jp/en/application2.html"
MHLW_QA_URL = "https://www.mhlw.go.jp/content/001686827.pdf"
MOFA_URL = "https://www.mofa.go.jp/j_info/visit/visa/short/novisa.html"
VJW_URL = "https://services.digital.go.jp/en/visit-japan-web/"
VJW_FAKE_URL = "https://www.customs.go.jp/english/news/20260528e.html"
JNTO_PLUG_URL = "https://www.japan.travel/en/plan/plug-and-electricity/"
JNTO_FAQ_URL = "https://www.japan.travel/en/faq/"
VJW_MANUAL_URL = "https://www.vjw.digital.go.jp/manual/main/visitjapanweb_manual_en.html"   # 1-3 Offline Usage：「Visit Japan Web can be used offline」（10-19 读原文；数字厅说明页写的「screenshots cannot be used」只指免税二维码）
JNTO_CUSTOMS_URL = "https://www.japan.travel/en/plan/customs-and-duty/"
SUICA_URL = "https://www.jreast.co.jp/en/multi/welcomesuicamobile/"
TAXFREE_URL = "https://www.japan.travel/en/ca/news/changes-are-coming-to-japans-tax-free-shopping/"
DEPTAX_URL = "https://www.mlit.go.jp/kankocho/content/001996466.pdf"
JAPAN_CHECK = chk_groups("jp", [
    ("When you book", ["Passport that stays valid for the whole trip. US citizens need no visa for a tourist stay of up to 90 days.",
                       "Check every medicine you take against the table below. Some common US prescriptions are banned in Japan.",
                       "If a medicine needs permission, apply at least 14 days before you fly.",
                       "More than a month's supply of an ordinary prescription medicine? Apply for Import Confirmation before you enter Japan.",
                       "Travel insurance that covers medical care abroad."]),
    ("Two weeks before", ["Set up Welcome Suica Mobile on your iPhone, or plan to buy an IC card at the station.",
                          "Mobile data for the trip: an eSIM or pocket Wi-Fi.",
                          "A credit card that works abroad, and your bank told you're traveling."]),
    ("One week before", ["Register on Visit Japan Web for immigration and customs. Every traveler, kids included, gets their own QR code.",
                         "Book anything that sells out: popular restaurants, museums, timed-entry sights."]),
    ("Three days before", ["Check the charger labels say 100–240 V. Japan runs at 100 V.",
                           "Plug adapter for any plug with a third, round pin. Japanese outlets take two flat pins (Type A); if one pin on your plug is wider than the other, pack an adapter to be safe.",
                           "Leave jerky and other meat snacks at home; Japan doesn't let meat products in.",
                           "Medicines in your carry-on, in their original packaging, with the permission or doctor’s certificate if the table below says you need one."]),
    ("The day before", ["Set up Visit Japan Web for offline use, so your QR code opens without a signal.",
                        "Some yen in cash.",
                        "Passport, phone, charger, cards, keys."]),
    ("In Japan", ["Tax-free shopping from November 1, 2026: you pay the price with tax and claim it back at customs when you leave.",
                  "Keep tax-free purchases where you can show them at the airport."]),
    ("Flying home", ["At the airport, file the tax-free refund at customs before you check in.",
                     "The departure tax is ¥3,000 from July 1, 2026, normally already in your ticket."]),
])
PAGES.append({"path": "/tools/japan-travel-checklist/", "lang": "en", "kind": "WebApplication", "app": "beforego", "published": "2026-10-19", "meta_top": True,
  "title": "Japan Travel Checklist 2026: What to Do Before You Fly From the US", "crumb": "Japan travel checklist",
  "description": "A Japan travel checklist to tick off and print: the 90-day visa-free stay, medicines Japan bans, Visit Japan Web, plugs, Suica, and the 2026 tax changes.",
  "hub_title": "Japan travel checklist", "hub_desc": "What to do before you fly, week by week: entry, medicines, Visit Japan Web, plugs, Suica.",
  "js": [CHECK_JS], "faq": [
    ("Do US citizens need a visa for Japan?", "Not for a tourist stay. Japan’s Ministry of Foreign Affairs lists the United States among the visa-exempt countries, with a 90-day period of stay granted on arrival."),
    ("Can I bring Adderall to Japan?", "No. Japan’s Narcotics Control Department says amphetamine, the active ingredient in Adderall, cannot be brought into Japan even for treatment. Lisdexamfetamine (Vyvanse) is allowed only with advance permission, applied for at least 14 days before you travel."),
    ("Can I bring Sudafed to Japan?", "Pseudoephedrine, the decongestant in Sudafed, is on Japan’s list of stimulants’ raw materials, which need advance permission. Check your product with the Narcotics Control Department before you pack it."),
    ("Do I need Visit Japan Web?", "For customs you don’t have to: Japan’s tourism board says the paper customs declaration form is available on the plane and at the airport. It saves time, though: you register your immigration and customs details before the flight, and one QR code covers both at the airport. Every traveler needs their own code. The service is free; Japan Customs warns about look-alike sites that charge a fee."),
    ("What plug does Japan use?", "Type A, the two flat pins also used in the US, at 100 volts. Eastern Japan runs at 50 Hz and western Japan, including Nagoya, Kyoto and Osaka, at 60 Hz. A plug with a third, round grounding pin needs an adapter; if one pin of your plug is wider than the other, bring an adapter to be safe."),
    ("Is there an app that makes a packing list for Japan?", "BeforeGo, our iPhone app, writes the packing list from your destination and dates, including the plugs, currency, entry rules and transit apps for where you are going, with reminders 7 days, 3 days, 24 hours and 3 hours before you leave. It does not check medicines for you; use Japan’s official pages for that."),
  ],
  "body": f"""<h1>Japan travel checklist: what to do before you fly</h1>
<p class="lede">A checklist for a trip to Japan from the US, in the order you need it, from the day you book to the flight home. Tick items off as you go; the ticks stay in this browser, and you can print the list. Every rule on this page links to the official page we checked it against.</p>
<div class="inv-wrap" id="chk" data-key="goka-japan-checklist">
<p class="print-title">Japan travel checklist</p>
<div class="inv-tools"><button class="btn" id="chk-print" type="button">Print / Save as PDF</button><button class="btn ghost" id="chk-copy" type="button">Copy as text</button></div>
{JAPAN_CHECK}
</div>
<h2>Medicines: what Japan bans and what needs permission</h2>
<p>This is where a trip to Japan can go wrong. Several medicines that are routine in the US are restricted in Japan, and one common ADHD medicine is banned outright.</p>
<table><thead><tr><th>Medicine</th><th>In Japan</th><th>What to do</th></tr></thead><tbody>
<tr><td>Adderall (amphetamine)</td><td>Banned, even with a prescription</td><td>Talk to your doctor about the trip well before you go</td></tr>
<tr><td>Vyvanse (lisdexamfetamine)</td><td>Stimulants’ raw material</td><td>Advance permission, applied for at least 14 days before you fly</td></tr>
<tr><td>Sudafed and other pseudoephedrine decongestants</td><td>Listed as a stimulants’ raw material</td><td>Check the product with the Narcotics Control Department before you pack it</td></tr>
<tr><td>Codeine, oxycodone, morphine and other narcotics</td><td>Narcotics</td><td>Advance permission, applied for at least 14 days before you fly</td></tr>
<tr><td>Zolpidem, alprazolam, diazepam and other psychotropics</td><td>Allowed up to a set amount</td><td>Check the amount on the Narcotics Control Department page; above it you need a doctor’s certificate</td></tr>
<tr><td>Other prescription medicines</td><td>Up to one month’s supply with no procedure</td><td>More than a month: apply online for Import Confirmation before you enter Japan</td></tr>
</tbody></table>
<p>Sources: the <a href="{NCD_URL}" rel="noopener">Narcotics Control Department</a> (banned substances, permission, the 14-day lead time) and the Ministry of Health’s <a href="{MHLW_QA_URL}" rel="noopener">Q&amp;A on bringing medicines into Japan</a> (the one-month rule and Import Confirmation). This is not medical or legal advice, and the rules can change: those two pages decide, and both list an email address for questions.</p>
<h2>Entry and arrival</h2>
<p>US citizens don’t need a visa for a tourist stay: Japan’s Ministry of Foreign Affairs lists the United States among the <a href="{MOFA_URL}" rel="noopener">visa-exempt countries</a>, with 90 days granted on arrival.</p>
<p>Register your immigration and customs details on <a href="{VJW_URL}" rel="noopener">Visit Japan Web</a> before the flight and you get one QR code that covers both at the airport. Every traveler needs their own, children included. Visit Japan Web also works offline; its <a href="{VJW_MANUAL_URL}" rel="noopener">official manual</a> shows how to set that up before you fly. The service is free, and Japan Customs <a href="{VJW_FAKE_URL}" rel="noopener">warns about look-alike sites</a> that charge for it. For customs it isn’t the only way: Japan’s tourism board says the paper <a href="{JNTO_CUSTOMS_URL}" rel="noopener">customs declaration form</a> is available on the plane and at the airport.</p>
<h2>Plugs, power and getting around</h2>
<ul><li><strong>Plugs.</strong> Japanese outlets take <a href="{JNTO_FAQ_URL}" rel="noopener">Type A plugs</a>, two flat pins like most US plugs, and the power is <a href="{JNTO_PLUG_URL}" rel="noopener">100 volts</a> everywhere: 50 Hz in eastern Japan and 60 Hz in the west, including Nagoya, Kyoto and Osaka. A plug with a third, round pin needs an adapter; if one pin of your plug is wider than the other, bring an adapter to be safe. Phone and laptop chargers labeled 100–240 V work anywhere.</li>
<li><strong>Suica on your iPhone.</strong> JR East’s <a href="{SUICA_URL}" rel="noopener">Welcome Suica Mobile</a> app issues a Suica and tops it up with a card in Apple Pay. Use it on trains, buses and in shops that show the IC logo. Some countries don’t allow issuing it before arrival; then set it up once you land.</li>
<li><strong>Food in your bag.</strong> Japan’s tourism board says <a href="{JNTO_CUSTOMS_URL}" rel="noopener">meat and meat products</a>, plants and plant products can’t be brought in. That includes jerky.</li></ul>
<h2>What changes in 2026</h2>
<table><thead><tr><th>Change</th><th>From</th><th>What it means for you</th></tr></thead><tbody>
<tr><td>Departure tax rises to ¥3,000</td><td>July 1, 2026</td><td>Usually already in the ticket price. Tickets issued by June 30, 2026 keep the old ¥1,000; children under 2 pay nothing.</td></tr>
<tr><td>Tax-free shopping becomes a refund</td><td>November 1, 2026</td><td>You pay the price with tax. At departure, file the refund at customs before you check in; goods must leave Japan within 90 days.</td></tr>
</tbody></table>
<p>Sources: the Japan Tourism Agency’s <a href="{DEPTAX_URL}" rel="noopener">International Tourist Tax notice</a> and Japan’s tourism board on the <a href="{TAXFREE_URL}" rel="noopener">tax-free shopping change</a>. Airport steps for the refund may still change; check your departure airport’s site before you fly.</p>
<h2>On your iPhone</h2>
<p><a href="/beforego/">BeforeGo</a>, our trip planner app, writes the packing list from your destination and dates: the plugs, currency, entry rules and transit apps for where you are going, with reminders 7 days, 3 days, 24 hours and 3 hours before you leave. Hand it a screenshot of a Japan guide and it files the places and days into your plan. It does not check medicines for you; the official pages above do that. For a general list, there is also the <a href="/tools/packing-list/">packing list generator</a>.</p>
<p class="meta" style="margin-top:18px">go ka is not a government site. The rules on this page were checked on the official pages linked above on October 19, 2026; check them again before you fly.</p>"""})

DISNEY_PACK = {"base": {   # {d} = 天数，{n} = 袜子 / 内衣按天、其余按半（PACK_JS）
  "Park bag": ["Phone with your tickets in the My Disney Experience app", "Refillable water bottle (not glass)", "Sunscreen", "Poncho", "Snacks that don’t need heating or a fridge", "Zip-top bag to keep the phone dry on water rides", "Hand sanitizer"],
  "Clothes": ["Underwear × {d}", "Socks × {d}", "T-shirts × {d}", "Shorts or light trousers × {n}", "A light layer for air-conditioned shows and restaurants", "Two pairs of broken-in walking shoes", "Hat and sunglasses", "Swimwear for the hotel pool", "Sleepwear"],
  "Toiletries & health": ["Toothbrush and toothpaste", "Travel-size shampoo and body wash", "Deodorant", "Any medication you take, plus a few days spare", "Blister plasters and pain relief", "After-sun lotion", "Insect repellent"],
  "Tech": ["Phone charger and a long cable", "Power bank, charged every night", "Headphones for the flight"],
  "Documents & money": ["Photo ID", "Hotel confirmation", "Dining reservation times", "Credit card and a little cash"]},
 "types": {
  "adults": [["Park bag", ["A small bag, well under the 24 × 15 × 18 in limit", "Handheld fan"]], ["Clothes", ["One nicer outfit for a sit-down dinner"]]],
  "kids": [["Park bag", ["Autograph book and a thick marker", "A change of clothes for each child", "Ear defenders for the fireworks", "Reusable ice packs for a cooler bag (no loose or dry ice)"]], ["Clothes", ["Kids’ outfits × {d}", "Kids’ pajamas", "Costume for kids under 14 (guests 14 and older can’t wear costumes)"]], ["Toiletries & health", ["Kids’ sunscreen", "Children’s pain and fever medicine"]]],
  "toddler": [["Park bag", ["Stroller no wider than 31 in and no longer than 52 in (no wagons)", "Stroller rain cover", "Diapers and wipes for the whole day", "Baby food (small glass baby-food jars are allowed)", "A change of clothes", "Clip-on stroller fan", "Ear defenders for the fireworks", "Reusable ice packs for milk or medicine (no loose or dry ice)"]], ["Clothes", ["Toddler outfits × {d}", "Toddler pajamas", "Swim diapers for the pool"]], ["Toiletries & health", ["Diapers for the whole trip", "Baby sunscreen", "Children’s pain and fever medicine"]]]}}
PARK_RULES_URL = "https://disneyworld.disney.go.com/park-rules/"
DISNEY_FOOD_URL = "https://disneyworld.disney.go.com/faq/parks/outside-food-and-drink/"
PAGES.append({"path": "/tools/disney-world-packing-list/", "lang": "en", "kind": "WebApplication", "app": "beforego", "published": "2026-10-19", "meta_top": True,
  "title": "Disney World Packing List (Printable) + What the Parks Don’t Allow", "crumb": "Disney World packing list",
  "description": "A free Disney World packing list to tick off, print or copy, for adults, kids or a toddler in a stroller, plus Disney’s rules on strollers, coolers and food.",
  "hub_title": "Disney World packing list", "hub_desc": "For adults, kids or a stroller; tick, print or copy. Plus the park rules on bags and food.",
  "js": [PACK_JS], "faq": [
    ("Can you bring food into Disney World?", "Yes. Disney lets you bring your own food and non-alcoholic drinks into the parks if they aren’t in glass, don’t need heating, reheating or refrigeration and don’t have a strong smell. Tell the security cast member about them at the entrance."),
    ("What size stroller is allowed at Disney World?", "No wider than 31 inches (79 cm) and no longer than 52 inches (132 cm). Wagons and stroller wagons are not allowed in the theme parks or water parks."),
    ("Can you bring a cooler into Disney World?", "Yes, if it is no larger than 24 inches long, 15 inches wide and 18 inches high, with or without wheels. Loose or dry ice is not allowed; Disney recommends reusable ice packs."),
    ("Are selfie sticks allowed at Disney World?", "No. Selfie sticks and other hand-held extension poles are not allowed in the theme parks or water parks. Tripods are allowed only if they fit inside a standard backpack and don’t extend over 6 feet."),
    ("Can adults wear costumes at Disney World?", "Not in the theme parks or water parks: guests 14 and older can’t wear costumes, and masks only for medical reasons. Special events such as the Halloween parties have their own costume rules."),
    ("Is there an app that makes a packing list for a Disney trip?", "BeforeGo, our iPhone app, writes a packing list from your destination and dates, with reminders 7 days, 3 days, 24 hours and 3 hours before you leave, and turns a screenshot of a guide into a day-by-day plan. It is a general trip planner, not a Disney app."),
  ],
  "body": f"""<h1>Disney World packing list</h1>
<p class="lede">Pick who’s coming and how long you’re staying, and you get a Walt Disney World packing list to tick off, print or copy. Ticks are saved on this device. Under it: what the parks don’t let you bring, from Disney’s own rules.</p>
<form class="calc pack-head" id="pack"><label>Who’s coming<select name="type"><option value="adults">Adults only</option><option value="kids" selected>With kids</option><option value="toddler">With a toddler (stroller)</option></select></label>
<label>Length<select name="days"><option value="4">4 days</option><option value="6" selected>6 days</option><option value="8">8 days</option></select></label><button type="submit" data-track-id="pack-submit">Make my list</button></form>
<div class="inv-wrap"><p class="print-title">Disney World packing list</p><div id="pack-out" hidden></div></div>
<p id="pack-actions" hidden><button class="btn ghost" id="pack-print" type="button">Print</button> <button class="btn ghost" id="pack-copy" type="button">Copy as text</button></p>
<script type="application/json" id="pack-data">{json.dumps(DISNEY_PACK)}</script>
<h2>What you can’t bring into the parks</h2>
<table><thead><tr><th>Item</th><th>Disney’s rule</th></tr></thead><tbody>
<tr><td>Strollers</td><td>No wider than 31 in (79 cm) and no longer than 52 in (132 cm). Wagons and stroller wagons are not allowed.</td></tr>
<tr><td>Bags and coolers</td><td>Nothing larger than 24 in long × 15 in wide × 18 in high (61 × 38 × 46 cm), with or without wheels. No loose or dry ice; reusable ice packs are recommended.</td></tr>
<tr><td>Glass</td><td>No glass containers, except small ones such as baby-food jars.</td></tr>
<tr><td>Alcohol</td><td>Not allowed, except at the Disney Resort hotels.</td></tr>
<tr><td>Selfie sticks and tripods</td><td>No selfie sticks or extension poles in the theme parks or water parks. Tripods only if they fit inside a standard backpack and don’t extend over 6 ft.</td></tr>
<tr><td>Folding chairs</td><td>Not allowed in the theme parks, the water parks or Disney Springs.</td></tr>
<tr><td>Recreational devices</td><td>No drones, remote-control toys, skateboards, scooters, inline skates or shoes with built-in wheels. Mobility devices are a separate rule: they need at least three wheels.</td></tr>
<tr><td>Costumes and masks</td><td>Not for guests 14 and older (masks only for medical reasons). Clothing that drags on the ground isn’t allowed either.</td></tr>
<tr><td>Balloons and plastic straws</td><td>Not allowed at Disney’s Animal Kingdom or the water parks.</td></tr>
</tbody></table>
<p>All from the Walt Disney World <a href="{PARK_RULES_URL}" rel="noopener">Property Rules</a>, which also list weapons, fireworks and other obvious ones. Disney can refuse any bag or item at security.</p>
<h2>Food and drinks</h2>
<p>You can bring your own food and non-alcoholic drinks into the parks, as long as they aren’t in glass, don’t need heating, reheating or refrigeration and don’t have a strong smell. Tell the security cast member about them when you go in (<a href="{DISNEY_FOOD_URL}" rel="noopener">Disney’s food and drink FAQ</a>).</p>
<h2>Three packing habits that pay off</h2>
<ul><li><strong>Two pairs of shoes.</strong> Swap them every day, so a soaked pair from a water ride or a downpour has a day to dry.</li>
<li><strong>Pack the park bag the night before.</strong> Charged power bank, sunscreen, poncho, snacks, the day’s reservation times.</li>
<li><strong>Write down what you forgot.</strong> It is the first line of the next trip’s list.</li></ul>
<h2>Plan the days too</h2>
<p>Put the parks and dining times in the <a href="/tools/disney-world-itinerary-template/">Disney World itinerary template</a>, and count down to the trip on your Lock Screen with the <a href="/tools/disney-countdown-widget-iphone/">Disney trip countdown widget</a>. For other trips there is the general <a href="/tools/packing-list/">packing list generator</a>.</p>
<h2>On your iPhone</h2>
<p><a href="/beforego/">BeforeGo</a>, our trip planner app, writes the packing list from your destination and dates, with reminders 7 days, 3 days, 24 hours and 3 hours before you leave, and turns a screenshot of a guide or a pasted link into a day-by-day plan. Free to start, no account.</p>
{DISNEY_NOTE.replace("The booking windows above were checked on disneyworld.disney.go.com on October 17, 2026", "The park rules above were checked on disneyworld.disney.go.com on October 19, 2026")}"""})


# 7e. 德国：InvoiceQR 的德语模板页（de）——10-17（用户：「invoice 的优化方向可以是德国」）
# 依据：10-17 Google 德国联想词「rechnungsvorlage kleinunternehmer / kostenlos / ohne anmeldung」「rechnung kleinunternehmer muster / pflichtangaben /
# ohne umsatzsteuer / ohne steuernummer」「e-rechnung kleinunternehmer」「angebot vorlage (pdf / kostenlos / dienstleistung)」「rechnung schreiben app iphone」。
# 法条全部逐条读过 gesetze-im-internet.de 原文（10-17）：§ 19 Abs. 1 UStG（25 000 / 100 000 €）、§ 14 Abs. 1/2/4 UStG（Pflichtangaben、E-Rechnung、
# Zustimmung）、§ 14b（8 年）、§ 27 Abs. 38 UStG（2025–26 / 2027 ≤ 800 000 € 过渡）、§ 33 / § 34a UStDV（Kleinbetrag 250 €、Kleinunternehmer 6 项、
# 两者都可永远发 sonstige Rechnung）、BGB § 145 / § 148 / § 632 Abs. 3 / § 649。BMF 的 E-Rechnung FAQ 有验证码打不开，没引用。
# App 说法只用 tools/store/invoiceqr.json de-DE 描述（1.1.24），外加 App 代码里核实过的：「Keine Steuer」、Steuernummer 印在单据上、
# 「Bedingungen & Notizen」印在单据底部、编号自动连号（手写 2026-001 后接 2026-002）。App 只出 PDF，不出 XRechnung / ZUGFeRD。
DE_NOTE = ('<p class="meta" style="margin-top:18px"><strong>Hinweis:</strong> Diese Seite fasst die gesetzlichen Angaben zusammen und ersetzt keine Steuerberatung. '
           'Die Vorlage erzeugt ein PDF, keine E-Rechnung in einem strukturierten Format wie XRechnung oder ZUGFeRD. Stand: Oktober 2026.</p>')
DE_APP = ('Ja: Smart Rechnung & Angebot, unsere App für iPhone und iPad. Sie merkt sich Kunden, Artikel und Steuersätze, nummeriert Rechnungen fortlaufend '
          'und wandelt ein Angebot nach der Zusage mit einem Tipp in eine Rechnung um. Als Kleinunternehmer wählst du „Keine Steuer“ und speicherst den Hinweis '
          'nach § 19 UStG als Klausel. Dein erstes Dokument ist kostenlos, ohne Konto.')
DE_TOOLS = ('<div class="inv-tools"><button class="btn" id="print" type="button">Drucken / als PDF speichern</button>'
            '<button class="btn ghost" id="addrow" type="button">+ Position hinzufügen</button></div>')

PAGES.append({"path": "/tools/de/rechnungsvorlage-kleinunternehmer/", "lang": "de", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-10-17",
  "title": "Rechnungsvorlage Kleinunternehmer kostenlos: Muster nach § 19 UStG", "crumb": "Rechnung Kleinunternehmer",
  "description": "Kostenlose Rechnungsvorlage für Kleinunternehmer: online ausfüllen, als PDF speichern. Mit Hinweis nach § 19 UStG und allen Pflichtangaben nach § 34a UStDV.",
  "hub_title": "Rechnungsvorlage für Kleinunternehmer", "hub_desc": "Ohne Umsatzsteuer, mit dem Hinweis nach § 19 UStG – im Browser ausfüllen und als PDF speichern.",
  "js": [INVOICE_JS], "faq": [
    ("Ist die Vorlage kostenlos?", "Ja. Alles läuft in deinem Browser: kein Konto, kein Wasserzeichen, es wird nichts hochgeladen. Ausfüllen, dann drucken oder als PDF speichern."),
    ("Welcher Satz muss auf die Rechnung?", "Ein Hinweis darauf, dass für die Leistung die Steuerbefreiung für Kleinunternehmer gilt (§ 34a Nr. 5 UStDV). Einen festen Wortlaut schreibt das Gesetz nicht vor; üblich ist „Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.“"),
    ("Brauche ich eine Steuernummer auf der Rechnung?", "In der Regel ja. § 34a UStDV verlangt die Steuernummer vom Finanzamt oder die Umsatzsteuer-Identifikationsnummer bzw. Kleinunternehmer-Identifikationsnummer vom Bundeszentralamt für Steuern. Ausnahme: Bei Rechnungen bis 250 € brutto reichen die Angaben einer Kleinbetragsrechnung (§ 33 UStDV), da ist keine Steuernummer nötig."),
    ("Darf ich als Kleinunternehmer Umsatzsteuer ausweisen?", "Nein. Wer Umsatzsteuer auf die Rechnung schreibt, obwohl er dazu nicht berechtigt ist, schuldet den ausgewiesenen Betrag (§ 14c UStG). Die Vorlage hat deshalb keine Steuerzeile."),
    ("Muss ich als Kleinunternehmer E-Rechnungen schreiben?", "Nein. Eine Kleinunternehmer-Rechnung darf immer als sonstige Rechnung übermittelt werden, also auf Papier oder, wenn der Kunde zustimmt, als PDF (§ 34a Satz 4 UStDV, § 14 Abs. 1 UStG). Empfangen musst du E-Rechnungen anderer Unternehmen trotzdem können."),
    ("Wie speichere ich die Rechnung als PDF?", "Klicke auf „Drucken / als PDF speichern“ und wähle im Druckfenster „Als PDF speichern“. Gedruckt wird nur die Rechnung, der Rest der Seite wird ausgeblendet."),
    ("Gibt es eine App für Kleinunternehmer-Rechnungen auf dem iPhone?", DE_APP),
  ],
  "more": [
    ("Rechnung als Kleinunternehmer ohne Steuernummer – geht das?", "Nur bei Rechnungen bis 250 € brutto: Für diese Kleinbetragsrechnungen genügen nach § 33 UStDV dein Name und deine Anschrift, das Datum, die Leistung und der Betrag mit dem Hinweis auf die Steuerbefreiung. Darüber gehört die Steuernummer oder eine der beiden Identifikationsnummern zu den Pflichtangaben nach § 34a UStDV."),
    ("Rechnung an eine Privatperson als Kleinunternehmer?", "Es gelten dieselben Angaben wie bei Firmenkunden: dein Name und deine Anschrift, Name und Anschrift des Kunden, Steuernummer, Datum, Leistung, Betrag und der Hinweis nach § 19 UStG; bis 250 € reicht eine Kleinbetragsrechnung. Die Vorlage oben passt für beides."),
    ("Was hat sich 2025 für Kleinunternehmer geändert?", "Seit dem 1. Januar 2025 gelten die Grenzen von 25.000 € im Vorjahr und 100.000 € im laufenden Jahr (§ 19 Abs. 1 UStG), und die Pflichtangaben für Kleinunternehmer-Rechnungen stehen in einer eigenen Vorschrift, § 34a UStDV."),
    ("Wie lange muss ich die Rechnungen aufbewahren?", "Acht Jahre, gerechnet ab dem Ende des Jahres, in dem die Rechnung ausgestellt wurde (§ 14b Abs. 1 UStG)."),
  ],
  "body": f"""<h1>Rechnungsvorlage für Kleinunternehmer (§ 19 UStG)</h1>
<p class="lede">Als Kleinunternehmer weist du keine Umsatzsteuer aus. Stattdessen steht auf der Rechnung ein Hinweis auf die Steuerbefreiung, zum Beispiel: <strong>„Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.“</strong> Die Vorlage unten hat diesen Satz schon drin. Klicke in ein gestricheltes Feld, um es zu ändern, und speichere die Rechnung danach als PDF. Es wird nichts hochgeladen.</p>
<div class="inv-wrap">
{DE_TOOLS}
<div class="inv" id="inv" data-newitem="Leistung" data-days="14">
<div class="inv-head"><div><div class="inv-title">RECHNUNG</div><p style="margin:6px 0 0"><span contenteditable="true">Dein Name / Firmenname</span><br><span contenteditable="true">Musterstraße 1, 12345 Musterstadt</span><br><span contenteditable="true">Steuernummer: 12/345/67890</span></p></div>
<div class="inv-meta"><div class="k">Rechnungsnummer</div><p style="margin:0 0 10px"><span contenteditable="true">2026-001</span></p><div class="k">Rechnungsdatum</div><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><div class="k">Leistungsdatum</div><p style="margin:0"><span contenteditable="true">wie Rechnungsdatum</span></p></div></div>
<div class="inv-parties"><div><div class="k">Rechnung an</div><p style="margin:0"><span contenteditable="true">Name des Kunden</span><br><span contenteditable="true">Straße und Hausnummer</span><br><span contenteditable="true">PLZ Ort</span></p></div>
<div><div class="k">Zahlung</div><p style="margin:0"><span contenteditable="true">Zahlbar innerhalb von 14 Tagen ohne Abzug</span><br><span contenteditable="true">IBAN DE00 0000 0000 0000 0000 00</span></p></div></div>
<table><thead><tr><th>Leistung</th><th>Menge</th><th>Einzelpreis</th><th>Betrag</th></tr></thead>
<tbody><tr><td contenteditable="true">Gestaltung Website-Startseite</td><td contenteditable="true">1</td><td contenteditable="true">850,00</td><td>850,00</td></tr>
<tr><td contenteditable="true">Fotos bearbeiten (Stunden)</td><td contenteditable="true">3</td><td contenteditable="true">45,00</td><td>135,00</td></tr></tbody></table>
<div class="totals"><div class="grand"><span>Gesamtbetrag</span><span><span id="total">985,00</span> €</span></div></div>
<p class="notes" contenteditable="true">Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.</p>
</div></div>
<h2>Was muss auf eine Kleinunternehmer-Rechnung?</h2>
<p>§ 34a UStDV nennt sechs Angaben:</p>
<ol><li><strong>Name und Anschrift</strong> von dir und von deinem Kunden, jeweils vollständig.</li><li>Deine <strong>Steuernummer</strong> vom Finanzamt oder deine Umsatzsteuer-Identifikationsnummer bzw. Kleinunternehmer-Identifikationsnummer.</li><li>Das <strong>Ausstellungsdatum</strong>.</li><li><strong>Menge und Art</strong> der gelieferten Waren oder <strong>Umfang und Art</strong> der Leistung.</li><li>Den <strong>Betrag in einer Summe</strong> mit dem <strong>Hinweis auf die Steuerbefreiung</strong> für Kleinunternehmer.</li><li>Das Wort <strong>„Gutschrift“</strong>, aber nur, wenn dein Kunde die Rechnung für dich ausstellt.</li></ol>
<p>Rechnungsnummer und Leistungsdatum verlangt § 34a nicht. Die Vorlage hat trotzdem beides, weil Kunden und Buchhaltung sie oft erwarten; du kannst die Felder auch leer lassen. Bei Rechnungen bis 250 € brutto genügen sogar weniger Angaben, dann ohne Steuernummer und ohne Kundenadresse (§ 33 UStDV).</p>
<h2>Wer ist Kleinunternehmer?</h2>
<p>Kleinunternehmer bist du, wenn dein Gesamtumsatz <strong>im Vorjahr höchstens 25.000 €</strong> betragen hat und <strong>im laufenden Jahr 100.000 € nicht überschreitet</strong> (§ 19 Abs. 1 UStG). Überschreitest du die 100.000 € im laufenden Jahr, fällt die Befreiung noch im selben Jahr weg. Kläre dann mit deinem Steuerberater, ab welcher Rechnung du Umsatzsteuer ausweisen musst.</p>
<p>Du kannst auf die Regelung auch verzichten und ganz normal mit Umsatzsteuer abrechnen; daran bist du dann mindestens fünf Jahre gebunden (§ 19 Abs. 3 UStG). Für Rechnungen mit Umsatzsteuer nimm die <a href="/tools/de/rechnungsvorlage/">Rechnungsvorlage mit 19 % MwSt.</a></p>
<h2>Kleinunternehmer und E-Rechnung</h2>
<table><thead><tr><th></th><th>Was gilt</th><th>Grundlage</th></tr></thead><tbody>
<tr><td>Rechnungen schreiben</td><td>Papier bleibt erlaubt, ein PDF mit Zustimmung des Kunden, auch nach 2027. Eine E-Rechnung musst du nicht ausstellen.</td><td>§ 34a Satz 4 UStDV</td></tr>
<tr><td>Rechnungen empfangen</td><td>Seit 2025 brauchen andere Unternehmen deine Zustimmung nicht mehr, um dir eine E-Rechnung zu schicken. Du musst sie also annehmen können.</td><td>§ 14 Abs. 1 und 2 UStG</td></tr>
</tbody></table>
<p>Du schreibst deine Rechnungen lieber auf dem iPhone? <a href="/tools/de/rechnung-schreiben-app-iphone/">So geht es Schritt für Schritt</a>, auch mit dem Hinweis nach § 19 UStG.</p>
{DE_NOTE}"""})

PAGES.append({"path": "/tools/de/rechnungsvorlage/", "lang": "de", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-10-17",
  "title": "Rechnungsvorlage kostenlos ohne Anmeldung: ausfüllen, PDF speichern", "crumb": "Rechnungsvorlage",
  "description": "Kostenlose Rechnungsvorlage ohne Anmeldung: Umsatzsteuer und Summe rechnen sich selbst, PDF speichern. Mit Pflichtangaben nach § 14 UStG und E-Rechnung-Fristen.",
  "hub_title": "Rechnungsvorlage mit MwSt.", "hub_desc": "Netto, 19 % Umsatzsteuer und Gesamtbetrag rechnen sich selbst. Drucken oder als PDF speichern.",
  "js": [INVOICE_JS], "faq": [
    ("Ist die Rechnungsvorlage kostenlos?", "Ja, und ohne Anmeldung. Alles läuft in deinem Browser: kein Konto, kein Wasserzeichen, es wird nichts hochgeladen."),
    ("Welchen Steuersatz trage ich ein?", "Der Regelsteuersatz ist 19 %. Für bestimmte Waren und Leistungen gilt der ermäßigte Satz von 7 %. Den Satz in der Vorlage kannst du anklicken und ändern; Steuer und Gesamtbetrag rechnen sich neu."),
    ("Wie muss die Rechnungsnummer aussehen?", "Fortlaufend und einmalig (§ 14 Abs. 4 Nr. 4 UStG). Sie darf aus einer oder mehreren Zahlenreihen bestehen, zum Beispiel 2026-001, 2026-002 und so weiter."),
    ("Ist eine Rechnung als PDF noch erlaubt?", "Ja, wenn der Empfänger zustimmt (§ 14 Abs. 1 UStG). An Privatkunden ohne Frist. An andere Unternehmen im Inland für Leistungen bis Ende 2026; für Leistungen im Jahr 2027 nur, wenn dein Gesamtumsatz im Vorjahr höchstens 800.000 € betrug. Ab 2028 ist dort die E-Rechnung Pflicht. Kleinunternehmer und Rechnungen bis 250 € dürfen weiter Papier oder PDF verwenden."),
    ("Wie lange muss ich Rechnungen aufbewahren?", "Acht Jahre, gerechnet ab dem Ende des Jahres, in dem die Rechnung ausgestellt wurde (§ 14b Abs. 1 UStG)."),
    ("Wie speichere ich die Rechnung als PDF?", "Klicke auf „Drucken / als PDF speichern“ und wähle im Druckfenster „Als PDF speichern“. Gedruckt wird nur die Rechnung."),
    ("Gibt es eine App zum Rechnungen schreiben auf dem iPhone?", DE_APP),
  ],
  "more": [
    ("Rechnung ohne MwSt. schreiben – wann geht das?", "Wenn keine Umsatzsteuer anfällt oder dein Kunde sie schuldet: als Kleinunternehmer (§ 19 UStG), bei steuerfreien Leistungen oder wenn die Steuerschuld auf den Kunden übergeht (§ 13b UStG). Statt Steuersatz und Steuerbetrag steht dann ein Hinweis auf der Rechnung. Für Kleinunternehmer gibt es eine eigene <a href=\"/tools/de/rechnungsvorlage-kleinunternehmer/\">Rechnungsvorlage nach § 19 UStG</a>."),
    ("Was ist eine Kleinbetragsrechnung?", "Eine Rechnung bis 250 € brutto. Sie braucht weniger Angaben (§ 33 UStDV): Name und Anschrift des Leistenden, Datum, Menge und Art der Leistung sowie den Bruttobetrag mit Steuersatz."),
    ("Was ist der Unterschied zwischen Rechnungsdatum und Leistungsdatum?", "Das Rechnungsdatum ist der Tag, an dem du die Rechnung ausstellst. Das Leistungsdatum ist der Tag oder Zeitraum, in dem du geliefert oder gearbeitet hast. Beides gehört auf die Rechnung (§ 14 Abs. 4 Nr. 3 und 6 UStG); ist es derselbe Tag, reicht ein Vermerk wie „Leistungsdatum entspricht Rechnungsdatum“."),
  ],
  "body": f"""<h1>Rechnungsvorlage kostenlos</h1>
<p class="lede">Füll die Rechnung direkt hier aus: Klicke in ein gestricheltes Feld, um es zu ändern. Beträge, 19 % Umsatzsteuer und Gesamtbetrag rechnen sich selbst. Danach druckst du sie oder speicherst sie als PDF. Es wird nichts hochgeladen.</p>
<div class="inv-wrap">
{DE_TOOLS}
<div class="inv" id="inv" data-newitem="Leistung" data-days="14">
<div class="inv-head"><div><div class="inv-title">RECHNUNG</div><p style="margin:6px 0 0"><span contenteditable="true">Dein Firmenname</span><br><span contenteditable="true">Musterstraße 1, 12345 Musterstadt</span><br><span contenteditable="true">Steuernummer: 12/345/67890</span></p></div>
<div class="inv-meta"><div class="k">Rechnungsnummer</div><p style="margin:0 0 10px"><span contenteditable="true">2026-001</span></p><div class="k">Rechnungsdatum</div><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><div class="k">Leistungsdatum</div><p style="margin:0 0 10px"><span contenteditable="true">wie Rechnungsdatum</span></p><div class="k">Fällig am</div><p style="margin:0"><span contenteditable="true" id="due"></span></p></div></div>
<div class="inv-parties"><div><div class="k">Rechnung an</div><p style="margin:0"><span contenteditable="true">Firma oder Name des Kunden</span><br><span contenteditable="true">Straße und Hausnummer</span><br><span contenteditable="true">PLZ Ort</span></p></div>
<div><div class="k">Bankverbindung</div><p style="margin:0"><span contenteditable="true">Musterbank</span><br><span contenteditable="true">IBAN DE00 0000 0000 0000 0000 00</span></p></div></div>
<table><thead><tr><th>Leistung</th><th>Menge</th><th>Einzelpreis</th><th>Betrag</th></tr></thead>
<tbody><tr><td contenteditable="true">Beratung (Stunden)</td><td contenteditable="true">6</td><td contenteditable="true">80,00</td><td>480,00</td></tr>
<tr><td contenteditable="true">Fahrtkosten pauschal</td><td contenteditable="true">1</td><td contenteditable="true">35,00</td><td>35,00</td></tr></tbody></table>
<div class="totals"><div><span>Nettobetrag</span><span><span id="sub">515,00</span> €</span></div><div><span>Umsatzsteuer <span contenteditable="true" id="taxrate">19</span> %</span><span><span id="tax">97,85</span> €</span></div><div class="grand"><span>Gesamtbetrag</span><span><span id="total">612,85</span> €</span></div></div>
<p class="notes" contenteditable="true">Vielen Dank für Ihren Auftrag. Bitte überweisen Sie den Gesamtbetrag bis zum Fälligkeitsdatum ohne Abzug.</p>
</div></div>
<h2>Pflichtangaben einer Rechnung (§ 14 Abs. 4 UStG)</h2>
<ol><li><strong>Name und Anschrift</strong> von dir und von deinem Kunden, jeweils vollständig.</li><li>Deine <strong>Steuernummer</strong> oder deine <strong>Umsatzsteuer-Identifikationsnummer</strong>.</li><li>Das <strong>Ausstellungsdatum</strong>.</li><li>Eine <strong>fortlaufende Rechnungsnummer</strong>, die du nur einmal vergibst.</li><li><strong>Menge und Art</strong> der gelieferten Waren oder <strong>Umfang und Art</strong> der Leistung.</li><li>Den <strong>Zeitpunkt der Lieferung oder Leistung</strong>.</li><li>Das <strong>Entgelt</strong>, also den Nettobetrag, aufgeteilt nach Steuersätzen, und jede vorher vereinbarte Minderung wie Skonto oder Rabatt.</li><li>Den <strong>Steuersatz und den Steuerbetrag</strong>, oder bei einer Steuerbefreiung einen Hinweis darauf.</li></ol>
<p>Zwei weitere Angaben brauchst du nur in Sonderfällen: einen Hinweis auf die Aufbewahrungspflicht des Kunden bei bestimmten Leistungen rund um ein Grundstück an Privatpersonen, und das Wort „Gutschrift“, wenn der Kunde die Rechnung ausstellt.</p>
<h2>Kleinbetragsrechnung bis 250 €</h2>
<p>Bei einem Gesamtbetrag bis 250 € reichen weniger Angaben (§ 33 UStDV): dein Name und deine Anschrift, das Datum, Menge und Art der Leistung und der Bruttobetrag mit dem Steuersatz. Name des Kunden, Steuernummer und Rechnungsnummer sind dann nicht nötig.</p>
<h2>Ab wann ist die E-Rechnung Pflicht?</h2>
<p>Die Pflicht betrifft nur Rechnungen an andere Unternehmen in Deutschland. Gemeint ist ein strukturiertes Format nach der europäischen Norm, zum Beispiel XRechnung oder ZUGFeRD; ein PDF zählt nicht dazu.</p>
<table><thead><tr><th>Leistung erbracht</th><th>Papier oder PDF an Unternehmen</th><th>Grundlage</th></tr></thead><tbody>
<tr><td>2025 und 2026</td><td>Erlaubt, wenn die Rechnung bis 31. Dezember 2026 übermittelt wird; ein PDF nur mit Zustimmung des Kunden.</td><td>§ 27 Abs. 38 Nr. 1 UStG</td></tr>
<tr><td>2027</td><td>Nur noch, wenn dein Gesamtumsatz im Vorjahr höchstens 800.000 € betrug und die Rechnung bis 31. Dezember 2027 übermittelt wird; ein PDF weiterhin nur mit Zustimmung.</td><td>§ 27 Abs. 38 Nr. 2 UStG</td></tr>
<tr><td>ab 2028</td><td>Nicht mehr: Es muss eine E-Rechnung sein.</td><td>§ 14 Abs. 2 UStG</td></tr>
</tbody></table>
<p>Ausgenommen bleiben Rechnungen an Privatpersonen, Kleinbetragsrechnungen bis 250 € (§ 33 UStDV) und Rechnungen von Kleinunternehmern (§ 34a UStDV), dafür gibt es die <a href="/tools/de/rechnungsvorlage-kleinunternehmer/">Rechnungsvorlage für Kleinunternehmer</a>. Noch kein Auftrag? Dann schick zuerst ein <a href="/tools/de/angebot-vorlage/">Angebot</a>.</p>
{DE_NOTE}"""})

PAGES.append({"path": "/tools/de/angebot-vorlage/", "lang": "de", "kind": "WebApplication", "app": "invoiceqr", "published": "2026-10-17",
  "title": "Angebotsvorlage kostenlos: Angebot online ausfüllen, als PDF speichern", "crumb": "Angebotsvorlage",
  "description": "Kostenlose Angebotsvorlage für Selbstständige und Handwerker: Umsatzsteuer und Summe rechnen sich selbst, mit Gültigkeitsdatum. Als PDF speichern.",
  "hub_title": "Angebotsvorlage", "hub_desc": "Mit Gültigkeitsdatum, Positionen und 19 % MwSt. Ausfüllen, als PDF schicken, nach der Zusage abrechnen.",
  "js": [INVOICE_JS], "faq": [
    ("Ist die Angebotsvorlage kostenlos?", "Ja, und ohne Anmeldung. Alles läuft in deinem Browser: kein Konto, kein Wasserzeichen, es wird nichts hochgeladen."),
    ("Wie lange ist ein Angebot gültig?", "So lange, wie du es hineinschreibst: Setzt du eine Frist, kann der Kunde nur innerhalb dieser Frist annehmen (§ 148 BGB). In der Vorlage steht automatisch ein Datum 30 Tage nach heute; klicke darauf, um es zu ändern."),
    ("Ist ein Angebot verbindlich?", "Ja. Wer ein Angebot macht, ist daran gebunden, es sei denn, er schließt das aus (§ 145 BGB), zum Beispiel mit dem Zusatz „freibleibend“."),
    ("Was ist der Unterschied zwischen Angebot und Kostenvoranschlag?", "Ein Angebot nennt einen Preis, an den du gebunden bist. Ein Kostenvoranschlag ist eine Schätzung. Zeichnet sich bei einem Werkvertrag eine wesentliche Überschreitung ab, musst du das dem Kunden unverzüglich anzeigen; kündigt er deshalb, steht dir nur die Vergütung für die bereits geleistete Arbeit samt Auslagen zu (§ 649 BGB). Bezahlt wird ein Kostenvoranschlag im Zweifel nicht (§ 632 Abs. 3 BGB)."),
    ("Ist ein Angebot eine Rechnung?", "Nein. Das Angebot kommt vor dem Auftrag, die Rechnung danach. Wenn der Kunde zusagt, übernimm die Positionen in die Rechnungsvorlage."),
    ("Gibt es eine App für Angebote auf dem iPhone?", DE_APP),
  ],
  "more": [
    ("Angebotsvorlage für Dienstleistung oder Handwerk?", "Die Vorlage passt für beides: Jede Position hat eine Menge, du kannst Stunden, Quadratmeter oder Pauschalen eintragen. Mit „+ Position hinzufügen“ kommen weitere Zeilen dazu."),
    ("Angebot als Kleinunternehmer ohne Umsatzsteuer?", "Setze den Steuersatz in der Vorlage auf 0 und schreib den Hinweis „Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.“ in die Notiz. Die passende Rechnung danach gibt es als <a href=\"/tools/de/rechnungsvorlage-kleinunternehmer/\">Rechnungsvorlage für Kleinunternehmer</a>."),
  ],
  "body": f"""<h1>Angebotsvorlage kostenlos</h1>
<p class="lede">Füll das Angebot direkt hier aus: Klicke in ein gestricheltes Feld, um es zu ändern. Beträge, 19 % Umsatzsteuer und Gesamtbetrag rechnen sich selbst, und als Gültigkeit sind schon 30 Tage eingetragen. Danach druckst du es oder speicherst es als PDF. Es wird nichts hochgeladen.</p>
<div class="inv-wrap">
{DE_TOOLS}
<div class="inv" id="inv" data-newitem="Position" data-days="30">
<div class="inv-head"><div><div class="inv-title">ANGEBOT</div><p style="margin:6px 0 0"><span contenteditable="true">Dein Firmenname</span><br><span contenteditable="true">Musterstraße 1, 12345 Musterstadt</span><br><span contenteditable="true">info@beispiel.de · 0170 0000000</span></p></div>
<div class="inv-meta"><div class="k">Angebotsnummer</div><p style="margin:0 0 10px"><span contenteditable="true">AN-2026-001</span></p><div class="k">Datum</div><p style="margin:0 0 10px"><span contenteditable="true" id="today"></span></p><div class="k">Gültig bis</div><p style="margin:0"><span contenteditable="true" id="due"></span></p></div></div>
<div class="inv-parties"><div><div class="k">Angebot für</div><p style="margin:0"><span contenteditable="true">Name des Kunden</span><br><span contenteditable="true">Straße und Hausnummer</span><br><span contenteditable="true">PLZ Ort</span></p></div>
<div><div class="k">Ausführung</div><p style="margin:0"><span contenteditable="true">Beginn nach Auftragserteilung</span><br><span contenteditable="true">Dauer etwa 3 Arbeitstage</span></p></div></div>
<table><thead><tr><th>Position</th><th>Menge</th><th>Einzelpreis</th><th>Betrag</th></tr></thead>
<tbody><tr><td contenteditable="true">Malerarbeiten Wohnzimmer (m²)</td><td contenteditable="true">42</td><td contenteditable="true">12,50</td><td>525,00</td></tr>
<tr><td contenteditable="true">Material: Farbe und Abdeckung</td><td contenteditable="true">1</td><td contenteditable="true">140,00</td><td>140,00</td></tr></tbody></table>
<div class="totals"><div><span>Nettobetrag</span><span><span id="sub">665,00</span> €</span></div><div><span>Umsatzsteuer <span contenteditable="true" id="taxrate">19</span> %</span><span><span id="tax">126,35</span> €</span></div><div class="grand"><span>Gesamtbetrag</span><span><span id="total">791,35</span> €</span></div></div>
<p class="notes" contenteditable="true">Dieses Angebot ist bis zum oben genannten Datum gültig. Wir freuen uns auf Ihren Auftrag.</p>
</div></div>
<h2>Was gehört in ein Angebot?</h2>
<ul><li><strong>Das Wort „Angebot“</strong> und eine Angebotsnummer, damit du es später wiederfindest.</li><li><strong>Datum</strong> und <strong>Gültigkeit</strong>: bis wann der Kunde annehmen kann.</li><li><strong>Deine Daten</strong> und die Daten des Kunden.</li><li><strong>Positionen</strong> mit Beschreibung, Menge, Einzelpreis und Betrag.</li><li><strong>Nettobetrag, Umsatzsteuer</strong> mit Steuersatz und <strong>Gesamtbetrag</strong>.</li><li><strong>Bedingungen</strong>: Ausführungszeitraum, Zahlungsziel und eine Anzahlung, wenn du eine willst.</li></ul>
<h2>Angebot, Kostenvoranschlag oder Rechnung</h2>
<table><thead><tr><th>Dokument</th><th>Wann</th><th>Was es bedeutet</th></tr></thead><tbody>
<tr><td>Angebot</td><td>Vor dem Auftrag</td><td>Fester Preis. Du bist daran gebunden, bis die Frist abläuft (§§ 145, 148 BGB).</td></tr>
<tr><td>Kostenvoranschlag</td><td>Vor dem Auftrag</td><td>Schätzung. Eine wesentliche Überschreitung musst du unverzüglich anzeigen; kündigt der Kunde deshalb, bekommst du nur die geleistete Arbeit bezahlt (§ 649 BGB).</td></tr>
<tr><td>Rechnung</td><td>Nach der Leistung</td><td>Rechnet ab, mit allen Pflichtangaben nach § 14 UStG.</td></tr>
</tbody></table>
<p>Der Kunde hat zugesagt? Übertrag die Positionen in die <a href="/tools/de/rechnungsvorlage/">Rechnungsvorlage</a>. Wenn du öfter Angebote schreibst: In <a href="/invoiceqr/de/">Smart Rechnung &amp; Angebot</a> auf dem iPhone wird aus dem Angebot nach der Zusage mit einem Tipp eine Rechnung. <a href="/tools/de/rechnung-schreiben-app-iphone/">So funktioniert es</a>.</p>
{DE_NOTE}"""})

PAGES.append({"path": "/tools/de/rechnung-schreiben-app-iphone/", "lang": "de", "kind": "Article", "app": "invoiceqr", "published": "2026-10-17",
  "title": "Rechnung schreiben mit der iPhone-App: Schritt für Schritt erklärt", "crumb": "Rechnung mit dem iPhone",
  "description": "So schreibst du eine Rechnung auf dem iPhone und schickst sie als PDF: Kunde, Positionen, 19 % Umsatzsteuer oder Hinweis nach § 19 UStG, Bankverbindung.",
  "hub_title": "Rechnung schreiben mit dem iPhone", "hub_desc": "Schritt für Schritt: vom Angebot zur Rechnung als PDF, mit 19 % USt. oder als Kleinunternehmer.",
  "faq": [
    ("Was kostet die App?", "Dein erstes Dokument ist kostenlos, ohne Konto und ohne Anmeldung: eines insgesamt, nicht eines pro Monat, egal ob Rechnung, Kostenvoranschlag oder Angebot. Gezählt wird einmal beim Erstellen; späteres Bearbeiten oder erneutes Senden kostet nichts. Mit Pro sind Rechnungen unbegrenzt; den Preis siehst du im App Store vor dem Kauf."),
    ("Kann ich als Kleinunternehmer Rechnungen ohne Umsatzsteuer schreiben?", "Ja. Wähle beim Steuersatz „Keine Steuer“ und trag den Hinweis nach § 19 UStG unter „Bedingungen & Notizen“ ein. Er wird unten auf die Rechnung gedruckt und lässt sich für die nächste Rechnung wiederverwenden."),
    ("Kann die App E-Rechnungen im Format XRechnung oder ZUGFeRD erstellen?", "Nein. Die App erstellt PDF-Rechnungen. Das reicht für Rechnungen an Privatkunden, für Kleinunternehmer, für Rechnungen bis 250 € und für Rechnungen an Unternehmen während der Übergangszeit: bis Ende 2026, bei höchstens 800.000 € Vorjahresumsatz bis Ende 2027. Ein PDF braucht jeweils die Zustimmung des Empfängers."),
    ("Brauche ich Internet oder ein Konto?", "Nein. Die App funktioniert offline und ohne Konto. Rechnungen und Kunden synchronisieren privat über deine eigene iCloud."),
    ("Gibt es die App für Android?", "Nein, sie ist für iPhone und iPad. Auf einem Android-Handy kannst du die Rechnungsvorlage im Browser ausfüllen und als PDF speichern."),
  ],
  "more": [
    ("Gibt es eine kostenlose App zum Rechnungen schreiben?", "Smart Rechnung & Angebot lässt dich dein erstes Dokument kostenlos schreiben, ohne Konto. Für einzelne Rechnungen zwischendurch ist die <a href=\"/tools/de/rechnungsvorlage/\">Rechnungsvorlage im Browser</a> kostenlos und ohne Anmeldung."),
    ("Rechnung schreiben als Kleingewerbe per App?", "Kleingewerbe heißt nicht automatisch Kleinunternehmer. Ob du Umsatzsteuer ausweist, hängt von § 19 UStG ab: höchstens 25.000 € Umsatz im Vorjahr und nicht mehr als 100.000 € im laufenden Jahr. Ist das so, wählst du in der App „Keine Steuer“; sonst den Steuersatz."),
  ],
  "body": f"""<h1>Rechnung schreiben mit dem iPhone</h1>
<p class="lede">Wenn du beim Kunden bist oder unterwegs abrechnest, schreib die Rechnung gleich auf dem iPhone: Vorlage wählen, Kunde und Positionen eintragen, als PDF per E-Mail oder WhatsApp schicken. Ein Angebot wird nach der Zusage mit einem Tipp zur Rechnung.</p>
{top_cta("invoiceqr", "de", "Im App Store laden – erstes Dokument gratis")}
<h2>Schritt für Schritt</h2>
<p>Mit <a href="/invoiceqr/de/">Smart Rechnung &amp; Angebot</a>, unserer App:</p>
<ol><li>Tippe auf <strong>„Neue Rechnung“</strong> und wähle eine Vorlage (mit Pro über 100). Logo, Markenfarbe und Schrift legst du einmal fest.</li><li>Trag im <strong>„Firmenprofil“</strong> einmalig Name und Adresse ein, und im Feld „Steuer-ID“ deine Steuernummer vom Finanzamt oder deine USt-IdNr. (nicht die persönliche Steuer-Identifikationsnummer). Sie steht danach auf jeder Rechnung.</li><li><strong>„Kunde hinzufügen“</strong>: Der Kunde bleibt gespeichert, genauso wie deine Artikel und Steuersätze.</li><li><strong>„Artikel hinzufügen“</strong> mit Menge und Preis. Rabatt und Versand gehen auch. Als Steuersatz trägst du 19 % ein, bei ermäßigten Leistungen 7 %; als Kleinunternehmer wählst du <strong>„Keine Steuer“</strong>.</li><li>Unter <strong>„Bedingungen &amp; Notizen“</strong> steht, was unten auf die Rechnung gedruckt wird: zum Beispiel „Gemäß § 19 UStG wird keine Umsatzsteuer berechnet.“ oder „Leistungsdatum entspricht Rechnungsdatum“. Als eigene Klausel gespeichert, ist der Satz beim nächsten Mal mit einem Tipp drin.</li><li>Wähle die Zahlungsart: <strong>„Banküberweisung“</strong> mit deiner Bankverbindung oder einen Zahlungslink, aus dem ein Bezahl-QR-Code auf der Rechnung wird.</li><li><strong>„Teilen“</strong>: als PDF per E-Mail, WhatsApp oder ausgedruckt.</li></ol>
<p>Die Rechnungsnummern zählt die App selbst hoch. Trägst du einmal eine eigene Nummer wie 2026-001 ein, geht es mit 2026-002 weiter.</p>
<h2>Vom Angebot zur Rechnung</h2>
<p>Mit <strong>„Neues Angebot“</strong> oder <strong>„Neuer Kostenvoranschlag“</strong> schreibst du zuerst das Angebot. Sagt der Kunde zu, tippst du auf <strong>„In Rechnung umwandeln“</strong>; Kunde und Positionen sind schon drin.</p>
<h2>Nach dem Versand</h2>
<ul><li>Du siehst auf einen Blick, was bezahlt, offen, teilweise bezahlt oder überfällig ist.</li><li>Mit „Zahlung erfassen“ trägst du Zahlungseingänge ein; der offene Betrag stimmt immer.</li><li>Ist alles bezahlt, teilst du dieselbe Rechnung als Beleg, als bezahlt markiert und mit dem Datum des Zahlungseingangs.</li><li>Ein Widget auf dem Home-Bildschirm zeigt dir offene Beträge.</li></ul>
<h2>Was kostenlos ist und was Pro</h2>
<table><thead><tr><th>Kostenlos</th><th>Pro</th></tr></thead><tbody>
<tr><td>Dein erstes Dokument, ohne Konto (eines insgesamt, nicht pro Monat)</td><td>Unbegrenzte Rechnungen und QR-Exporte</td></tr>
<tr><td>4 der 16 fertigen QR-Designs</td><td>100+ Rechnungsvorlagen, alle QR-Stile und Designs</td></tr>
<tr><td>Exporte tragen unten eine kleine Zeile mit dem App-Namen</td><td>Komplettes Marken-Kit, ohne die Zeile mit dem App-Namen</td></tr>
</tbody></table>
<h2>Was die App nicht macht</h2>
<p>Sie erstellt PDF-Rechnungen, keine E-Rechnungen im Format XRechnung oder ZUGFeRD. Ab 2028 müssen Rechnungen an andere Unternehmen in Deutschland E-Rechnungen sein; Rechnungen an Privatkunden, Kleinbetragsrechnungen bis 250 € und Rechnungen von Kleinunternehmern sind davon ausgenommen. Die Fristen stehen bei der <a href="/tools/de/rechnungsvorlage/">Rechnungsvorlage</a>.</p>
<h2>Kein iPhone zur Hand?</h2>
<p>Füll die <a href="/tools/de/rechnungsvorlage/">Rechnungsvorlage</a> oder die <a href="/tools/de/rechnungsvorlage-kleinunternehmer/">Vorlage für Kleinunternehmer</a> im Browser aus und speichere sie als PDF. Vor dem Auftrag gibt es die <a href="/tools/de/angebot-vorlage/">Angebotsvorlage</a>.</p>
{DE_NOTE.replace("Die Vorlage erzeugt ein PDF, keine E-Rechnung", "Die App und die Vorlagen erzeugen PDFs, keine E-Rechnungen")}"""})


# 7d4. 美区：倒数壁纸生成器（Countdown）——10-25
# 用户 10-25：「把 App 的功能搬到网站上导流」。选题证据（10-25 Google 美国联想词）：countdown wallpaper iphone / pc / for laptop、
# christmas countdown wallpaper live、countdown link to share / maker、countdown to share on imessage、photo countdown widget；
# GSC 历史上有点击的只有「待ち受け / 倒數桌布 / 锁屏」这类想把倒数放到手机上的意图（site-countdown-queries-are-zero-click）。
# 页面做的事：日期 + 标题 + 自己的照片 → 浏览器里用 canvas 画成锁屏 / 电脑壁纸（JPEG 下载），外加一条分享链接（只带标题、日期、底色，不带照片）。
# 交给 App 的点：壁纸是死的，数字不会变；Countdown 的锁屏小组件免费、每天自己变（en-US 商店 1.4.2x：every widget size free；自己的照片属于 Pro）。
# 锁屏换壁纸步骤同照片小组件页（Apple 支持「Create a custom Lock Screen」：长按 → + → Photos → Add → Set as Wallpaper Pair）。
# 埋点：表单 id=wallpaper（form_start / form_submit = 生成），关键按钮 data-track-id（wp-preset-* / wp-make / wp-download / wp-share-link / wp-photo-remove），
# 生成后的商店按钮 ct=web-countdown-wallpaper、区块 wallpaper-next；分享链接带 ref=wallpaper-share，对方打开时记在 source_ref。见 ANALYTICS.md。
WALL_JS = r"""
(function(){var f=document.getElementById('wallpaper'),S=window.gkStudio;if(!f||!S)return;
function $(i){return document.getElementById(i)}
var cv=$('wp-canvas'),stage=$('wp-wrap'),box=f.closest('.st'),dropz=$('wp-drop'),thumb=$('wp-thumb'),timg=$('wp-thumbimg'),save=$('wp-save'),share=$('wp-share'),linkBox=$('wp-link'),ctl=$('wp-photo-ctl'),bgstep=$('wp-bgstep'),msg=$('wp-msg'),nextc=$('wp-next'),lb=$('wp-lb'),dim=$('wp-dim');
var img=null,pending=false;
var BG={cream:['#fffaf0','#f5dc61',0],ink:['#141414','#3d3d3d',1],dusk:['#2b2d5e','#e98a6b',1],pine:['#123a2e','#5c8f6b',1]};
var DISP='"Josefin Sans","Manrope",system-ui,sans-serif',TXT='"Manrope",system-ui,-apple-system,"Hiragino Sans","PingFang SC",sans-serif';
function E(n){return f.elements[n]}
function pad(n){return(n<10?'0':'')+n}
function iso(d){return d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate())}
function today(){var n=new Date();return new Date(n.getFullYear(),n.getMonth(),n.getDate())}
function next(m,d){var t=today(),x=new Date(t.getFullYear(),m,d);return x<t?new Date(t.getFullYear()+1,m,d):x}
function thanks(){function q(y){var d=new Date(y,10,1);return new Date(y,10,1+(4-d.getDay()+7)%7+21)}var t=today(),x=q(t.getFullYear());return x<t?q(t.getFullYear()+1):x}
var PRE={christmas:['Christmas',function(){return next(11,25)}],newyear:['New Year',function(){return next(0,1)}],thanksgiving:['Thanksgiving',thanks],valentines:["Valentine's Day",function(){return next(1,14)}],halloween:['Halloween',function(){return next(9,31)}]};
function parse(v){if(!/^\d{4}-\d{2}-\d{2}$/.test(v||''))return null;var p=v.split('-'),d=new Date(+p[0],+p[1]-1,+p[2]);return isNaN(d)||d.getMonth()!==+p[1]-1?null:d}
function size(){var s=E('size').value.split('x');return[+s[0]||1206,+s[1]||2622]}
function bgKey(){var r=f.querySelector('input[name=bg]:checked');return r&&BG[r.value]?r.value:'cream'}
function title(){return(E('title').value||'').trim().slice(0,40)}
function days(d){return Math.round((d-today())/864e5)}
function words(n,t){var a=Math.abs(n),u=a===1?'day':'days';if(n===0)return['Today','',t];return[String(a),u+(n>0?(t?' until':' to go'):(t?' since':' ago')),t]}
function lines(x,t,max,n){var w=t.split(/\s+/),out=[],line='';for(var i=0;i<w.length;i++){var s=w[i],test=line?line+' '+s:s;if(x.measureText(test).width<=max){line=test;continue}if(line)out.push(line);line='';
while(s.length>1&&x.measureText(s).width>max){var k=s.length;while(k>1&&x.measureText(s.slice(0,k)).width>max)k--;out.push(s.slice(0,k));s=s.slice(k)}line=s}if(line)out.push(line);
if(out.length>n){out=out.slice(0,n);var l=out[n-1];while(l.length>1&&x.measureText(l+'…').width>max)l=l.slice(0,-1);out[n-1]=l+'…'}return out}
function draw(c,W,H,prev){c.width=W;c.height=H;var x=c.getContext('2d'),land=W>H,B=BG[bgKey()],dark=img?1:B[2],u=land?H:W;
if(img){var s=Math.max(W/img.naturalWidth,H/img.naturalHeight),dw=img.naturalWidth*s,dh=img.naturalHeight*s,p=+E('pos').value/100;x.drawImage(img,dw>W+1?(W-dw)*p:(W-dw)/2,dh>H+1?(H-dh)*p:(H-dh)/2,dw,dh);
var sh=+E('shade').value/100;if(sh>0){x.fillStyle='rgba(0,0,0,'+sh+')';x.fillRect(0,0,W,H)}}
else{var g=x.createLinearGradient(0,0,0,H);g.addColorStop(0,B[0]);g.addColorStop(1,B[1]);x.fillStyle=g;x.fillRect(0,0,W,H)}
var ink=dark?'#ffffff':'#141414';x.textAlign='center';x.textBaseline='alphabetic';x.fillStyle=ink;
if(prev&&!land){x.save();x.globalAlpha=.3;x.font='600 '+Math.round(u*.042)+'px '+TXT;x.fillText(today().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'}),W/2,H*.09);
x.font='600 '+Math.round(u*.21)+'px '+TXT;x.fillText('9:41',W/2,H*.215);x.restore()}
if(dark){x.shadowColor='rgba(0,0,0,.35)';x.shadowBlur=u*.025}
var d=parse(E('date').value);if(!d){x.font='600 '+Math.round(u*.06)+'px '+TXT;x.fillText('Pick a date',W/2,land?H*.5:H*.6);return}
var n=days(d),wd=words(n,title()),big=u*(land?.26:.3)*(n===0?.55:1),maxW=W*(land?.62:.84);
x.font='600 '+Math.round(big)+'px '+DISP;var nw=x.measureText(wd[0]).width;if(nw>maxW){big*=maxW/nw;x.font='600 '+Math.round(big)+'px '+DISP}
var L1=u*(land?.054:.064),T=u*(land?.064:.078),D=u*(land?.036:.042),rows=[];
rows.push([wd[0],x.font,big*.74,0]);
if(wd[1])rows.push([wd[1],'600 '+Math.round(L1)+'px '+TXT,L1*.78,u*.035]);
if(wd[2]){x.font='700 '+Math.round(T)+'px '+TXT;var tl=lines(x,wd[2],maxW,9);if(tl.length>2){T*=.8;x.font='700 '+Math.round(T)+'px '+TXT;tl=lines(x,wd[2],maxW,3)}tl.forEach(function(l,i){rows.push([l,x.font,T*.78,i?T*.32:(wd[1]?u*.018:u*.035)])})}
rows.push([d.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'}),'500 '+Math.round(D)+'px '+TXT,D*.78,u*.04]);
var h=0;rows.forEach(function(r){h+=r[2]+r[3]});var y=(land?H*.5:H*.6)-h/2;if(!land&&y+h>H*.84)y=H*.84-h;
rows.forEach(function(r,i){y+=r[3]+r[2];x.font=r[1];x.globalAlpha=i===rows.length-1?.88:1;x.fillText(r[0],W/2,y)});x.globalAlpha=1}
function preview(){pending=false;var s=size(),land=s[0]>s[1],pw=land?640:360;box.classList.toggle('land',land);dim.textContent=s[0]+' × '+s[1];draw(cv,pw,Math.round(pw*s[1]/s[0]),true)}
function redraw(){if(!pending){pending=true;requestAnimationFrame(preview)}}
function photo(on){ctl.hidden=!on;bgstep.hidden=on;dropz.hidden=on;thumb.hidden=!on}
function shareURL(){var q=new URLSearchParams();if(title())q.set('t',title());q.set('d',E('date').value);q.set('bg',bgKey());q.set('ref','wallpaper-share');return location.origin+location.pathname+'?'+q}
f.addEventListener('input',redraw);f.addEventListener('change',function(){redraw();S.bump(stage)});
f.querySelectorAll('[data-preset]').forEach(function(b){b.addEventListener('click',function(){var p=PRE[b.getAttribute('data-preset')];if(!p)return;E('title').value=p[0];E('date').value=iso(p[1]());redraw();S.bump(stage)})});
S.drop(dropz,E('photo'),function(file){msg.hidden=true;var src=URL.createObjectURL(file),im=new Image();
im.onload=function(){img=im;timg.src=src;photo(true);redraw();S.bump(stage)};im.onerror=function(){URL.revokeObjectURL(src);E('photo').value='';msg.textContent='That file could not be opened as a picture. Try a JPEG or PNG.';msg.hidden=false};im.src=src});
$('wp-clear').addEventListener('click',function(){img=null;E('photo').value='';photo(false);redraw();S.bump(stage)});
f.addEventListener('submit',function(e){e.preventDefault()});
save.addEventListener('click',function(){if(!parse(E('date').value)){E('date').focus();return}var s=size(),c=document.createElement('canvas');draw(c,s[0],s[1],false);
S.deliver(c,'countdown-wallpaper.jpg',lb);S.done(save,'Saved');nextc.hidden=false});
share.addEventListener('click',function(){var link=shareURL();if(navigator.share&&S.coarse){navigator.share({title:'Countdown',url:link}).catch(function(){});return}
function show(){linkBox.value=link;linkBox.hidden=false;linkBox.select()}
if(navigator.clipboard)navigator.clipboard.writeText(link).then(function(){S.done(share,'Link copied')},show);else show()});
var q=new URLSearchParams(location.search),sd=parse(q.get('d'));
if(sd){E('date').value=q.get('d');E('title').value=(q.get('t')||'').trim().slice(0,40);var r=f.querySelector('input[name=bg][value="'+(BG[q.get('bg')]?q.get('bg'):'cream')+'"]');if(r)r.checked=true;
var n=days(sd),wd=words(n,title()),banner=$('wp-shared');banner.textContent='Shared with you: '+(n===0?(wd[2]||'The big day')+' is today.':wd[0]+' '+wd[1]+(wd[2]?' '+wd[2]:'')+'.')+' Add your own photo below and make it your wallpaper.';banner.hidden=false}
else{E('title').value=PRE.christmas[0];E('date').value=iso(PRE.christmas[1]())}
preview();if(document.fonts&&document.fonts.load)Promise.all([document.fonts.load('600 40px "Josefin Sans"'),document.fonts.load('700 20px "Manrope"')]).then(preview,preview)})();
"""
# 10-25 用户看了里程碑卡片的结果区：「save card 放在顶部很丑；交互？动画？参考我们精品的网站」。
# 参照 BarcodeGuru 生成器（~/Desktop/Github/Project_Web_Barcode/generator.html：左设置卡、右预览卡、下载按钮在预览正下方、按钮带图标和悬停上浮、区块淡入）
# 和 QR 站的柔光 / 浮动动效，两个生成器（壁纸、里程碑卡片）改成同一套「分步面板 + 实时预览舞台」：
# 改了就是预览，「保存」放在预览正下方（form="…" 的提交按钮，form_submit 即保存），保存后按钮变「已保存」、App 卡从下面滑出；
# 手机上预览在最上面、操作条贴底；照顾 prefers-reduced-motion。
ICO_DL = '<svg class="si" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>'
ICO_LINK = '<svg class="si" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5"/></svg>'
ICO_PRINT = '<svg class="si" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/></svg>'
ICO_IMG = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/></svg>'
STUDIO_CSS = """
.st{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,380px);gap:28px;align-items:start;width:min(1032px,calc(100vw - 2 * var(--gutter)));margin:28px 0 12px;animation:stIn .5s cubic-bezier(.2,.8,.2,1) both}
.st-panel{padding:8px 26px 26px;border-radius:24px;background:#fff;border:1px solid var(--rule);box-shadow:0 22px 44px -30px rgba(20,20,20,.35)}
.st-step{border:0;margin:0;padding:20px 0 0;min-width:0}.st-step+.st-step{margin-top:18px;border-top:1px solid var(--rule)}
.st-step>legend{float:left;width:100%;display:flex;align-items:center;gap:10px;padding:0;margin:0 0 14px;font:700 12px/1 var(--text);letter-spacing:1.4px;text-transform:uppercase;color:var(--ink)}
.st-step>legend+*{clear:both}.st-step>legend b{display:inline-grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--ink);color:#fff;font-size:11px;letter-spacing:0}
.st-step>legend small{font:500 12px/1 var(--text);letter-spacing:0;text-transform:none;color:var(--soft)}
.st-stack{display:grid;gap:12px}.st-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}
.st-field{display:grid;gap:6px;font:600 13px/1.2 var(--text);color:var(--muted)}
.st input[type=text],.st input[type=date]{font:400 16px/1.3 var(--text);padding:12px 14px;border:1.5px solid var(--rule);border-radius:12px;background:#fff;color:var(--ink);width:100%;min-width:0;transition:border-color .15s,box-shadow .15s}
.st input[type=text]:hover,.st input[type=date]:hover{border-color:#cfc8b8}
.st input[type=text]:focus-visible,.st input[type=date]:focus-visible{outline:none;border-color:var(--ink);box-shadow:0 0 0 4px rgba(245,220,97,.55)}
.st input[type=range]{width:100%;accent-color:var(--ink)}
.st-chips{display:flex;flex-wrap:wrap;gap:8px}.st-chips+.st-chips{margin-top:10px}.st-glabel{display:block;margin:12px 0 8px;font:600 12px/1 var(--text);color:var(--soft)}
.st-chip{position:relative;display:inline-flex}.st-chip input{position:absolute;inset:0;opacity:0;margin:0;cursor:pointer}
.st-chip span,.st-chipbtn{display:inline-flex;align-items:center;justify-content:center;min-height:38px;min-width:38px;padding:0 14px;border:1.5px solid var(--rule);border-radius:999px;font:600 14px/1 var(--text);color:var(--ink);background:#fff;cursor:pointer;transition:background .15s,border-color .15s,color .15s,transform .12s}
.st-chip:hover span,.st-chipbtn:hover{border-color:var(--ink)}.st-chip input:checked+span{background:var(--ink);border-color:var(--ink);color:#fff}
.st-chip input:focus-visible+span,.st-chipbtn:focus-visible{outline:none;box-shadow:0 0 0 4px rgba(245,220,97,.6)}.st-chip:active span,.st-chipbtn:active{transform:scale(.95)}
.st-swatches{display:flex;flex-wrap:wrap;gap:14px}.st-sw{position:relative;display:inline-block;width:40px;height:40px}
.st-sw input{position:absolute;inset:0;opacity:0;margin:0;cursor:pointer;z-index:1}.st-sw i{display:block;width:40px;height:40px;border-radius:50%;box-shadow:inset 0 0 0 1px rgba(0,0,0,.14);transition:transform .15s,box-shadow .15s}
.st-sw:hover i{transform:scale(1.06)}.st-sw input:checked+i{box-shadow:inset 0 0 0 1px rgba(0,0,0,.14),0 0 0 3px #fff,0 0 0 5px var(--ink)}
.st-sw input:focus-visible+i{box-shadow:0 0 0 3px #fff,0 0 0 5px var(--ink),0 0 0 9px rgba(245,220,97,.6)}
.st-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.st-seg{display:inline-flex;flex-wrap:wrap;gap:4px;padding:4px;border-radius:16px;background:var(--cream);border:1px solid var(--rule);max-width:100%}
.st-segi{position:relative;display:inline-flex}.st-segi input{position:absolute;inset:0;opacity:0;margin:0;cursor:pointer}
.st-segi span{display:inline-flex;align-items:center;min-height:38px;padding:0 14px;border-radius:12px;font:600 14px/1 var(--text);color:var(--muted);transition:background .15s,color .15s,box-shadow .15s}
.st-segi input:checked+span{background:#fff;color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.08),0 4px 10px -4px rgba(0,0,0,.18)}.st-segi input:focus-visible+span{box-shadow:0 0 0 3px rgba(245,220,97,.7)}
.st-drop{position:relative;display:flex;align-items:center;gap:14px;padding:14px 16px;border:1.5px dashed #cfc8b8;border-radius:16px;background:var(--cream);cursor:pointer;transition:border-color .15s,background .15s,transform .15s}
.st-drop:hover,.st-drop.is-over{border-color:var(--ink);background:#fff4cc}.st-drop:focus-within{border-color:var(--ink);border-style:solid;box-shadow:0 0 0 4px rgba(245,220,97,.6)}.st-drop.is-over{transform:scale(1.01)}
.st-drop input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}
.st-ico{flex:none;display:grid;place-items:center;width:44px;height:44px;border-radius:12px;background:#fff;color:var(--ink);box-shadow:inset 0 0 0 1px var(--rule)}
.st-drop b,.st-thumb b{display:block;font:600 15px/1.3 var(--text);color:var(--ink)}.st-drop small,.st-thumb small{display:block;margin-top:2px;font-size:13px;color:var(--muted)}
.st-thumb{display:flex;align-items:center;gap:12px;padding:10px;border-radius:16px;background:var(--cream);border:1px solid var(--rule);animation:stUp .3s ease both}
.st-thumb img{width:56px;height:56px;object-fit:cover;border-radius:12px;flex:none}.st-thumb div{flex:1;min-width:0}
.st-x{flex:none;width:36px;height:36px;border-radius:50%;border:1.5px solid var(--rule);background:#fff;color:var(--ink);font:500 20px/1 var(--text);cursor:pointer;transition:border-color .15s,transform .12s}
.st-x:hover{border-color:var(--ink)}.st-x:active{transform:scale(.92)}.st-msg{margin:0;color:#a3341f;font-size:14px}
.st-side{position:sticky;top:20px;display:grid;gap:14px}
.st-stage{margin:0;padding:18px 22px 22px;border-radius:28px;background:radial-gradient(130% 90% at 50% 0%,#fff 0%,var(--cream) 55%,#f2e7cf 100%);border:1px solid var(--rule)}
.st-top{display:flex;justify-content:space-between;align-items:center;margin:0 0 16px;font:700 11px/1 var(--text);letter-spacing:1.3px;text-transform:uppercase;color:var(--soft)}
.st-live{display:inline-flex;align-items:center;gap:7px}.st-live i{width:8px;height:8px;border-radius:50%;background:#3fb37f;animation:stPulse 1.8s ease-out infinite}
.st-wrap{display:grid;place-items:center}.st-wrap.bump{animation:stBump .38s cubic-bezier(.2,.8,.2,1)}
.st-cap{margin:14px 0 0;font-size:12.5px;line-height:1.5;color:var(--soft);text-align:center}
.st-actions{display:grid;gap:10px}.st-actions .btn{width:100%;justify-content:center;padding:15px 20px;transition:background .15s,color .15s,transform .15s,box-shadow .15s}
.st-actions .btn:hover{transform:translateY(-1px);box-shadow:0 10px 20px -12px rgba(20,20,20,.55)}.st-actions .btn:active{transform:translateY(0)}
.st .btn svg.si{fill:none}.st-save.is-done{background:#2f8f5b;color:#fff}
.st-hint{margin:2px 0 0;font-size:13px;line-height:1.5;color:var(--muted);text-align:center}.st-hint-ios,.st-hint-desk{display:none}html.is-ios .st-hint-ios,html.is-desk .st-hint-desk{display:block}
.st-link{width:100%;font:400 14px/1.3 var(--text);padding:10px 12px;border:1.5px solid var(--rule);border-radius:10px;color:var(--ink);background:#fff}
.st-next{padding:18px;border-radius:20px;background:#fff;border:1.5px solid var(--ink);animation:stUp .45s cubic-bezier(.2,.8,.2,1) both}.st-next p{margin:0 0 14px;font-size:15px}.st-next .btn{width:100%;justify-content:center}
.st-lb{position:fixed;inset:0;z-index:60;display:grid;place-items:center;padding:24px;background:rgba(20,20,20,.78);animation:stFade .2s ease both}
.st-lb figure{margin:0;display:grid;gap:12px;justify-items:center}.st-lb img{max-width:min(86vw,420px);max-height:72vh;border-radius:14px;box-shadow:0 20px 50px rgba(0,0,0,.5)}
.st-lb figcaption{color:#fff;font:600 15px/1.4 var(--text);text-align:center}.st-lbx{position:absolute;top:16px;right:16px;width:44px;height:44px;border-radius:50%;border:0;background:#fff;color:var(--ink);font:500 24px/1 var(--text);cursor:pointer}
.st [hidden],.st-lb[hidden]{display:none!important}
@keyframes stIn{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}@keyframes stUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes stFade{from{opacity:0}to{opacity:1}}@keyframes stBump{40%{transform:scale(.982)}100%{transform:scale(1)}}
@keyframes stPulse{0%{box-shadow:0 0 0 0 rgba(63,179,127,.5)}70%{box-shadow:0 0 0 7px rgba(63,179,127,0)}100%{box-shadow:0 0 0 0 rgba(63,179,127,0)}}
@media (prefers-reduced-motion:reduce){.st,.st *,.st-lb{animation:none!important;transition:none!important}}
@media (max-width:860px){.st{grid-template-columns:minmax(0,1fr);gap:16px}.st-side{display:contents}.st-stage{order:-1;padding:14px 16px 16px}.st-panel{order:0;padding:4px 18px 20px}
.st-actions{order:1;position:sticky;bottom:0;z-index:5;grid-template-columns:minmax(0,1fr) auto;padding:12px 0 calc(12px + env(safe-area-inset-bottom));background:linear-gradient(rgba(255,255,255,0),#fff 26%)}.st-actions .btn.ghost{width:52px;padding:0;background:#fff}.st-actions .btn.ghost span{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}.st-actions .st-hint{grid-column:1/-1;margin:0;font-size:12.5px;line-height:1.35}.st-actions .st-link{grid-column:1/-1}.st-next{order:2}.st-row{grid-template-columns:minmax(0,1fr)}}
"""

STUDIO_JS = r"""
window.gkStudio=(function(){var coarse=!!(window.matchMedia&&matchMedia('(pointer:coarse)').matches),reduce=!!(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches);
function toBlob(d){var p=d.split(','),b=atob(p[1]),n=b.length,u=new Uint8Array(n);while(n--)u[n]=b.charCodeAt(n);return new Blob([u],{type:'image/jpeg'})}
function bump(el){if(reduce||!el)return;el.classList.remove('bump');void el.offsetWidth;el.classList.add('bump')}
function done(btn,text){var lab=btn&&btn.querySelector('span');if(!lab)return;if(!btn.getAttribute('data-label'))btn.setAttribute('data-label',lab.textContent);lab.textContent='✓ '+text;btn.classList.add('is-done');clearTimeout(btn._t);btn._t=setTimeout(function(){lab.textContent=btn.getAttribute('data-label');btn.classList.remove('is-done')},2200)}
function lightbox(lb,src){lb.querySelector('img').src=src;lb.hidden=false;var x=lb.querySelector('.st-lbx');x.focus();function close(){lb.hidden=true;document.removeEventListener('keydown',key)}function key(e){if(e.key==='Escape')close()}x.onclick=close;lb.onclick=function(e){if(e.target===lb)close()};document.addEventListener('keydown',key)}
function deliver(canvas,name,lb){var data=canvas.toDataURL('image/jpeg',.92),blob=toBlob(data),file=null;try{file=new File([blob],name,{type:'image/jpeg'})}catch(e){}
if(file&&coarse&&navigator.canShare&&navigator.canShare({files:[file]})){navigator.share({files:[file]}).catch(function(){});return}
if(coarse&&lb){lightbox(lb,data);return}
var a=document.createElement('a'),u=URL.createObjectURL(blob);a.href=u;a.download=name;a.click();setTimeout(function(){URL.revokeObjectURL(u)},4000)}
function drop(zone,input,onFile){['dragenter','dragover'].forEach(function(t){zone.addEventListener(t,function(e){e.preventDefault();zone.classList.add('is-over')})});
['dragleave','dragend'].forEach(function(t){zone.addEventListener(t,function(){zone.classList.remove('is-over')})});
zone.addEventListener('drop',function(e){e.preventDefault();zone.classList.remove('is-over');var f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];if(f)onFile(f)});
input.addEventListener('change',function(){var f=input.files&&input.files[0];if(f)onFile(f)})}
return{coarse:coarse,bump:bump,done:done,deliver:deliver,drop:drop}})();
"""
WALL_CSS = STUDIO_CSS + """
.wp-shared{margin:0 0 4px;padding:14px 18px;border-radius:14px;background:var(--yellow);color:var(--ink)!important;font-weight:600}
.wp .st-device{width:min(100%,248px);padding:9px;border-radius:44px;background:#151515;box-shadow:inset 0 0 0 1.5px #343434,0 32px 50px -28px rgba(0,0,0,.6)}
.wp .st-device canvas{display:block;width:100%;height:auto;border-radius:35px;background:#fff}
.wp.land .st-wrap{padding-bottom:16px}.wp.land .st-device{position:relative;width:100%;padding:8px 8px 18px;border-radius:14px}.wp.land .st-device canvas{border-radius:6px}
.wp.land .st-device::after{content:"";position:absolute;left:50%;bottom:-14px;width:28%;height:14px;transform:translateX(-50%);background:#d8cfbb;border-radius:0 0 10px 10px}
.wp.land .st-cap{display:none}
@media (max-width:860px){.wp .st-device{width:min(60vw,226px)}}
"""
def wall_store(where):
    p = BY_KEY["countdown"]
    return bp.store_link(p, bp.store_of(p), where)

PAGES.append({"path": "/tools/countdown-wallpaper-maker/", "lang": "en", "kind": "WebApplication", "app": "countdown", "published": "2026-10-25",
  "title": "Free Online Countdown Wallpaper Maker, With Your Own Photo", "crumb": "Countdown wallpaper maker",
  "description": "Make a countdown wallpaper for your iPhone Lock Screen or computer: pick a date, add your own photo, download it. Free, no sign-up, nothing is uploaded.",
  "hub_title": "Free online countdown wallpaper maker", "hub_desc": "Your date and your photo on a Lock Screen or desktop wallpaper, plus a link to share the countdown.",
  "js": [STUDIO_JS, WALL_JS], "css": WALL_CSS,
  "faq": [
    ("Is the countdown wallpaper maker free?", "Yes. There is no sign-up, no watermark and no limit on how many wallpapers you make."),
    ("Is my photo uploaded anywhere?", "No. Your browser draws the wallpaper on this page, and the photo never leaves your device. The share link carries only the title, the date and the background color, never the photo."),
    ("Will the number on the wallpaper count down by itself?", "No. A wallpaper is a still picture, so it keeps the number it had on the day you made it. For a number that changes every day, use a countdown widget instead, with a plain photo as the wallpaper; in Countdown Widget: Any Event every widget size on the Lock Screen and the Home Screen is free."),
    ("How do I set it as my iPhone Lock Screen?", "Save the wallpaper to Photos, then touch and hold the Lock Screen, tap +, tap Photos and choose it. Tap Add, then Set as Wallpaper Pair."),
    ("Which sizes can I download?", "iPhone (1206 × 2622 pixels, the screen of a 6.3-inch iPhone), Large iPhone (1320 × 2868, the screen of a 6.9-inch iPhone) and a 16:9 computer size (2560 × 1440). Other iPhones have almost the same shape, and you can pinch and drag the picture when you set it."),
    ("Does it work on Android or Windows?", "Yes. The download is an ordinary JPEG picture, so any phone or computer can use it as a wallpaper. Countdown, the app with the countdown widget, is for iPhone and iPad."),
  ],
  "more": [
    ("Is there a Christmas countdown wallpaper that updates live?", 'A picture can’t change by itself, so on iPhone the “live” part is a widget: use a Christmas photo as your Lock Screen wallpaper and put the Countdown widget over it; the number goes down every day. The <a href="/tools/christmas-countdown-widget-iphone/">Christmas countdown widget</a> page has the steps.'),
    ("Can I make a countdown wallpaper for my laptop?", "Yes. Choose Computer (16:9) as the size. On a Mac, right-click the downloaded file in Finder and choose Set Desktop Picture; on Windows, right-click it and choose Set as desktop background."),
    ("Can I send the countdown to a friend?", "Yes. Tap Share the countdown and send the link. It opens this page with the same title, date and background, counted from the day they open it, so they can make their own wallpaper. Photos are never part of the link."),
  ],
  "body": f"""<h1>Free online countdown wallpaper maker</h1>
<p class="lede">Pick a date, add your own photo and download a countdown wallpaper for your iPhone Lock Screen or your computer. Free, no sign-up, no watermark. Your browser draws the picture on this page, so the photo never leaves your device.</p>
<p class="wp-shared" id="wp-shared" hidden></p>
<div class="st wp">
<form class="st-panel" id="wallpaper">
<fieldset class="st-step"><legend><b>1</b>Your countdown</legend><div class="st-stack">
<div class="st-chips" role="group" aria-label="Quick picks"><button type="button" class="st-chipbtn" data-preset="christmas" data-track-id="wp-preset-christmas">Christmas</button><button type="button" class="st-chipbtn" data-preset="newyear" data-track-id="wp-preset-newyear">New Year</button><button type="button" class="st-chipbtn" data-preset="thanksgiving" data-track-id="wp-preset-thanksgiving">Thanksgiving</button><button type="button" class="st-chipbtn" data-preset="valentines" data-track-id="wp-preset-valentines">Valentine’s Day</button><button type="button" class="st-chipbtn" data-preset="halloween" data-track-id="wp-preset-halloween">Halloween</button></div>
<div class="st-row"><label class="st-field">Counting down to<input type="text" name="title" maxlength="40" placeholder="Our trip to Lisbon" autocomplete="off"></label><label class="st-field">Date<input type="date" name="date" required></label></div>
</div></fieldset>
<fieldset class="st-step"><legend><b>2</b>Photo <small>optional</small></legend><div class="st-stack">
<label class="st-drop" id="wp-drop"><input type="file" name="photo" accept="image/*"><span class="st-ico">{ICO_IMG}</span><span><b>Add a photo</b><small>Choose one, or drop it here</small></span></label>
<div class="st-thumb" id="wp-thumb" hidden><img id="wp-thumbimg" alt="" width="56" height="56"><div><b>Your photo</b><small>It stays on this device</small></div><button type="button" class="st-x" id="wp-clear" data-track-id="wp-photo-remove" aria-label="Remove photo">×</button></div>
<p class="st-msg" id="wp-msg" role="alert" hidden></p>
<div class="st-stack" id="wp-photo-ctl" hidden><label class="st-field">Photo position<input type="range" name="pos" min="0" max="100" value="50"></label><label class="st-field">Darken photo<input type="range" name="shade" min="0" max="60" value="25"></label></div>
</div></fieldset>
<fieldset class="st-step" id="wp-bgstep"><legend><b>3</b>Background</legend><div class="st-swatches"><label class="st-sw" title="Cream"><input type="radio" name="bg" value="cream" checked><i style="background:linear-gradient(#fffaf0,#f5dc61)"></i><span class="st-sr">Cream</span></label><label class="st-sw" title="Ink"><input type="radio" name="bg" value="ink"><i style="background:linear-gradient(#141414,#3d3d3d)"></i><span class="st-sr">Ink</span></label><label class="st-sw" title="Dusk"><input type="radio" name="bg" value="dusk"><i style="background:linear-gradient(#2b2d5e,#e98a6b)"></i><span class="st-sr">Dusk</span></label><label class="st-sw" title="Pine"><input type="radio" name="bg" value="pine"><i style="background:linear-gradient(#123a2e,#5c8f6b)"></i><span class="st-sr">Pine</span></label></div></fieldset>
<fieldset class="st-step"><legend><b>4</b>Size</legend><div class="st-seg"><label class="st-segi"><input type="radio" name="size" value="1206x2622" checked><span>iPhone</span></label><label class="st-segi"><input type="radio" name="size" value="1320x2868"><span>Large iPhone</span></label><label class="st-segi"><input type="radio" name="size" value="2560x1440"><span>Computer</span></label></div></fieldset>
</form>
<div class="st-side">
<figure class="st-stage"><figcaption class="st-top"><span class="st-live"><i></i>Live preview</span><span id="wp-dim">1206 × 2622</span></figcaption>
<div class="st-wrap" id="wp-wrap"><div class="st-device"><canvas id="wp-canvas" width="360" height="783" aria-label="Preview of your countdown wallpaper"></canvas></div></div>
<p class="st-cap">The grey time marks where the iPhone clock sits. It isn’t in the download.</p></figure>
<div class="st-actions" data-track-section="wallpaper-stage">
<button type="button" class="btn st-save" id="wp-save" data-track-id="wp-download">{ICO_DL}<span>Save wallpaper</span></button>
<button type="button" class="btn ghost" id="wp-share" data-track-id="wp-share-link">{ICO_LINK}<span>Share the countdown</span></button>
<input class="st-link" id="wp-link" type="text" readonly hidden aria-label="Link to this countdown">
<p class="st-hint st-hint-ios">On iPhone, tap Save wallpaper, then Save Image.</p><p class="st-hint st-hint-desk">On a computer the wallpaper downloads as a JPEG.</p>
</div>
<div class="st-next" id="wp-next" hidden data-track-section="wallpaper-next"><p><strong>A wallpaper won’t count down.</strong> It keeps the number it shows today. On iPhone, the free Countdown widget shows a number that changes by itself every midnight, on the Lock Screen or the Home Screen.</p>
<a class="btn" href="{esc(wall_store("wallpaper"))}">{bp.APPLE}Get the Countdown widget, free</a></div>
</div>
</div>
<div class="st-lb" id="wp-lb" hidden role="dialog" aria-modal="true" aria-label="Your wallpaper"><figure><img alt="Your countdown wallpaper"><figcaption>Touch and hold the picture to save it to Photos.</figcaption></figure><button type="button" class="st-lbx" aria-label="Close">×</button></div>
<h2>Set it as your iPhone Lock Screen</h2>
<ol><li>Tap <strong>Save wallpaper</strong>, then <strong>Save Image</strong>.</li>
<li>Touch and hold the Lock Screen, tap <strong>+</strong>, tap <strong>Photos</strong> and choose the wallpaper.</li>
<li>Pinch or drag to adjust it if you like, tap <strong>Add</strong>, then <strong>Set as Wallpaper Pair</strong>.</li></ol>
<p>The Lock Screen clock and widgets sit at the top of the screen, so the maker places your number in the lower half. That is what the grey time in the preview is for.</p>
<h2>Make the number count down by itself</h2>
<p>A wallpaper keeps the number it was made with. A widget is the part of the Lock Screen that changes: in <a href="/countdown/">Countdown Widget: Any Event</a> every widget size on the Lock Screen and the Home Screen is free, with unlimited countdowns and no ads.</p>
<ul>{EN_WIDGET_STEPS}</ul>
<p>If you switch to the widget, use a photo without a number as your wallpaper, so the screen doesn’t show an old count next to the new one. Lock Screen widgets are drawn in one tint over the wallpaper; on the Home Screen, the widget itself can show your own photo, which is part of Countdown Pro (<a href="/tools/countdown-widget-with-your-own-photo-iphone/">how it works</a>).</p>
<h2>On a computer</h2>
<p>Choose <strong>Computer (16:9)</strong> as the size. On a Mac, right-click the downloaded file in Finder and choose <strong>Set Desktop Picture</strong>. On Windows, right-click it and choose <strong>Set as desktop background</strong>.</p>
<h2>Ideas</h2>
<ul><li><strong>Christmas.</strong> The days to December 25 over a photo from last year. For a number that updates itself, see the <a href="/tools/christmas-countdown-widget-iphone/">Christmas countdown widget</a>.</li>
<li><strong>A trip.</strong> The beach you are going to, with the date you fly out. See the <a href="/tools/vacation-countdown-widget-iphone/">vacation countdown</a> for reminders before you leave.</li>
<li><strong>A birthday.</strong> Their photo and their day; the <a href="/tools/birthday-countdown-widget-iphone/">birthday countdown</a> repeats every year.</li>
<li><strong>The two of you.</strong> Send the share link to your partner, or <a href="/tools/shared-countdown-app-couples/">share one countdown</a> that shows up on both iPhones.</li></ul>
<p>Need only the number? The <a href="/tools/days-until/">days until calculator</a> counts to any date.</p>"""})


# 7d5. Pagewren 里程碑卡片 / Meilensteinkarten（10-25 上线）当天就随 Pagewren 搬到独立站 pagewrenbaby.com，
# 代码在 ~/Documents/pagewren-site（content/pages/*.html + public/assets/js/milestone.js），旧地址在 vercel.json 里 301。


# ------------------------------------------------------------------ About（10-25）
# claude-seo 的「谁写的 / 怎么做的 / 为什么写」三问：站内原来只有首页 #about 一小段，没有说明页面怎么核对事实。
# 说法都按现状写：「independent developer」首页早就这么写；不写真人姓名（要不要加由用户定）；AI 协助起草和翻译是实情，照实写。
# 不进工具目录（nohub），面包屑 Home › About，sitemap 归 pages 组，统计 page_type=about——这几处在 build_seo.py 里按 kind == "AboutPage" 分支。
ABOUT_APPS = [a for a in APPS if a.get("live") and not a.get("variantOf") and a.get("appId") and a["path"] != "/"]
_CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
def about_name(a): return a["home"]["label"] if _CJK.search(a["name"]) else a["name"]            # 单词兽只有中文商店名：英文页用首页卡片上的英文名
def about_line(a): return a["home"]["tagline"] if _CJK.search(a.get("oneLiner", "")) else a.get("oneLiner", "")
def about_hl(a): return ' hreflang="zh-Hans"' if _CJK.search(a["name"]) else ""                   # 链过去是中文页，先告诉读者
ABOUT_SOCIAL = " · ".join(f'<a href="{esc(x["url"])}" rel="me noopener">{esc(x.get("nameIntl", x["name"]))}</a>' for x in bp.SOCIAL)
PAGES.append({"path": "/about/", "lang": "en", "kind": "AboutPage", "nohub": True, "published": "2026-10-25",
  "title": "About go ka: Who Makes These Apps and How We Check Facts", "crumbs": [("Home", "/"), ("About", None)],
  "description": "go ka is an independent developer of small iPhone apps. Who we are, the apps we make, and how the facts on this site are sourced and checked.",
  "body": f"""<h1>About go ka</h1>
<p class="lede">go ka is an independent developer making small iPhone apps for everyday things. All {len(ABOUT_APPS)} apps are published on the App Store under one developer account, and this site is where we explain them and keep a few free tools.</p>
<h2>The apps</h2>
<ul>{"".join(f'<li><a href="{bp.site_url(a) if a.get("site") else a["path"]}"{"" if a.get("site") else about_hl(a)}>{esc(about_name(a))}</a>: {esc(about_line(a))}</li>' for a in ABOUT_APPS)}</ul>
<p>Every app is free to download, none of them asks you to create an account, and the price of anything extra is shown in the App Store before you pay. All of them are listed on our <a href="{esc(CFG["site"]["developerUrl"])}" rel="noopener">App Store developer page</a>.</p>
<h2>How we check what these pages say</h2>
<ul><li><strong>What an app does</strong> comes from its own App Store description, in the language of the page. Where the description says nothing, we check the app itself before writing a sentence about it.</li>
<li><strong>Dates and rules</strong>, such as exam dates, school calendars, tax law and park rules, come from the official source wherever there is one: the exam board, the education department, the published law or the park’s own rules. Many pages also say which source and when we checked it.</li>
<li><strong>Other apps</strong> in a comparison are described only with what their own App Store listing says. Nobody pays to be listed, and our own app is always marked as ours.</li>
<li><strong>Prices</strong> are not written on this site. The App Store shows the current price for your country.</li></ul>
<p>We use AI tools to help draft and translate pages. Before a page goes live, its facts are checked against the sources above, and a separate review checks the page on a phone and on a computer.</p>
<h2>The free tools</h2>
<p>The <a href="/tools/">calculators, templates and makers</a> run in your browser. What you type, and any photo you add to the <a href="/tools/countdown-wallpaper-maker/">countdown wallpaper maker</a>, stays on your device. We count visits and button taps to see which pages help; the <a href="/privacy-policy/">privacy policy</a> lists exactly what is measured.</p>
<h2>Found a mistake?</h2>
<p>Email <a href="mailto:{EMAIL}">{EMAIL}</a> with the page and what is wrong. We fix it, and the page’s “Updated” date changes with the fix.</p>
<p>Elsewhere: {ABOUT_SOCIAL}.</p>"""})

# 德国开票页的署名（10-25）：涉及税法的页，claude-seo 认为「谁写的」是硬要求。日期 = 10-17 逐条读 gesetze-im-internet.de 原文那天（见 7e 节注释）。
DE_BYLINE = ('<p class="meta" style="margin-top:12px"><strong>Über diese Seite:</strong> Geschrieben von go ka, dem unabhängigen Entwickler der App '
             'Smart Rechnung &amp; Angebot. Die genannten Paragrafen haben wir am 17. Oktober 2026 im Wortlaut auf gesetze-im-internet.de nachgelesen. '
             'Fehler gefunden? Schreiben Sie an <a href="mailto:' + EMAIL + '">' + EMAIL + '</a>. <a href="/about/" hreflang="en">Wie wir Fakten prüfen</a> (Englisch).</p>')
for _pg in PAGES:
    if _pg["path"].startswith("/tools/de/") and _pg.get("app") == "invoiceqr":   # 只给开票页；德语 Pagewren 卡片页不是法规内容
        _pg["body"] = _pg["body"] + "\n" + DE_BYLINE

# ------------------------------------------------------------------ 目录页
HUB_EN_EXTRA = {"de": ("Weitere kostenlose Tools (auf Englisch)", [
    ("/tools/days-until/", "Datum eingeben, verbleibende Tage und Wochen sehen."),
    ("/tools/countdown-wallpaper-maker/", "Einen Countdown als Hintergrundbild für Handy oder Computer erstellen.")])}   # 打包清单 10-26 随 BeforeGo 搬走
# ------------------------------------------------------------------ 10-26 BeforeGo 搬到独立站 beforegotech.com
# 下面这几页不再在本站生成（vercel.json 308 到新站同路径，正文已搬进新站仓库 ~/Documents/beforego-site）；
# 其余页面正文里指向它们和 /beforego/ 的链接，写文件时改成新站的绝对地址（bg_links）。
# 韩语트리플替代页 /tools/ko/yeohaeng-iljeong-aep/ 是旧站唯一有 Google 点击的 BeforeGo 页，트리플 11-03 停服前后正值高峰，11 月中旬再搬。
BG_SITE = "https://beforegotech.com"
BG_MOVED = {"/tools/packing-list/", "/tools/japan-travel-checklist/", "/tools/disney-world-packing-list/",
            "/tools/disney-world-itinerary-template/", "/tools/ja/ryoko-keikaku-app/", "/tools/zh-hant/xing-cheng-gui-hua-app/",
            "/blog/packing-list-by-destination/", "/blog/travel-post-screenshot-to-itinerary/"}
PAGES[:] = [p for p in PAGES if p["path"] not in BG_MOVED]

def bg_links(page):
    page = re.sub(r'href="/beforego/(?:([a-z-]+)/)?"', lambda m: f'href="{BG_SITE}/{m[1] + "/" if m[1] else ""}"', page)
    for p in BG_MOVED:
        page = page.replace(f'href="{p}"', f'href="{BG_SITE}{p}"')
    return page

def hub_page(lang):
    hub_path = HUBS[lang]
    items = sorted([p for p in PAGES if p["lang"] == lang and not p.get("nohub")], key=lambda p: "/ferias-escolares-" in p["path"])   # 分州校历页排在其它工具后面（稳定排序）
    # 卡片小字：英文目录用 app 短名；其它语言用该语言商店名（09-28：西语目录显示 Invoice Maker 是英文）
    label = lambda k: (BY_KEY[k]["home"]["label"] if lang == "en" else bp.store_of({"variantOf": k, "lang": lang})["name"]) if k else ""
    cards = "\n".join(f'  <a href="{p["path"]}"><b>{esc(p["hub_title"])}</b><span>{esc(p["hub_desc"])}</span><small>{esc(label(p["app"]))}</small></a>' for p in items)
    body = f"""<h1>{esc(ts(lang, "hub_title"))}</h1>
<p class="lede">{esc(ts(lang, "hub_lede"))}</p>
<div class="hub">
{cards}
</div>"""
    if lang in HUB_EN_EXTRA:   # 10-17 评审：Countdown / BeforeGo 的德语页「Tools」也指到这里，不能只剩发票模板——补上英文的倒数和打包工具
        h2, extra = HUB_EN_EXTRA[lang]; by = {p["path"]: p for p in PAGES}
        body += f'\n<h2>{esc(h2)}</h2>\n<div class="hub">\n' + "\n".join(
            f'  <a href="{u}" hreflang="en"><b lang="en">{esc(by[u]["hub_title"])}</b><span>{esc(d)}</span><small>{esc(BY_KEY[by[u]["app"]]["home"]["label"])}</small></a>' for u, d in extra) + "\n</div>"
    title, desc = {
        "en": ("Free tools & guides — go ka", "Free, no-sign-up tools from go ka: a days-until calculator, holiday countdowns, a countdown wallpaper maker, and an invoice template and guide."),
        "pt-BR": ("Ferramentas e guias grátis — go ka", "Ferramentas grátis da go ka, sem cadastro: contador de dias, aniversário, férias com dias úteis, dias de namoro e contagem para o ENEM e o Natal."),
        "es-MX": ("Herramientas y guías gratis — go ka", "Herramientas gratis y sin registro de go ka: formatos de cotización y nota de venta en línea, cómo cotizar desde el iPhone y una alternativa a Invoice Simple."),
        "ko": ("무료 도구와 가이드 — go ka", "go ka의 무료 가이드: 아이폰 잠금 화면에 디데이 위젯을 띄우는 방법, 그리고 트리플 서비스 종료 후 쓸 만한 여행 일정 앱 비교."),
        "th": ("เครื่องมือและคู่มือฟรี — go ka", "เครื่องมือฟรีจาก go ka ไม่ต้องสมัคร: แบบฟอร์มใบเสนอราคาและใบเสร็จรับเงินสำหรับบุคคลธรรมดาและฟรีแลนซ์ กรอกบนหน้าเว็บ คำนวณยอดให้เอง พิมพ์หรือบันทึกเป็น PDF"),
        "ja": ("無料ツールとガイド — go ka", "go ka の無料ツール（登録不要）：今日からあと何日かを数える日数計算、共通テスト2027までのカウントダウン、カウントダウンを待ち受けにする方法。"),
        "de": ("Kostenlose Vorlagen und Anleitungen — go ka", "Kostenlose Vorlagen ohne Anmeldung: Rechnung, Rechnung für Kleinunternehmer (§ 19 UStG) und Angebot, im Browser ausfüllen und als PDF speichern."),
        "zh-Hant": ("免費工具與指南 — go ka", "go ka 的免費工具，不用註冊：報價單範本、收據範本（線上填寫、自動計算、存成 PDF），以及 2027 農曆新年倒數。"),
    }[lang]
    return {"path": hub_path, "lang": lang, "kind": "CollectionPage", "title": title,
            "description": desc,
            "body": body, "published": None, "faq": [], "js": []}

# ------------------------------------------------------------------ 博客（09-26 用户要求：参照 EasyNotes 官网补博客）
BLOG_SRC = ROOT / "tools/blog/posts.en.json"
BLOG = json.loads(BLOG_SRC.read_text(encoding="utf-8"))["posts"] if BLOG_SRC.exists() else []
BLOG = [p for p in BLOG if f"/blog/{p['slug']}/" not in BG_MOVED]   # 10-26 BeforeGo 两篇搬到新站
APP_ORDER = {"countdown": 0, "invoiceqr": 1, "beforego": 2}
POST_SHOT = {  # 每篇配一张对应功能的插画（assets/art，编号同 features.en.json；09-28 起不用商店截图）
    "countdown-widget-iphone-home-lock-screen": ("countdown", "07"), "count-down-birthday-exam-trip-iphone": ("countdown", "09"),
    "payment-qr-code-on-invoice": ("invoiceqr", "08"), "venmo-cash-app-paypal-zelle-qr-code-on-invoice": ("invoiceqr", "08", "Clients scan the code on the invoice to pay"), "invoice-vs-estimate-vs-quote": ("invoiceqr", "05", "Invoice, estimate and quote side by side"),
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
            "hub_title": post["title"], "hub_desc": post["description"], "headline": post["h1"], "image": post_image(post["slug"]), "meta_top": post.get("meta_top", False)}

def blog_hub():
    groups = []
    for key in sorted({p["app"] for p in BLOG}, key=lambda k: APP_ORDER.get(k, 9)):
        cards = "\n".join(f'  <a href="/blog/{p["slug"]}/"><b>{esc(p["title"])}</b><span>{esc(p["description"])}</span><small>{esc(BY_KEY[key]["home"]["label"])}</small></a>'
                          for p in BLOG if p["app"] == key)
        groups.append(f'<h2>{esc(BY_KEY[key]["home"]["label"])}</h2>\n<div class="hub">\n{cards}\n</div>')
    body = f"""<h1>Blog</h1>
<p class="lede">Plain how-to guides for the everyday things our apps do: countdown widgets, invoices and payment QR codes. Trip planning and packing guides moved to <a href="https://beforegotech.com/tools/">beforegotech.com</a>, the BeforeGo website.</p>
{chr(10).join(groups)}"""
    return {"path": "/blog/", "lang": "en", "kind": "CollectionPage", "title": "Blog — guides for countdowns and invoices | go ka",
            "description": "How-to guides from go ka: countdown widgets on iPhone, payment QR codes on invoices, and the difference between invoices, estimates and quotes.",
            "body": body, "published": None, "faq": [], "js": []}

def main():
    manifest = []
    blog = [blog_page(p) for p in BLOG]
    for pg in PAGES + blog + [hub_page(l) for l in HUBS] + ([blog_hub()] if blog else []):
        out = ROOT / pg["path"].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(bg_links(shell(pg, pg["body"])), encoding="utf-8")
        manifest.append({"path": pg["path"], "lang": pg["lang"], "kind": pg["kind"], "title": pg["title"], "description": pg["description"],
                         "faq": [{"q": q, "a": a} for q, a in pg.get("faq", [])], "published": pg.get("published"), "app": pg.get("app"),
                         "hubTitle": pg.get("hub_title", pg["title"]), "items": pg.get("items", []),
                         "headline": pg.get("headline"), "image": pg.get("image"),
                         "crumbHome": ts(pg["lang"], "home"), "crumbHub": ts(pg["lang"], "tools")})
        if pg.get("iphone_only"): manifest[-1]["iphoneOnly"] = True
        print(f"  {pg['path']}")
    (ROOT / "tools/tools.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"工具页 {len(manifest)} 页；接着跑 tools/build_seo.py")

if __name__ == "__main__":
    main()
