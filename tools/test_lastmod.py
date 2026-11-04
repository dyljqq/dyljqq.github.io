"""A Git read failure must not invent a new editorial modification date."""
import subprocess
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import build_seo as seo


class LastmodTests(unittest.TestCase):
    def test_history_failure_stops_instead_of_returning_today(self):
        for error in (subprocess.TimeoutExpired('git', 600),
                      subprocess.CalledProcessError(128, 'git')):
            with self.subTest(error=type(error).__name__):
                with patch.object(seo.subprocess, 'run', side_effect=error) as run:
                    with self.assertRaisesRegex(RuntimeError, '无法核实 lastmod'):
                        seo.git_lastmod(seo.ROOT / 'example/index.html', '<body>Existing content</body>')
                    self.assertEqual(run.call_count, 2 if isinstance(error, subprocess.TimeoutExpired) else 1)

    def test_new_page_without_history_uses_today(self):
        with patch.object(seo.subprocess, 'run', return_value=subprocess.CompletedProcess('git', 0, '')):
            self.assertEqual(seo.git_lastmod(seo.ROOT / 'new/index.html', '<body>New content</body>'),
                             date.today().isoformat())


class RestoredPageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'page.html'
        self.source = '<title>Page</title><body>Existing editorial content</body>'
        self.git('init', '-q')
        self.path.write_text(self.source)
        self.commit('2026-10-20')
        self.path.unlink()
        self.commit('2026-10-21')
        self.path.write_text(self.source)
        self.root_patch = patch.object(seo, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def git(self, *args, env=None):
        return subprocess.run(['git', *args], cwd=self.root, env=env, check=True,
                              capture_output=True, text=True)

    def commit(self, day):
        self.git('add', '.')
        env = dict(os.environ, GIT_AUTHOR_NAME='Test', GIT_COMMITTER_NAME='Test',
                   GIT_AUTHOR_EMAIL='test@example.invalid', GIT_COMMITTER_EMAIL='test@example.invalid',
                   GIT_AUTHOR_DATE=day + 'T12:00:00+00:00', GIT_COMMITTER_DATE=day + 'T12:00:00+00:00')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture', env=env)

    def test_uncommitted_restore_uses_today(self):
        self.assertEqual(seo.git_lastmod(self.path), date.today().isoformat())

    def test_committed_restore_uses_restoration_date_not_original_date(self):
        self.commit('2026-10-22')
        self.assertEqual(seo.git_lastmod(self.path), '2026-10-22')

    def test_title_only_change_preserves_last_body_change_date(self):
        self.commit('2026-10-22')
        self.path.write_text(self.source.replace('<title>Page</title>', '<title>New title</title>'))
        self.commit('2026-10-23')
        self.assertEqual(seo.git_lastmod(self.path), '2026-10-22')

    def test_git_show_timeout_retries_once_and_preserves_lastmod(self):
        self.commit('2026-10-22')
        real_run = subprocess.run
        show_calls = []

        def timeout_once(args, **kwargs):
            self.assertEqual(kwargs['timeout'], 600)
            if args[:2] == ['git', 'show']:
                show_calls.append(args)
                if len(show_calls) == 1:
                    raise subprocess.TimeoutExpired(args, 600)
            return real_run(args, **kwargs)

        with patch.object(seo.subprocess, 'run', side_effect=timeout_once):
            self.assertEqual(seo.git_lastmod(self.path), '2026-10-22')
        self.assertEqual(show_calls[0], show_calls[1])

    def test_existing_blob_read_failure_still_stops_build(self):
        self.commit('2026-10-22')
        real_run = subprocess.run

        def fail_show(args, **kwargs):
            if args[:2] == ['git', 'show']:
                return subprocess.CompletedProcess(args, 128, '', 'fatal: cannot read object')
            return real_run(args, **kwargs)

        with patch.object(seo.subprocess, 'run', side_effect=fail_show):
            with self.assertRaisesRegex(RuntimeError, '无法核实 lastmod'):
                seo.git_lastmod(self.path)


if __name__ == '__main__':
    unittest.main()
