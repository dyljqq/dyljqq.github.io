# Backup copy evidence — 2026-11-05

Read-only source inspection; no App/device recovery test.

- /Users/polarisdev/Documents/CountDown/Sources/Core/Backup/BackupEngine.swift:89–95: dailyRetentionCount=30, safetyRetentionCount=10. This is count retention, not a guarantee of 30 consecutive calendar days.
- Sources/Core/Persistence/StoreLocator.swift:26–33,54–58: snapshots in local App Group / Application Support directory, not an independent off-device backup.
- Sources/Core/Persistence/PersistenceController.swift:98–109: CloudKit mirrored store with local-only fallback.
- Sources/Core/Persistence/EventStore.swift:888–905: daily snapshot conditional and may fail; :992–1003 exports own events plus stories/pages/attachments.
- Product rendering override applies only to English /countdown/. Cached App Store source remains an unmodified historical snapshot. Other language product copy still needs individual editorial review; do not claim sitewide recovery copy fixed.
- Existing be119f0 comparison decision matrix and birthday guidance retained; no unsupported paid-tier test added.
