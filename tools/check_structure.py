"""发布前结构审计（离线）：canonical 自指 / 单 H1 / JSON-LD 可解析 / FAQ 与 ItemList 在可见文字里逐字出现 /
站内死链 / sitemap 与可索引页一致 / llms.txt 死链 / title 与 description 长度。

  python3 tools/check_structure.py [仓库根目录，默认当前目录]
有问题退出码 1。
"""
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
ORIGIN = json.loads((ROOT / "tools/site.json").read_text())["site"]["origin"]

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.title = []; self.in_title = False; self.metas = []; self.links = []
        self.h1 = 0; self.a = []; self.imgs = []; self.ld = []; self.in_ld = False; self.buf = ""
        self.text = []; self.skip = 0; self.lang = None; self.heads = []; self.cur_h = None
    def handle_starttag(self, t, at):
        d = dict(at)
        if t == "html": self.lang = d.get("lang")
        if t == "title": self.in_title = True
        if t == "meta": self.metas.append(d)
        if t == "link": self.links.append(d)
        if t == "h1": self.h1 += 1
        if t in ("h1", "h2", "h3", "h4"): self.cur_h = [t, ""]
        if t == "a": self.a.append(d)
        if t == "img": self.imgs.append(d)
        if t == "script" and d.get("type") == "application/ld+json": self.in_ld = True; self.buf = ""
        elif t in ("script", "style"): self.skip += 1
    def handle_endtag(self, t):
        if t == "title": self.in_title = False
        if t == "script" and self.in_ld: self.ld.append(self.buf); self.in_ld = False
        elif t in ("script", "style") and self.skip: self.skip -= 1
        if self.cur_h and t == self.cur_h[0]: self.heads.append(tuple(self.cur_h)); self.cur_h = None
    def handle_data(self, x):
        if self.in_title: self.title.append(x)
        if self.in_ld: self.buf += x
        elif not self.skip:
            self.text.append(x)
            if self.cur_h: self.cur_h[1] += x

def url_of(path):
    rel = path.relative_to(ROOT).as_posix()
    return ORIGIN + "/" + rel[: -len("index.html")]

issues, rows = [], []
pages = sorted(p for p in ROOT.rglob("index.html") if ".git" not in p.parts and "diary" not in p.parts)
titles = {}
for path in pages:
    s = path.read_text(encoding="utf-8"); p = P(); p.feed(s)
    url = url_of(path)
    meta = lambda **kw: [m for m in p.metas if all(m.get(k) == v for k, v in kw.items())]
    canon = [l["href"] for l in p.links if l.get("rel") == "canonical"]
    desc = meta(name="description"); robots = meta(name="robots")
    noindex = any("noindex" in (m.get("content") or "") for m in robots)
    ogurl = meta(property="og:url")
    title = "".join(p.title).strip()
    tag = path.relative_to(ROOT).as_posix()
    def bad(msg): issues.append(f"{tag}: {msg}")
    if not title: bad("缺 title")
    titles.setdefault(title, []).append(tag)
    if len(desc) != 1 or not desc[0].get("content"): bad("description 缺失或多条")
    elif len(desc[0]["content"]) > 170: bad(f"description {len(desc[0]['content'])} 字（上限 170）")
    if len(title) > 70: bad(f"title {len(title)} 字（上限 70）")
    elif re.search(r"\.\.\.|…", desc[0]["content"]): bad("description 含截断符")
    if len(canon) != 1: bad(f"canonical 数量 {len(canon)}")
    elif canon[0] != url: bad(f"canonical {canon[0]} != {url}")
    if ogurl and ogurl[0].get("content") != (canon[0] if canon else None): bad("og:url != canonical")
    if p.h1 != 1: bad(f"H1 数量 {p.h1}")
    if not p.lang: bad("html 缺 lang")
    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and k in ("url", "@id", "sameAs", "downloadUrl", "installUrl", "contentUrl", "image", "logo"):
                    yield v
                else: yield from walk(v)
        elif isinstance(o, list):
            for v in o: yield from (walk(v) if not isinstance(v, str) else [v])
    for raw in p.ld:
        try: ld = json.loads(raw)
        except Exception as e: bad(f"JSON-LD 解析失败 {e}"); continue
        # 09-26 第 3 轮评审：卡片改成商店链接后，JSON-LD 被拼成 https://beforego.arthttps://apps.apple.com/…?pt=…
        for u in walk(ld):
            if u.startswith("http") and (u.count("://") > 1 or re.search(r"[?&](pt|ct)=", u)):
                bad(f"JSON-LD 链接非法或带活动参数：{u[:90]}")
    text = re.sub(r"\s+", " ", " ".join(p.text))
    # FAQ / ItemList 可见性（7.2 / 7.7）
    for raw in p.ld:
        d = json.loads(raw)
        if d.get("@type") == "FAQPage":
            for q in d["mainEntity"]:
                if q["name"] not in text: bad(f"FAQ 问题不可见：{q['name'][:40]}")
                if q["acceptedAnswer"]["text"] not in text: bad(f"FAQ 答案不可见：{q['name'][:40]}")
        if d.get("@type") == "CollectionPage" and "mainEntity" in d:
            for it in d["mainEntity"]["itemListElement"]:
                if it["item"]["name"] not in text: bad(f"ItemList 名称不可见：{it['item']['name']}")
                if it["item"]["description"] not in text: bad(f"ItemList 描述不可见：{it['item']['name']}")
    for a in p.a:
        h = a.get("href")
        if h in (None, "", "#") or (h or "").startswith("javascript:"): bad(f"空链接 {h!r}")
        elif h.startswith("/") and not h.startswith("//"):
            target = ROOT / h.lstrip("/").split("#")[0]
            if h.split("#")[0].endswith("/"): target = target / "index.html"
            if not target.exists(): bad(f"站内死链 {h}")
        if a.get("target") == "_blank" and "noopener" not in (a.get("rel") or ""): bad(f"_blank 缺 noopener {h}")
    for i in p.imgs:
        if "alt" not in i: bad(f"img 缺 alt {i.get('src')}")
    for l in p.links:
        h = l.get("href", "")
        if l.get("rel") in ("icon", "apple-touch-icon", "preload") and h.startswith("/") and not (ROOT / h.lstrip("/")).exists():
            bad(f"head 资源不存在 {h}")
    if re.search(r"lorem ipsum|\bTODO\b|\bplaceholder\b(?!=)", s): bad("疑似占位内容")
    rows.append((tag, noindex, title))

for t, tags in titles.items():
    if len(tags) > 1: issues.append(f"title 重复：{t!r} ← {tags}")

sm = (ROOT / "sitemap.xml").read_text()
locs = re.findall(r"<loc>(.*?)</loc>", sm)
for loc in locs:
    f = ROOT / loc[len(ORIGIN) + 1:] / "index.html" if loc != ORIGIN + "/" else ROOT / "index.html"
    if not f.exists(): issues.append(f"sitemap 指向不存在的页面 {loc}")
    elif 'content="noindex' in f.read_text(): issues.append(f"sitemap 含 noindex 页 {loc}")
indexable = {ORIGIN + "/" + r[0][: -len("index.html")] for r in rows if not r[1]}
missing = indexable - set(locs)
if missing: issues.append(f"可索引但不在 sitemap：{sorted(missing)}")
for u in re.findall(re.escape(ORIGIN) + r"(/[^\s)]*)", (ROOT / "llms.txt").read_text()):
    f = ROOT / u.lstrip("/") / ("index.html" if u.endswith("/") else "")
    if not f.exists(): issues.append(f"llms.txt 死链 {u}")

print(f"结构审计：页面 {len(pages)}，sitemap {len(locs)} 条，" + ("全部通过" if not issues else f"{len(issues)} 个问题"))
if issues:
    print("\n".join("  ✗ " + i for i in issues)); sys.exit(1)
