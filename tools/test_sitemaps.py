"""Splitting sitemaps must preserve page coverage, dates and existing consumers."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import build_seo as seo

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
ORIGIN = "https://beforego.art"


class SitemapTests(unittest.TestCase):
    def test_grouping_keeps_every_public_url_and_its_date(self):
        records = [
            ("/", Path("home.html"), {}, "home"),
            ("/app/", Path("app.html"), {"live": True}, "product"),
            ("/tools/example/", Path("tool.html"), {}, "tool"),
            ("/blog/example/", Path("blog.html"), {}, "tool"),
            ("/app/privacy/", Path("legal.html"), {"live": True}, "legal"),
            ("/unreleased/", Path("hidden.html"), {"live": False}, "product"),
        ]
        dates = {p: f"2026-10-{i + 10:02}" for i, (_, p, _, _) in enumerate(records)}
        with patch.object(seo, "pages", return_value=iter(records)), \
             patch.object(seo, "git_lastmod", side_effect=lambda p, text: dates[p]):
            documents, count = seo.build_sitemap()
        self.assertIsInstance(documents, dict)
        self.assertEqual(count, 5)
        expected = {
            "sitemap-products.xml": {ORIGIN + "/app/": dates[Path("app.html")]},
            "sitemap-tools.xml": {ORIGIN + "/tools/example/": dates[Path("tool.html")]},
            "sitemap-blog.xml": {ORIGIN + "/blog/example/": dates[Path("blog.html")]},
            "sitemap-pages.xml": {ORIGIN + "/": dates[Path("home.html")],
                                  ORIGIN + "/app/privacy/": dates[Path("legal.html")]},
        }
        index = ET.fromstring(documents["sitemap.xml"])
        self.assertEqual(index.tag, NS + "sitemapindex")
        self.assertEqual({e.findtext(NS + "loc") for e in index},
                         {ORIGIN + "/" + name for name in expected})
        for name, entries in expected.items():
            tree = ET.fromstring(documents[name])
            self.assertEqual(tree.tag, NS + "urlset")
            self.assertEqual({e.findtext(NS + "loc"): e.findtext(NS + "lastmod") for e in tree}, entries)

    def test_reader_supports_the_old_flat_map_and_the_new_index(self):
        from sitemap import sitemap_urls
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            one = f'<urlset xmlns="{NS[1:-1]}"><url><loc>{ORIGIN}/</loc></url></urlset>'
            two = f'<urlset xmlns="{NS[1:-1]}"><url><loc>{ORIGIN}/app/</loc></url></urlset>'
            (root / "sitemap.xml").write_text(one)
            self.assertEqual(sitemap_urls(root, ORIGIN), [ORIGIN + "/"])
            (root / "sitemap-pages.xml").write_text(one)
            (root / "sitemap-products.xml").write_text(two)
            (root / "sitemap.xml").write_text(
                f'<sitemapindex xmlns="{NS[1:-1]}"><sitemap><loc>{ORIGIN}/sitemap-pages.xml</loc></sitemap>'
                f'<sitemap><loc>{ORIGIN}/sitemap-products.xml</loc></sitemap></sitemapindex>')
            self.assertEqual(sitemap_urls(root, ORIGIN), [ORIGIN + "/", ORIGIN + "/app/"])

    def test_reader_rejects_duplicates_and_unsafe_child_references(self):
        from sitemap import sitemap_urls
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sitemap.xml").write_text(
                f'<urlset xmlns="{NS[1:-1]}"><url><loc>{ORIGIN}/</loc></url>'
                f'<url><loc>{ORIGIN}/</loc></url></urlset>')
            with self.assertRaises(ValueError):
                sitemap_urls(root, ORIGIN)
            for child in ["https://other.example/sitemap.xml", ORIGIN + "/../outside.xml"]:
                (root / "sitemap.xml").write_text(
                    f'<sitemapindex xmlns="{NS[1:-1]}"><sitemap><loc>{child}</loc></sitemap></sitemapindex>')
                with self.assertRaises(ValueError):
                    sitemap_urls(root, ORIGIN)


if __name__ == "__main__":
    unittest.main()
