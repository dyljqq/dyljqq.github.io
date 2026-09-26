#!/usr/bin/env python3
"""从 tools/site.json 生成抓取入口，并把每个页面的 head 补齐。

  python3 tools/build_seo.py          # 写文件
  python3 tools/build_seo.py --check  # 只报告差异，不落盘（CI / 提交前用）

生成：robots.txt、sitemap.xml、llms.txt
改写：每个 *.html 的 head——canonical / description / og / twitter /
      SoftwareApplication JSON-LD，全部放在 <!-- seo:start --> 标记块里，
      重跑先删旧块再写新块，所以脚本可以反复跑。
首页（/）：品牌首页，数据在 site.json 的 home 和各 app 的 home 字段。除了 head，
      还生成正文里的 <!-- apps --> 作品卡片、<!-- homefaq --> 可见 FAQ、<!-- legal --> 页脚法务链接；
      插画在 tools/home/illus/<key>.svg（只写 <svg> 内部，脚本内联进页面）。

手写的 FAQPage JSON-LD 不动：那是页面自己的内容，标记块之外的东西一律保留。
"""
import json, re, subprocess, sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools" / "site.json").read_text(encoding="utf-8"))
ORIGIN = CFG["site"]["origin"]
BRAND = CFG["site"]["brand"]
EMAIL = CFG["site"]["email"]
APPS = [a for a in CFG["apps"] if not a["key"].startswith("_")]
HOME = CFG.get("home")
TOOLS_PATH = ROOT / "tools/tools.json"      # build_tools.py 写的工具页清单
TOOLS = json.loads(TOOLS_PATH.read_text(encoding="utf-8")) if TOOLS_PATH.exists() else []
DEV_URL = CFG["site"].get("developerUrl")
HOME_APPS = sorted((a for a in APPS if a.get("home") and a.get("live")), key=lambda a: a["home"]["order"])
CHECK = "--check" in sys.argv

START, END = "<!-- seo:start -->", "<!-- seo:end -->"

# App Store 活动归因：ASC → App Analytics → 营销活动。pt 是开发者账号的 provider token（09-26 从 ASC 生成器取）。
# ct 只按「app × 入口类型」切（web-<key>-app / -home / -tool），每个活动 ≥5 个安装才显示数据，切太细会全部看不见。
# 结构化数据和 llms.txt 里保持干净的商店链接，只有页面上可点的按钮带参数。
PT = "128309253"
# Vercel Web Analytics（无 cookie）。/_vercel/insights/script.js 由 Vercel 在生产环境提供。
ANALYTICS = ('<script>window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)};</script>\n'
             '<script defer src="/_vercel/insights/script.js"></script>')

def root_key(app):
    return app.get("variantOf") or app["key"]

def campaign_url(app_id, ct, cc=None):
    assert len(ct) <= 30, ct   # ASC 活动名上限 30
    return f"https://apps.apple.com/{cc + '/' if cc else ''}app/apple-store/id{app_id}?pt={PT}&ct={ct}&mt=8"

def store_url(app):
    return f"https://apps.apple.com/app/id{app['appId']}" if app.get("live") and app.get("appId") else None

def git_lastmod(path: Path) -> str:
    """用 git 里这个文件最后一次真实提交的日期做 lastmod，不用构建时间——
    每次构建都刷新 lastmod 等于告诉爬虫全站都变了，几轮之后它就不信了。"""
    try:
        rel = str(path.relative_to(ROOT))
        # 有未提交改动的文件＝这次发布会更新它：用今天，免得修改日期早于发布日期（09-26 评审）
        if subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip():
            return date.today().isoformat()
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", rel],
                             cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        if out:
            return datetime.fromisoformat(out).astimezone(timezone.utc).date().isoformat()
    except Exception:
        pass
    return date.today().isoformat()

def variants_of(app):
    """同一个 app 的其它语言页：site.json 里 variantOf 指向主条目 key 的条目。
    它们不是新的 app——llms.txt 和 Organization 里不单列，只在主条目下挂一行。"""
    return [a for a in APPS if a.get("variantOf") == app["key"] and a.get("live")]

def hreflang_links(app):
    """同一个 app 有多语言页时，每页都列出全家（含自己）+ x-default 指向主条目。"""
    parent = next((a for a in APPS if a["key"] == app.get("variantOf")), None) or app
    family = [parent] + variants_of(parent)
    if len(family) < 2:
        return []
    out = [f'<link rel="alternate" hreflang="{a.get("lang", "en")}" href="{ORIGIN}{a["path"]}">'
           for a in family]
    out.append(f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}{parent["path"]}">')
    return out

def pages():
    """产出 (url_path, html_path, app, kind)。kind: home / product / legal；home 的 app 是 None。"""
    if HOME:
        for lang in HOME_LANGS:
            f = ROOT / "index.html" if lang == "en" else ROOT / home_path(lang).strip("/") / "index.html"
            if f.exists():
                yield home_path(lang), f, {"lang": lang}, "home"
    for tp in TOOLS:
        f = ROOT / tp["path"].strip("/") / "index.html"
        if f.exists():
            yield tp["path"], f, tp, "tool"
    for app in APPS:
        p = ROOT / app["path"].strip("/") / "index.html" if app["path"] != "/" else ROOT / "index.html"
        if p.exists():
            yield app["path"], p, app, "product"
        for href, label in app.get("legal", []):
            lp = ROOT / href.strip("/") / "index.html"
            if lp.exists():
                yield href, lp, app, "legal"

# ---------------------------------------------------------------- robots.txt
ROBOTS = f"""# {ORIGIN}
# 全站允许抓取。这里显式列出 AI 检索爬虫，是为了防止将来加 CDN/WAF 时
# 有人按默认规则把它们一起拦掉——OAI-SearchBot 被拦 = 不会出现在 ChatGPT 的搜索结果里。

User-agent: *
Allow: /

# AI 检索（回答里会引用并给出链接）
User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

# 训练用爬虫。允许——这些页面本来就是公开的产品介绍，
# 被写进模型权重反而是我们想要的结果。
User-agent: GPTBot
Allow: /

Sitemap: {ORIGIN}/sitemap.xml
"""

# ---------------------------------------------------------------- sitemap.xml
def build_sitemap():
    rows = []
    for url, path, app, kind in pages():
        if kind in ("product", "legal") and not app.get("live"):
            continue          # 没上架的 app 不进 sitemap，页面另有 noindex
        rows.append((url, git_lastmod(path), {"home": "1.0", "product": "0.9", "tool": "0.7"}.get(kind, "0.3")))
    rows.sort(key=lambda r: (r[0] != "/", r[0]))
    body = "\n".join(
        f"  <url>\n    <loc>{ORIGIN}{u}</loc>\n    <lastmod>{m}</lastmod>\n"
        f"    <priority>{p}</priority>\n  </url>" for u, m, p in rows)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}\n</urlset>\n"), len(rows)

# ---------------------------------------------------------------- llms.txt
def build_llms():
    live = [a for a in APPS if a.get("live") and not a.get("variantOf")]
    out = [f"# {BRAND}", "",
           f"> {HOME['description']}" if HOME else f"> {len(live)} iPhone apps.",
           "> Every app has its own page here; the features, free parts and prices written on it",
           "> are what the app actually does.",
           "",
           f"- Home: {ORIGIN}/",
           *[f"- Home ({l}): {ORIGIN}{home_path(l)}" for l in HOME_LANGS if l != "en"],
           *([f"- All apps on the App Store: {DEV_URL}"] if DEV_URL else []),
           f"- Contact: {EMAIL}",
           *[f"- {x.get('nameIntl', x['name'])}: {x['url']}" for x in CFG["site"].get("social", [])],
           "", "## Apps", ""]
    for a in live:
        su = store_url(a)
        out.append(f"### {a['name']}")
        out.append("")
        out.append(a["oneLiner"])
        out.append("")
        out.append(f"- Page: {ORIGIN}{a['path']}")
        for v in variants_of(a):
            out.append(f"- Page ({v['lang']}): {ORIGIN}{v['path']}")
        if su:
            out.append(f"- App Store: {su}")
        out.append(f"- Platform: iOS (iPhone, iPad)")
        out.append(f"- Category: {a['genre']}")
        if a.get("audience"):
            out.append(f"- For: {a['audience']}")
        if a.get("free"):
            out.append(f"- Free: {a['free']}")
        if a.get("paid"):
            out.append(f"- Paid: {a['paid']}")
        out.append("")
    if TOOLS:
        out += ["## Free tools & guides", ""]
        for tp in TOOLS:
            out.append(f"- [{tp['hubTitle']}]({ORIGIN}{tp['path']}) — {tp['description']}")
        out.append("")
    if HOME and HOME.get("faq"):
        out += ["## FAQ", ""]
        for f in HOME["faq"]:
            out += [f"### {f['q']}", "", f["a"], ""]
    out += ["## Notes", "",
            "- Every app is free to download. Paid parts, where there are any, are listed on each app's page.",
            "- No app asks for an account or sign-up. Where an app syncs, it uses the user's own iCloud.",
            f"- Support and feedback: {EMAIL}", ""]
    return "\n".join(out)

# ---------------------------------------------------------------- head 改写
def software_jsonld(app, kind="product"):
    d = {"@context": "https://schema.org", "@type": "SoftwareApplication",
         "@id": f"{ORIGIN}{app['path']}#app",
         "name": app["name"], "alternateName": app["shortName"],
         "applicationCategory": app["category"],
         "operatingSystem": f"iOS {app.get('minOS', '17.0')} or later",
         "description": app["description"],
         "url": f"{ORIGIN}{app['path']}",
         "inLanguage": app.get("lang", "en"),
         "author": {"@type": "Organization", "@id": f"{ORIGIN}/#org", "name": BRAND},
         "publisher": {"@type": "Organization", "@id": f"{ORIGIN}/#org", "name": BRAND},
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
    su = store_url(app)
    if su:
        d["downloadUrl"] = su
        d["installUrl"] = su
        d["sameAs"] = [su]
    if app.get("icon"):
        d["image"] = asset(app["icon"])
    # 生成页：截图和预览视频来自商店缓存 / assets/<key>/preview（与页面上展示的一致）
    parent = next((a for a in APPS if a["key"] == app.get("variantOf")), None) or app
    if parent.get("generated") and kind == "product":      # 截图 / 视频只放在真有它们的产品页，法务页不带
        cache = json.loads((ROOT / f"tools/store/{parent['key']}.json").read_text(encoding="utf-8"))
        lang = app.get("lang", "en")
        L2S = {"en": "en-US", "en-GB": "en-GB", "de": "de-DE", "fr": "fr-FR", "it": "it", "es": "es-ES", "es-MX": "es-MX",
               "pt-BR": "pt-BR", "ja": "ja", "ko": "ko", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "th": "th"}
        st = cache.get(L2S.get(lang, "en-US")) or cache["en-US"]
        d["screenshot"] = [re.sub(r"/[^/]+$", "/920x0w.webp", u) for u in st["screenshots"][:6]]
        d["inLanguage"] = lang
        vf = {"en": "en", "en-GB": "en", "pt-BR": "pt"}.get(lang, lang)
        for cand in ((vf, "en") if lang in ("en", "en-GB") else (vf,)):   # 与页面一致：非英文页不拿英文视频顶
            f = ROOT / "assets" / parent["key"] / "preview" / f"{cand}.mp4"
            if f.exists():
                d["video"] = {"@type": "VideoObject", "name": bp.t(lang, "video_label", name=st["name"]),
                              "description": st["description"].split("\n")[0][:200],
                              "thumbnailUrl": f"{ORIGIN}/assets/{parent['key']}/preview/{cand}.jpg",
                              "contentUrl": f"{ORIGIN}/assets/{parent['key']}/preview/{cand}.mp4",
                              "uploadDate": git_lastmod(f), "inLanguage": lang}
                break
    return d

def faq_jsonld(app):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "@id": f"{ORIGIN}{app['path']}#faq",
            "inLanguage": app.get("lang", "en"),
            "mainEntity": [{"@type": "Question", "name": f["q"],
                            "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                           for f in app["faq"]]}

FAQ_START, FAQ_END = "<!-- faq:start -->", "<!-- faq:end -->"
# 可见 FAQ 的标题，按 site.json 的 lang 选；先按完整 tag（zh-Hant）找，再退回语言前缀（de-DE → de）
FAQ_HEADING = {
    "en": "Questions people ask", "pt": "Perguntas frequentes", "de": "Häufige Fragen",
    "fr": "Questions fréquentes", "it": "Domande frequenti", "es": "Preguntas frecuentes", "ja": "よくある質問",
    "ko": "자주 묻는 질문", "th": "คำถามที่พบบ่อย", "zh-Hans": "常见问题", "zh-Hant": "常見問題", "zh": "常见问题",
}

def faq_html(app):
    """可见 FAQ。schema 里的问答必须在页面上看得见、且逐字一致（清单 7.7），
    所以两边都从 site.json 的同一份数据生成，杜绝改了一边忘了另一边。"""
    lang = app.get("lang", "en")
    heading = FAQ_HEADING.get(lang) or FAQ_HEADING.get(lang.split("-")[0], "Questions people ask")
    rows = "\n".join(
        '    <div class="card">\n      <h3>%s</h3>\n      <p>%s</p>\n    </div>'
        % (esc_text(f["q"]), esc_text(f["a"])) for f in app["faq"])
    return (f'{FAQ_START}\n  <h2 id="faq">{heading}</h2>\n'
            f'  <div class="grid">\n{rows}\n  </div>\n  {FAQ_END}')

def esc_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def org_jsonld():
    return {"@context": "https://schema.org", "@type": "Organization",
            "@id": f"{ORIGIN}/#org", "name": BRAND, "url": f"{ORIGIN}/",
            "email": EMAIL,
            "description": f"Independent iOS developer. {len([a for a in APPS if a.get('live') and not a.get('variantOf')])} apps on the App Store.",
            **({"logo": asset(HOME["logo"])} if HOME and HOME.get("logo") else {}),
            "sameAs": list(dict.fromkeys(([DEV_URL] if DEV_URL else []) + [x["url"] for x in CFG["site"].get("social", [])] +
                                         [u for u in (store_url(a) for a in APPS) if u]))}

def meta_desc(s, limit=160):
    """meta description 按句子截到 160 字内；JSON-LD 里仍用全文。CJK 短句不动。"""
    if len(s) <= limit: return s
    out = ""
    for part in re.split(r"(?<=[.!?。！？])\s+", s):
        if len(out) + len(part) + 1 > limit: break
        out = (out + " " + part).strip()
    if not out:
        raise SystemExit(f"description 第一句就超过 {limit} 字，会被截成半句，去改源文案：{s[:80]}…")
    return out

def head_block(url, app, kind):
    is_product = kind == "product"
    canonical = f"{ORIGIN}{url}"
    if is_product:
        title, desc = app["title"], app["description"]
        img = asset(app["ogImage"]) if app.get("ogImage") else (
              asset(app["icon"]) if app.get("icon") else None)
    else:
        label = next((l for h, l in app.get("legal", []) if h == url), "Legal")
        title = f"{label} · {app['name']}"
        desc = f"{label} for {app['name']}. {app['oneLiner']}"
        img = asset(app["icon"]) if app.get("icon") else None

    desc = meta_desc(desc)
    lines = [START,
             '<meta name="description" content="%s">' % esc(desc),
             f'<link rel="canonical" href="{canonical}">']
    if is_product:
        lines += hreflang_links(app)
    if not app.get("live"):
        lines.append('<meta name="robots" content="noindex,follow">')
    lines += ['<meta property="og:type" content="website">',
              '<meta property="og:site_name" content="%s">' % esc(BRAND),
              '<meta property="og:title" content="%s">' % esc(title),
              '<meta property="og:description" content="%s">' % esc(desc),
              f'<meta property="og:url" content="{canonical}">']
    if img:
        lines.append(f'<meta property="og:image" content="{img}">')
        lines.append('<meta name="twitter:card" content="summary_large_image">')
        lines.append(f'<meta name="twitter:image" content="{img}">')
    else:
        lines.append('<meta name="twitter:card" content="summary">')
    lines += ['<meta name="twitter:title" content="%s">' % esc(title),
              '<meta name="twitter:description" content="%s">' % esc(desc)]
    if app.get("live") and app.get("appId"):
        lines.append(f'<meta name="apple-itunes-app" content="app-id={app["appId"]}, '
                     f'affiliate-data=ct=web-{root_key(app)}-app&amp;pt={PT}">')

    blobs = [software_jsonld(app, kind)]
    if is_product and app.get("faq"):
        blobs.append(faq_jsonld(app))
    for b in blobs:
        lines.append('<script type="application/ld+json">\n%s\n</script>'
                     % json.dumps(b, ensure_ascii=False, indent=2))
    lines.append(ANALYTICS)
    lines.append(END)
    return "\n".join(lines) + "\n"

# ---------------------------------------------------------------- 首页（多语言）+ 页头语言切换
sys.path.insert(0, str(ROOT / "tools"))
import build_pages as bp          # NATIVE / LANG2STORE / parse_desc / sibling_path / family（只读用）

HOME_EN_STR = json.loads((ROOT / "tools/i18n/home.en.json").read_text(encoding="utf-8")) if (ROOT / "tools/i18n/home.en.json").exists() else {}
HOME_I18N = json.loads((ROOT / "tools/i18n/home.json").read_text(encoding="utf-8")) if (ROOT / "tools/i18n/home.json").exists() else {}
HOME_LANGS = ["en"] + [l for l in ("de", "fr", "it", "es", "es-MX", "pt-BR", "ja", "ko", "zh-Hans", "zh-Hant", "th") if l in HOME_I18N]
SUBS = json.loads((ROOT / "tools/store/subtitles.json").read_text(encoding="utf-8")) if (ROOT / "tools/store/subtitles.json").exists() else {}
ASC_LOC = {"en": "en-US", "de": "de-DE", "fr": "fr-FR", "it": "it", "es": "es-ES", "es-MX": "es-MX", "pt-BR": "pt-BR",
           "ja": "ja", "ko": "ko", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "th": "th"}

def home_path(lang):
    return "/" if lang == "en" else f"/{lang.lower()}/"

def H(lang, key):
    """首页文案：非英语取 tools/i18n/home.json；英语的 title/description/faq 取 site.json 的 home，其余取 home.en.json。"""
    if lang != "en" and key in HOME_I18N.get(lang, {}):
        return HOME_I18N[lang][key]
    return HOME[key] if key in ("title", "description", "faq") else HOME_EN_STR[key]

def home_name(a):
    """英文首页：卡片和 ItemList 用美区商店名；中文产品页的 app（单词兽）另存了英文名。"""
    return a["home"].get("storeNameEn", a["name"])

def cut_sentences(s, n=320):
    if len(s) <= n:
        return s
    out = ""
    for part in re.split(r"(?<=[.!?。！？])\s*", s):
        if not part: continue
        if len(out) + len(part) + 1 > n: break
        out = (out + (" " if out and not re.search(r"[。！？]$", out) else "") + part).strip()
    if out:
        return out
    # 泰文没有句号，整段是「一句」：退到最后一个空格（泰文的短语边界），不在词中间截断；数字不单独留在末尾
    cut = s[:n].rsplit(" ", 1)[0] if " " in s[:n] else s[:n]
    cut = re.sub(r"\s+\d+$", "", cut)
    if s[len(cut):].lstrip()[:1].isdigit() and " " in cut:   # 「ใช้ฟรี | 3 ครั้ง」：数量被截掉时，前面那半句也不要
        cut = cut.rsplit(" ", 1)[0]
    return cut

def home_card(a, lang):
    """一张首页卡片的文案。英语用 site.json（逐字的美区副标题 + 描述首段）；其它语言取该语言商店：
    名字 = 商店名，一句话 = 商店副标题（ASC app-info），介绍 = 商店描述首段。该语言没本地化的 app 自然回落成英文。"""
    h = a["home"]
    if lang == "en":
        return {"name": home_name(a), "tagline": h["tagline"], "blurb": h["blurb"], "page": bp.page_for(a, "en", "home"), "cc": None}
    cache = json.loads((ROOT / f"tools/store/{a['key']}.json").read_text(encoding="utf-8"))
    st = cache.get(bp.LANG2STORE[lang]) or cache["en-US"]
    sub = (SUBS.get(a["key"], {}).get(ASC_LOC[lang]) or {}).get("subtitle")
    lede, sections, _ = bp.parse_desc(st["description"])
    text = ("" if lang.startswith(("zh", "ja")) else " ").join(lede) or (" ".join(sections[0]["paras"]) if sections and sections[0]["paras"] else
                              " ".join(sections[0]["items"][:3]) if sections else "")
    text = re.sub(r"(?<=[。！？」』）])\s+", "", text)
    if lang.startswith(("zh", "ja")):
        text = re.sub(r"(?<=[\u3040-\u30ff\u4e00-\u9fff]),\s*(?=[\u3040-\u30ff\u4e00-\u9fff])", "，" if lang.startswith("zh") else "、", text)
    blurb = cut_sentences(text)
    if not bp.localized(a, lang):          # 商店没这个语言：卡片文案用 tools/i18n/fallback.json 的译文（名字仍是商店名）
        sub = bp.fallback(a, lang, "tagline") or sub
        blurb = bp.fallback(a, lang, "blurb") or blurb
    return {"name": st["name"], "tagline": sub, "blurb": blurb, "page": bp.page_for(a, lang, "home"),
            "cc": st.get("storefront")}

GLOBE = ('<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" '
         'stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.8 3.9 5.8 3.9 9s-1.3 6.2-3.9 9c-2.6-2.8-3.9-5.8-3.9-9s1.3-6.2 3.9-9z"/></svg>')
SWITCH_CSS = ('<style>.lang-switch{position:relative;flex:none}.lang-switch summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:6px;'
  'font:600 13px/1 var(--text);padding:10px 12px;border:1px solid var(--rule);border-radius:999px;white-space:nowrap;color:var(--ink)}'
  '.lang-switch summary::-webkit-details-marker{display:none}.lang-switch summary:hover{background:var(--cream)}'
  '.lang-switch summary svg{width:16px;height:16px;flex:none}.lang-switch ul{position:absolute;right:0;top:calc(100% + 8px);z-index:30;margin:0;padding:6px;'
  'list-style:none;background:#fff;border:1px solid var(--rule);border-radius:14px;box-shadow:0 14px 34px -14px rgba(0,0,0,.28);min-width:200px;max-height:70vh;overflow:auto}'
  '.lang-switch li a{display:block;padding:10px 12px;border-radius:9px;text-decoration:none;font:500 14px/1.2 var(--text);color:var(--ink)}'
  '.lang-switch li a:hover{background:var(--cream)}.lang-switch li a[aria-current]{font-weight:700;background:var(--cream)}'
  '.lang-switch .ln-note{padding:10px 12px 6px;border-top:1px solid var(--rule);margin-top:6px;font:500 12px/1.4 var(--text);color:var(--muted)}'
  '.lang-switch .ln-code{display:none}@media (max-width:760px){.lang-switch .ln-full{display:none}.lang-switch .ln-code{display:inline}'
  '.lang-switch summary{padding:9px 10px}}</style>')
SWITCH_JS = ('<script>document.addEventListener("click",function(e){document.querySelectorAll("details.lang-switch[open]").forEach('
             'function(d){if(!d.contains(e.target))d.removeAttribute("open")})});</script>')
SHORT = {"zh-Hans": "简", "zh-Hant": "繁", "es-MX": "MX", "pt-BR": "PT"}

def lang_switch(current, options, extra=None):
    """页头语言切换：<details> 下拉，全是真实 <a href>，爬虫顺着能走到每个语言版本。options = [(lang, path)]，
    只放「同一内容」的语言版本；extra = {"note", "links": [(lang, path, label)]} 放在分隔线下（单语言工具页指向另一种语言的工具目录）。"""
    if len({l for l, _ in options}) < 2 and not extra:
        return "<!-- lang:start -->\n  <!-- lang:end -->"
    items = "".join('<li><a href="%s" hreflang="%s" lang="%s"%s>%s</a></li>'
                    % (p, l, l, ' aria-current="true"' if l == current else "", esc_text(bp.NATIVE.get(l, l))) for l, p in options)
    if extra:
        if extra.get("note"):
            items += '<li class="ln-note">%s</li>' % esc_text(extra["note"])
        items += "".join('<li class="ln-other"><a href="%s" hreflang="%s" lang="%s">%s</a></li>' % (p, l, l, esc_text(lb))
                         for l, p, lb in extra["links"])
    code = SHORT.get(current, current.split("-")[0].upper())
    return ("<!-- lang:start -->\n  " + SWITCH_CSS +
            f'<details class="lang-switch"><summary>{GLOBE}<span class="ln-full">{esc_text(bp.NATIVE.get(current, current))}</span>'
            f'<span class="ln-code">{esc_text(code)}</span></summary><ul>{items}</ul></details>' + SWITCH_JS + "\n  <!-- lang:end -->")

def fill_lang(html, current, options, extra=None):
    return re.sub(r"<!-- lang:start -->.*?<!-- lang:end -->", lambda m: lang_switch(current, options, extra), html, count=1, flags=re.S)

def home_options():
    return [(l, home_path(l)) for l in HOME_LANGS if (ROOT / home_path(l).strip("/") / "index.html").exists() or l == "en"]

def product_options(app):
    parent = next((a for a in APPS if a["key"] == app.get("variantOf")), None) or app
    fam = [parent] + variants_of(parent)
    return [(a.get("lang", "en"), a["path"]) for a in sorted(fam, key=lambda a: bp.order_key(a.get("lang", "en")))]

TOOL_HUBS = {"en": "/tools/", "pt-BR": "/tools/pt-br/"}
ONLY_IN = {"en": "This page is in English only", "pt-BR": "Esta página só existe em português"}
HUB_LABEL = {"en": "Free tools & guides in English", "pt-BR": "Ferramentas grátis em português"}

def tool_options(tp):
    """返回 (options, extra)。目录页互为语言版本；单语言工具页只列自己，另一种语言的目录放 extra。"""
    if tp["path"] in TOOL_HUBS.values():
        return list(TOOL_HUBS.items()), None
    extra = [(l, p, HUB_LABEL[l]) for l, p in TOOL_HUBS.items() if l != tp["lang"]]
    return [(tp["lang"], tp["path"])], {"note": ONLY_IN.get(tp["lang"], ""), "links": extra}

def home_head(lang="en"):
    path = home_path(lang); canonical = f"{ORIGIN}{path}"
    title, desc = H(lang, "title"), meta_desc(H(lang, "description"))
    img = asset(HOME["ogImage"])
    lines = [START,
             '<meta name="description" content="%s">' % esc(desc),
             f'<link rel="canonical" href="{canonical}">']
    for l, p in home_options():
        lines.append(f'<link rel="alternate" hreflang="{l}" href="{ORIGIN}{p}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/">')
    lines += ['<meta property="og:type" content="website">',
             '<meta property="og:site_name" content="%s">' % esc(BRAND),
             '<meta property="og:title" content="%s">' % esc(title),
             '<meta property="og:description" content="%s">' % esc(desc),
             f'<meta property="og:url" content="{canonical}">',
             f'<meta property="og:image" content="{img}">',
             '<meta property="og:image:width" content="1200">',
             '<meta property="og:image:height" content="630">',
             '<meta property="og:image:alt" content="%s">' % esc(title),
             '<meta name="twitter:card" content="summary_large_image">',
             '<meta name="twitter:title" content="%s">' % esc(title),
             '<meta name="twitter:description" content="%s">' % esc(desc),
             f'<meta name="twitter:image" content="{img}">']
    items = []
    for i, a in enumerate(HOME_APPS, 1):
        c = home_card(a, lang); su = store_url(a)
        # 结构化数据里永远用站内页面地址（卡片链接可能是带活动参数的商店链接，不能进 JSON-LD）；
        # 只有卡片上的名字和那一页实体的名字一致时才挂 @id，免得同一个 @id 在不同页面叫不同名字
        target = bp.sibling_path(a, lang)
        ent = next((x for x in APPS if x["path"] == target), a)
        item = {"@type": "SoftwareApplication",
                **({"@id": f"{ORIGIN}{target}#app"} if c["name"] == ent["name"] else {}),
                "name": c["name"], "alternateName": a["home"]["label"],
                "url": f"{ORIGIN}{target}", "description": c["blurb"],
                "applicationCategory": a["category"],
                "operatingSystem": f"iOS {a.get('minOS', '17.0')} or later",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                "publisher": {"@id": f"{ORIGIN}/#org"}}
        if a.get("icon"):
            item["image"] = asset(a["icon"])
        if su:
            item["downloadUrl"] = su
            item["sameAs"] = [su]
        items.append({"@type": "ListItem", "position": i, "item": item})
    blobs = [
        org_jsonld(),
        {"@context": "https://schema.org", "@type": "WebSite", "@id": f"{ORIGIN}/#website",
         "url": f"{ORIGIN}/", "name": BRAND, "description": HOME["description"], "inLanguage": HOME_LANGS,
         "publisher": {"@id": f"{ORIGIN}/#org"}},
        {"@context": "https://schema.org", "@type": "CollectionPage", "@id": f"{canonical}#webpage",
         "url": canonical, "name": title, "description": desc, "inLanguage": lang,
         "isPartOf": {"@id": f"{ORIGIN}/#website"}, "about": {"@id": f"{ORIGIN}/#org"},
         "primaryImageOfPage": img,
         "mainEntity": {"@type": "ItemList", "@id": f"{canonical}#apps", "name": f"Apps by {BRAND}",
                        "numberOfItems": len(items), "itemListElement": items}},
        {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{canonical}#faq",
         "inLanguage": lang,
         "mainEntity": [{"@type": "Question", "name": f["q"],
                         "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in H(lang, "faq")]},
    ]
    for b in blobs:
        lines.append('<script type="application/ld+json">\n%s\n</script>'
                     % json.dumps(b, ensure_ascii=False, indent=2))
    lines.append(ANALYTICS)
    lines.append(END)
    return "\n".join(lines) + "\n"

# 插画里的英文小字按语言换掉（09-26 第 3 轮评审）；译文比原文长就用 textLength 压回原来的宽度，免得撑出图形
ILLUS_W = {"DAYS TO GO": 72, "PAID": 46, "SCAN ME": 52}
ILLUS = {
    "de": ("TAGE ÜBRIG", "BEZAHLT", "SCANNEN"), "fr": ("JOURS RESTANTS", "PAYÉ", "SCANNEZ"),
    "it": ("GIORNI RIMASTI", "PAGATO", "SCANSIONA"), "es": ("DÍAS QUE FALTAN", "PAGADO", "ESCANÉAME"),
    "es-MX": ("DÍAS QUE FALTAN", "PAGADO", "ESCANÉAME"), "pt-BR": ("DIAS RESTANTES", "PAGO", "ESCANEIE"),
    "ja": ("日後", "支払済", "スキャン"), "ko": ("일 남음", "결제 완료", "스캔하세요"),
    "zh-Hans": ("天后", "已付款", "扫一扫"), "zh-Hant": ("天後", "已付款", "掃一掃"),
    "th": ("วันข้างหน้า", "ชำระแล้ว", "สแกนเลย"),
}

def localize_illus(svg, lang):
    if lang not in ILLUS:
        return svg
    for en, loc in zip(("DAYS TO GO", "PAID", "SCAN ME"), ILLUS[lang]):
        def sub(m):
            attrs = m.group(1)
            if len(loc) > len(en):
                attrs += f' textLength="{ILLUS_W[en]}" lengthAdjust="spacingAndGlyphs"'
            return f"<text{attrs}>{esc_text(loc)}</text>"
        svg = re.sub(r"<text([^>]*)>" + re.escape(en) + "</text>", sub, svg)
    return svg

def home_apps_html(lang="en"):
    cards = []
    for a in HOME_APPS:
        h, key = a["home"], a["key"]; c = home_card(a, lang); page = c["page"]
        svg = (ROOT / "tools" / "home" / "illus" / f"{key}.svg").read_text(encoding="utf-8").strip()
        svg = localize_illus(svg, lang)
        svg = "\n".join("        " + l for l in svg.splitlines())
        hl = f' hreflang="{h["hreflang"]}"' if h.get("hreflang") and page == a["path"] else ""
        page = esc(page)
        label = esc_text(h["label"])
        su = esc(campaign_url(a["appId"], f"web-{key}-home", c["cc"] if lang != "en" else None)) if store_url(a) else None
        btn = esc_text(H(lang, "get_on_store").replace("{label}", h["label"]))
        get = f'\n      <a class="get" href="{su}">{btn} ↗</a>' if su else ""
        tag = f'\n      <p class="tagline">{esc_text(c["tagline"])}</p>' if c["tagline"] else ""
        cards.append(f"""    <article class="app" id="app-{key}">
      <a class="art" href="{page}"{hl} tabindex="-1" aria-hidden="true">
        <svg class="illus" viewBox="0 0 240 180" focusable="false">
{svg}
        </svg>
      </a>
      <div class="app-head">
        <h3><a href="{page}"{hl}>{label}.</a></h3>
        <span class="arrow" aria-hidden="true">↗</span>
      </div>
      <p class="store-name">{esc_text(c["name"])}</p>{tag}
      <p class="blurb">{esc_text(c["blurb"])}</p>{get}
    </article>""")
    return ('<!-- apps:start -->\n  <div class="apps">\n' + "\n".join(cards)
            + "\n  </div>\n  <!-- apps:end -->")

def home_faq_html(lang="en"):
    rows = "\n".join('    <div class="qa">\n      <h3>%s</h3>\n      <p>%s</p>\n    </div>'
                     % (esc_text(f["q"]), esc_text(f["a"])) for f in H(lang, "faq"))
    return ('<!-- homefaq:start -->\n  <div class="faq-list">\n' + rows
            + "\n  </div>\n  <!-- homefaq:end -->")

def home_legal_html(lang="en"):
    rows = []
    for a in HOME_APPS:
        target = a["home"].get("hreflang") or "en"          # 法务页本身的语言
        if lang == "en":                                    # 英文首页沿用原文标题（单词兽的是中文，标 lang）
            attr = f' hreflang="{target}" lang="{target}"' if target != "en" else ""
            label_of = lambda href, label: label
        else:
            attr = f' hreflang="{target}"'
            label_of = lambda href, label: bp.t(lang, "privacy") if "privacy" in href else bp.t(lang, "terms")
        links = " · ".join('<a href="%s"%s>%s</a>' % (href, attr, esc_text(label_of(href, label)))
                           for href, label in a.get("legal", []))
        rows.append("          <li>%s — %s</li>" % (esc_text(a["home"]["label"]), links))
    return ('<!-- legal:start -->\n        <ul class="legal">\n' + "\n".join(rows)
            + "\n        </ul>\n        <!-- legal:end -->")

def tool_head(tp):
    url, lang = tp["path"], tp["lang"]; canonical = f"{ORIGIN}{url}"
    title, desc = tp["title"], meta_desc(tp["description"]); img = asset(HOME["ogImage"])
    hub_alts = [f'<link rel="alternate" hreflang="{l}" href="{ORIGIN}{p}">' for l, p in TOOL_HUBS.items()] + \
               [f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/tools/">'] if url in TOOL_HUBS.values() else []
    lines = [START, '<meta name="description" content="%s">' % esc(desc), f'<link rel="canonical" href="{canonical}">',
             '<meta property="og:type" content="%s">' % ("article" if tp["kind"] == "Article" else "website"),
             '<meta property="og:site_name" content="%s">' % esc(BRAND), '<meta property="og:title" content="%s">' % esc(title),
             '<meta property="og:description" content="%s">' % esc(desc), f'<meta property="og:url" content="{canonical}">',
             f'<meta property="og:image" content="{img}">', '<meta name="twitter:card" content="summary_large_image">',
             '<meta name="twitter:title" content="%s">' % esc(title), '<meta name="twitter:description" content="%s">' % esc(desc),
             f'<meta name="twitter:image" content="{img}">'] + hub_alts
    hub = "/blog/" if url.startswith("/blog/") else ("/tools/pt-br/" if lang == "pt-BR" else "/tools/")
    page = {"@context": "https://schema.org", "@type": tp["kind"], "@id": f"{canonical}#page", "url": canonical, "name": title,
            "headline": tp.get("headline") or title, "description": desc, "inLanguage": lang, "isPartOf": {"@id": f"{ORIGIN}/#website"},
            "publisher": {"@id": f"{ORIGIN}/#org"}, "author": {"@id": f"{ORIGIN}/#org"}, "isAccessibleForFree": True, "image": tp.get("image") or img}
    if tp.get("published"):
        page["datePublished"] = tp["published"]; page["dateModified"] = git_lastmod(ROOT / url.strip("/") / "index.html")
    if tp["kind"] == "WebApplication":
        page.update({"applicationCategory": "UtilitiesApplication", "operatingSystem": "Any (web browser)", "browserRequirements": "Requires JavaScript",
                     "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}})
    if tp.get("app"):
        page["about"] = {"@id": f"{ORIGIN}{next(a['path'] for a in APPS if a['key'] == tp['app'])}#app"}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home" if lang == "en" else "Início", "item": f"{ORIGIN}{home_path(lang)}"},
        {"@type": "ListItem", "position": 2, "name": "Blog" if hub == "/blog/" else ("Tools" if lang == "en" else "Ferramentas"), "item": f"{ORIGIN}{hub}"}]}
    if url != hub:
        crumbs["itemListElement"].append({"@type": "ListItem", "position": 3, "name": title, "item": canonical})
    blobs = [page, crumbs]
    if tp.get("items"):
        blobs.append({"@context": "https://schema.org", "@type": "ItemList", "@id": f"{canonical}#list", "name": title,
                      "itemListOrder": "https://schema.org/ItemListOrderAscending", "numberOfItems": len(tp["items"]),
                      "itemListElement": [{"@type": "ListItem", "position": i, "name": it["name"], "url": it["url"]} for i, it in enumerate(tp["items"], 1)]})
    if tp.get("faq"):
        blobs.append({"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{canonical}#faq", "inLanguage": lang,
                      "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in tp["faq"]]})
    for b in blobs:
        lines.append('<script type="application/ld+json">\n%s\n</script>' % json.dumps(b, ensure_ascii=False, indent=2))
    lines.append(ANALYTICS)
    lines.append(END)
    return "\n".join(lines) + "\n"

def patch_tool(path: Path, tp):
    html = path.read_text(encoding="utf-8")
    head_end = html.lower().find("</head>")
    if head_end == -1:
        return None
    head, rest = html[:head_end], html[head_end:]
    for pat in OWNED:
        head = re.sub(pat, "", head, flags=re.S | re.I)
    opts, extra = tool_options(tp)
    return fill_lang(head.rstrip() + "\n" + tool_head(tp) + rest, tp["lang"], opts, extra)

def patch_home(path: Path, lang="en"):
    html = path.read_text(encoding="utf-8")
    head_end = html.lower().find("</head>")
    if head_end == -1:
        return None
    head, rest = html[:head_end], html[head_end:]
    for pat in OWNED:
        head = re.sub(pat, "", head, flags=re.S | re.I)
    head = re.sub(r"<title>.*?</title>", lambda m: "<title>%s</title>" % esc_text(H(lang, "title")),
                  head, count=1, flags=re.S)
    out = head.rstrip() + "\n" + home_head(lang) + rest
    out = fill_lang(out, lang, home_options())
    for tag, fn in (("apps", lambda: home_apps_html(lang)), ("homefaq", lambda: home_faq_html(lang)),
                    ("legal", lambda: home_legal_html(lang))):
        a, b = f"<!-- {tag}:start -->", f"<!-- {tag}:end -->"
        if a not in out or b not in out:
            raise SystemExit(f"index.html 缺少标记 {a} / {b}")
        out = re.sub(re.escape(a) + r".*?" + re.escape(b), lambda m: fn(), out, count=1, flags=re.S)
    return out

def asset(u):
    """icon / ogImage 允许写站内路径或绝对 URL（App Store 的图标 CDN）。"""
    return u if u.startswith("http") else f"{ORIGIN}{u}"

def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

OWNED = [
    r'<!-- seo:start -->.*?<!-- seo:end -->\s*',
    r'<meta\s+name="description"[^>]*>\s*',
    r'<link\s+rel="canonical"[^>]*>\s*',
    r'<meta\s+property="og:[^"]*"[^>]*>\s*',
    r'<meta\s+name="twitter:[^"]*"[^>]*>\s*',
    r'<meta\s+name="apple-itunes-app"[^>]*>\s*',
    r'<meta\s+name="robots"[^>]*>\s*',
]

STORE_HREF = re.compile(r'href="https://apps\.apple\.com/(?:([a-z]{2})/)?app/(?:[^"/?]+/)?id(\d+)(?:\?[^"]*)?"')

def campaignize_body(body):
    """手写页正文里的商店按钮统一换成活动链接（只动 </head> 之后，不碰结构化数据）。"""
    by_id = {a["appId"]: root_key(a) for a in APPS if a.get("appId") and a.get("live")}
    def sub(m):
        if "pt=" in m.group(0) or m.group(2) not in by_id:
            return m.group(0)
        return f'href="{campaign_url(m.group(2), f"web-{by_id[m.group(2)]}-app", m.group(1))}"'
    return STORE_HREF.sub(sub, body)

def patch(path: Path, url, app, kind):
    html = path.read_text(encoding="utf-8")
    head_end = html.lower().find("</head>")
    if head_end == -1:
        return None
    head, rest = html[:head_end], html[head_end:]
    for pat in OWNED:
        head = re.sub(pat, "", head, flags=re.S | re.I)
    # 旧的 SoftwareApplication JSON-LD 由脚本接管；手写的 FAQPage 等原样留下
    if app.get("faq"):
        head = re.sub(r'<script type="application/ld\+json">(?:(?!</script>).)*?"FAQPage"'
                      r'(?:(?!</script>).)*?</script>\s*', "", head, flags=re.S)
    head = re.sub(r'<script type="application/ld\+json">(?:(?!</script>).)*?"SoftwareApplication"'
                  r'(?:(?!</script>).)*?</script>\s*', "", head, flags=re.S)
    head = head.rstrip() + "\n" + head_block(url, app, kind)
    out = head + campaignize_body(rest)
    if kind == "product" and "<!-- lang:start -->" in out:
        out = fill_lang(out, app.get("lang", "en"), product_options(app))
    if kind == "product" and app.get("faq") and FAQ_START in out:
        out = re.sub(re.escape(FAQ_START) + r".*?" + re.escape(FAQ_END),
                     lambda m: faq_html(app), out, flags=re.S)
    return out

FR_SPLIT = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", re.S | re.I)
def french_spacing(html):
    """法语排版：?!:;» 前、« 后是不换行空格，否则「»」会单独掉到下一行（09-26 评审）。"""
    parts = FR_SPLIT.split(html)
    for i in range(0, len(parts), 2):
        t = parts[i]
        t = re.sub(r"[ \t]+([?!:;»])", "\u00a0\\1", t)
        t = re.sub(r"«[ \t]+", "«\u00a0", t)
        parts[i] = t
    return "".join(parts)

def main():
    changed = []
    def write(rel, text):
        p = ROOT / rel
        old = p.read_text(encoding="utf-8") if p.exists() else None
        if old != text:
            changed.append(rel)
            if not CHECK:
                p.write_text(text, encoding="utf-8")

    sitemap, n = build_sitemap()
    write("robots.txt", ROBOTS)
    write("sitemap.xml", sitemap)
    write("llms.txt", build_llms())
    for url, path, app, kind in pages():
        out = patch_home(path, app["lang"]) if kind == "home" else patch_tool(path, app) if kind == "tool" else patch(path, url, app, kind)
        if out is None:
            print(f"  !! 没有 </head>，跳过：{path}")
            continue
        if '<html lang="fr"' in out[:300]:
            out = french_spacing(out)
        write(str(path.relative_to(ROOT)), out)

    print(f"sitemap: {n} 条 URL")
    print(("需要更新" if CHECK else "已写入") + f" {len(changed)} 个文件")
    for c in changed:
        print("  -", c)
    if CHECK and changed:
        sys.exit(1)

main()
