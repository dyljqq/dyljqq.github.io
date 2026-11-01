#!/usr/bin/env python3
"""Reproduce the 2026-11-01 consolidation report from local evidence only."""

import argparse
import collections
import hashlib
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from sitemap import sitemap_urls


ORIGIN = "https://beforego.art"
START, END = "2026-10-04", "2026-10-17"
PROTECTED = {
    "/tools/ja/kyotsu-test-2027/",
    "/tools/best-countdown-widget-apps-iphone/",
    "/countdown/de/",
    "/tools/ko/yeohaeng-iljeong-aep/",
    "/tools/pt-br/quantos-dias-faltam-para-as-ferias/",
}
FAMILY_LABELS = {
    "H": "首页语言族",
    "P-C": "Countdown 产品语言族",
    "P-I": "Invoice Maker 产品语言族",
    "P-W": "Word Beast 产品（单页）",
    "P-D": "DailyCalorie 产品（单页）",
    "P-Q": "QR Studio 产品（单页）",
    "P-R": "Repdex 产品（单页）",
    "L-P": "App 隐私说明族",
    "L-T": "App 使用条款族",
    "I": "内容目录族（工具语言目录、博客目录）",
    "T-D": "日期倒数族（通用、生日、假期、节日、考试）",
    "T-W": "倒数小组件设置指南族（场景、语言）",
    "T-A": "倒数 App 榜单语言族",
    "T-C": "日期表与日历族（工作日、连假）",
    "T-E": "可编辑单据族（单据类型、地区、语言）",
    "T-G": "开单操作指南族（语言、地区）",
    "B-Q": "发票支付二维码指南族",
    "S-C": "Invoice Simple 墨西哥替代指南（单页）",
    "S-T": "韩国旅行 App 迁移指南（单页）",
    "S-W": "倒数壁纸生成器（单页）",
    "S-I": "单据类型解释（单页）",
    "S-A": "关于（单页）",
    "S-S": "支持（单页）",
}
EXPLICIT_FAMILIES = {
    "T-D": """
        /tools/days-until/ /tools/ja/ato-nannichi/
        /tools/pt-br/quantos-dias-faltam/
        /tools/days-until-christmas/ /tools/days-until-diwali/
        /tools/days-until-halloween/ /tools/days-until-new-year/
        /tools/days-until-thanksgiving/
        /tools/pt-br/contador-de-dias-de-namoro/
        /tools/pt-br/quantos-dias-faltam-para-o-meu-aniversario/
        /tools/pt-br/quantos-dias-faltam-para-as-ferias/
        /tools/pt-br/contagem-regressiva-black-friday-2026/
        /tools/pt-br/contagem-regressiva-reveillon-2027/
        /tools/pt-br/quantos-dias-faltam-para-o-carnaval-2027/
        /tools/pt-br/quantos-dias-faltam-para-o-natal-2026/
        /tools/pt-br/dias-para-o-enem-2026/
        /tools/ja/kyotsu-test-2027/ /tools/ja/toritsu-nyushi-2027/
        /tools/zh-hant/116-hui-kao-dao-shu/ /tools/zh-hant/116-xue-ce-dao-shu/
        /tools/zh-hant/nong-li-xin-nian-2027/
    """,
    "T-W": """
        /tools/birthday-countdown-widget-iphone/
        /tools/christmas-countdown-widget-iphone/
        /tools/disney-countdown-widget-iphone/
        /tools/countdown-widget-with-your-own-photo-iphone/
        /tools/shared-countdown-app-couples/
        /tools/vacation-countdown-widget-iphone/
        /tools/ja/countdown-machiuke-iphone/ /tools/ko/iphone-didei-wijet/
        /tools/pt-br/contagem-regressiva-tela-de-bloqueio-iphone/
        /tools/zh-hant/iphone-zhu-hua-mian-dao-shu/
        /blog/countdown-widget-iphone-home-lock-screen/
        /blog/count-down-birthday-exam-trip-iphone/
    """,
    "T-A": """
        /tools/best-countdown-widget-apps-iphone/
        /tools/pt-br/melhores-apps-contagem-regressiva/
    """,
    "T-C": "/tools/pt-br/quinto-dia-util/ /tools/zh-hant/2027-lian-jia-xing-shi-li/",
    "T-E": """
        /tools/invoice-template/ /tools/es-mx/formato-de-cotizacion/
        /tools/es-mx/nota-de-venta/ /tools/th/bai-sanoe-rakha/
        /tools/zh-hant/bao-jia-dan-fan-ben/ /tools/zh-hant/shou-ju-fan-ben/
        /tools/de/angebot-vorlage/ /tools/de/rechnungsvorlage/
        /tools/de/rechnungsvorlage-kleinunternehmer/
    """,
    "T-G": """
        /tools/how-to-write-an-invoice/
        /tools/es-mx/app-para-hacer-cotizaciones-iphone/
        /tools/de/rechnung-schreiben-app-iphone/
    """,
    "B-Q": """
        /blog/payment-qr-code-on-invoice/
        /blog/venmo-cash-app-paypal-zelle-qr-code-on-invoice/
    """,
    "S-C": "/tools/es-mx/alternativa-a-invoice-simple/",
    "S-T": "/tools/ko/yeohaeng-iljeong-aep/",
    "S-W": "/tools/countdown-wallpaper-maker/",
    "S-I": "/blog/invoice-vs-estimate-vs-quote/",
    "S-A": "/about/",
    "S-S": "/support/",
}
EXPLICIT = {path: family for family, paths in EXPLICIT_FAMILIES.items() for path in paths.split()}
LANGUAGES = {"de", "es", "es-mx", "fr", "it", "ja", "ko", "pt-br", "th", "zh-hans", "zh-hant"}
CANDIDATE_PLANS = {
    "/tools/th/": (
        "/tools/",
        "目录主页面。先增加明确的泰语工具入口并保留泰语说明，更新语言导航；当前英文目录没有承接泰语单据入口，不能直接跳转。",
    ),
    "/invoiceqr/es-mx/": (
        "/invoiceqr/es/",
        "同产品的西语主页面。先加入墨西哥地区说明、nota de venta / cotización 入口与不提供 CFDI 的限制，避免把普通 factura 描述当成墨西哥税务功能；保留地区选择。",
    ),
    "/invoiceqr/privacy-policy/": (
        "/privacy-policy/",
        "隐私族根路径现为 BeforeGo 专用。只有先改成明确覆盖各 App 的隐私总页、完整保留 Invoice 的数据类型、AI 同意、存储与分析披露，并更新 App/商店隐私入口后才可承接；不同意重构总页就保留原页。",
    ),
}


def family_for(path):
    if path in EXPLICIT:
        return EXPLICIT[path]
    parts = path.strip("/").split("/")
    if path == "/" or len(parts) == 1 and parts[0] in LANGUAGES:
        return "H"
    if parts[-1] == "privacy-policy":
        return "L-P"
    if parts[-1] in {"terms-of-use", "terms-of-service"}:
        return "L-T"
    if path == "/blog/" or parts[0] == "tools" and (len(parts) == 1 or len(parts) == 2 and parts[1] in LANGUAGES):
        return "I"
    if parts[0] in {"countdown", "invoiceqr"} and (len(parts) == 1 or len(parts) == 2 and parts[1] in LANGUAGES):
        return "P-C" if parts[0] == "countdown" else "P-I"
    single = {"/citu/": "P-W", "/dailycalorie/": "P-D", "/qrcodestudio/": "P-Q", "/repdex/": "P-R"}
    if path in single:
        return single[path]
    raise ValueError(f"New sitemap path needs editorial family review: {path}")


def uniqueness(root):
    """Same eligible corpus, removal, tokenization and 5-token sets as uniq-reference.py."""
    tokens = {}
    for directory, _, names in os.walk(root):
        if any(excluded in directory for excluded in ("/.git", "/node_modules", "/tools/store", "/assets")):
            continue
        if "index.html" not in names:
            continue
        path = Path(directory) / "index.html"
        source = path.read_text(encoding="utf-8", errors="ignore")
        if 'noindex' in source[:6000] and 'name="robots"' in source[:6000]:
            continue
        language = (re.search(r'<html[^>]*lang="([^"]+)"', source) or [None, "?"])[1]
        source = re.sub(r'<!-- sitefooter:start -->.*?<!-- sitefooter:end -->', '', source, flags=re.S)
        source = re.sub(r'<(script|style|svg|head|nav|header|footer)\b.*?</\1>', '', source, flags=re.S | re.I)
        text = html.unescape(re.sub(r'<[^>]+>', ' ', source))
        if language.split("-")[0] in {"ja", "zh", "ko", "th"}:
            page_tokens = list(re.sub(r'\s+', '', text))
        else:
            page_tokens = re.findall(r'\w+', text.lower())
        relative = path.parent.relative_to(root).as_posix()
        url = "/" if relative == "." else "/" + relative + "/"
        tokens[url] = page_tokens
    shingles = {u: set(tuple(t[i:i + 5]) for i in range(max(0, len(t) - 4))) for u, t in tokens.items()}
    counts = collections.Counter(piece for pieces in shingles.values() for piece in pieces)
    ratios = {u: sum(counts[piece] == 1 for piece in pieces) / len(pieces) if pieces else None for u, pieces in shingles.items()}
    digest = hashlib.sha256(json.dumps(tokens, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return ratios, digest


def aggregate(rows):
    """Never average row positions without impression weights."""
    impressions = sum(row["impressions"] for row in rows)
    return {
        "clicks": sum(row["clicks"] for row in rows),
        "impressions": impressions,
        "position": sum(row["position"] * row["impressions"] for row in rows) / impressions if impressions else None,
    }


def page_metrics(group):
    dimensions = group["request"]["dimensions"]
    position = dimensions.index("page")
    by_page = collections.defaultdict(list)
    for row in group["raw_response"].get("rows", []):
        url = urlsplit(row["keys"][position])
        if url.scheme + "://" + url.netloc != ORIGIN:
            raise ValueError(f"Unexpected source origin: {url.geturl()}")
        by_page[url.path].append(row)
    return {path: aggregate(rows) for path, rows in by_page.items()}


def display_metrics(row):
    if row is None:
        return "未知 / 未知 / 未知"
    rank = "未知" if row["position"] is None else f'{row["position"]:.2f}'
    return f'{row["clicks"]:g} / {row["impressions"]:g} / {rank}'


def make_report(root):
    paths = sorted(url.removeprefix(ORIGIN) for url in sitemap_urls(root, ORIGIN))
    ratios, corpus_hash = uniqueness(root)
    if any(path not in ratios or ratios[path] is None for path in paths):
        raise ValueError("Every sitemap page must have an eligible non-empty HTML body")
    families = {path: family_for(path) for path in paths}
    family_counts = collections.Counter(families.values())
    # GSC / Bing 原始数据不进公开仓库：放在本机报表仓库，用 SEO_EVIDENCE_DIR 指过来
    evidence = Path(os.environ.get("SEO_EVIDENCE_DIR", root / "docs/facts"))
    gsc = json.loads((evidence / "gsc-beforego.art-1004-1031.json").read_text())
    other = json.loads((evidence / "bing-and-pagewren-gsc-2026-11-01.json").read_text())
    page_group = gsc["groups"]["page"]
    if page_group["request"]["dimensions"] != ["page"]:
        raise ValueError("Re-review evidence windows: page group dimensions changed")
    if (page_group["request"]["startDate"], page_group["request"]["endDate"]) != ("2026-10-04", "2026-10-31"):
        raise ValueError("Re-review evidence windows: page group dates changed")
    pages = page_metrics(page_group)
    site_rows = [row for row in gsc["groups"]["date"]["raw_response"]["rows"] if START <= row["keys"][0] <= END]
    if len(site_rows) != 14:
        raise ValueError("Pre-drop site date coverage is incomplete")
    site_before = aggregate(site_rows)
    bing = {row[0]: row[1] for row in other["bing_beforego_art_30d"]["pages"]}
    chatgpt = {row[0]: row[1] for row in other["ga4_chatgpt_landings_beforego_art_10_18_to_10_31"]}

    def zero_evidence(path):
        return path in pages and pages[path]["clicks"] == 0

    candidates = [path for path in paths if family_counts[families[path]] > 1 and ratios[path] < .4 and zero_evidence(path) and path not in PROTECTED]
    if set(candidates) != set(CANDIDATE_PLANS):
        raise ValueError(f"Candidate changes need editorial target review: {candidates}")
    for path, (target, _) in CANDIDATE_PLANS.items():
        if target not in paths or families[target] != families[path] or target in candidates:
            raise ValueError(f"Invalid family target: {path} -> {target}")
        source = (root / target.strip("/") / "index.html").read_text()
        canonical = re.search(r'<link\b[^>]*rel="canonical"[^>]*href="([^"]+)"', source)
        if not canonical or canonical.group(1) != ORIGIN + target:
            raise ValueError(f"Target self-canonical missing: {target}")

    lines = [
        "# 模板族合并候选清单 · 2026-11-01",
        "",
        f"当前 sitemap 为 **{len(paths)} 页**。按四项规则得到 **{len(candidates)} 个有条件候选**；现有目标内容均须先补齐，当前没有可直接执行的重定向。仅出报告，没有改页面、sitemap 或重定向配置。",
        "",
        "## 证据与计算口径",
        "",
        "- 范围：`sitemap.xml` 引用的四张子图，逐 URL 覆盖，不把已迁出的 BeforeGo、Pagewren 或已经合并的巴西分州旧页重新算入本站。模板族按正文/工具骨架人工归类；同族表示可比较，不表示每页没有独立价值。单页主题仍列出，但不满足‘属于重复模板族’。",
        f"- 独有率：逐项复现 [uniq-reference.py](facts/uniq-reference.py)；扫描本地所有符合其条件的 `index.html`（本次 {len(ratios)} 页），移除 sitefooter、head、script、style、svg、nav、header、footer 后，普通语言用小写词，ja/zh/ko/th 按非空白字符，取连续 5 token 的**集合**。独有率 = 全站只在本页出现的片段数 / 本页片段数。表中显示两位小数，40% 阈值用未舍入值判断；这是正文重叠指标，不是 Google 的质量评分，跨语言语义重复也不能靠它检出。",
        "- GSC：来源 GSC 原始 JSON `gsc-beforego.art-1004-1031.json`（不进公开仓库，在本机报表仓库 `reports/seo/2026-11-01-next-round/evidence/`）的 `groups.page`，请求窗口是 **10-04~10-31**，没有 page×date。`groups.query_page` 也没有日期且漏匿名查询，不能与 page 相加、互相补齐或反推出 10-04~10-17。逐页的目标窗口曝光与排名均为**未知**。28 天返回行明确为 0 点击时，因点击数非负，可推知其 10-04~10-17 子窗口也是 0，表中标 `0†`；正点击页的目标窗口点击无法拆分，标未知。没有返回行仍为未知，绝不补零。这是基于导出返回行的筛选证据，不承诺 API 覆盖所有数据。",
        f"- 唯一可直接聚合的掉量前数据是 `groups.date` 的全站 14 天：**{display_metrics(site_before)}**（点击 / 曝光 / 平均排名）。排名按 `Σ(曝光×排名) / Σ曝光` 计算；下表 28 天逐页参考也采用此加权口径。它不是逐页 14 天数值，不能按全站比例分摊。JSON 声明 `api_guarantees_all_rows=false`，10-31 在按日结果中缺失且定义为 unknown_not_zero。",
        "- Bing：来源 Bing / GA4 汇总 `bing-and-pagewren-gsc-2026-11-01.json`（同上，不进公开仓库）的 `bing_beforego_art_30d.pages`。只对列出的页填写曝光，未列页填未知。文件将该报表标为 30 天，但未给严格起止日期；日数组覆盖 10-02~10-29，不能擅自把数组或 GSC 窗口替换成同一窗口。7 个已列页面合计 938 曝光，站点总量 950，余下 12 不分摊。",
        "- ChatGPT：同文件 `ga4_chatgpt_landings_beforego_art_10_18_to_10_31`。`是(n)` 指该窗口明确记录的落地会话；未列页填未知，不写‘否’。细分列表合计 25 会话，其中 `/pagewren/de/` 的 1 次已不在当前 sitemap；任务背景称 26 会话，差额 1 次未分配。商店关键事件不等于下载或安装。",
        "- 原任务背景把 10-18 后变化称为‘限流’，但现有事实只证明搜索曝光骤降；不能凭这份报告认定是模板处罚，也不能保证合并后恢复流量。当前快照无法验收实际 HTTP 响应或线上任务完成，本报告只检查本地目标存在且自指 canonical。",
        "",
        "## 模板族与逐页清单",
        "",
        "`GSC 前` = 10-04~10-17 点击 / 曝光 / 加权排名；`GSC 28天参考` = 请求窗口 10-04~10-31 的 page 返回行。`0†` 的推断范围见上文。‘未知’不是 0。",
        "",
        "| 族 | 页数 | 归组范围 |",
        "| --- | ---: | --- |",
    ]
    for family in FAMILY_LABELS:
        if family in family_counts:
            lines.append(f"| {family} | {family_counts[family]} | {FAMILY_LABELS[family]} |")
    lines += [
        "",
        "节日、考试与地区倒数统一放在 T-D，通用计算页与具体日期页是该族子型；T-W 含小组件设置的场景与语言变体。App 隐私说明虽共享骨架，披露主体和数据处理不同，低独有率不表示可直接互相替代。I 目录族复用条目列表骨架，泰语目录只有一个工具入口，因此容易被片段算法判为低独有率。",
        "",
        "| 页面 | 族 | 独有率 | GSC 前 | GSC 28天参考 | Bing 30天曝光 | ChatGPT 落地 | 判定 |",
        "| --- | --- | ---: | --- | --- | ---: | --- | --- |",
    ]
    for path in sorted(paths, key=lambda path: (list(FAMILY_LABELS).index(families[path]), path)):
        before = "0† / 未知 / 未知" if zero_evidence(path) else "未知 / 未知 / 未知"
        chat = f"是({chatgpt[path]})" if path in chatgpt else "未知"
        decision = "保护" if path in PROTECTED else "有条件候选" if path in candidates else "独有率不足，点击未知" if ratios[path] < .4 else "未达候选条件"
        lines.append(f"| `{path}` | {families[path]} | {ratios[path] * 100:.2f}% | {before} | {display_metrics(pages.get(path))} | {bing.get(path, '未知')} | {chat} | {decision} |")
    lines += [
        "",
        "## 四条件候选与 308 草案",
        "",
        "规则逐项取交集：重复模板族 + 未舍入独有率 < 40% + 掉量前 0 点击证据 + 不在保护名单。下列页全部满足四项。`0†` 来自已返回 page 全窗口 0 点击的子窗口推断；如果要求只能用 14 天直接查询行确认，当前直接证据候选为 0，需先补导出。",
        "",
        "| 来源 | 同族既有目标 | 四条件核对 | 执行前的承接要求 |",
        "| --- | --- | --- | --- |",
    ]
    for path in candidates:
        target, note = CANDIDATE_PLANS[path]
        lines.append(f"| `{path}` | `{target}` | {families[path]}；{ratios[path] * 100:.2f}% < 40%；0†；非保护 | {note} |")
    lines += [
        "",
        "以下只给待批准规则，**不要把这段直接应用到当前目标正文**。目标路径已在当前 sitemap，和来源属于同族，不指回来源、也不形成候选链；承接内容和语言/隐私入口完成后，再逐条验证目标 200、永久跳转 308、canonical、hreflang、站内链接与 sitemap。",
        "",
        "```text",
    ]
    for path in candidates:
        lines.append(f"308 {path} -> {CANDIDATE_PLANS[path][0]}")
    lines += [
        "```",
        "",
        "这三条属于审阅候选，不建议为了减少页数直接牺牲本地化用途或 App 专属隐私入口。若目标无法保持这些用途，保留来源。尤其 `/invoiceqr/es-mx/` 的原始比值是 492/1242 = 39.6135%，参考脚本的整数输出会显示 40；本报告没有把四舍五入值用于阈值。",
        "",
        "## 保护与暂缓",
        "",
        "保护名单五页均保留，不论任何其他指标：",
        "",
    ]
    for path in sorted(PROTECTED):
        lines.append(f"- `{path}`")
    lines += [
        "",
        "低于 40% 但没有 GSC page 返回行的 `/blog/`、`/invoiceqr/es/`、`/countdown/privacy-policy/`、`/qrcodestudio/privacy-policy/`：掉量前点击未知，因此不列候选。所有当前节日/考试倒数页都高于 40%，不能因为属于模板族就合并。Bing 或 ChatGPT 数据缺失没有被当成额外的零流量条件。",
        "",
        "巴西 SP/MG/PR/RS/PE 五个分州旧页与泰语旧收据页已在 10-25 合并（[ANALYTICS.md](../ANALYTICS.md)），不在当前 sitemap；原始 GSC 仍有历史行，但不得再次计入可减少页数。BeforeGo 与 Pagewren 外迁网址也不纳入本报告数量。",
        "",
        "## 复现与复核",
        "",
        "只读现有 HTML / sitemap / facts，再写本报告；不联网、不构建、不提交：",
        "",
        "```sh",
        "python3 tools/report_consolidation.py",
        "python3 docs/facts/uniq-reference.py . /tmp/beforego-uniq-reference.json",
        "```",
        "",
        "第二条用于复核算法的整数展示值；主报告保留分数精度。若榜单正文或任意页面改变，须重新运行第一条，因为独有率的分母与全站片段频次会一起改变。脚本对每个 sitemap URL 要求显式模板归组，对新增候选要求人工确定同族目标；遇到新 URL 或候选变化会失败，避免自动生成未经审阅的合并建议。",
        "",
        f"正文 token 语料 SHA-256：`{corpus_hash}`。",
        "",
        f"**数量结论：当前 {len(paths)} 页；四条件有条件候选 {len(candidates)} 页；可直接执行 0 页。若用户批准全部候选、目标完成内容承接并验收，再移除这 {len(candidates)} 个来源 URL，预计 sitemap 为 {len(paths) - len(candidates)} 页；本次仍为 {len(paths)} 页。**",
        "",
    ]
    return "\n".join(lines), len(candidates), len(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    # 报告里有逐页 GSC/Bing 数字，仓库是公开的，只写到仓库外
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    report, candidates, pages = make_report(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(report, encoding="utf-8")
    print(f"Consolidation report: {pages} pages; {candidates} conditional candidates; projected {pages - candidates}; immediately executable 0")


if __name__ == "__main__":
    main()
