# GEO content fixes — 2026-11-06

## 改了什么

- 修正 `/tools/ja/kyotsu-test-2027/` 的外语、听力、理科、数学和情報Ⅰ时刻；保留一科/两科条件，明确考试开始不等于入室截止。链接2027官方指南和2028日程，核验日期改为2026-11-06。
- 同页纠正准考证与持物规则：自行打印含报名照片的准考证、有效照片身份证明、符合规定的笔与钟表、通信设备收进包内。删除旧「写真票」和现场补发保证，FAQ同步；12月入室截止通知保持待公布。
- 修正英文比较页的恢复能力：最多30份常规本机快照，不保证30天历史或卸载/换机恢复；说明应核对已同步副本并在App外保存导出。商店评级、版本、竞品描述仍标为11月1日快照，历史缓存未改。
- 改生成源 `tools/build_tools.py` 后在隔离副本构建。与任务前工作区逐文件比较，原有文件只改变该生成源、两个目标HTML与 `sitemap-tools.xml`。无新URL；仅两页的lastmod更新为2026-11-06。既有其他工作区修改保留。

[事实依据](../../facts/geo-content-corrections-2026-11-06.md)、[精确源码差异](source.diff)、[文件校验值](changed-files.json)、[sitemap差异](sitemap-changes.json)。

## 怎么验的

| 命令/操作 | 结果 |
| --- | --- |
| `python3 tools/build_tools.py` → `python3 tools/build_seo.py`（隔离副本） | 构建成功；119个网页URL；仅目标产物带回工作区 |
| `python3 tools/check_structure.py .` | `结构审计：页面 119，sitemap 119 条，全部通过` |
| `python3 tools/check_page_budget.py .` | 通过，0新增URL、0变化页低于现有规则阈值；相对既有发布日志的15个变化页包含本轮前改动，并非本轮改了15页 |
| `python3 -m unittest discover -s tools -p test_daily_metadata.py` | 3 tests，OK |
| `git diff --check -- tools/build_tools.py tools/best-countdown-widget-apps-iphone/index.html tools/ja/kyotsu-test-2027/index.html sitemap-tools.xml` | 通过 |
| `node /tmp/beforego-geo-fix-browser.cjs`（[脚本副本](browser-check.cjs)） | 两页各在1280px/375px视口通过，0横向溢出、0页面脚本异常；自指正式canonical，JSON-LD可解析且日期更新 |
| 2026-11-06东京日期下打开考试页 | 正确显示至2027-01-16还有71天；8行时刻表、官方链接、准考证规则均核对通过 |
| 官方PDF GET | A/C-2/D三份均HTTP200、有效PDF；[原始记录](official-sources.json) |

浏览器使用隔离Chromium和临时本地端口，阻断外部请求，没有写入生产分析。浏览器与本轮本地服务已关闭，没有操作用户既有8788服务。此次是页面内容修复，未重复工具导出全套回归或运行性能压测。

截图：[考试手机](exam-mobile.png)、[考试桌面](exam-desktop.png)、[比较页手机](comparison-mobile.png)、[比较页桌面](comparison-desktop.png)。主代理已查看手机截图。详细结果：[浏览器](browser-results.json)、[检查清单](checks.json)。

独立代理只读审阅了本轮源码差异，未发现阻断问题；其关于「タイマー」泛化官方禁用范围的意见已修正为「キッチンタイマー・学習タイマー」。这不是全站发布评分或原生设备恢复认证。

## 已知问题

- **本地修复并验证，尚未提交或部署。线上原问题仍存在，不能称已上线。**
- 12月上旬官方《受験上の注意》发布后，仍需核对具体入室截止及后续通知；本轮没有编造未公布内容。
- 未实测原生App卸载/换机恢复；保守文案不承诺恢复成功。
- 未取得新的消费端AI回答、GSC/Bing或转化数据，不能声称本次修复提高了引用或流量。压缩工具的内容实验仍是独立待办。
- 页面预算检查保留7条既有页面警告；本轮两个变化页通过。它们不是这次修复新增的问题，详细日志见 `page-budget.log`。
