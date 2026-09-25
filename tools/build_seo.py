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
DEV_URL = CFG["site"].get("developerUrl")
HOME_APPS = sorted((a for a in APPS if a.get("home") and a.get("live")), key=lambda a: a["home"]["order"])
CHECK = "--check" in sys.argv

START, END = "<!-- seo:start -->", "<!-- seo:end -->"

def store_url(app):
    return f"https://apps.apple.com/app/id{app['appId']}" if app.get("live") and app.get("appId") else None

def git_lastmod(path: Path) -> str:
    """用 git 里这个文件最后一次真实提交的日期做 lastmod，不用构建时间——
    每次构建都刷新 lastmod 等于告诉爬虫全站都变了，几轮之后它就不信了。"""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", str(path.relative_to(ROOT))],
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
    if HOME and (ROOT / "index.html").exists():
        yield "/", ROOT / "index.html", None, "home"
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
        if app is not None and not app.get("live"):
            continue          # 没上架的 app 不进 sitemap，页面另有 noindex
        rows.append((url, git_lastmod(path), {"home": "1.0", "product": "0.9"}.get(kind, "0.3")))
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
           *([f"- All apps on the App Store: {DEV_URL}"] if DEV_URL else []),
           f"- Contact: {EMAIL}", "", "## Apps", ""]
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
def software_jsonld(app):
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
    "fr": "Questions fréquentes", "it": "Domande frequenti", "ja": "よくある質問",
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
            "sameAs": list(dict.fromkeys(([DEV_URL] if DEV_URL else []) +
                                         [u for u in (store_url(a) for a in APPS) if u]))}

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
        lines.append(f'<meta name="apple-itunes-app" content="app-id={app["appId"]}">')

    blobs = [software_jsonld(app)]
    if is_product and app.get("faq"):
        blobs.append(faq_jsonld(app))
    for b in blobs:
        lines.append('<script type="application/ld+json">\n%s\n</script>'
                     % json.dumps(b, ensure_ascii=False, indent=2))
    lines.append(END)
    return "\n".join(lines) + "\n"

# ---------------------------------------------------------------- 首页
def home_name(a):
    """首页是英文页：卡片和 ItemList 用美区商店名；中文产品页的 app（单词兽）另存了英文名。"""
    return a["home"].get("storeNameEn", a["name"])

def home_head():
    canonical = f"{ORIGIN}/"
    title, desc = HOME["title"], HOME["description"]
    img = asset(HOME["ogImage"])
    lines = [START,
             '<meta name="description" content="%s">' % esc(desc),
             f'<link rel="canonical" href="{canonical}">',
             '<meta property="og:type" content="website">',
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
        su = store_url(a)
        item = {"@type": "SoftwareApplication", "@id": f"{ORIGIN}{a['path']}#app",
                "name": home_name(a), "alternateName": a["home"]["label"],
                "url": f"{ORIGIN}{a['path']}", "description": a["home"]["blurb"],
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
         "url": canonical, "name": BRAND, "description": desc, "inLanguage": "en",
         "publisher": {"@id": f"{ORIGIN}/#org"}},
        {"@context": "https://schema.org", "@type": "CollectionPage", "@id": f"{ORIGIN}/#webpage",
         "url": canonical, "name": title, "description": desc, "inLanguage": "en",
         "isPartOf": {"@id": f"{ORIGIN}/#website"}, "about": {"@id": f"{ORIGIN}/#org"},
         "primaryImageOfPage": img,
         "mainEntity": {"@type": "ItemList", "@id": f"{ORIGIN}/#apps", "name": f"Apps by {BRAND}",
                        "numberOfItems": len(items), "itemListElement": items}},
        {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{ORIGIN}/#faq",
         "inLanguage": "en",
         "mainEntity": [{"@type": "Question", "name": f["q"],
                         "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in HOME["faq"]]},
    ]
    for b in blobs:
        lines.append('<script type="application/ld+json">\n%s\n</script>'
                     % json.dumps(b, ensure_ascii=False, indent=2))
    lines.append(END)
    return "\n".join(lines) + "\n"

def home_apps_html():
    cards = []
    for a in HOME_APPS:
        h, key, page = a["home"], a["key"], a["path"]
        svg = (ROOT / "tools" / "home" / "illus" / f"{key}.svg").read_text(encoding="utf-8").strip()
        svg = "\n".join("        " + l for l in svg.splitlines())
        hl = f' hreflang="{h["hreflang"]}"' if h.get("hreflang") else ""
        label = esc_text(h["label"])
        su = store_url(a)
        get = f'\n      <a class="get" href="{su}">{label} on the App Store ↗</a>' if su else ""
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
      <p class="store-name">{esc_text(home_name(a))}</p>
      <p class="tagline">{esc_text(h["tagline"])}</p>
      <p class="blurb">{esc_text(h["blurb"])}</p>{get}
    </article>""")
    return ('<!-- apps:start -->\n  <div class="apps">\n' + "\n".join(cards)
            + "\n  </div>\n  <!-- apps:end -->")

def home_faq_html():
    rows = "\n".join('    <div class="qa">\n      <h3>%s</h3>\n      <p>%s</p>\n    </div>'
                     % (esc_text(f["q"]), esc_text(f["a"])) for f in HOME["faq"])
    return ('<!-- homefaq:start -->\n  <div class="faq-list">\n' + rows
            + "\n  </div>\n  <!-- homefaq:end -->")

def home_legal_html():
    rows = []
    for a in HOME_APPS:
        hl = a["home"].get("hreflang")
        attr = f' hreflang="{hl}" lang="{hl}"' if hl else ""
        links = " · ".join('<a href="%s"%s>%s</a>' % (href, attr, esc_text(label))
                           for href, label in a.get("legal", []))
        rows.append("          <li>%s — %s</li>" % (esc_text(a["home"]["label"]), links))
    return ('<!-- legal:start -->\n        <ul class="legal">\n' + "\n".join(rows)
            + "\n        </ul>\n        <!-- legal:end -->")

def patch_home(path: Path):
    html = path.read_text(encoding="utf-8")
    head_end = html.lower().find("</head>")
    if head_end == -1:
        return None
    head, rest = html[:head_end], html[head_end:]
    for pat in OWNED:
        head = re.sub(pat, "", head, flags=re.S | re.I)
    head = re.sub(r"<title>.*?</title>", lambda m: "<title>%s</title>" % esc_text(HOME["title"]),
                  head, count=1, flags=re.S)
    out = head.rstrip() + "\n" + home_head() + rest
    for tag, fn in (("apps", home_apps_html), ("homefaq", home_faq_html), ("legal", home_legal_html)):
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
    out = head + rest
    if kind == "product" and app.get("faq") and FAQ_START in out:
        out = re.sub(re.escape(FAQ_START) + r".*?" + re.escape(FAQ_END),
                     lambda m: faq_html(app), out, flags=re.S)
    return out

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
        out = patch_home(path) if kind == "home" else patch(path, url, app, kind)
        if out is None:
            print(f"  !! 没有 </head>，跳过：{path}")
            continue
        write(str(path.relative_to(ROOT)), out)

    print(f"sitemap: {n} 条 URL")
    print(("需要更新" if CHECK else "已写入") + f" {len(changed)} 个文件")
    for c in changed:
        print("  -", c)
    if CHECK and changed:
        sys.exit(1)

main()
