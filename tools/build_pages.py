#!/usr/bin/env python3
"""从 site.json + tools/store/<app>.json（商店本地化文案与截图缓存）生成产品承载页。

  python3 tools/build_pages.py            # 生成所有 generated:true 的 app（含其语言变体）
  python3 tools/build_pages.py countdown  # 只生成一个 app

页面正文全部来自 App Store 商店文案（名字、钩子句、各段小标题与要点、订阅条款），
截图直接引用苹果 CDN 的 WebP（<w>x0w.webp），预览视频在 assets/<key>/preview/<lang>.mp4。
只有 <title> 的 tagline、meta description、FAQ 和界面词需要翻译（tools/i18n/*.json）。
生成完必须再跑 tools/build_seo.py：head 的 SEO 块和可见 FAQ 由它填。
"""
import json, re, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools/site.json").read_text(encoding="utf-8"))
APPS = [a for a in CFG["apps"] if not a["key"].startswith("_")]
BY_KEY = {a["key"]: a for a in APPS}
EMAIL = CFG["site"]["email"]
UI_PATH = ROOT / "tools/i18n/ui.json"
UI = json.loads(UI_PATH.read_text(encoding="utf-8")) if UI_PATH.exists() else {}

EN_UI = {
  "nav_all_apps": "All apps", "nav_privacy": "Privacy", "nav_support": "Support",
  "cta_store": "Download on the App Store", "meta_free": "Free to download", "meta_devices": "iPhone & iPad",
  "meta_ios": "iOS {v} or later", "meta_no_account": "No account needed",
  "h_preview": "See it in action", "h_screens": "Screenshots", "h_features": "What's inside",
  "h_fine": "Pricing and subscription terms", "h_faq": "Questions people ask", "h_other": "More from go ka",
  "h_languages": "This page in other languages", "screenshot_alt": "{name} — screenshot {n}",
  "video_label": "{name} — app preview", "footer_made": "{name} is made by go ka.",
  "footer_email": "Questions or feedback: {email}", "privacy": "Privacy Policy", "terms": "Terms of Use",
  "breadcrumb_home": "Home", "get_app": "Get {name}",
}
# site.json 的 lang → 商店缓存的 locale 键
LANG2STORE = {"en": "en-US", "en-GB": "en-GB", "de": "de-DE", "fr": "fr-FR", "it": "it", "es": "es-ES",
              "es-MX": "es-MX", "pt-BR": "pt-BR", "ja": "ja", "ko": "ko", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "th": "th"}
NATIVE = {"en": "English", "en-GB": "English (UK)", "de": "Deutsch", "fr": "Français", "it": "Italiano", "es": "Español",
          "es-MX": "Español (México)", "pt-BR": "Português (Brasil)", "ja": "日本語", "ko": "한국어",
          "zh-Hans": "简体中文", "zh-Hant": "繁體中文", "th": "ไทย"}
# 预览视频文件名（assets/<key>/preview/<file>.mp4）
VIDEO_FILE = {"en": "en", "en-GB": "en", "pt-BR": "pt", "es": "en", "es-MX": "en"}
LEGAL = re.compile(r"auto-?renew|renews automatically|renouvel|verlängert|rinnov|renueva|renova|Apple Account|Apple ID|"
                   r"24 hours|24 Stunden|24 heures|24 ore|24 horas|24時間|24시간|24 ?小时|24 ?小時|24 ชั่วโมง|"
                   r"自動更新|자동 갱신|自动续|自動續|ต่ออายุ", re.I)

def esc(s): return html.escape(s, quote=True)
def t(lang, key, **kw):
    for l in (lang, lang.split("-")[0], "en"):
        if l in UI and key in UI[l]:
            return UI[l][key].format(**kw)
    return EN_UI[key].format(**kw)

def parent_of(a): return BY_KEY[a["variantOf"]] if a.get("variantOf") else a
def lang_of(a): return a.get("lang", "en")
def store_of(a):
    p = parent_of(a); cache = json.loads((ROOT / f"tools/store/{p['key']}.json").read_text(encoding="utf-8"))
    return cache.get(LANG2STORE[lang_of(a)]) or cache["en-US"]
def cdn(url, w): return re.sub(r"/[^/]+$", f"/{w}x0w.webp", url)
def store_link(a, s):
    p = parent_of(a); cc = s.get("storefront", "us")
    return f"https://apps.apple.com/app/id{p['appId']}" if lang_of(a) == "en" else f"https://apps.apple.com/{cc}/app/id{p['appId']}"

def parse_desc(text):
    """商店描述 → lede 段落 / 小标题板块 / 订阅条款小字。所有语言结构一致：空行分块，块首行是小标题，• 开头是要点。"""
    blocks = [[l.strip() for l in b.split("\n") if l.strip()] for b in re.split(r"\n\s*\n", text.strip())]
    lede, sections, fine, in_fine = [], [], [], False
    for b in blocks:
        first = b[0]
        if re.match(r"^[—\-–_]{3,}$", first):
            # 分隔线之后全是订阅条款；分隔线常和下一行同块（中间没空行），只丢掉线本身
            in_fine = True; b = b[1:]
            if b: fine.append(b)
            continue
        header = len(b) >= 2 and not first.startswith("•") and len(first) <= 60 and not first.endswith(("。", ".", "!", "?", "。", "！"))
        joined = " ".join(b)
        if in_fine or (not header and LEGAL.search(joined)):
            in_fine = True; fine.append(b); continue
        if not sections and not header:
            lede.append(joined); continue
        if header:
            paras = [l for l in b[1:] if not l.startswith("•")]
            # 小标题块里夹着的订阅条款句（「auto-renewing」「24 hours」…）挪到小字，不当卖点展示
            legal_lines = [l for l in paras if LEGAL.search(l)]
            if legal_lines:
                paras = [l for l in paras if l not in legal_lines]; fine.append(legal_lines)
            sections.append({"h": first, "items": [l[1:].strip() for l in b[1:] if l.startswith("•")], "paras": paras})
        elif sections:
            sections[-1]["paras"].append(joined)
    # 商店描述末尾的「Privacy Policy: https://…」「Terms of Use (EULA): https://…」纯链接行不进网页（页脚已有链接）
    fine = [[l for l in b if not re.search(r"https?://", l)] for b in fine]
    fine = [b for b in fine if b]
    return lede, sections, fine

def nice_heading(h):
    """商店描述的英文小标题是全大写（EVERY WIDGET, FREE）——网页上改成句首大写；专有名词保留。"""
    if h != h.upper() or not re.search(r"[A-Z]", h): return h
    keep = {"QR", "PDF", "AI", "PRO", "ICLOUD", "IOS", "IPHONE", "IPAD", "WIFI"}
    fix = {"ICLOUD": "iCloud", "IOS": "iOS", "IPHONE": "iPhone", "IPAD": "iPad", "WIFI": "WiFi", "PRO": "Pro"}
    words = h.lower().split(" ")
    out = []
    for i, w in enumerate(words):
        up = w.upper().strip(",.:")
        if up in keep: out.append(w.upper().replace(up, fix.get(up, up)))
        elif i == 0: out.append(w[:1].upper() + w[1:])
        else: out.append(w)
    return " ".join(out)

def video_of(a):
    p = parent_of(a); lang = lang_of(a); name = VIDEO_FILE.get(lang, lang)
    for cand in (name, "en"):
        f = ROOT / "assets" / p["key"] / "preview" / f"{cand}.mp4"
        if f.exists():
            return f"/assets/{p['key']}/preview/{cand}.mp4", f"/assets/{p['key']}/preview/{cand}.jpg"
    return None, None

def family(a):
    p = parent_of(a)
    return [p] + [v for v in APPS if v.get("variantOf") == p["key"] and v.get("live")]

def sibling_path(other_parent, lang):
    """其它 app 在同一语言下的页面；没有就回英文页。"""
    for v in APPS:
        if v.get("variantOf") == other_parent["key"] and lang_of(v) == lang and v.get("live"):
            return v["path"]
    return other_parent["path"]

CSS = """
@font-face{font-family:"Josefin Sans";src:url(/assets/fonts/josefin-sans-latin.woff2) format("woff2");font-weight:100 700;font-display:swap}
@font-face{font-family:"Manrope";src:url(/assets/fonts/manrope-latin.woff2) format("woff2");font-weight:200 800;font-display:swap}
:root{--ink:#141414;--line:#151515;--muted:#5a5a5a;--soft:#737373;--rule:#e7e5df;--paper:#fff;--cream:#fffaf0;--yellow:#f5dc61;
--display:"Josefin Sans","Manrope","PingFang SC","Hiragino Sans",system-ui,sans-serif;
--text:"Manrope","PingFang SC","Hiragino Sans","Microsoft YaHei","Noto Sans Thai",system-ui,sans-serif;--wrap:1080px;--gutter:24px}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:400 16px/1.7 var(--text);-webkit-font-smoothing:antialiased;overflow-x:hidden}
a{color:inherit}img,video,svg{display:block;max-width:100%}
.wrap{max-width:var(--wrap);margin:0 auto;padding:0 var(--gutter)}
:focus-visible{outline:2px solid var(--ink);outline-offset:3px;border-radius:4px}
.top{display:flex;align-items:center;justify-content:space-between;height:80px;gap:16px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;flex:none}.brand svg{width:30px;height:30px;flex:none}
.brand b{font:600 20px/1 var(--display);letter-spacing:-.4px;white-space:nowrap}
.nav{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end}.nav a{font:700 12px/1 var(--text);letter-spacing:1.3px;text-transform:uppercase;text-decoration:none;padding:12px 10px;border-radius:999px;white-space:nowrap}
html[lang^=ja] .nav a,html[lang^=zh] .nav a,html[lang^=ko] .nav a,html[lang^=th] .nav a{letter-spacing:0;text-transform:none}
html[lang^=ja] h1,html[lang^=zh] h1,html[lang^=ko] h1{letter-spacing:0;font-weight:600}
.nav a:hover{background:var(--cream)}
.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(32px,6vw,72px);align-items:center;padding:clamp(24px,5vw,56px) 0 clamp(32px,6vw,64px)}
.hero .icon{width:84px;height:84px;border-radius:19px;box-shadow:0 10px 30px -14px rgba(0,0,0,.35);margin-bottom:22px}
h1{margin:0;font:500 clamp(34px,5vw,54px)/1.08 var(--display);letter-spacing:-.03em;text-wrap:balance}
.lede{margin:20px 0 0;color:var(--muted);font-size:17px;line-height:1.7}.lede p{margin:0 0 12px}
.cta{display:inline-flex;align-items:center;gap:10px;margin-top:22px;background:var(--ink);color:#fff;text-decoration:none;font:700 15px/1 var(--text);padding:16px 24px;border-radius:999px;transition:background .2s,color .2s}
.cta:hover{background:var(--yellow);color:var(--ink)}.cta svg{width:18px;height:18px;fill:currentColor}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0;padding:0;list-style:none;font:600 12px/1 var(--text);letter-spacing:.6px;color:var(--muted)}
.chips li{border:1px solid var(--rule);border-radius:999px;padding:9px 12px}
.hero-media{position:relative}.hero-media video,.hero-media img{width:min(100%,360px);margin:0 auto;border-radius:28px;aspect-ratio:886/1920;background:var(--cream);object-fit:cover}
.hero-media .play{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);pointer-events:none;width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.92);display:grid;place-items:center;box-shadow:0 8px 24px -8px rgba(0,0,0,.4)}
.hero-media .play svg{width:22px;height:22px;margin-left:3px}
section{scroll-margin-top:20px}
.sec{padding:clamp(40px,7vw,80px) 0 0}
h2{margin:0 0 20px;font:500 clamp(26px,3.4vw,36px)/1.15 var(--display);letter-spacing:-.02em}
.label{font:700 12px/1 var(--text);letter-spacing:2.2px;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
.shots{display:flex;gap:14px;overflow-x:auto;padding:4px 0 18px;margin:0;list-style:none;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch}
.shots li{flex:0 0 auto;scroll-snap-align:start}.shots img{width:230px;aspect-ratio:1320/2868;height:auto;border-radius:20px;border:1px solid var(--rule);background:var(--cream)}
.feats{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:clamp(24px,4vw,44px) clamp(28px,5vw,64px)}
.feat h3{margin:0 0 10px;font:600 18px/1.35 var(--text);letter-spacing:-.2px}
.feat ul{margin:0;padding:0;list-style:none}.feat li{position:relative;padding-left:22px;margin:0 0 8px;color:var(--muted)}
.feat li::before{content:"";position:absolute;left:0;top:.62em;width:10px;height:10px;border-radius:50%;background:var(--yellow);border:1.5px solid var(--ink)}
.feat p{margin:0 0 10px;color:var(--muted)}
.fine{margin-top:clamp(28px,4vw,40px);border-top:1px solid var(--rule);padding-top:18px}
.fine summary{cursor:pointer;font:600 15px/1.4 var(--text);list-style:none;display:flex;align-items:center;gap:8px}
.fine summary::-webkit-details-marker{display:none}.fine summary::before{content:"+";font:500 20px/1 var(--display);width:20px}
.fine[open] summary::before{content:"–"}.fine p{margin:10px 0 0;color:var(--muted);font-size:14px;line-height:1.65}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:0 clamp(28px,5vw,64px)}
.card{padding:22px 0;border-top:1px solid var(--rule)}.card h3{margin:0;font:600 17px/1.4 var(--text);letter-spacing:-.2px}
.card p{margin:10px 0 0;color:var(--muted);font-size:15px}
.langs{display:flex;flex-wrap:wrap;gap:8px 18px;margin:0;padding:0;list-style:none;font-size:14px}.langs a{color:var(--muted);text-underline-offset:4px}
.langs a[aria-current]{color:var(--ink);font-weight:700;text-decoration:none}
.others{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.others a{display:flex;align-items:center;gap:12px;text-decoration:none;border:1px solid var(--rule);border-radius:16px;padding:14px;transition:background .2s}
.others a:hover{background:var(--cream)}.others img{width:44px;height:44px;border-radius:10px}.others b{display:block;font:600 15px/1.3 var(--text)}
.others small{display:block;color:var(--soft);font-size:12px;margin-top:2px}
.end{text-align:center;padding:clamp(48px,8vw,90px) 0 clamp(40px,6vw,60px)}
footer{border-top:1px solid var(--rule);padding:32px 0 48px;font-size:13px;color:var(--muted)}
footer p{margin:0 0 8px}footer a{text-underline-offset:3px}
@media (max-width:760px){:root{--gutter:16px}.top{height:68px}.hero{grid-template-columns:1fr}.hero-media{order:-1}.hero-media video,.hero-media img{width:min(72vw,300px)}
.nav a{padding:10px 7px;letter-spacing:.8px;font-size:11px}.shots img{width:200px}}
"""

SCRIPT = '<script>document.querySelectorAll(".hero-media video").forEach(function(v){v.addEventListener("play",function(){var p=v.parentNode.querySelector(".play");if(p)p.remove()},{once:true})});</script>'
LOGO = '<svg viewBox="0 0 34 34" aria-hidden="true"><circle cx="17" cy="19" r="9.5" fill="#f5dc61" stroke="#151515" stroke-width="2"/><rect x="0" y="22" width="34" height="12" fill="#fff"/><path d="M3 22h28M9 27h16" stroke="#151515" stroke-width="2" stroke-linecap="round"/></svg>'
APPLE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16.4 12.7c0-2.5 2-3.7 2.1-3.8-1.2-1.7-3-1.9-3.6-2-1.5-.2-3 .9-3.8.9-.8 0-2-.9-3.3-.9-1.7 0-3.3 1-4.2 2.5-1.8 3.1-.5 7.7 1.3 10.3.9 1.2 1.9 2.6 3.2 2.6 1.3-.1 1.8-.8 3.3-.8s2 .8 3.3.8c1.4 0 2.3-1.3 3.1-2.5 1-1.4 1.4-2.8 1.4-2.9-.1 0-2.8-1.1-2.8-4.2zM14 5.3c.7-.8 1.1-2 1-3.1-1 0-2.2.7-2.9 1.5-.6.7-1.2 1.9-1.1 3 1.1.1 2.3-.6 3-1.4z"/></svg>'

def render(a):
    p, lang, s = parent_of(a), lang_of(a), store_of(a)
    name = s["name"]
    lede, sections, fine = parse_desc(s["description"])
    video, poster = video_of(a)
    legal = a.get("legal") or p.get("legal") or []
    privacy = next((h for h, l in legal if "privacy" in h), None)
    terms = next((h for h, l in legal if "terms" in h), None)
    shots = s["screenshots"][:10]
    icon = cdn(s["icon"], 256) if s.get("icon", "").startswith("http") else (p.get("icon") or "")
    fam = family(a)
    T = lambda k, **kw: t(lang, k, **kw)

    chips = [T("meta_free"), T("meta_devices"), T("meta_ios", v=(s.get("minOS") or "17.0").split(".")[0])]
    if p.get("noAccount"): chips.append(T("meta_no_account"))

    media = ""
    if video:
        media = (f'<div class="hero-media"><video controls playsinline preload="none" poster="{poster}" '
                 f'aria-label="{esc(T("video_label", name=name))}"><source src="{video}" type="video/mp4"></video>'
                 f'<span class="play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></span></div>')
    elif shots:
        media = (f'<div class="hero-media"><img src="{cdn(shots[0], 460)}" srcset="{cdn(shots[0], 460)} 460w, {cdn(shots[0], 920)} 920w" '
                 f'sizes="(max-width:760px) 72vw, 360px" width="460" height="999" alt="{esc(T("screenshot_alt", name=name, n=1))}" fetchpriority="high"></div>')

    shot_items = "\n".join(
        f'      <li><img loading="lazy" decoding="async" src="{cdn(u, 460)}" srcset="{cdn(u, 460)} 460w, {cdn(u, 920)} 920w" '
        f'sizes="(max-width:760px) 200px, 230px" width="230" height="500" alt="{esc(T("screenshot_alt", name=name, n=i))}"></li>'
        for i, u in enumerate(shots, 1))

    feats = []
    for sec in sections:
        body = ""
        if sec["items"]: body += "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in sec["items"]) + "</ul>"
        body += "".join(f"<p>{esc(x)}</p>" for x in sec["paras"])
        feats.append(f'    <div class="feat"><h3>{esc(nice_heading(sec["h"]))}</h3>{body}</div>')
    fine_html = ""
    if fine:
        fine_html = (f'  <details class="fine"><summary>{esc(T("h_fine"))}</summary>'
                     + "".join(f"<p>{esc(' '.join(b))}</p>" for b in fine) + "</details>")

    langs = "\n".join(
        f'      <li><a href="{v["path"]}" hreflang="{lang_of(v)}" lang="{lang_of(v)}"{" aria-current=\"page\"" if v is a else ""}>{NATIVE.get(lang_of(v), lang_of(v))}</a></li>'
        for v in sorted(fam, key=lambda v: (v is not p, NATIVE.get(lang_of(v), ""))))
    others = []
    for o in sorted((x for x in APPS if x.get("home") and x.get("live") and x["key"] != p["key"]), key=lambda x: x["home"]["order"]):
        oi = cdn(o["icon"], 128) if o.get("icon", "").startswith("http") else o.get("icon", "")
        others.append(f'      <a href="{sibling_path(o, lang)}"><img src="{oi}" width="44" height="44" alt="" loading="lazy">'
                      f'<span><b>{esc(o["home"]["label"])}</b><small>{esc(o["home"]["tagline"])}</small></span></a>')

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(a["title"])}</title>
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
  <a class="brand" href="/">{LOGO}<b>go ka</b></a>
  <nav class="nav" aria-label="Main">
    <a href="/">{esc(T("nav_all_apps"))}</a>
    {f'<a href="{privacy}">{esc(T("nav_privacy"))}</a>' if privacy else ''}
    <a href="mailto:{EMAIL}?subject={esc(p['shortName'])}">{esc(T("nav_support"))}</a>
  </nav>
</header>

<main class="wrap">
<section class="hero">
  <div>
    <img class="icon" src="{icon}" width="84" height="84" alt="">
    <h1>{esc(name)}</h1>
    <div class="lede">{"".join(f"<p>{esc(x)}</p>" for x in lede)}</div>
    <a class="cta" href="{store_link(a, s)}">{APPLE}{esc(T("cta_store"))}</a>
    <ul class="chips">{"".join(f"<li>{esc(c)}</li>" for c in chips)}</ul>
  </div>
  {media}
</section>

<section class="sec" id="screenshots" aria-labelledby="h-screens">
  <h2 id="h-screens">{esc(T("h_screens"))}</h2>
  <ul class="shots">
{shot_items}
  </ul>
</section>

<section class="sec" id="features" aria-labelledby="h-features">
  <h2 id="h-features">{esc(T("h_features"))}</h2>
  <div class="feats">
{chr(10).join(feats)}
  </div>
{fine_html}
</section>

<section class="sec" id="faq-section">
  <!-- faq:start -->
  <!-- faq:end -->
</section>

<section class="sec" id="languages" aria-labelledby="h-langs">
  <p class="label" id="h-langs">{esc(T("h_languages"))}</p>
  <ul class="langs">
{langs}
  </ul>
</section>

<section class="sec" id="more" aria-labelledby="h-more">
  <h2 id="h-more">{esc(T("h_other"))}</h2>
  <div class="others">
{chr(10).join(others)}
  </div>
</section>

<div class="end">
  <a class="cta" href="{store_link(a, s)}">{APPLE}{esc(T("get_app", name=name))}</a>
</div>
</main>

<footer>
  <div class="wrap">
    <p>{esc(T("footer_made", name=name))} {esc(T("footer_email", email=""))}<a href="mailto:{EMAIL}">{EMAIL}</a></p>
    <p>{f'<a href="{privacy}">{esc(T("privacy"))}</a>' if privacy else ''}{' · ' if privacy and terms else ''}{f'<a href="{terms}">{esc(T("terms"))}</a>' if terms else ''} · <a href="/">go ka</a></p>
  </div>
</footer>
{SCRIPT}
</body>
</html>
"""

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    n = 0
    for a in APPS:
        p = parent_of(a)
        if not p.get("generated") or not a.get("live"): continue
        if only and p["key"] != only: continue
        out = ROOT / a["path"].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(a), encoding="utf-8"); n += 1
        print(f"  {a['path']}  ← {LANG2STORE[lang_of(a)]}")
    print(f"生成 {n} 页；接着跑 tools/build_seo.py")

if __name__ == "__main__":
    main()
