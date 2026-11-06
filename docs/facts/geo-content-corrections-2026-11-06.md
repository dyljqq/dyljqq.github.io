# Two existing-page corrections — 2026-11-06

Scope: `/tools/ja/kyotsu-test-2027/` and `/tools/best-countdown-widget-apps-iphone/`. Edit the source in `tools/build_tools.py`; rebuild the existing pages and their sitemap metadata. No new URL or competitor refresh.

## Exam facts

Official sources, checked 2026-11-06:

- [2027 examination guide](https://www.dnc.ac.jp/kyotsu/shiken_jouhou/r9/r9_jukenannai.html).
- [A — overview](https://www.dnc.ac.jp/albums/abm.php?d=2164&f=abm00017475.pdf), printed p8: January 16 foreign-language written exam 15:20–16:40; English listening 17:20–18:20. January 17 science 9:30–11:40 for two registered subjects or 10:40–11:40 for one, mathematics ① 13:00–14:10, mathematics ② 15:00–16:10, information I 17:00–18:00. History/civics and Japanese language slots were already correct. Listening includes equipment preparation, with 30 minutes of answers; the two-subject blocks contain a 10-minute collection interval.
- [C-2 — admission ticket](https://www.dnc.ac.jp/albums/abm.php?d=2164&f=abm00017486.pdf), printed pp42–44: obtain the admission ticket from My Page starting December 4 at 10:00; print at original size on A4 white paper in portrait. It includes the registered photo; displaying it on a phone does not suffice. Removed the unsupported separate photograph-ticket requirement and guaranteed on-site replacement claim.
- [D — examination](https://www.dnc.ac.jp/albums/abm.php?d=2164&f=abm00017490.pdf), printed pp48–49: valid photo identification is mandatory. Checked the pencil, eraser, watch, communication-device storage and clothing restrictions. Exact normal room-entry deadlines will be specified in the December notice; they are not the examination start times. Printed p53 confirms January 23–24 supplementary/repeat dates with exceptional rescheduling conditions.
- [2028 official schedule](https://www.dnc.ac.jp/kyotsu/shiken_jouhou/r10/): January 15–16.

PDF bytes, checksums and retrieval times are retained in `docs/qa/geo-content-fix-2026-11-06/official-sources.json`. This correction does not claim the future December notice has already been checked.

## Local snapshot limits

The November 1 App Store lookup remains a historical snapshot and is not edited. Ratings, versions and competitor descriptions still refer to that snapshot. The comparison now separately discloses the November 6 correction to our own product's recovery wording.

Source checks:

- `/Users/polarisdev/Documents/CountDown/Sources/Core/Backup/BackupEngine.swift:89`: default routine retention count 30; the prune implementation counts retained files rather than guaranteeing 30 consecutive days.
- `/Users/polarisdev/Documents/CountDown/Sources/Core/Persistence/StoreLocator.swift:54`: snapshot directory is within local application storage.
- `/Users/polarisdev/Documents/CountDown/Sources/Core/Persistence/EventStore.swift:888`: daily snapshot creation is conditional and can fail.
- Existing published `/countdown/` guidance and `docs/facts/countdown-backup-copy-2026-11-05.md` describe the same limits.

The new comparison copy states up to 30 routine on-device snapshots, no guaranteed 30-day history, and no uninstall/replacement recovery guarantee. It asks readers to verify a synced copy and save an export outside the app before either operation. This is source review, not a device recovery test or evidence of a search/conversion improvement.

## Independent review

A separate permitted non-Claude agent reviewed only this task's source diff and checked official sources. No blocking issue was found. Its narrower wording correction — use the official kitchen/study timer restriction instead of a blanket ban on all timers — was incorporated. Review did not certify unchanged competitor claims or native-device recovery.
