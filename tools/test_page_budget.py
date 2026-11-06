"""Release-budget checks use local Git history and never contact the network."""
import contextlib
import io
import json
import os
import runpy
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import check_page_budget as budget

ORIGIN = "https://beforego.art"
NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
COPY = "one two three four five six seven eight nine ten eleven twelve"


def page(text=COPY, lang="en", script="old.js"):
    return (f'<html lang="{lang}"><head><title>Example</title><script src="{script}"></script></head>'
            f'<body><main><p>{text}</p></main><script>track("{script}")</script></body></html>')


class PageBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tools").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "tools/site.json").write_text(json.dumps({"site": {"origin": ORIGIN}}))
        self.run_git("init", "-q")
        self.write_page("/a/")
        self.write_page("/b/")
        self.write_map(["/a/", "/b/"])
        self.commit("2026-10-24T12:00:00+00:00")
        self.old = self.run_git("rev-parse", "HEAD").strip()
        (self.root / "content").mkdir()
        self.log = self.root / "content/published-log.tsv"
        self.log.write_text(f"2026-10-24T12:00:00Z\t{self.old}\n")
        self.write_map(["/a/", "/b/"], split=True)
        self.commit("2026-10-31T12:00:00+00:00")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.record_publication()
        self.run_git("tag", "-f", "published", "HEAD")

    def record_publication(self):
        revision = self.run_git("rev-parse", "HEAD").strip()
        with self.log.open("a") as ledger:
            ledger.write(f"2026-10-31T13:00:00Z\t{revision}\n")

    def run_git(self, *args, env=None):
        return subprocess.run(["git", *args], cwd=self.root, env=env, check=True,
                              capture_output=True, text=True).stdout

    def commit(self, stamp):
        self.run_git("add", ".")
        env = dict(os.environ, GIT_AUTHOR_NAME="Budget test", GIT_COMMITTER_NAME="Budget test",
                   GIT_AUTHOR_EMAIL="test@example.invalid", GIT_COMMITTER_EMAIL="test@example.invalid",
                   GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        self.run_git("-c", "commit.gpgsign=false", "commit", "-qm", "fixture", env=env)

    def write_page(self, path, source=None):
        target = self.root / budget.page_file(ORIGIN + path, ORIGIN)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source if source is not None else page(), encoding="utf-8")

    def write_map(self, paths, split=False):
        xml = f'<urlset xmlns="{budget.NS[1:-1]}">' + ''.join(
            f'<url><loc>{ORIGIN}{path}</loc></url>' for path in paths) + '</urlset>'
        if split:
            (self.root / "sitemap-pages.xml").write_text(xml)
            xml = (f'<sitemapindex xmlns="{budget.NS[1:-1]}"><sitemap>'
                   f'<loc>{ORIGIN}/sitemap-pages.xml</loc></sitemap></sitemapindex>')
        (self.root / "sitemap.xml").write_text(xml)

    def check(self, allow=None, now=NOW):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            passed = budget.check(self.root, now, allow)
        return passed, output.getvalue()

    def test_seven_day_published_history_supports_flat_and_split_maps(self):
        revision, cutoff = budget.weekly_baseline(self.root, NOW)
        self.assertEqual(revision, self.old)
        self.assertEqual(cutoff.isoformat(), "2026-10-25T12:00:00+00:00")
        expected = {ORIGIN + "/a/", ORIGIN + "/b/"}
        self.assertEqual(budget.snapshot_urls(self.root, revision, ORIGIN), expected)
        self.assertEqual(budget.snapshot_urls(self.root, "origin/main", ORIGIN), expected)
        revision, _ = budget.weekly_baseline(self.root, datetime(2026, 10, 25, tzinfo=timezone.utc))
        self.assertEqual(revision, self.old)

    def test_four_pages_committed_eight_days_ago_but_never_published_fail(self):
        published = budget.published_revision(self.root)
        added = [f"/unpublished{i}/" for i in range(4)]
        for index, path in enumerate(added):
            self.write_page(path, page(' '.join(f"unique{index}word{n}" for n in range(20))))
        self.write_map(["/a/", "/b/", *added])
        self.commit("2026-10-24T12:00:00+00:00")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        passed, output = self.check()
        self.assertFalse(passed)
        self.assertEqual(budget.published_revision(self.root), published)
        self.assertEqual(budget.weekly_baseline(self.root, NOW)[0], self.old)
        self.assertIn("本次新增 4", output)
        self.assertIn("滚动新增 4 / 3", output)
        self.assertIn("独有率未达标 0 页", output)

    def test_publication_time_and_inclusive_cutoff_select_latest_release(self):
        latest = self.run_git("rev-parse", "HEAD").strip()
        # Out-of-order rows and an old commit released recently must not change the cutoff.
        self.log.write_text(f"2026-10-31T12:00:00Z\t{self.old}\n"
                            f"2026-10-25T12:00:00Z\t{latest}\n"
                            f"2026-10-24T12:00:00Z\t{self.old}\n")
        self.assertEqual(budget.weekly_baseline(self.root, NOW)[0], latest)

    def test_no_release_before_cutoff_uses_earliest_publication(self):
        latest = self.run_git("rev-parse", "HEAD").strip()
        self.log.write_text(f"2026-10-31T12:00:00Z\t{self.old}\n"
                            f"2026-10-30T12:00:00Z\t{latest}\n")
        self.assertEqual(budget.weekly_baseline(self.root, NOW)[0], latest)

    def test_empty_or_missing_log_uses_fixed_initial_published_commit(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                if missing:
                    self.log.unlink()
                else:
                    self.log.write_text("")
                with patch.object(budget, "INITIAL_PUBLISHED", self.old):
                    self.assertEqual(budget.weekly_baseline(self.root, NOW)[0], self.old)
                    self.assertEqual(budget.published_revision(self.root), self.old)

    def test_invalid_publication_records_fail_closed(self):
        for line in (f"2026-10-24T12:00:00\t{self.old}",
                     f"2026-10-24T12:00:00+09:00\t{self.old}",
                     "2026-10-24T12:00:00Z\tHEAD", "invalid"):
            with self.subTest(line=line):
                self.log.write_text(line)
                with self.assertRaisesRegex(ValueError, "发布记录无效"):
                    budget.weekly_baseline(self.root, NOW)
                with self.assertRaisesRegex(ValueError, "发布记录无效"):
                    budget.published_revision(self.root)

    def test_young_repository_with_no_new_urls_passes(self):
        # On Nov 1 this repository has existed for less than seven days.
        self.run_git("checkout", "--orphan", "young")
        self.commit("2026-10-30T12:00:00+00:00")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.record_publication()
        passed, output = self.check()
        self.assertTrue(passed)
        self.assertIn("本次新增 0", output)
        self.assertIn("滚动新增 0 / 3", output)

    def test_missing_tag_keeps_logged_commit_even_after_main_moves(self):
        initial = budget.published_revision(self.root)
        self.run_git("tag", "-d", "published")
        self.write_page("/new/")
        self.write_map(["/a/", "/b/", "/new/"])
        self.commit("2026-11-01T10:00:00+00:00")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.run_git("update-ref", "refs/heads/main", "HEAD")
        with patch.object(budget, "INITIAL_PUBLISHED", initial):
            passed, output = self.check()
        self.assertFalse(passed)
        self.assertIn("本次新增 1", output)
        self.assertNotIn("回退", output)

    def test_latest_log_row_is_published_without_a_tag(self):
        latest = self.run_git("rev-parse", "HEAD").strip()
        self.log.write_text(f"2026-10-31T12:00:00Z\t{self.old}\n"
                            f"2026-10-30T12:00:00Z\t{latest}\n")
        self.run_git("tag", "-d", "published")
        self.assertEqual(budget.published_revision(self.root), latest)

    def test_conflicting_tag_cannot_override_latest_log_row(self):
        latest = self.run_git("rev-parse", "HEAD").strip()
        self.log.write_text(f"2026-10-24T12:00:00Z\t{self.old}\n"
                            f"2026-10-31T12:00:00Z\t{latest}\n")
        self.run_git("tag", "-f", "published", self.old)
        self.assertEqual(budget.published_revision(self.root), latest)

    def test_merging_into_main_keeps_unpublished_urls_and_body_changes(self):
        published = budget.published_revision(self.root)
        self.run_git("checkout", "-B", "main")
        self.run_git("checkout", "-b", "draft")
        self.write_page("/new/")
        self.write_page("/a/", page(COPY + "."))
        self.write_map(["/a/", "/b/", "/new/"])
        self.commit("2026-11-01T10:00:00+00:00")
        self.run_git("checkout", "main")
        self.run_git("merge", "--ff-only", "draft")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        passed, output = self.check()
        self.assertFalse(passed)
        self.assertEqual(budget.published_revision(self.root), published)
        self.assertIn("本次新增 1", output)
        self.assertIn("本次新增/正文变化 2 页", output)

    def test_inline_formatting_keeps_text_and_word_boundaries(self):
        for tag in ("b", "strong", "em", "a", "span", "i", "small"):
            with self.subTest(tag=tag):
                changed = COPY.replace("two", f'<{tag} class="accent" data-track-id="word">two</{tag}>')
                self.write_page("/a/", page(changed))
                passed, output = self.check()
                self.assertTrue(passed)
                self.assertIn("本次新增/正文变化 0 页", output)
                self.assertEqual(budget.body_signature(page("something"), None),
                                 budget.body_signature(page(f"some<{tag}>thing</{tag}>"), None))
        self.assertNotEqual(budget.body_signature(page("something"), None),
                            budget.body_signature(page("some<div>thing</div>"), None))

    def test_shared_header_navigation_does_not_change_editorial_content(self):
        def with_header(href):
            return page().replace('<body>', '<body><header class="wrap top"><nav>'
                                  f'<a href="{href}">Support</a></nav></header>')
        before = with_header('mailto:qinqiangji@gmail.com')
        after = with_header('/support/')
        self.assertEqual(budget.body_signature(before, None), budget.body_signature(after, None))
        self.assertEqual(budget._lastmod_norm(before), budget._lastmod_norm(after))
        for wrapper in ('header', 'nav', 'p'):
            before = page(f'<{wrapper}><a href="/old/">Read more</a></{wrapper}>')
            after = before.replace('/old/', '/new/')
            self.assertNotEqual(budget.body_signature(before, None), budget.body_signature(after, None))

    def test_unchanged_pages_on_november_2_and_3(self):
        # The persisted build remains unchanged even when the check runs later.
        source = page('<b data-n>10</b>On October 31, 2026, there were 10 days. The counter recalculates.')
        self.write_page("/a/", source)
        self.write_page("/b/", source)
        self.commit("2026-10-31T13:00:00+00:00")
        self.record_publication()
        for day in (2, 3):
            with self.subTest(day=day):
                passed, output = self.check(now=NOW.replace(day=day))
                self.assertTrue(passed)
                self.assertIn("本次新增/正文变化 0 页", output)
                # A rebuild changes only daily counters/copy, plus presentation.
                changed = source.replace('data-n>10', f'data-n>{10-day}').replace(
                    'October 31, 2026, there were 10', f'November {day}, 2026, there were {10-day}')
                self.write_page("/a/", changed)
                passed, output = self.check(now=NOW.replace(day=day))
                self.assertTrue(passed)
                self.assertIn("本次新增/正文变化 0 页", output)
                self.write_page("/a/", source)

    def test_rolling_over_budget_only_blocks_when_this_run_adds_urls(self):
        added = [f"/new{i}/" for i in range(5)]
        for i, path in enumerate(added):
            self.write_page(path, page(' '.join(f"word{i}unique{n}" for n in range(20))))
        self.write_map(["/a/", "/b/", *added[:4]])
        self.commit("2026-10-31T13:00:00+00:00")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.record_publication()
        passed, output = self.check()
        self.assertTrue(passed)
        self.assertIn("滚动新增 4 / 3", output)
        self.write_map(["/a/", "/b/", *added])
        passed, output = self.check()
        self.assertFalse(passed)
        self.assertIn("本次新增 1", output)
        self.assertIn("滚动新增 5 / 3", output)

    def test_one_new_url_within_rolling_budget_passes(self):
        self.write_page("/new/", page("independent useful original practical reliable clear local complete readable helpful"))
        self.write_map(["/a/", "/b/", "/new/"])
        passed, output = self.check()
        self.assertTrue(passed)
        self.assertIn("本次新增 1", output)
        self.assertIn("滚动新增 1 / 3", output)

    def test_existing_duplicates_warn_and_analytics_changes_do_not_gate(self):
        self.write_page("/a/", page(script="firebase-web-v2.js"))
        passed, output = self.check()
        self.assertTrue(passed)
        self.assertIn("存量警告 2 页", output)
        self.assertIn("本次新增/正文变化 0 页", output)

    def test_body_edit_or_new_duplicate_fails(self):
        self.write_page("/a/", page(COPY + "."))
        passed, output = self.check()
        self.assertFalse(passed)
        self.assertIn("独有率未达标 1 页", output)
        self.write_page("/a/")
        self.write_page("/new/")
        self.write_map(["/a/", "/b/", "/new/"])
        passed, output = self.check()
        self.assertFalse(passed)
        self.assertIn("新增/正文变化页面独有率 0.00%", output)

    def test_thai_hub_presentation_only_edits_do_not_gate(self):
        source = (budget.ROOT / "tools/th/index.html").read_text(encoding="utf-8")
        self.write_page("/tools/th/", source)
        self.write_page("/duplicate/", source)
        self.write_map(["/tools/th/", "/duplicate/"])
        self.commit("2026-10-31T13:00:00+00:00")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.record_publication()
        changed = source.replace('class="', 'class="layout-v2 ').replace('<main ', '<main style="padding:2rem" ')
        self.assertNotEqual(source, changed)
        self.write_page("/tools/th/", changed)
        passed, output = self.check()
        self.assertTrue(passed)
        self.assertIn("本次新增/正文变化 0 页", output)
        self.assertIn("存量警告 2 页", output)

    def test_content_attributes_remain_in_signature(self):
        for attr in ('href', 'src', 'alt', 'title', 'aria-label', 'value', 'data-date'):
            with self.subTest(attr=attr):
                self.assertNotEqual(budget.body_signature(page(f'<a {attr}="before">text</a>'), None),
                                    budget.body_signature(page(f'<a {attr}="after">text</a>'), None))
        self.assertEqual(budget.body_signature(page('<p class="old" style="color:red">text</p>'), None),
                         budget.body_signature(page('<p style="color:blue" class="new">text</p>'), None))
        for attr in ('href', 'src', 'alt', 'title', 'data-date'):
            with self.subTest(date_attribute=attr):
                self.assertNotEqual(budget.body_signature(page(f'<a {attr}="/2026-12-25/">text</a>'), None),
                                    budget.body_signature(page(f'<a {attr}="/2026-12-31/">text</a>'), None))

    def test_four_weekly_urls_require_override_and_each_current_dated_reason(self):
        added = ["/c/", "/c/ja/", "/c/de/", "/c/zh/"]
        for index, path in enumerate(added):
            self.write_page(path, page(' '.join(f"unique{index}word{n}" for n in range(20))))
        # Count pages already released in this week, even though not new this run.
        self.write_map(["/a/", "/b/", added[0]])
        self.commit("2026-10-31T13:00:00+00:00")
        self.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.record_publication()
        self.write_map(["/a/", "/b/", *added])
        passed, output = self.check()
        self.assertFalse(passed)
        self.assertIn("新增 4 / 3", output)
        ledger = self.root / "docs/page-budget.md"
        with self.assertRaisesRegex(ValueError, "逐网址理由"):
            self.check("4")
        ledger.write_text('\n'.join(f"| 2026-10-31 | {path} | Independent task |" for path in added))
        with self.assertRaisesRegex(ValueError, "缺少当天"):
            self.check("4")
        ledger.write_text('\n'.join(f"| 2026-11-01 | {path} | Independent task |" for path in added[1:-1]))
        with self.assertRaisesRegex(ValueError, "/c/zh/"):
            self.check("4")
        with ledger.open("a") as target:
            target.write(f"\n| 2026-11-01 | {ORIGIN}{added[-1]} | 独立用户任务和核验理由 |\n")
        passed, output = self.check("4")
        self.assertTrue(passed)
        self.assertIn("新增 4 / 4", output)
        self.assertIn("本次新增/正文变化 3 页", output)

    def test_bad_override_and_empty_or_placeholder_reasons_fail(self):
        added = {ORIGIN + "/new/"}
        ledger = self.root / "docs/page-budget.md"
        for value in ("", "-1", "2", "4.5", "four"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                budget.override_limit(value, ledger, added, ORIGIN, NOW.date())
        for reason in ("", "---", "TODO", "待补充"):
            ledger.write_text(f"| 2026-11-01 | /new/ | {reason} |")
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                budget.override_limit("4", ledger, added, ORIGIN, NOW.date())

    def test_reference_tokens_use_shingle_sets_and_cjk_characters(self):
        self.assertEqual(budget.tokens(page("甲 乙 丙 丁 戊 己", lang="zh-Hant")), list("甲乙丙丁戊己"))
        source = page("ONE two three four five &amp; six")
        self.assertEqual(budget.tokens(source), ["one", "two", "three", "four", "five", "six"])
        ratios = budget.uniqueness({"a": page("one two three four five six"),
                                    "b": page("one two three four five seven"),
                                    "short": page("too short")})
        self.assertEqual(ratios, {"a": .5, "b": .5, "short": 0})
        repeated = page("one two three four five one two three four five")
        self.assertEqual(budget.uniqueness({"a": repeated, "b": repeated}), {"a": 0, "b": 0})

    def test_daily_counters_and_footer_are_not_body_edits(self):
        before = page('<b data-n>10</b>On October 20, 2026, there were 10 days. The counter recalculates.')
        after = page('<b data-n>9</b>On October 21, 2026, there were 9 days. The counter recalculates.')
        after = after.replace('</body>', '<footer>new global footer</footer></body>')
        self.assertEqual(budget.body_signature(before, date(2026, 10, 20)),
                         budget.body_signature(after, date(2026, 10, 21)))

    def test_body_iso_facts_remain_content_even_on_the_build_day(self):
        for text in ("The exam is on 2026-11-01.",
                     '<b data-n>7</b>The exam is on 2026-11-01; bring 2 pencils.',
                     '<p class="meta">Source checked 2026-11-01.</p>',
                     '<p class="meta">Published 2026-11-01 · Updated 2026-10-31 · go ka</p>'):
            before = page(text)
            after = page(text.replace("2026-11-01", "2026-11-02"))
            with self.subTest(text=text):
                self.assertNotEqual(budget.body_signature(before, None), budget.body_signature(after, None))
                self.assertNotEqual(budget.body_signature(before, date(2026, 11, 1)),
                                    budget.body_signature(after, date(2026, 11, 2)))

    def test_generated_update_dates_and_daily_iso_counts_stay_equal(self):
        for label in ("Updated", "更新", "Atualizado"):
            before = page(f'<p class="meta meta-top">Published 2026-10-01 · {label} 2026-11-01 · go ka</p>'
                          '<div><span data-n>7</span><small data-unit>days</small></div>'
                          '<p class="meta">Numbers above were computed on 2026-11-01 and update live when the page loads.</p>'
                          '<table><tr><th>Days left in 2026</th><td>61 (as of 2026-11-01)</td></tr></table>')
            after = before.replace("2026-11-01", "2026-11-02").replace("data-n>7", "data-n>6").replace("61 (as of", "60 (as of")
            before = before.replace('</head>', '<script type="application/ld+json">{"dateModified":"2026-11-01"}</script></head>')
            after = after.replace('</head>', '<script type="application/ld+json">{"dateModified":"2026-11-02"}</script></head>')
            with self.subTest(label=label):
                self.assertEqual(budget.body_signature(before, date(2026, 11, 1)),
                                 budget.body_signature(after, date(2026, 11, 2)))

    def test_november_2_and_3_optional_week_summary_is_not_a_body_edit(self):
        before = page('<div data-date="2026-11-08"><span data-n>7</span>'
                      '<small data-unit>days</small></div><p class="count-sub">'
                      'Sunday, 8 November 2026 · <span data-weeks>1 week</span></p>')
        for day in (2, 3):
            after = before.replace('data-n>7', f'data-n>{8-day}').replace(
                ' · <span data-weeks>1 week</span>', '')
            with self.subTest(day=day):
                self.assertEqual(budget.body_signature(before, date(2026, 11, 1)),
                                 budget.body_signature(after, date(2026, 11, day)))
                self.assertNotEqual(budget.body_signature(before, date(2026, 11, 1)),
                                    budget.body_signature(after.replace('2026-11-08', '2026-11-09'),
                                                          date(2026, 11, day)))

    def test_generated_byline_ignores_reordered_attributes(self):
        for label in ("Updated", "更新"):
            before = page(f'<p class="meta meta-top" id="byline">Published 2026-10-01 · '
                          f'{label} 2026-11-01 · go ka</p>')
            after = before.replace('class="meta meta-top" id="byline"',
                                   'id="byline" class="meta-top meta"').replace(
                                       '2026-11-01', '2026-11-02')
            with self.subTest(label=label):
                self.assertEqual(budget.body_signature(before, None), budget.body_signature(after, None))
                self.assertEqual(budget.body_signature(before, date(2026, 11, 1)),
                                 budget.body_signature(after, date(2026, 11, 2)))

    def test_generated_byline_ignores_added_style(self):
        for label in ("Updated", "更新"):
            before = page(f'<p class="meta meta-top">Published 2026-10-01 · '
                          f'{label} 2026-11-01 · go ka</p>')
            after = before.replace('class="meta meta-top"',
                                   'class="meta meta-top" style="color:gray"').replace(
                                       '2026-11-01', '2026-11-02')
            with self.subTest(label=label):
                self.assertEqual(budget.body_signature(before, None), budget.body_signature(after, None))
                self.assertEqual(budget.body_signature(before, date(2026, 11, 1)),
                                 budget.body_signature(after, date(2026, 11, 2)))

    def test_styled_meta_keeps_publication_and_source_fact_dates(self):
        before = page('<p style="color:gray" class="meta">Published 2026-10-01 · Updated '
                      '2026-11-01 · go ka</p><p style="color:gray" class="meta">'
                      'Source checked 2026-11-01; exam 2026-12-01.</p>')
        for stamp in ('2026-10-01', 'Source checked 2026-11-01', '2026-12-01'):
            with self.subTest(stamp=stamp):
                after = before.replace(stamp, stamp[:-2] + '02')
                self.assertNotEqual(budget.body_signature(before, date(2026, 11, 1)),
                                    budget.body_signature(after, date(2026, 11, 2)))

    def test_fixed_date_input_limits_remain_content(self):
        for name in ("desde", "event"):
            before = page(f'<input type="date" name="{name}" max="2026-12-01">')
            after = before.replace('2026-12-01', '2026-12-02')
            self.assertNotEqual(budget.body_signature(before, date(2026, 11, 1)),
                                budget.body_signature(after, date(2026, 11, 2)))

    def test_actual_generated_pages_stay_stable_on_november_2_and_3(self):
        paths = {"/tools/days-until-diwali/", "/tools/pt-br/dias-para-o-enem-2026/",
                 "/tools/pt-br/contador-de-dias-de-namoro/", "/tools/ja/kyotsu-test-2027/"}
        snapshots = {}
        for day in (1, 2, 3):
            class BuildDate(date):
                @classmethod
                def today(cls):
                    return cls(2026, 11, day)
            with patch("datetime.date", BuildDate):
                generated = runpy.run_path(str(budget.ROOT / "tools/build_tools.py"))
                snapshots[day] = {pg["path"]: generated["shell"](pg, pg["body"])
                                  for pg in generated["PAGES"] if pg["path"] in paths}
            self.assertEqual(set(snapshots[day]), paths)
        for path in paths:
            for day in (2, 3):
                with self.subTest(path=path, day=day):
                    self.assertEqual(budget.body_signature(snapshots[1][path], date(2026, 11, 1)),
                                     budget.body_signature(snapshots[day][path], date(2026, 11, day)))
                    self.assertEqual(budget._lastmod_norm(snapshots[1][path], date(2026, 11, 1)),
                                     budget._lastmod_norm(snapshots[day][path], date(2026, 11, day)))

    def test_unsafe_page_paths_are_rejected(self):
        for url in ("https://other.invalid/a/", ORIGIN + "/../outside/",
                    ORIGIN + "/%2e%2e/outside/", ORIGIN + "/a/?q=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                budget.page_file(url, ORIGIN)


if __name__ == "__main__":
    unittest.main()
