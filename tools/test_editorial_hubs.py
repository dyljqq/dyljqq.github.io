"""Editorial comparison pages can belong to a hub without endorsing one app."""
import unittest
import json
import re
import xml.etree.ElementTree as ET
import build_tools
from sitemap import NS


class EditorialHubTests(unittest.TestCase):
    def test_comparison_without_app_renders_in_korean_hub(self):
        page = build_tools.hub_page('ko')
        self.assertIn('/tools/ko/yeohaeng-iljeong-aep/', page['body'])
        self.assertIn('트리플 대체 앱 비교', page['body'])

    def test_comparison_source_dates_match_editorial_update(self):
        for page in (build_tools.best_page(), build_tools.best_page_pt()):
            with self.subTest(path=page['path']):
                self.assertEqual(page['updated'], '2026-11-01')
                source = build_tools.shell(page, page['body'])
                self.assertIn(f"{build_tools.ts(page['lang'], 'updated')} 2026-11-01 · go ka", source)

    def test_built_comparison_dates_agree_with_sitemap(self):
        root = build_tools.ROOT
        tree = ET.parse(root / 'sitemap-tools.xml')
        dates = {node.findtext(NS + 'loc'): node.findtext(NS + 'lastmod')
                 for node in tree.findall(NS + 'url')}
        for page in (build_tools.best_page(), build_tools.best_page_pt()):
            with self.subTest(path=page['path']):
                source = (root / page['path'].strip('/') / 'index.html').read_text()
                label = re.escape(build_tools.ts(page['lang'], 'updated'))
                visible = re.search(label + r' (\d{4}-\d{2}-\d{2}) · go ka', source).group(1)
                article = next(json.loads(blob) for blob in re.findall(
                    r'<script type="application/ld\+json">(.*?)</script>', source, re.S)
                    if json.loads(blob).get('@type') == 'Article')
                self.assertEqual(visible, article['dateModified'])
                self.assertEqual(visible, dates[article['url']])
                self.assertGreaterEqual(visible, page['updated'])


if __name__ == '__main__':
    unittest.main()
