# Independent review — 2026-11-05

总分：**95 / 100；尚未达到 >95 发布门槛**。基线 HEAD `0567953`，保留既有已发布 `be119f0`。本轮审查旧站未提交修改；审查者未参与原始韩语迁移/英语备份修改。期间发现英语首屏绝对承诺残留，主线程授权本审查者仅修正这一句及其生成路径，已复拍验证；该补丁需主线程做最终独立抽查。无提交、推送、部署。

| 维度 | 得分 | 依据 / 扣分 |
|---|---:|---|
| 视觉与布局 | 25/25 | 实际查看首页英/德/日/es-MX、Countdown、InvoiceQR、DailyCalorie、三个工具、韩文指南与法务截图；未见错位或裁字 |
| 手机端 | 10/10 | 14路径 × 375×812 / 1280×900，共28视口；零横溢出、零页头越界；修复后Countdown再次复拍 |
| 语言切换 | 10/10 | 结构审计通过，hreflang/本地目标互返；截图中的当前语种标记正确；未实际点击每个菜单 |
| 本地化质量 | 19/20 | 韩文迁移正文可读、日期正确；韩语导航仍使用英文“Blog”（存量轻微项） |
| 事实准确 | 11/15 | 英语备份限制与源码吻合；韩语Countdown FAQ仍在重装语境承诺30天记录，未同步英文已证实边界，扣4分 |
| SEO/GEO技术 | 15/15 | 119页结构审计、FAQ可见文本一致、canonical/hreflang/schema/地图通过；0本次新增；预算通过 |
| 链接与归因 | 5/5 | 结构检查通过，工具真实保存成功；归因参数保留 |

## 缺陷与修复

1. **一般、待修：`/countdown/ko/` 仍有误导恢复承诺。** `tools/site.json:487-488` 问“업데이트 오류나 재설치 후에 디데이는 어떻게 되나요?”，答“30일치 기록이 남고 어떤 백업이든 한 번의 탭으로 복원됩니다. iCloud 동기화도 되고 계정은 필요 없습니다.” 这把最多30份本机快照写成30天，并在重装语境中省略本机快照不可依赖的限制；同文件`:496` 又说明个人Apple账户。应逐句修韩语，不能将本轮英语修复宣传为全语言修复。其他语种未逐句核验，不推断已经合格。
2. **轻微：韩文指南页头 Blog 未本地化。** 手机/桌面截图均可见。存量导航项，本轮未动。
3. **已修：英语“never loses your days”。** 原Countdown首屏与VideoObject以及根首页引用仍使用绝对承诺。授权后改 `tools/site.json` 的 home.blurb 和 descriptionReplacements；`tools/build_seo.py` 的VideoObject描述同样应用该覆盖；商店历史缓存未改。当前可见首屏和VideoObject均为 `Keep your important days close, with local snapshots and optional iCloud sync.` 根首页及多页App推广卡同步更新。生成传播后预算统计19页正文变化；0新增。修复后截图见 `evidence/2026-11-05-independent/_countdown_-desktop-fixed.png` 与 `...-mobile-fixed.png`。

## 内容事实核验

- 韩语迁移指南：`tools/build_tools.py:2705` 起；可见更新日和Article.dateModified均2026-11-05，published保留2026-10-12。竞品App比较明确仍为10-30快照，官方迁移程序11-05核验，不混用时间。
- 官方证据 `docs/facts/triple-migration-2026-11-05.md` 明示：结束后12个月可迁、NOL转换、一个账户、不可撤回/换账户、旅行逐项选择、已迁行程不得重复迁、不双向同步、时间/预约号显示缺失、账本/清单/同伴功能未提供。更新正文及FAQ对应这些限制。CSV无备份恢复未知明确写成未知，并给官方邮箱；未宣称实际迁移测试成功。
- Countdown源码抽查：`/Users/polarisdev/Documents/CountDown/Sources/Core/Backup/BackupEngine.swift:89` 的 dailyRetentionCount=30、safetyRetentionCount=10；`StoreLocator.swift:26-33` 是本地容器/本地Application Support；`EventStore.swift:888-905` daily snapshot有条件跳过并可能失败；`PersistenceController.swift:98-109` CloudKit不可用回退本地。英语新文案保留这些边界，不承诺删App/丢手机可恢复。未做实机恢复。

## 真实浏览器与导出证据

使用Node22 CDP + Chrome headless独立临时profile、localhost:8801；未接个人profile。14个路径见 `evidence/2026-11-05-independent/browser-results.json`，28视口全部 scrollWidth≤375/1280，headerOutside为空。关键截图已由审查者实际打开查看；不是只生成未看。首次Countdown桌面图标尚在加载，延时复拍正常，最终fixed截图为准。

Console并非“零错误”：每页有本地Python静态服务不提供 `/_vercel/insights/script.js` 的404；法务页另有 `/favicon.ico`404。没有Runtime.exceptionThrown。该记录不能证明生产Vercel资源有错。壁纸missingImages数组两个空URL来自隐藏的照片/预览占位img；页面可见图与真实导出正常。

壁纸实际编辑标题为 `Independent review trip`、日期 `2026-12-25`，点击真实Save wallpaper处理器后下载 `evidence/2026-11-05-independent/downloads/countdown-wallpaper.jpg`。已打开下载图片检查：1206×2622，50 days until，标题与Friday, December 25, 2026保留，未包含预览时钟。文件104744 bytes，SHA256 `eb8fc8c2ef2ea3ee6da7eb31fe3053dfc439e8664abba1db461e89820c25cc22`。默认背景路径验证成功；没有测试照片上传、全部尺寸、iOS分享菜单。壁纸没有独立打印按钮，本轮没有把网页printToPDF算作其产品打印功能。

## 检查与未测

- 重建 tools/build_tools.py、build_pages.py、build_home.py、build_seo.py；最终 `check_structure.py .`：119页/119地图URL全部通过。
- 最终页面预算：0本次新增，19正文变化均达标；7个存量低独有率警告保留，非搜索引擎质量判定。
- `python3 -m unittest discover -s tools -p 'test_lastmod.py'`：7测试通过；`git diff --check`通过。
- 未测：完整全部语种逐句事实、iPhone/App恢复、真实NOL账号迁移、实体打印、移动系统保存分享、生产部署后回归及实际AI引用。故本报告不声称全站或App流程已完成验收。

## 附录：韩语局部修复复验（2026-11-05）

主线程另行授权修复同一韩语页的事实一致性。本次仅改 `tools/site.json` 中 `countdown-ko` 与 `tools/i18n/features.json:792`；未刷新商店缓存、未改其他语言。`tools/site.json:487-488` 明确一般快照最多30份而非30天，删App/丢手机后不能依赖本机快照保证恢复；`:496` 区分不需另建Countdown账户与iCloud需要个人Apple账户；`:499-504` 通过现有descriptionReplacements修正首屏及详情的同类绝对承诺、无账户iCloud说法，并将详情标题改为“기능과 백업 안내”。历史原文仍存于tools/store/countdown.json。

只调用生成器render(countdown-ko)，随后build_seo更新该页与sitemap-products.xml。所有FAQ问答出现在可见正文、JSON-LD可解析；旧可见语句“30일치 기록,”、“계정이 필요 없는 iCloud”、“소중한 날을 잃어버리지 않고”、“위험한 작업 전에도 반드시”均已消失。结构审计119页通过，预算0本次新增、20正文变化全部达标；7项lastmod测试通过；git diff --check通过。

Chrome独立profile在375×812与1280×900重新打开韩语页、滚动到目标恢复问答，截图已实际查看。问答和账户说明完整可读，未横向溢出；无Runtime异常。仍仅有本地/_vercel/insights/script.js 404。证据 `evidence/2026-11-05-independent/browser-ko-faq-results.json`、`_countdown_ko_-mobile-ko-faq-fixed.png`、`_countdown_ko_-desktop-ko-faq-fixed.png`。

按同一抽查范围，原扣4分的事实问题已修，**修复后评分99/100**（本地化19/20仍扣韩文导航Blog 1分，其余同前）。但此附录修复由原审查者本人执行，属于修复自验，**需主线程/另一审查者独立抽查上述源代码和截图后，才能把99分作为新的独立发布评审结果**。未扩展到其他未审语言，未实测App备份、重装或恢复。

## 附录：第二审查者独立确认韩语修复（2026-11-05）

**独立复核通过；在原报告既定抽查范围内，确认修复后评分为99/100。** 本次第二审查者未参与上述韩语产品文案修改，仅只读核对 `evidence/2026-11-05-independent/korean-reviewed-facts.json`、`tools/site.json:487-504`、`tools/i18n/features.json:792` 与 `docs/facts/countdown-backup-copy-2026-11-05.md`，并实际打开查看 `_countdown_ko_-mobile-ko-faq-fixed.png`。

核对结果：韩语明确“最多30份一般本机快照”不等于30天记录；不保证卸载App或丢失手机后能依靠本机副本恢复；iCloud需要个人Apple账户与正常连接，恢复取决于可用同步副本或已导出至App外的文件；不再承诺数据永不离机。功能卡同样将一般快照与另存的安全副本区分。截图中恢复限制、外部导出建议和账户说明完整可读，未见该截图范围内的裁字或横向溢出。

据此独立核准原事实项回补4分（11/15 → 15/15）；其余维度沿用原独立报告，韩语导航英文“Blog”的1分扣分仍保留。本次没有重新进行全站或浏览器审计，不代表全部语种事实均已核验；未启动App或模拟器，未实测备份、卸载、丢机或恢复流程。事实依据文档中较早的“仅英语覆盖”描述属于此前阶段，不能据本次韩语局部通过推及其他语种。
