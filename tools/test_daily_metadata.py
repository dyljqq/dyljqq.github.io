"""Daily counters must not make fixed event dates look like content changes."""
import unittest
from datetime import date

from build_seo import _lastmod_norm


def page(text, count=10):
    return f'<title>Countdown</title><body><b data-n>{count}</b><p>{text}</p></body>'


class DailyMetadataTests(unittest.TestCase):
    def test_static_dates_matching_the_old_commit_day_remain_content(self):
        fixed = [
            'D-30은 2026년 10월 20일(화), D-7은 2026년 11월 12일(목)입니다.',
            '2026年10月20日に確認した試験日です。',
            '考試日期為2026年10月20日。',
            'The event is on October 20, 2026.',
            'A data do evento é 20/10/2026.',
        ]
        for text in fixed:
            with self.subTest(text=text):
                html = page(text)
                self.assertEqual(_lastmod_norm(html, date(2026, 10, 20)),
                                 _lastmod_norm(html, date(2026, 10, 21)))

    def test_real_changes_to_fixed_dates_are_not_hidden(self):
        before = page('D-30은 2026년 10월 20일(화)입니다.')
        after = page('D-30은 2026년 10월 21일(수)입니다.')
        self.assertNotEqual(_lastmod_norm(before, date(2026, 10, 20)),
                            _lastmod_norm(after, date(2026, 10, 21)))

    def test_actual_daily_copy_and_counters_stay_stable_across_days(self):
        pairs = [
            ('On October 20, 2026, there were 10 days. The counter recalculates when you open it.',
             'On October 21, 2026, there were 9 days. The counter recalculates when you open it.'),
            ('Em 20/10/2026, faltavam 10 dias. O contador desta página recalcula no dia em que você abre.',
             'Em 21/10/2026, faltavam 9 dias. O contador desta página recalcula no dia em que você abre.'),
            ('10 (em 20/10/2026, contando hoje)', '9 (em 21/10/2026, contando hoje)'),
            ('在2026年10月20日，還有10天。本頁的倒數會在你打開當天重新計算。',
             '在2026年10月21日，還有9天。本頁的倒數會在你打開當天重新計算。'),
            ('2026年10月20日の時点で10日です。', '2026年10月21日の時点で9日です。'),
            ('남은 날은 2026년 10월 20일 기준으로 계산했고, 페이지를 열 때 다시 계산됩니다.',
             '남은 날은 2026년 10월 21일 기준으로 계산했고, 페이지를 열 때 다시 계산됩니다.'),
        ]
        for before, after in pairs:
            with self.subTest(before=before):
                self.assertEqual(_lastmod_norm(page(before, 10), date(2026, 10, 20)),
                                 _lastmod_norm(page(after, 9), date(2026, 10, 21)))


if __name__ == '__main__':
    unittest.main()
