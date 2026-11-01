"""IndexNow tracks editorial signals and normalized body content, all offline."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import indexnow as ix


class IndexNowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = self.root / 'tools/indexnow-state.json'
        self.state.parent.mkdir()
        for name, value in [('ROOT', self.root), ('STATE', self.state), ('DRY', True), ('RECORD', False)]:
            patcher = patch.object(ix, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # Every test is offline, including simulated success/failure of submission.
        self.network = patch.object(ix.urllib.request, 'urlopen').start()
        self.addCleanup(patch.stopall)
        self.page('2026-10-30', 'A countdown', 50)

    def page(self, lastmod, desc, days):
        (self.root / 'sitemap.xml').write_text(
            f'<urlset xmlns="{ix.NS[1:-1]}"><url><loc>{ix.ORIGIN}/</loc>'
            f'<lastmod>{lastmod}</lastmod></url></urlset>')
        (self.root / 'index.html').write_text(
            f'<html><head><meta name="description" content="{desc}"></head>'
            f'<body><p><span data-n>{days}</span> days / '
            f'<span data-weeks>{days // 7} weeks</span> remaining</p></body></html>')

    def git_history(self, files=None):
        if files is None:
            files = {name: (self.root / name).read_text() for name in ['sitemap.xml', 'index.html']}

        def git(args, **kwargs):
            if args[1] == 'log':
                self.assertEqual(args[2:], ['-1', '--format=%H', '--', 'tools/indexnow-state.json'])
                output = 'abc123\n'
            else:
                name = args[2].removeprefix('abc123:')
                if name not in files:
                    raise subprocess.CalledProcessError(128, args, stderr=f'Missing {name}')
                output = files[name]
            return subprocess.CompletedProcess(args, 0, output)

        return patch.object(ix.subprocess, 'run', side_effect=git)

    def test_daily_days_and_weeks_do_not_count_as_modified(self):
        old = ix.current()
        self.page('2026-10-30', 'A countdown', 49)
        self.assertEqual(dict(ix.changes(ix.current(), old))['修改'], [])

    def test_generated_dates_and_counters_share_budget_normalization(self):
        target = self.root / 'index.html'
        before = target.read_text().replace('</body>',
            '<p class="meta" style="color:gray">Published 2026-10-01 · Updated '
            '2026-11-01 · go ka</p><p>Numbers above were computed on 2026-11-01 '
            'and update live when the page loads.</p><p>Exam: 2026-12-01.</p></body>')
        target.write_text(before)
        with patch.object(ix, 'date') as clock:
            clock.today.return_value = date(2026, 11, 1)
            old = ix.current()
            clock.today.return_value = date(2026, 11, 2)
            target.write_text(before.replace('2026-11-01', '2026-11-02').replace('>50<', '>49<'))
            self.assertEqual(dict(ix.changes(ix.current(), old))['修改'], [])
            target.write_text(target.read_text().replace('2026-12-01', '2026-12-02'))
            self.assertEqual(dict(ix.changes(ix.current(), old))['修改'], ['/'])

    def test_changed_lastmod_counts_even_when_body_is_identical(self):
        old = ix.current()
        for day in ['2026-11-01', '2026-10-29']:
            with self.subTest(day=day):
                self.page(day, 'A countdown', 50)
                self.assertEqual(dict(ix.changes(ix.current(), old))['修改'], ['/'])

    def test_description_change_without_lastmod_change_counts(self):
        old = ix.current()
        self.page('2026-10-30', 'Updated description', 50)
        self.assertEqual(dict(ix.changes(ix.current(), old))['修改'], ['/'])

    def test_second_body_edit_on_same_day_is_submitted_again(self):
        self.state.write_text(json.dumps(ix.current()))
        self.network.return_value.status = 202
        target = self.root / 'index.html'
        for fact in ('First editorial addition.', 'Second editorial addition.'):
            target.write_text(target.read_text().replace('</body>', f'<p>{fact}</p></body>'))
            with patch.object(ix, 'DRY', False), contextlib.redirect_stdout(io.StringIO()):
                ix.main()
            saved = json.loads(self.state.read_text())
            self.assertEqual(saved['/']['lastmod'], '2026-10-30')
            self.assertEqual(saved['/']['description'], 'A countdown')
            self.assertEqual(saved, ix.current())
        self.assertEqual(self.network.call_count, 2)

    def test_missing_or_old_signature_migrates_without_submission(self):
        current = ix.current()
        variants = [
            {'lastmod': current['/']['lastmod'], 'description': current['/']['description']},
            {**current['/'], 'body_signature': 'obsolete', 'body_signature_version': 0},
            {**current['/'], 'body_signature': 'obsolete', 'body_signature_version': None},
        ]
        for previous in variants:
            with self.subTest(previous=previous):
                self.state.write_text(json.dumps({'/': previous}))
                before = self.state.read_bytes()
                with contextlib.redirect_stdout(io.StringIO()):
                    ix.main()
                self.assertEqual(self.state.read_bytes(), before)
                with patch.object(ix, 'DRY', False), contextlib.redirect_stdout(io.StringIO()):
                    ix.main()
                self.assertEqual(json.loads(self.state.read_text()), current)
                self.network.assert_not_called()

    def test_signature_migration_does_not_hide_lastmod_or_description_changes(self):
        current = ix.current()
        for version in (None, 0):
            for field in ('lastmod', 'description'):
                previous = {**current['/'], 'body_signature_version': version, field: 'old'}
                with self.subTest(version=version, field=field):
                    self.assertEqual(dict(ix.changes(current, {'/': previous}))['修改'], ['/'])

    def test_description_parsing_ignores_attribute_order_and_entity_encoding(self):
        self.assertEqual(ix.description("<META content='Days &amp; weeks' NAME='description'>"),
                         ix.description('<meta name="description" content="Days &#38; weeks">'))

    def test_legacy_hash_uses_historical_lastmod_not_normalization(self):
        with self.git_history():
            for day in ['2026-10-29', '2026-10-30', '2026-11-01']:
                with self.subTest(day=day):
                    self.page(day, 'A countdown', 49)
                    expected = [] if day == '2026-10-30' else ['/']
                    self.assertEqual(dict(ix.changes(ix.current(), {'/': 'obsolete-hash'}))['修改'], expected)

    def test_legacy_description_change_is_detected(self):
        with self.git_history():
            self.page('2026-10-30', 'Updated description', 50)
            self.assertEqual(dict(ix.changes(ix.current(), {'/': 'old-hash'}))['修改'], ['/'])

    def test_legacy_lastmod_correction_before_record_commit_is_detected(self):
        self.page('2026-10-18', 'A countdown', 50)
        historical_sitemap = (self.root / 'sitemap.xml').read_text().replace('2026-10-18', '2026-10-25')

        with self.git_history({'sitemap.xml': historical_sitemap,
                               'index.html': (self.root / 'index.html').read_text()}):
            self.assertEqual(dict(ix.changes(ix.current(), {'/': 'old-hash'}))['修改'], ['/'])

    def test_legacy_snapshot_reads_sitemap_and_description_from_record_commit(self):
        with self.git_history():
            self.page('2026-11-01', 'Updated description', 49)
            self.assertEqual(ix.legacy_snapshot(['/']),
                             {'/': {'lastmod': '2026-10-30', 'description': 'A countdown'}})

    def test_legacy_split_sitemap_compares_each_page_and_ignores_index_dates(self):
        sitemap = (self.root / 'sitemap.xml').read_text().replace('2026-10-30', '2026-10-25')
        files = {
            'sitemap.xml': f'<sitemapindex xmlns="{ix.NS[1:-1]}">'
                          f'<sitemap><loc>{ix.ORIGIN}/sitemap-first.xml</loc>'
                          '<lastmod>2026-11-01</lastmod></sitemap>'
                          f'<sitemap><loc>{ix.ORIGIN}/sitemap-second.xml</loc></sitemap></sitemapindex>',
            'sitemap-first.xml': sitemap,
            'sitemap-second.xml': sitemap.replace(f'{ix.ORIGIN}/</loc>', f'{ix.ORIGIN}/same/</loc>'),
            'index.html': (self.root / 'index.html').read_text(),
            'same/index.html': (self.root / 'index.html').read_text(),
        }
        cur = {'/': {'lastmod': '2026-10-18', 'description': 'A countdown'},
               '/same/': {'lastmod': '2026-10-25', 'description': 'A countdown'}}
        with self.git_history(files):
            self.assertEqual(dict(ix.changes(cur, {'/': 'old-hash', '/same/': 'old-hash'}))['修改'], ['/'])

    def test_partial_legacy_record_preserves_its_existing_fields(self):
        with self.git_history():
            self.page('2026-10-18', 'A countdown', 49)
            old = {'/': {'lastmod': '2026-10-18'}}
            self.assertEqual(dict(ix.changes(ix.current(), old))['修改'], [])
            self.page('2026-10-30', 'Updated description', 49)
            old = {'/': {'description': 'Updated description'}}
            self.assertEqual(dict(ix.changes(ix.current(), old))['修改'], [])

    def test_invalid_or_missing_historical_sitemaps_stop_migration(self):
        sitemap = (self.root / 'sitemap.xml').read_text()
        index = f'<sitemapindex xmlns="{ix.NS[1:-1]}"><sitemap><loc>{{}}</loc></sitemap></sitemapindex>'
        cases = [
            {},
            {'sitemap.xml': '<broken'},
            {'sitemap.xml': '<unsupported/>'},
            {'sitemap.xml': sitemap.replace(f'{ix.ORIGIN}/</loc>', f'{ix.ORIGIN}/other/</loc>')},
            {'sitemap.xml': sitemap.replace('</urlset>', sitemap[sitemap.index('<url>'):])},
            {'sitemap.xml': index.format(f'{ix.ORIGIN}/missing.xml')},
            {'sitemap.xml': index.format('https://example.invalid/sitemap.xml')},
            {'sitemap.xml': index.format(f'{ix.ORIGIN}/../sitemap.xml')},
        ]
        for files in cases:
            with self.subTest(files=files), self.git_history(files):
                with self.assertRaisesRegex(RuntimeError, '无法核实旧 IndexNow'):
                    ix.changes(ix.current(), {'/': 'old-hash'})

    def test_missing_git_executable_is_reported_as_unavailable_history(self):
        with patch.object(ix.subprocess, 'run', side_effect=FileNotFoundError('git')):
            with self.assertRaisesRegex(RuntimeError, '无法核实旧 IndexNow'):
                ix.changes(ix.current(), {'/': 'old-hash'})

    def test_missing_legacy_history_stops_instead_of_flagging_every_page(self):
        with patch.object(ix.subprocess, 'run', return_value=subprocess.CompletedProcess('git', 0, '')):
            with self.assertRaisesRegex(RuntimeError, '无法核实旧 IndexNow'):
                ix.changes(ix.current(), {'/': 'old-hash'})

    def test_additions_and_deletions_are_unchanged(self):
        self.assertEqual(dict(ix.changes(ix.current(), {'/removed/': 'old-hash'})),
                         {'新增': ['/'], '修改': [], '删除': ['/removed/']})

    def test_sitemap_index_reads_page_lastmod_not_index_lastmod(self):
        (self.root / 'sitemap.xml').rename(self.root / 'sitemap-pages.xml')
        (self.root / 'sitemap.xml').write_text(
            f'<sitemapindex xmlns="{ix.NS[1:-1]}"><sitemap>'
            f'<loc>{ix.ORIGIN}/sitemap-pages.xml</loc><lastmod>2026-11-01</lastmod>'
            '</sitemap></sitemapindex>')
        self.assertEqual(ix.current()['/']['lastmod'], '2026-10-30')

    def test_dry_run_does_not_submit_or_rewrite_legacy_state(self):
        self.state.write_text('{"/": "old-hash"}\n')
        before = self.state.read_bytes()
        with self.git_history(), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.page('2026-10-18', 'A countdown', 49)
            ix.main()
        self.assertIn('新增 0 · 修改 1 · 删除 0', output.getvalue())
        self.assertEqual(self.state.read_bytes(), before)
        self.network.assert_not_called()

    def test_dry_run_history_failure_does_not_submit_or_rewrite_state(self):
        self.state.write_text('{"/": "old-hash"}\n')
        before = self.state.read_bytes()
        with self.git_history({}):
            with self.assertRaisesRegex(RuntimeError, '无法核实旧 IndexNow'):
                ix.main()
        self.assertEqual(self.state.read_bytes(), before)
        self.network.assert_not_called()

    def test_successful_submission_records_lastmod_and_description(self):
        self.state.write_text('{}')
        self.network.return_value.status = 202
        with patch.object(ix, 'DRY', False), contextlib.redirect_stdout(io.StringIO()):
            ix.main()
        self.assertEqual(json.loads(self.state.read_text()),
                         ix.current())
        self.network.assert_called_once()

    def test_failed_submission_preserves_old_state(self):
        self.state.write_text('{}')
        self.network.side_effect = OSError('offline')
        with patch.object(ix, 'DRY', False), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                ix.main()
        self.assertEqual(self.state.read_text(), '{}')


if __name__ == '__main__':
    unittest.main()
