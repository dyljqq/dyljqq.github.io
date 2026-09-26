#!/usr/bin/env python3
"""从 site.json + tools/store/<app>.json（商店本地化文案与截图缓存）生成产品承载页。

  python3 tools/build_pages.py            # 生成所有 generated:true 的 app（含其语言变体）
  python3 tools/build_pages.py countdown  # 只生成一个 app

页面正文全部来自 App Store 商店文案（名字、钩子句、各段小标题与要点、订阅条款），
截图直接引用苹果 CDN 的 WebP（<w>x0w.webp），预览视频在 assets/<key>/preview/<lang>.mp4。
只有 <title> 的 tagline、meta description、FAQ 和界面词需要翻译（tools/i18n/*.json）。
生成完必须再跑 tools/build_seo.py：head 的 SEO 块和可见 FAQ 由它填。
"""
from urllib.parse import quote
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
  "h_whatsnew": "What's new in version {v}", "h_guides": "Guides and free tools", "nav_blog": "Blog", "nav_tools": "Tools",
  "follow": "Follow go ka",
}
# site.json 的 lang → 商店缓存的 locale 键
LANG2STORE = {"en": "en-US", "en-GB": "en-GB", "de": "de-DE", "fr": "fr-FR", "it": "it", "es": "es-ES",
              "es-MX": "es-MX", "pt-BR": "pt-BR", "ja": "ja", "ko": "ko", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "th": "th"}
NATIVE = {"en": "English", "en-GB": "English (UK)", "de": "Deutsch", "fr": "Français", "it": "Italiano", "es": "Español",
          "es-MX": "Español (México)", "pt-BR": "Português (Brasil)", "ja": "日本語", "ko": "한국어",
          "zh-Hans": "简体中文", "zh-Hant": "繁體中文", "th": "ไทย"}
ORDER = ["en", "en-GB", "de", "fr", "it", "es", "es-MX", "pt-BR", "ja", "ko", "zh-Hans", "zh-Hant", "th"]
ASC_LOC = {"en": "en-US", "en-GB": "en-GB", "de": "de-DE", "fr": "fr-FR", "es": "es-ES"}   # 其余语言 ASC locale 同名
SUBS_PATH = ROOT / "tools/store/subtitles.json"
SUBS = json.loads(SUBS_PATH.read_text(encoding="utf-8")) if SUBS_PATH.exists() else {}
order_key = lambda lang: ORDER.index(lang) if lang in ORDER else 99

FALLBACK_PATH = ROOT / "tools/i18n/fallback.json"
FALLBACK = json.loads(FALLBACK_PATH.read_text(encoding="utf-8")) if FALLBACK_PATH.exists() else {}

def localized(app, lang):
    """商店在这个语言有没有本地化（以 ASC app-info 有没有这个 locale 为准；巴西商店回落欧葡也算没有）。"""
    return ASC_LOC.get(lang, lang) in SUBS.get(app["key"], {})

def fallback(app, lang, key):
    return (FALLBACK.get(app["key"], {}).get(lang) or {}).get(key)

def subtitle(app, lang):
    """该语言商店副标题（ASC app-info）；商店没这个语言就用 fallback.json 的译文，最后才回落英文。"""
    if lang == "en":
        return app["home"]["tagline"]
    if localized(app, lang):
        return SUBS[app["key"]][ASC_LOC.get(lang, lang)].get("subtitle") or app["home"]["tagline"]
    return fallback(app, lang, "tagline") or app["home"]["tagline"]

def icon_of(app, w=128):
    """site.json 没存图标的 app（Repdex）从商店缓存取。"""
    u = app.get("icon") or ""
    if not u.startswith("http"):
        try:
            cache = json.loads((ROOT / f"tools/store/{app['key']}.json").read_text(encoding="utf-8"))
            u = next(v["icon"] for v in cache.values() if v and v.get("icon"))
        except (OSError, StopIteration):
            return ""
    return cdn(u, w)

def page_for(app, lang, where="more"):
    """站内对应语言的页面；页面只有中文（单词兽）而读者不是中文时，直接去商店，别把人送到看不懂的页面。"""
    page_lang = app.get("lang") or "en"
    if page_lang.startswith("zh") and not lang.startswith("zh"):
        return f"https://apps.apple.com/app/apple-store/id{app['appId']}?pt={PT}&ct=web-{app['key']}-{where}&mt=8"
    return sibling_path(app, lang)

SEP = re.compile(r"(\s*[-–—:：·・|｜、，,&＆]\s*)")
def title_html(name, lang):
    """中日文标题没有空格，浏览器会在词中间断行（BeforeGo 简中断成「AI行/程规划」）：按标点切成不可拆的段。"""
    if lang == "th":        # 泰文词之间不空格、词典断词会把「ใบเสร็จ」拆开；商店名里的空格才是短语边界
        return " ".join(f'<span class="seg">{esc(x)}</span>' for x in name.split())
    if not lang.startswith(("zh", "ja")):
        return esc(name)
    parts = SEP.split(name); segs = []
    for i in range(0, len(parts), 2):
        segs.append(parts[i] + (parts[i + 1] if i + 1 < len(parts) else ""))
    return "".join(f'<span class="seg">{esc(x)}</span>' for x in segs if x)

FEAT_EN_PATH = ROOT / "tools/i18n/features.en.json"
FEAT_TR_PATH = ROOT / "tools/i18n/features.json"
FEAT_EN = json.loads(FEAT_EN_PATH.read_text(encoding="utf-8")) if FEAT_EN_PATH.exists() else {}
FEAT_TR = json.loads(FEAT_TR_PATH.read_text(encoding="utf-8")) if FEAT_TR_PATH.exists() else {}

def shot_num(url):
    """商店截图地址倒数第二段是上传时的文件名（01-guide.png）；取编号前缀，跨语言对得上同一张图。"""
    m = re.match(r"(\d+)", url.rstrip("/").split("/")[-2])
    return m.group(1).zfill(2) if m else None

def feature_shot(f, s, lang):
    """功能块配哪张截图：有 key 就按文件名关键词找（各语言商店截图的编号不一定一样——BeforeGo 日文/简中的 07/09 互换、10 是品牌图），
    没有 key 才按编号；该语言没有这张图就返回 None（这一块在该语言不出现）。"""
    names = [(u, u.rstrip("/").split("/")[-2]) for u in s["screenshots"]]
    if f.get("key"):
        return next((u for u, n in names if f["key"] in n), None)
    num = f.get("override", {}).get(lang, f["shot"])
    return next((u for u, n in names if shot_num(u) == num), None)

def highlights(a, s, lang):
    """功能图文块（参照 EasyNotes 官网）：一张商店截图配一个标题 + 两三句。英文源稿 tools/i18n/features.en.json，
    其它语言 tools/i18n/features.json（低阶模型译）；该语言没有译文就不出这一节，不拿英文顶。"""
    p = parent_of(a); src = FEAT_EN.get(p["key"])
    if not src:
        return ""
    if lang in ("en", "en-GB"):
        texts, ui = src, FEAT_EN["ui"]
    else:
        tr = FEAT_TR.get(lang) or {}
        texts, ui = tr.get(p["key"]), tr.get("ui")
        if not texts or not ui or len(texts) != len(src):
            return ""
    rows = []
    for f, t in zip(src, texts):
        u = feature_shot(f, s, lang)
        if not u:
            continue
        rows.append(f'    <div class="hl"><figure><img loading="lazy" decoding="async" src="{cdn(u, 460)}" '
                    f'srcset="{cdn(u, 460)} 460w, {cdn(u, 920)} 920w" sizes="(max-width:760px) 70vw, 300px" width="460" height="999" '
                    f'alt="{esc(t["title"])}"></figure><div><h3>{esc(t["title"])}</h3><p>{esc(t["text"])}</p></div></div>')
    if not rows:
        return ""
    return (f'<section class="sec" id="highlights" aria-labelledby="h-highlights">\n  <h2 id="h-highlights">{esc(ui["h_highlights"])}</h2>\n'
            f'  <div class="hls">\n' + "\n".join(rows) + '\n  </div>\n</section>\n'), ui["h_details"]

TOOLS_MANIFEST = ROOT / "tools/tools.json"
SOCIAL = CFG["site"].get("social") or []      # [{"name": "Instagram", "url": "..."}]，用户给了账号才会出现在页脚

def whatsnew(s, lang, override=None):
    """商店当前版本的更新说明（各语言商店原文）；override = site.json 的 whatsNew（原文把单据叫 factura / 發票、或用 Sie 时的改写版，事实不变）。"""
    notes, ver = (override or s.get("releaseNotes") or "").strip(), s.get("version")
    if not notes or not ver:
        return ""
    out = []
    for b in re.split(r"\n\s*\n", notes):
        lines = [l.strip() for l in b.split("\n") if l.strip()]
        items = [l.lstrip("•-– ").strip() for l in lines if l.startswith(("•", "- ", "– "))]
        text = [l for l in lines if not l.startswith(("•", "- ", "– "))]
        for i, l in enumerate(text):
            is_head = len(lines) > 1 and i == 0 and len(l) <= 60 and not l.endswith((".", "。", "!", "！", "?", "？"))
            out.append(f"<h3>{esc(nice_heading(l, lang))}</h3>" if is_head else f"<p>{esc(l)}</p>")
        if items:
            out.append("<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>")
    return (f'<section class="sec" id="whats-new" aria-labelledby="h-new">\n  <h2 id="h-new">{esc(t(lang, "h_whatsnew", v=ver))}</h2>\n'
            f'  <div class="news">{"".join(out)}</div>\n</section>\n')

def guides(p, lang):
    """这个 app 的同语言指南 / 工具页 / 博客（产品页和内容页互链）。"""
    try:
        items = json.loads(TOOLS_MANIFEST.read_text(encoding="utf-8"))
    except OSError:
        return ""
    mine = [x for x in items if x.get("app") == p["key"] and (x.get("lang") or "en") == ("en" if lang == "en-GB" else lang)]
    if not mine:
        return ""
    cards = "".join(f'<a href="{x["path"]}"><b>{esc(x.get("hubTitle") or x.get("title"))}</b><span>{esc(x.get("description", ""))}</span></a>' for x in mine)
    return (f'<section class="sec" id="guides" aria-labelledby="h-guides">\n  <h2 id="h-guides">{esc(t(lang, "h_guides"))}</h2>\n'
            f'  <div class="guides">{cards}</div>\n</section>\n')

SOCIAL_ICON = {
    "instagram": '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="17.5" cy="6.5" r="1.2"/></svg>',
    "x": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4l16 16M20 4L4 20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
}
def social_html(lang):
    """页脚社媒：TikTok / Reddit / 小红书（site.json site.social）。rel=me 让搜索引擎把这些账号认成同一个实体。"""
    if not SOCIAL:
        return ""
    def name(x):
        if x.get("key") == "xhs":
            return "小紅書" if lang == "zh-Hant" else ("小红书" if lang.startswith("zh") else x.get("nameIntl", x["name"]))
        return x["name"]
    links = " · ".join(f'<a href="{esc(x["url"])}" rel="me noopener" target="_blank">{esc(name(x))}</a>' for x in SOCIAL)
    colon = "：" if lang.startswith(("zh", "ja")) else ("\u00a0: " if lang == "fr" else ": ")
    return f'<p class="social">{esc(t(lang, "follow"))}{colon}{links}</p>'

# 预览视频文件名（assets/<key>/preview/<file>.mp4）
VIDEO_FILE = {"en": "en", "en-GB": "en", "pt-BR": "pt"}
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
PT = "128309253"   # App Store 活动归因 provider token（见 build_seo.py 的说明）
def store_link(a, s, where="app"):
    """页面上的下载按钮：带活动参数 ct=web-<app>-<入口>，非英文页落到对应国家的商店。"""
    p = parent_of(a); cc = s.get("storefront", "us")
    ct = f"web-{p['key']}-{where}"; assert len(ct) <= 30
    region = "" if lang_of(a) == "en" else f"{cc}/"
    return f"https://apps.apple.com/{region}app/apple-store/id{p['appId']}?pt={PT}&ct={ct}&mt=8"

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
        joined = re.sub(r"(?<=[。！？」』）])\s+", "", " ".join(b))   # 中日文句末标点后按行拼接不留半角空格
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
            paras = [l for l in paras if not re.search(r"https?://", l)]
            sections.append({"h": first, "items": [l[1:].strip() for l in b[1:] if l.startswith("•")], "paras": paras})
        elif sections and not re.search(r"https?://", joined):
            sections[-1]["paras"].append(joined)
    # 商店描述末尾的「Privacy Policy: https://…」「Terms of Use (EULA): https://…」纯链接行不进网页（页脚已有链接）
    fine = [[l for l in b if not re.search(r"https?://", l)] for b in fine]
    fine = [b for b in fine if b]
    return lede, sections, fine

def nice_heading(h, lang="en"):
    """商店描述的英文小标题是全大写（EVERY WIDGET, FREE）——网页上改成句首大写；专有名词保留。
    德语不改（名词必须大写，转小写会写错，09-26 评审）；含中日韩泰文字的不改（「QR코드」会被改成「Qr코드」），只把夹在汉字间的半角逗号换成全角。"""
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af\u0e00-\u0e7f]", h):
        return re.sub(r"(?<=[\u3400-\u9fff]),\s*(?=[\u3400-\u9fff])", "，", h)
    if lang.startswith("de") or h != h.upper() or not re.search(r"[A-Z]", h): return h
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
    for cand in ((name, "en") if lang in ("en", "en-GB") else (name,)):
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
.nav{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;margin-left:auto}.nav a{font:700 12px/1 var(--text);letter-spacing:1.3px;text-transform:uppercase;text-decoration:none;padding:12px 10px;border-radius:999px;white-space:nowrap}
html[lang^=ja] .nav a,html[lang^=zh] .nav a,html[lang^=ko] .nav a,html[lang^=th] .nav a{letter-spacing:0;text-transform:none}
html[lang^=ja] h1,html[lang^=zh] h1,html[lang^=ko] h1{letter-spacing:0;font-weight:600}
html[lang^=ko] body{word-break:keep-all;overflow-wrap:anywhere}
html[lang^=zh] h1{text-wrap:wrap}
html[lang^=th] *{letter-spacing:0!important}
.seg{display:inline-block}html[lang^=ja] h1{word-break:auto-phrase}
.nav a:hover{background:var(--cream)}
.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(32px,6vw,72px);align-items:center;padding:clamp(24px,5vw,56px) 0 clamp(32px,6vw,64px)}
.hero .icon{width:84px;height:84px;border-radius:19px;box-shadow:0 10px 30px -14px rgba(0,0,0,.35);margin-bottom:22px}
h1{margin:0;font:500 clamp(34px,5vw,54px)/1.08 var(--display);letter-spacing:-.03em;text-wrap:balance}
.lede{margin:20px 0 0;color:var(--muted);font-size:17px;line-height:1.7}.lede p{margin:0 0 12px}
.cta{display:inline-flex;align-items:center;gap:10px;margin-top:22px;background:var(--ink);color:#fff;text-decoration:none;font:700 15px/1 var(--text);padding:16px 24px;border-radius:999px;transition:background .2s,color .2s}
.cta:hover{background:var(--yellow);color:var(--ink)}.cta svg{width:18px;height:18px;fill:currentColor}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0;padding:0;list-style:none;font:600 12px/1 var(--text);letter-spacing:.6px;color:var(--muted)}
.chips li{border:1px solid var(--rule);border-radius:999px;padding:9px 12px}
.hero-media{position:relative}.hero-media video,.hero-media img{width:min(100%,360px);height:auto;margin:0 auto;border-radius:28px;aspect-ratio:886/1920;background:var(--cream);object-fit:cover}
.hero-media .play{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);cursor:pointer;border:0;padding:0;width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,.92);display:grid;place-items:center;box-shadow:0 8px 24px -8px rgba(0,0,0,.4)}
.hero-media .play svg{width:22px;height:22px;margin-left:3px}
section{scroll-margin-top:20px}
.sec{padding:clamp(40px,7vw,80px) 0 0}
h2{margin:0 0 20px;font:500 clamp(26px,3.4vw,36px)/1.15 var(--display);letter-spacing:-.02em}
.label{font:700 12px/1 var(--text);letter-spacing:2.2px;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
.shots{display:flex;gap:14px;overflow-x:auto;padding:4px 0 18px;margin:0;list-style:none;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch}
.shots li{flex:0 0 auto;scroll-snap-align:start}.shots img{width:230px;aspect-ratio:1320/2868;height:auto;border-radius:20px;border:1px solid var(--rule);background:var(--cream)}
.feats{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:clamp(24px,4vw,44px) clamp(28px,5vw,64px)}
.feat h3{margin:0 0 10px;font:600 18px/1.35 var(--text);letter-spacing:-.2px}.feat h3.caps{font-size:14px;letter-spacing:.08em}
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
.hls{margin-top:8px}.hl{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(24px,6vw,80px);align-items:center;padding:clamp(28px,5vw,56px) 0;border-top:1px solid var(--rule)}
.hl:nth-child(even) figure{order:2}.hl figure{margin:0;display:flex;justify-content:center}.hl img{width:min(100%,300px);height:auto;border-radius:26px;border:1px solid var(--rule);background:var(--cream)}.hl h3{margin:0 0 14px;font:500 clamp(26px,3.2vw,36px)/1.15 var(--display);letter-spacing:-.02em;text-wrap:balance}.hl p{margin:0;color:var(--muted);font-size:17px;line-height:1.7;max-width:32em}html:is([lang^=ja],[lang^=zh],[lang^=ko]) .hl h3{letter-spacing:0;font-weight:600}html[lang^=ja] .hl h3{word-break:auto-phrase}
.news{max-width:46em;color:var(--muted)}.news h3{margin:18px 0 6px;font:600 16px/1.4 var(--text);color:var(--ink)}.news p{margin:0 0 10px}.news ul{margin:0 0 10px;padding-left:20px}.news li{margin:0 0 6px}
.guides{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}.guides a{display:block;text-decoration:none;border:1px solid var(--rule);border-radius:16px;padding:18px 20px;transition:background .2s}.guides a:hover{background:var(--cream)}.guides b{display:block;font:600 16px/1.35 var(--text)}.guides span{display:block;margin-top:6px;color:var(--muted);font-size:14px;line-height:1.55}
.others{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.others a{display:flex;align-items:center;gap:12px;text-decoration:none;border:1px solid var(--rule);border-radius:16px;padding:14px;transition:background .2s}
.others a:hover{background:var(--cream)}.others img{width:44px;height:44px;border-radius:10px}.others b{display:block;font:600 15px/1.3 var(--text)}
.others small{display:block;color:var(--soft);font-size:12px;margin-top:2px}
.end{text-align:center;padding:clamp(48px,8vw,90px) 0 clamp(40px,6vw,60px)}
footer{border-top:1px solid var(--rule);padding:32px 0 48px;font-size:13px;color:var(--muted)}
footer p{margin:0 0 8px}footer a{text-underline-offset:3px}
@media (max-width:760px){.hl{grid-template-columns:1fr}.hl:nth-child(even) figure{order:0}.hl figure{order:2}.hl img{width:min(70vw,280px)}:root{--gutter:16px}.top{height:auto;flex-wrap:wrap;row-gap:2px;padding-top:12px;padding-bottom:2px}.top .lang-switch{margin-left:auto}.nav{order:3;width:100%;margin:0 0 0 -7px;flex-wrap:nowrap;justify-content:flex-start;overflow-x:auto;scrollbar-width:none}.nav::-webkit-scrollbar{display:none}.hero{grid-template-columns:1fr}.hero-media video,.hero-media img{width:min(72vw,300px)}
.nav a{padding:10px 7px;letter-spacing:.8px;font-size:11px;flex:none}.shots img{width:200px}}
"""

SCRIPT = '<script>document.querySelectorAll(".hero-media").forEach(function(m){var v=m.querySelector("video"),b=m.querySelector(".play");if(!v||!b)return;b.addEventListener("click",function(){v.controls=true;v.play();b.remove()})});</script>'
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
    k = a.get("shotStart", 0)
    shots = shots[k:] + shots[:k]
    # 首屏图别和「功能图文」第一块重复：挑第一张没被功能图文用到的截图（没有功能图文就照旧）
    used = {feature_shot(f, s, lang_of(a)) for f in FEAT_EN.get(parent_of(a)["key"], [])} if highlights(a, s, lang_of(a)) else set()
    hero_shot = next((u for u in shots if u not in used), shots[0] if shots else None)
    icon = cdn(s["icon"], 256) if s.get("icon", "").startswith("http") else (p.get("icon") or "")
    fam = family(a)
    T = lambda k, **kw: t(lang, k, **kw)
    hl = highlights(a, s, lang)
    home = "/" if lang in ("en", "en-GB") or not (ROOT / lang.lower() / "index.html").exists() else f"/{lang.lower()}/"
    hl_html, details_h = hl if hl else ("", None)

    chips = [T("meta_free"), T("meta_devices"), T("meta_ios", v=(s.get("minOS") or "17.0").split(".")[0])]
    if p.get("noAccount"): chips.append(T("meta_no_account"))

    media = ""
    if video:
        media = (f'<div class="hero-media"><video playsinline preload="none" poster="{poster}" '
                 f'aria-label="{esc(T("video_label", name=name))}"><source src="{video}" type="video/mp4"></video>'
                 f'<button type="button" class="play" aria-label="{esc(T("video_label", name=name))}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg></button></div>')
    elif shots:
        media = (f'<div class="hero-media"><img src="{cdn(hero_shot, 460)}" srcset="{cdn(hero_shot, 460)} 460w, {cdn(hero_shot, 920)} 920w" '
                 f'sizes="(max-width:760px) 72vw, 360px" width="460" height="999" alt="{esc(T("screenshot_alt", name=name, n=1))}" fetchpriority="high"></div>')

    shot_items = "\n".join(
        f'      <li><img loading="lazy" decoding="async" src="{cdn(u, 460)}" srcset="{cdn(u, 460)} 460w, {cdn(u, 920)} 920w" '
        f'sizes="(max-width:760px) 200px, 230px" width="230" height="500" alt="{esc(T("screenshot_alt", name=name, n=i))}"></li>'
        for i, u in enumerate(shots, 1))

    feats = []
    for sec in sections:
        lead = [x for x in sec["paras"] if x.rstrip().endswith((":", "："))]   # 「Go Pro to unlock everything:」这类引导句放在列表前
        rest = [x for x in sec["paras"] if x not in lead]
        body = "".join(f"<p>{esc(x)}</p>" for x in lead)
        if sec["items"]: body += "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in sec["items"]) + "</ul>"
        body += "".join(f"<p>{esc(x)}</p>" for x in rest)
        hd = nice_heading(sec["h"], lang)
        cls = ' class="caps"' if hd == hd.upper() and re.search(r"[A-ZÄÖÜ]{3}", hd) else ""
        feats.append(f'    <div class="feat"><h3{cls}>{esc(hd)}</h3>{body}</div>')
    fine_html = ""
    if fine:
        fine_html = (f'  <details class="fine"><summary>{esc(T("h_fine"))}</summary>'
                     + "".join(f"<p>{esc(' '.join(b))}</p>" for b in fine) + "</details>")

    langs = "\n".join(
        f'      <li><a href="{v["path"]}" hreflang="{lang_of(v)}" lang="{lang_of(v)}"{" aria-current=\"page\"" if v is a else ""}>{NATIVE.get(lang_of(v), lang_of(v))}</a></li>'
        for v in sorted(fam, key=lambda v: order_key(lang_of(v))))
    others = []
    for o in sorted((x for x in APPS if x.get("home") and x.get("live") and x["key"] != p["key"]), key=lambda x: x["home"]["order"]):
        others.append(f'      <a href="{esc(page_for(o, lang))}"><img src="{icon_of(o)}" width="44" height="44" alt="" loading="lazy">'
                      f'<span><b>{esc(o["home"]["label"])}</b><small>{esc(subtitle(o, lang))}</small></span></a>')

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
<link rel="preconnect" href="https://is1-ssl.mzstatic.com" crossorigin>
{f'<link rel="preload" as="image" href="{poster}">' if video else (f'<link rel="preload" as="image" href="{cdn(hero_shot, 460)}" imagesrcset="{cdn(hero_shot, 460)} 460w, {cdn(hero_shot, 920)} 920w" imagesizes="(max-width:760px) 72vw, 360px">' if shots else '')}
<style>{CSS}</style>
</head>
<body>
<header class="wrap top">
  <a class="brand" href="{home}">{LOGO}<b>go ka</b></a>
  <nav class="nav" aria-label="Main">
    <a href="{home}">{esc(T("nav_all_apps"))}</a>
    <a href="{'/tools/pt-br/' if lang == 'pt-BR' else '/tools/'}">{esc(T("nav_tools"))}</a>
    <a href="/blog/">{esc(T("nav_blog"))}</a>
    <a href="mailto:{EMAIL}?subject={quote(p['shortName'])}">{esc(T("nav_support"))}</a>
  </nav>
  <!-- lang:start -->
  <!-- lang:end -->
</header>

<main class="wrap">
<section class="hero">
  <div>
    <img class="icon" src="{icon}" width="84" height="84" alt="">
    <h1>{title_html(name, lang)}</h1>
    <div class="lede">{"".join(f"<p>{esc(x)}</p>" for x in lede)}</div>
    <a class="cta" href="{esc(store_link(a, s))}">{APPLE}{esc(T("cta_store"))}</a>
    <ul class="chips">{"".join(f"<li>{esc(c)}</li>" for c in chips)}</ul>
  </div>
  {media}
</section>

{hl_html}<section class="sec" id="screenshots" aria-labelledby="h-screens">
  <h2 id="h-screens">{esc(T("h_screens"))}</h2>
  <ul class="shots">
{shot_items}
  </ul>
</section>

<section class="sec" id="features" aria-labelledby="h-features">
  <h2 id="h-features">{esc(details_h or T("h_features"))}</h2>
  <div class="feats">
{chr(10).join(feats)}
  </div>
{fine_html}
</section>

{"" if a.get("hideWhatsNew") else whatsnew(s, lang, a.get("whatsNew"))}<section class="sec" id="faq-section">
  <!-- faq:start -->
  <!-- faq:end -->
</section>

{guides(p, lang)}<section class="sec" id="languages" aria-labelledby="h-langs">
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
  <a class="cta" href="{esc(store_link(a, s))}">{APPLE}{esc(T("get_app", name=name))}</a>
</div>
</main>

<footer>
  <div class="wrap">
    <p>{esc(T("footer_made", name=name))}{"" if lang.startswith(("zh", "ja")) else " "}{esc(T("footer_email", email=""))}<a href="mailto:{EMAIL}">{EMAIL}</a></p>
    {social_html(lang)}
    <p>{f'<a href="{privacy}">{esc(T("privacy"))}</a>' if privacy else ''}{' · ' if privacy and terms else ''}{f'<a href="{terms}">{esc(T("terms"))}</a>' if terms else ''} · <a href="{home}">go ka</a></p>
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
