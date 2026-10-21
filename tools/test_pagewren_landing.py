"""The localized landing page keeps truthful samples and working download links."""
import copy
import unittest
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from build_pages import APPS, PAGEWREN_COPY, esc, lang_of, parent_of, render


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.ids = []
        self.headings = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "h1":
            self.headings += 1


class PagewrenLandingTests(unittest.TestCase):
    def test_every_live_locale_has_a_complete_landing_page(self):
        apps = [a for a in APPS if a.get("live") and parent_of(a)["key"] == "pagewren"]
        self.assertEqual(set(PAGEWREN_COPY), {lang_of(a) for a in apps})
        for app in apps:
            with self.subTest(locale=lang_of(app)):
                html = render(app)
                page = Links(html)
                self.assertEqual(page.headings, 1)
                self.assertEqual(len(page.ids), len(set(page.ids)))
                self.assertIn("#example", page.links)
                self.assertIn("example", page.ids)
                self.assertIn("pricing", page.ids)
                example = PAGEWREN_COPY[lang_of(app)]["example"]
                self.assertIn(esc(example["label"]), html)
                self.assertIn(esc(example["caption"]), html)

    def test_download_links_keep_the_existing_campaign(self):
        page = Links(render(next(a for a in APPS if a["key"] == "pagewren")))
        downloads = [urlparse(url) for url in page.links
                     if "apps.apple.com" in url and "6823661619" in url]
        self.assertGreaterEqual(len(downloads), 3)
        for url in downloads:
            self.assertEqual(url.hostname, "apps.apple.com")
            query = parse_qs(url.query)
            self.assertEqual(query["ct"], ["web-pagewren-app"])
            self.assertEqual(query["pt"], ["128309253"])

    def test_authored_text_cannot_inject_html(self):
        app = next(a for a in APPS if a["key"] == "pagewren")
        text = '<script>alert("sample")</script>'
        changed = copy.deepcopy(PAGEWREN_COPY["en"])
        changed["intro"] = text
        changed["example"]["quote"] = text
        changed["pricing"]["note"] = text
        with patch.dict(PAGEWREN_COPY, {"en": changed}):
            html = render(app)
        self.assertNotIn(text, html)
        self.assertEqual(html.count(esc(text)), 3)

    def test_other_apps_do_not_receive_pagewren_content_or_styles(self):
        for key in ("countdown", "invoiceqr", "beforego"):
            with self.subTest(app=key):
                html = render(next(a for a in APPS if a["key"] == key))
                self.assertNotIn('class="pagewren"', html)
                self.assertNotIn(".pagewren", html)
                self.assertNotIn('id="example"', html)


if __name__ == "__main__":
    unittest.main()
