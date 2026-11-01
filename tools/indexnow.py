#!/usr/bin/env python3
"""IndexNow：只推内容变了的页面。Bing 的要求是只提交新增、修改、删除的 URL——
10-16 之前每次发布都把 sitemap 全部 124 个 URL 推一遍，Bing WMT 累计提交 1K 次，只收录 5 页。

  python3 tools/indexnow.py --dry-run   # 列出这次会推哪些 URL，不推、不写记录（publish.sh --check 会跑）
  python3 tools/indexnow.py             # 推送并更新记录（publish.sh 在 Vercel 部署成功后跑）
  python3 tools/indexnow.py --record    # 只按当前文件重写记录、不推（记录坏了、或线上和本地一致想清零时用）

记录在 tools/indexnow-state.json，逐页保存 lastmod、description、正文签名及签名版本。
修改 = sitemap lastmod、meta description 或同版本正文签名变化；每日日期与计数不触发。
旧的纯 hash 记录从记录文件最后一次 Git 提交恢复 sitemap lastmod 和页面 description，
逐页比较是否变化（包括日期向后纠正）。缺少正文签名或签名版本变化时仅建立签名基线，
不会单因迁移推送；已有 lastmod / description 的真实变化仍推送。
新增 = 记录里没有；删除 = 记录里有、sitemap 里没了。推送失败或 dry-run 不写记录。
没有记录文件（第一次跑）：只记录、不推送。
"""
import hashlib, json, subprocess, sys, urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import ROOT, ORIGIN  # import 时设为越南时间，与 sitemap 的日期口径一致
import check_page_budget as budget
from sitemap import NS, sitemap_urls

KEY = "6bc0c7e758182078db2f4e3107b328d5"     # 站根的 <KEY>.txt 就是验证文件
STATE = ROOT / "tools/indexnow-state.json"
DRY, RECORD = "--dry-run" in sys.argv, "--record" in sys.argv

class DescriptionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.description = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content") or ""


def description(html):
    parser = DescriptionParser()
    parser.feed(html)
    return parser.description


def page_file(path):
    return ROOT / path.strip("/") / "index.html" if path.endswith("/") else ROOT / path.lstrip("/")


def current():
    """读取本地发布信号；正文与页面预算共用日期和计数归一化规则。"""
    urls = sitemap_urls(ROOT, ORIGIN)  # 同时校验子图引用、URL 和重复项
    tree = ET.parse(ROOT / "sitemap.xml").getroot()
    maps = [tree]
    if tree.tag == NS + "sitemapindex":
        maps = [ET.parse(ROOT / child.findtext(NS + "loc")[len(ORIGIN) + 1:]).getroot()
                for child in tree.findall(NS + "sitemap")]
    lastmods = {page.findtext(NS + "loc"): page.findtext(NS + "lastmod")
                for tree in maps for page in tree.findall(NS + "url")}
    out = {}
    for loc in urls:
        path = loc[len(ORIGIN):]
        f = page_file(path)
        source = f.read_text(encoding="utf-8") if f.suffix == ".html" else ""
        signature = json.dumps(budget.body_signature(source, date.today()), ensure_ascii=False,
                               separators=(",", ":")).encode("utf-8")
        out[path] = {"lastmod": lastmods[loc],
                     "description": description(source),
                     "body_signature": hashlib.sha256(signature).hexdigest(),
                     "body_signature_version": budget.BODY_SIGNATURE_VERSION}
    return out


def legacy_snapshot(paths):
    """从旧记录的提交恢复逐页信号，包含该提交引用的拆分 sitemap。"""
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                              text=True, timeout=30).stdout
    try:
        commit = git("log", "-1", "--format=%H", "--",
                     STATE.relative_to(ROOT).as_posix()).strip()
        if not commit:
            raise ValueError("记录文件没有 Git 提交")
        tree = ET.fromstring(git("show", f"{commit}:sitemap.xml"))
        maps = [tree]
        if tree.tag == NS + "sitemapindex":
            maps = []
            for child in tree.findall(NS + "sitemap"):
                loc = child.findtext(NS + "loc") or ""
                name = loc.removeprefix(ORIGIN + "/")
                if not loc.startswith(ORIGIN + "/") or "/" in name or not name.endswith(".xml"):
                    raise ValueError(f"Invalid historical sitemap reference: {loc}")
                maps.append(ET.fromstring(git("show", f"{commit}:{name}")))
        lastmods = {}
        for tree in maps:
            if tree.tag != NS + "urlset":
                raise ValueError("Expected a historical sitemap urlset")
            for page in tree.findall(NS + "url"):
                loc = page.findtext(NS + "loc") or ""
                if not loc.startswith(ORIGIN + "/") or loc in lastmods:
                    raise ValueError(f"Invalid or duplicated historical sitemap URL: {loc}")
                lastmods[loc] = page.findtext(NS + "lastmod")
        snapshot = {}
        for path in paths:
            if ORIGIN + path not in lastmods:
                raise ValueError(f"Historical sitemap is missing recorded URL: {path}")
            f = page_file(path)
            snapshot[path] = {
                "lastmod": lastmods[ORIGIN + path],
                "description": description(git("show", f"{commit}:{f.relative_to(ROOT).as_posix()}"))
                if f.suffix == ".html" else ""}
        return snapshot
    except (subprocess.SubprocessError, OSError, ValueError, ET.ParseError) as error:
        raise RuntimeError("无法核实旧 IndexNow 记录的 sitemap lastmod 或 description；"
                           f"请恢复记录文件及对应 sitemap / 页面的 Git 历史（{error}）") from error


def changes(cur, old):
    shared = [p for p in cur if p in old]
    legacy = [p for p in shared if not isinstance(old[p], dict)
              or "lastmod" not in old[p] or "description" not in old[p]]
    snapshot = legacy_snapshot(legacy) if legacy else {}
    modified = []
    for path in shared:
        previous = old[path] if isinstance(old[path], dict) else {}
        baseline = {**snapshot.get(path, {}), **previous}
        date_changed = baseline["lastmod"] != cur[path]["lastmod"]
        old_description = baseline["description"]
        # Missing or outdated signatures are migration, not evidence of an edit.
        # Compare only compatible signatures; save(cur) establishes the new
        # baseline after a successful submission or a no-change non-dry run.
        body_changed = ("body_signature" in previous and "body_signature" in cur[path]
                        and previous.get("body_signature_version") == budget.BODY_SIGNATURE_VERSION
                        and cur[path].get("body_signature_version") == budget.BODY_SIGNATURE_VERSION
                        and previous["body_signature"] != cur[path]["body_signature"])
        if date_changed or old_description != cur[path]["description"] or body_changed:
            modified.append(path)
    return (("新增", [p for p in cur if p not in old]),
            ("修改", modified),
            ("删除", [p for p in old if p not in cur]))


def save(state):
    STATE.write_text(json.dumps(state, indent=0, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def main():
    cur = current()
    if RECORD or not STATE.exists():
        why = "--record" if RECORD else "没有记录文件，第一次运行"
        if DRY:
            print(f"IndexNow（dry-run）：{why}——只会记录 {len(cur)} 页的 lastmod / description / 正文签名，不推送")
            return
        save(cur)
        print(f"IndexNow：{why}——已记录 {len(cur)} 页的 lastmod / description / 正文签名，本次不推送")
        return
    try:
        old = json.loads(STATE.read_text(encoding="utf-8"))
        assert isinstance(old, dict)
    except Exception as e:          # 多半是合并冲突标记：别悄悄跳过，publish.sh 也不会把它提交
        sys.exit(f"✗ IndexNow 记录 tools/{STATE.name} 读不出来（{e!r}，合并冲突？）——"
                 "修好它，或跑 python3 tools/indexnow.py --record 按当前文件重建")
    groups = changes(cur, old)
    paths = [p for _, ps in groups for p in ps]
    head = "IndexNow（dry-run）" if DRY else "IndexNow"
    print(f"{head}：sitemap 共 {len(cur)} 页，" + " · ".join(f"{name} {len(ps)}" for name, ps in groups))
    for name, ps in groups:
        for p in ps:
            print(f"  {name}  {ORIGIN}{p}")
    if not paths:
        if not DRY and cur != old:
            save(cur)
        print("  没有内容变化的页面，不推送")
        return
    if DRY:
        return
    body = json.dumps({"host": ORIGIN.split("://")[1], "key": KEY, "keyLocation": f"{ORIGIN}/{KEY}.txt",
                       "urlList": [ORIGIN + p for p in paths]}).encode()
    try:
        r = urllib.request.urlopen(urllib.request.Request("https://api.indexnow.org/IndexNow", data=body,
                                   headers={"Content-Type": "application/json; charset=utf-8"}), timeout=30)
    except Exception as e:          # 4xx/5xx/网络：记录不动，下次发布再推
        sys.exit(f"✗ IndexNow 推送失败（{e}），记录未更新，下次发布会把这 {len(paths)} 个 URL 连同新变化一起再推")
    if r.status not in (200, 202):
        sys.exit(f"✗ IndexNow 返回 {r.status}，记录未更新，下次发布再推")
    save(cur)
    print(f"IndexNow {r.status}：推了 {len(paths)} 个 URL，记录已更新")

if __name__ == "__main__":
    main()
