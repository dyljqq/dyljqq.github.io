#!/usr/bin/env python3
"""Check the rolling seven-day URL budget and reference five-token uniqueness.

Read the local publication log; never fetch or submit URLs.
Run after the site build: python3 tools/check_page_budget.py
"""
import argparse
import collections
import html
import io
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from build_seo import _lastmod_norm
from sitemap import NS, sitemap_urls

INITIAL_PUBLISHED = "ecd433cd86c7d06be7bed0ca5522f9e46841fefa"
DEFAULT_LIMIT = 3
MIN_UNIQUENESS = 0.4
# Bump when normalization changes: IndexNow establishes a fresh baseline once.
BODY_SIGNATURE_VERSION = 1
ROOT = Path(__file__).resolve().parent.parent


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True,
                            text=True, timeout=30)
    if result.returncode:
        raise ValueError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def published_revision(root):
    releases = publication_log(root)
    revision = releases[-1][1] if releases else INITIAL_PUBLISHED
    if not releases:
        print(f"⚠ 发布日志为空或缺失，回退到初始已发布基线 {INITIAL_PUBLISHED}。")
    return git(root, "rev-parse", f"{revision}^{{commit}}").strip()


def publication_log(root):
    """Validate every row and preserve append order for the deployed baseline."""
    ledger = root / "content/published-log.tsv"
    releases = []
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines() if ledger.exists() else [], 1):
        if not line.strip():
            continue
        try:
            stamp, revision = line.split("\t")
            published_at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if published_at.utcoffset() != timedelta(0) or not re.fullmatch(r"[0-9a-f]{40}", revision):
                raise ValueError("需要 UTC 时间和完整提交哈希")
        except ValueError as exc:
            raise ValueError(f"{ledger}:{number} 发布记录无效：{exc}") from exc
        releases.append((published_at, revision))
    return releases


def weekly_baseline(root, now):
    cutoff = now - timedelta(days=7)
    releases = publication_log(root)
    # Publication time, never commit age, determines whether URLs enter the baseline.
    releases.sort(key=lambda release: release[0])
    eligible = [release for release in releases if release[0] <= cutoff]
    revision = eligible[-1][1] if eligible else releases[0][1] if releases else INITIAL_PUBLISHED
    return git(root, "rev-parse", f"{revision}^{{commit}}").strip(), cutoff


def snapshot_urls(root, revision, origin):
    """Read both historical flat sitemaps and the current split sitemap format."""
    tree = ET.fromstring(git(root, "show", f"{revision}:sitemap.xml"))
    maps = [tree]
    if tree.tag == NS + "sitemapindex":
        maps = []
        for child in tree.findall(NS + "sitemap"):
            loc = child.findtext(NS + "loc") or ""
            name = loc.removeprefix(origin + "/")
            if not loc.startswith(origin + "/") or "/" in name or not name.endswith(".xml"):
                raise ValueError(f"Invalid historical sitemap reference: {loc}")
            maps.append(ET.fromstring(git(root, "show", f"{revision}:{name}")))
    urls = []
    for tree in maps:
        if tree.tag != NS + "urlset":
            raise ValueError("Expected a historical sitemap urlset")
        urls.extend(page.findtext(NS + "loc") or "" for page in tree.findall(NS + "url"))
    if not urls or len(urls) != len(set(urls)):
        raise ValueError("Historical sitemap page URLs are empty or duplicated")
    for url in urls:
        page_file(url, origin)
    return set(urls)


def page_file(url, origin):
    if not url.startswith(origin + "/"):
        raise ValueError(f"Invalid sitemap page URL: {url}")
    parsed = urlsplit(url)
    path = unquote(parsed.path)
    if parsed.query or parsed.fragment or any(p in (".", "..") for p in path.split("/")):
        raise ValueError(f"Invalid sitemap page URL: {url}")
    return path.lstrip("/") + "index.html" if path.endswith("/") else path.lstrip("/")


def published_pages(root, paths, revision):
    """Read blobs in one Git process; per-page `git show` makes this gate slow."""
    paths = sorted(paths)
    if not paths:
        return {}
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=root,
                            input=''.join(f"{revision}:{path}\n" for path in paths).encode(),
                            capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.decode())
    stream, pages = io.BytesIO(result.stdout), {}
    for path in paths:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError(f"{revision} 缺少 sitemap 对应的 HTML：{path}")
        pages[path] = stream.read(int(header[2])).decode("utf-8")
        if stream.read(1) != b"\n":
            raise ValueError(f"读取历史 HTML 失败：{path}")
    return pages


def tokens(source):
    """Keep the extraction/tokenization exactly aligned with uniq-reference.py."""
    lang = (re.search(r'<html[^>]*lang="([^"]+)"', source) or [None, "?"])[1]
    source = re.sub(r'<!-- sitefooter:start -->.*?<!-- sitefooter:end -->', '', source, flags=re.S)
    source = re.sub(r'<(script|style|svg|head|nav|header|footer)\b.*?</\1>', '', source, flags=re.S | re.I)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', source))
    if lang.split('-')[0] in ('ja', 'zh', 'ko', 'th'):
        return list(re.sub(r'\s+', '', text))
    return re.findall(r'\w+', text.lower())


def uniqueness(pages):
    shingles = {}
    for url, source in pages.items():
        words = tokens(source)
        shingles[url] = {tuple(words[i:i + 5]) for i in range(max(0, len(words) - 4))}
    counts = collections.Counter(shingle for page in shingles.values() for shingle in page)
    # A page with fewer than five tokens has no evidence of unique content.
    return {url: sum(counts[s] == 1 for s in page) / len(page) if page else 0.0
            for url, page in shingles.items()}


class ContentSignature(HTMLParser):
    """Join inline text; only block boundaries separate it. Keep content attributes."""
    PRESENTATION = {"class", "style", "width", "height", "align", "valign",
                    "bgcolor", "border", "cellpadding", "cellspacing", "color", "face", "size"}
    BLOCKS = {"address", "article", "aside", "blockquote", "body", "br", "caption",
              "dd", "details", "div", "dl", "dt", "fieldset", "figcaption", "figure",
              "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr",
              "li", "main", "nav", "ol", "p", "pre", "section", "summary", "table",
              "tbody", "td", "tfoot", "th", "thead", "title", "tr", "ul"}

    def __init__(self, day):
        self.day = day
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.attributes = []
        self.meta_start = None

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self.parts.append(" ")
        # This generated input caps the start date at the build day.
        # Other date limits and event targets remain editorial content.
        values = dict(attrs)
        if tag == "p":
            self.meta_start = len(self.parts) if "meta" in (values.get("class") or "").split() else None
        if (self.day is not None and tag == "input" and values.get("type") == "date"
                and values.get("name") == "desde" and values.get("max") == self.day.isoformat()):
            attrs = [(key, value) for key, value in attrs if key != "max"]
        content = tuple(sorted((key, value) for key, value in attrs
                               if key not in self.PRESENTATION and not key.startswith("data-track-")))
        if content:
            self.attributes.append((tag, content))

    def handle_endtag(self, tag):
        if tag == "p" and self.meta_start is not None:
            # Identify the generated byline by its element and full text, not
            # attribute order. Keep its publication date and all factual dates.
            text = "".join(self.parts[self.meta_start:])
            text = re.sub(r'^(\s*[^·]*?\d{4}-\d{2}-\d{2}\s*·\s*'
                          r'(?:Updated|更新|Atualizado(?: em)?|Actualizado|อัปเดต|업데이트|Aktualisiert)\s+)'
                          r'\d{4}-\d{2}-\d{2}(\s*·\s*go ka\s*)$', r'\1#\2', text)
            self.parts[self.meta_start:] = [text]
            self.meta_start = None
        if tag in self.BLOCKS:
            self.parts.append(" ")

    def handle_data(self, data):
        self.parts.append(data)

    def signature(self):
        return (re.sub(r"\s+", " ", "".join(self.parts)).strip(), tuple(self.attributes))


def body_signature(source, day):
    # Reuse daily-counter/date/footer/tracking normalization. Script changes,
    # including analytics asset version bumps, are not editorial body changes.
    source = re.sub(r'<script\b[^>]*>.*?</script\s*>', '', source, flags=re.S | re.I)
    if day is not None:
        # These are the two generated ISO-date copies in build_tools.py.
        # Limit the counter substitution to its known table row, never any
        # arbitrary paragraph whose factual date happens to be the build day.
        stamp = re.escape(day.isoformat())
        source = re.sub(r'(Numbers above were computed on )' + stamp,
                        r'\1#', source)
        source = re.sub(r'(<th>Days left in 2026</th><td>)\d+ \(as of ' + stamp + r'\)',
                        r'\1#', source)
    # _lastmod_norm masks ISO dates globally, and mask_daily also masks numbers
    # beside today's ISO date. Protect dates in both text and attributes first;
    # HTMLParser decodes them after the shared daily/footer normalization.
    source = re.sub(r'\d{4}-\d{2}-\d{2}',
                    lambda match: match[0].replace('-', '&#45;'), source)
    parser = ContentSignature(day)
    parser.feed(_lastmod_norm(source, day))
    parser.close()
    return parser.signature()


def override_limit(value, ledger, added, origin, today):
    if value is None:
        return DEFAULT_LIMIT
    if not re.fullmatch(r'\d+', value) or int(value) < DEFAULT_LIMIT:
        raise ValueError(f"ALLOW_NEW_PAGES 必须为不小于 {DEFAULT_LIMIT} 的整数。")
    limit = int(value)
    if limit == DEFAULT_LIMIT or not added:
        return limit
    if not ledger.exists():
        raise ValueError("ALLOW_NEW_PAGES 需要 docs/page-budget.md 中当天的逐网址理由。")
    approved = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) != 3 or cells[0] != today.isoformat():
            continue
        url, reason = cells[1:]
        if url.startswith("/"):
            url = origin + url
        if reason and re.search(r'\w', reason) and reason.lower() not in {"todo", "tbd", "理由", "待补", "待补充"}:
            approved.add(url)
    missing = sorted(added - approved)
    if missing:
        raise ValueError("预算放宽缺少当天日期 / 网址 / 理由记录：\n  " + "\n  ".join(missing))
    return limit


def check(root, now=None, allow=None):
    now = now or datetime.now().astimezone()
    origin = json.loads((root / "tools/site.json").read_text(encoding="utf-8"))["site"]["origin"].rstrip("/")
    published_rev = published_revision(root)
    baseline, cutoff = weekly_baseline(root, now)
    current = set(sitemap_urls(root, origin))
    weekly_added = current - snapshot_urls(root, baseline, origin)
    published = snapshot_urls(root, published_rev, origin)
    added = current - published
    limit = DEFAULT_LIMIT
    if added and len(weekly_added) > DEFAULT_LIMIT:
        limit = override_limit(allow, root / "docs/page-budget.md", added, origin, now.date())
    print(f"页面预算：已发布基线 {published_rev[:12]}，本次新增 {len(added)}；7 天已发布基线 {baseline[:12]}（截止 {cutoff.isoformat(timespec='seconds')}，无截止前发布用最早发布，记录为空用初始已发布提交），滚动新增 {len(weekly_added)} / {limit}")
    for url in sorted(weekly_added):
        print(f"  新增 {url}")

    old_pages = published_pages(root, {page_file(url, origin) for url in current & published}, published_rev)
    pages, changed = {}, set()
    for url in sorted(current):
        rel = page_file(url, origin)
        source = (root / rel).read_text(encoding="utf-8")
        if 'noindex' in source[:6000] and 'name="robots"' in source[:6000]:
            raise ValueError(f"sitemap 含 noindex 页面：{url}")
        pages[url] = source
        if url not in published:
            changed.add(url)
            continue
        old = old_pages[rel]
        if body_signature(source, None) == body_signature(old, None):
            continue
        # The HTML may have last been built before the branch's tip commit.
        stamp = git(root, "log", "-1", "--format=%cI", published_rev, "--", rel).strip()
        old_day = datetime.fromisoformat(stamp).astimezone(now.tzinfo).date()
        if body_signature(source, now.date()) != body_signature(old, old_day):
            changed.add(url)

    ratios = uniqueness(pages)
    failures = sorted(url for url in changed if ratios[url] < MIN_UNIQUENESS)
    warnings = sorted(url for url in current - changed if ratios[url] < MIN_UNIQUENESS)
    for url in warnings:
        print(f"⚠ 存量独有率 {ratios[url]:.2%} < 40%：{url}")
    for url in failures:
        print(f"✗ 新增/正文变化页面独有率 {ratios[url]:.2%} < 40%：{url}")
    over_budget = bool(added) and len(weekly_added) > limit
    if over_budget:
        print("✗ 7 天新增网址超出预算；放宽须同时设置 ALLOW_NEW_PAGES 并逐网址记录当天理由。")
    passed = not over_budget and not failures
    print(f"页面预算检查：{'通过' if passed else '失败'}；可索引 {len(current)} 页，本次新增/正文变化 {len(changed)} 页，独有率未达标 {len(failures)} 页，存量警告 {len(warnings)} 页。")
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        return 0 if check(args.root.resolve(), allow=os.environ.get("ALLOW_NEW_PAGES")) else 1
    except (ValueError, OSError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print(f"✗ 页面预算检查失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
