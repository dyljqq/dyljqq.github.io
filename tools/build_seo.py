#!/usr/bin/env python3
"""从 tools/site.json 生成抓取入口，并把每个页面的 head 补齐。

  python3 tools/build_seo.py          # 写文件
  python3 tools/build_seo.py --check  # 只报告差异，不落盘（CI / 提交前用）

生成：robots.txt、sitemap.xml、llms.txt
改写：每个 *.html 的 head——canonical / description / og / twitter /
      SoftwareApplication JSON-LD，全部放在 <!-- seo:start --> 标记块里，
      重跑先删旧块再写新块，所以脚本可以反复跑。

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

def pages():
    """产出 (url_path, html_path, app, kind)。kind: product / legal。"""
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
        if not app.get("live"):
            continue          # 没上架的 app 不进 sitemap，页面另有 noindex
        rows.append((url, git_lastmod(path), "0.9" if kind == "product" else "0.3"))
    rows.sort(key=lambda r: (r[0] != "/", r[0]))
    body = "\n".join(
        f"  <url>\n    <loc>{ORIGIN}{u}</loc>\n    <lastmod>{m}</lastmod>\n"
        f"    <priority>{p}</priority>\n  </url>" for u, m, p in rows)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}\n</urlset>\n"), len(rows)

# ---------------------------------------------------------------- llms.txt
def build_llms():
    live = [a for a in APPS if a.get("live")]
    out = [f"# {BRAND}", "",
           f"> {len(live)} 个独立开发的 iPhone app。每个 app 一个产品页，页面上写的功能、",
           "> 免费范围和价格就是应用内的实际情况，没有第二套说法。",
           "",
           f"Contact: {EMAIL}", "", "## Apps", ""]
    for a in live:
        su = store_url(a)
        out.append(f"### {a['name']}")
        out.append("")
        out.append(a["oneLiner"])
        out.append("")
        out.append(f"- Page: {ORIGIN}{a['path']}")
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
    out += ["## Notes", "",
            "- 所有 app 都是免费下载。付费部分（如果有）写在各自的产品页上。",
            "- 没有服务器账号体系；数据留在设备和用户自己的 iCloud 里。",
            f"- 支持与反馈：{EMAIL}", ""]
    return "\n".join(out)

# ---------------------------------------------------------------- head 改写
def software_jsonld(app):
    d = {"@context": "https://schema.org", "@type": "SoftwareApplication",
         "@id": f"{ORIGIN}{app['path']}#app",
         "name": app["name"], "alternateName": app["shortName"],
         "applicationCategory": app["category"],
         "operatingSystem": "iOS 17.0 or later",
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

def faq_html(app):
    """可见 FAQ。schema 里的问答必须在页面上看得见、且逐字一致（清单 7.7），
    所以两边都从 site.json 的同一份数据生成，杜绝改了一边忘了另一边。"""
    heading = "常见问题" if app.get("lang", "en").startswith("zh") else "Questions people ask"
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
            "description": f"Independent iOS developer. {len([a for a in APPS if a.get('live')])} apps on the App Store.",
            "sameAs": [u for u in (store_url(a) for a in APPS) if u]}

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
    if url == "/":
        blobs.append(org_jsonld())
        blobs.append({"@context": "https://schema.org", "@type": "WebSite",
                      "@id": f"{ORIGIN}/#website", "url": f"{ORIGIN}/", "name": BRAND,
                      "publisher": {"@id": f"{ORIGIN}/#org"}})
    for b in blobs:
        lines.append('<script type="application/ld+json">\n%s\n</script>'
                     % json.dumps(b, ensure_ascii=False, indent=2))
    lines.append(END)
    return "\n".join(lines) + "\n"

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
        out = patch(path, url, app, kind)
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
