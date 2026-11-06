# Backup copy evidence — 2026-11-05

Read-only source inspection; no App/device recovery test.

- /Users/polarisdev/Documents/CountDown/Sources/Core/Backup/BackupEngine.swift:89–95: dailyRetentionCount=30, safetyRetentionCount=10. This is count retention, not a guarantee of 30 consecutive calendar days.
- Sources/Core/Persistence/StoreLocator.swift:26–33,54–58: snapshots in local App Group / Application Support directory, not an independent off-device backup.
- Sources/Core/Persistence/PersistenceController.swift:98–109: CloudKit mirrored store with local-only fallback.
- Sources/Core/Persistence/EventStore.swift:888–905: daily snapshot conditional and may fail; :992–1003 exports own events plus stories/pages/attachments.
- Product rendering override applies only to English /countdown/. Cached App Store source remains an unmodified historical snapshot. Other language product copy still needs individual editorial review; do not claim sitewide recovery copy fixed.
- Existing be119f0 comparison decision matrix and birthday guidance retained; no unsupported paid-tier test added.

## 2026-11-06 补充

沿用以上App源码证据，逐页修正pt-BR/de/fr/it/ja/th/zh-Hans/zh-Hant现有产品页的首段、功能块、商店描述显示覆盖、免费功能列表与两项FAQ；英语同步澄清无需单独Countdown账号与本机快照口径。韩语已修正文案保留。历史tools/store/countdown.json未改。

关键区别：最多30份常规快照不是保证连续30日；本机文件不是离机备份；iCloud需要自己的Apple账户与正常同步连接；卸载或换机前应核对已同步副本并把导出存放在App之外。没有同步副本或导出不能保证恢复。原始商店描述中的“最常见投诉”等无来源比较也从这8个显示段落移除。

这是源代码核对与网站编辑，不是设备恢复实测。没有修改商店文案、App功能或订阅配置；不将这些纠错宣称为转化提升或搜索流量提升。
