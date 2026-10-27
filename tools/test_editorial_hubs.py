"""Editorial comparison pages can belong to a hub without endorsing one app."""
import unittest
import build_tools


class EditorialHubTests(unittest.TestCase):
    def test_comparison_without_app_renders_in_korean_hub(self):
        page = build_tools.hub_page('ko')
        self.assertIn('/tools/ko/yeohaeng-iljeong-aep/', page['body'])
        self.assertIn('트리플 대체 앱 비교', page['body'])


if __name__ == '__main__':
    unittest.main()
