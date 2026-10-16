#!/usr/bin/env python3
"""IndexNow：只推内容变了的页面。Bing 的要求是只提交新增、修改、删除的 URL——
10-16 之前每次发布都把 sitemap 全部 124 个 URL 推一遍，Bing WMT 累计提交 1K 次，只收录 5 页。

  python3 tools/indexnow.py --dry-run   # 列出这次会推哪些 URL，不推、不写记录（publish.sh --check 会跑）
  python3 tools/indexnow.py             # 推送并更新记录（publish.sh 在 Vercel 部署成功后跑）
  python3 tools/indexnow.py --record    # 只按当前文件重写记录、不推（记录坏了、或线上和本地一致想清零时用）

记录在 tools/indexnow-state.json：{URL 路径: 内容 hash}，即上次推送成功时各页的样子；publish.sh 推完会把它提交，
换个 worktree 发布也接得上。没有记录文件（第一次跑）：只记录、不推送。推送失败不写记录，下次发布连同新变化一起再推。

「内容」= meta description + sitemap lastmod 口径的正文（build_seo._lastmod_norm：<title> 和 <body>，去掉样式、
YYYY-MM-DD、全站页脚、空白），再去掉倒数页每天重建都会变的两样——10-16 一次重建就让 30 页变了，天天推等于又回到全量推：
  - 计数器（data-n / data-unit / data-weeks / data-days）里的文字，浏览器打开时本来就会重算；
  - 写着构建当天日期的那段文字里的数字（build_tools.py 的「On 16 October 2026 there were 70 days…」「2026年10月16日の時点で…」）。
别处的数字照比：假期页、考试页改了日期会推。构建和本脚本要在同一天（越南时间）跑，publish.sh 是连着跑的。
会多推、无害的情况：跨零点发布时倒数页（约 30 页）那次和下一次各推一遍；正文里写死的日期恰好是发布当天
（如「2026年10月15日に確認」、韩语教程里「D-30은 2026년 10월 20일」），那段当天被当成每日文字，当天和下一次各推一遍，之后稳定。
新增 = 记录里没有；删除 = 记录里有、sitemap 里没了（推了让 Bing 回来看到 404 / noindex 再除名）。
"""
import hashlib, json, re, sys, urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import ROOT, ORIGIN, _lastmod_norm     # import 时已把时区设成越南时间，date.today() 和构建同口径

KEY = "6bc0c7e758182078db2f4e3107b328d5"     # 站根的 <KEY>.txt 就是验证文件
STATE = ROOT / "tools/indexnow-state.json"
DRY, RECORD = "--dry-run" in sys.argv, "--record" in sys.argv

COUNTER = re.compile(r"(<[a-z]+\b[^>]*\sdata-(?:n|unit|weeks|days)\b[^>]*>)[^<]*")
DESC = re.compile(r'<meta name="description" content="([^"]*)"')
TODAY = date.today()
# build_tools.py 写「截至今天」那句用到的日期写法：ISO、英文 %-d %B %Y、葡语 %d/%m/%Y、中日 年月日、韩 년월일
TODAY_FORMS = (TODAY.isoformat(), TODAY.strftime("%-d %B %Y"), TODAY.strftime("%d/%m/%Y"),
               f"{TODAY.year}年{TODAY.month}月{TODAY.day}日", f"{TODAY.year}년 {TODAY.month}월 {TODAY.day}일")
TODAY_RE = re.compile("|".join(r"(?<!\d)" + re.escape(f) for f in TODAY_FORMS))   # 前面不能是数字：「1 November」别命中「11 November」

def mask_today(m):
    t = m.group(1)
    if TODAY_RE.search(t):
        # 先去掉 YYYY-MM-DD 再抹数字：「更新 2026-10-16」今天会命中、明天不会，两天都要归一成同一个样子，否则当天改过的页第二天又被推一次
        t = re.sub(r"\d+", "#", re.sub(r"\d{4}-\d{2}-\d{2}", "", t))
    return ">" + t + "<"

def norm(html):
    html = re.sub(r">([^<]*)<", mask_today, COUNTER.sub(r"\1", html))
    desc = DESC.search(html)
    return (desc.group(1) if desc else "") + "\n" + _lastmod_norm(html)

def current():
    """sitemap 里每个 URL 路径 → 内容 hash。读的是本地文件，所以要在构建之后、和刚部署的内容一致时跑。"""
    out = {}
    for loc in re.findall(r"<loc>(.*?)</loc>", (ROOT / "sitemap.xml").read_text(encoding="utf-8")):
        assert loc.startswith(ORIGIN + "/"), loc
        path = loc[len(ORIGIN):]
        f = ROOT / path.strip("/") / "index.html" if path.endswith("/") else ROOT / path.lstrip("/")
        body = norm(f.read_text(encoding="utf-8")).encode() if f.suffix == ".html" else f.read_bytes()
        out[path] = hashlib.sha256(body).hexdigest()[:16]
    return out

def save(state):
    STATE.write_text(json.dumps(state, indent=0, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def main():
    cur = current()
    if RECORD or not STATE.exists():
        why = "--record" if RECORD else "没有记录文件，第一次运行"
        if DRY:
            print(f"IndexNow（dry-run）：{why}——只会记录 {len(cur)} 页的 hash，不推送")
            return
        save(cur)
        print(f"IndexNow：{why}——已记录 {len(cur)} 页的 hash，本次不推送")
        return
    try:
        old = json.loads(STATE.read_text(encoding="utf-8"))
        assert isinstance(old, dict)
    except Exception as e:          # 多半是合并冲突标记：别悄悄跳过，publish.sh 也不会把它提交
        sys.exit(f"✗ IndexNow 记录 tools/{STATE.name} 读不出来（{e!r}，合并冲突？）——"
                 "修好它，或跑 python3 tools/indexnow.py --record 按当前文件重建")
    groups = (("新增", [p for p in cur if p not in old]),
              ("修改", [p for p in cur if p in old and old[p] != cur[p]]),
              ("删除", [p for p in old if p not in cur]))
    paths = [p for _, ps in groups for p in ps]
    head = "IndexNow（dry-run）" if DRY else "IndexNow"
    print(f"{head}：sitemap 共 {len(cur)} 页，" + " · ".join(f"{name} {len(ps)}" for name, ps in groups))
    for name, ps in groups:
        for p in ps:
            print(f"  {name}  {ORIGIN}{p}")
    if not paths:
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
