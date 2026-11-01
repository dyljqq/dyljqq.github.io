# 2026-11-01 本地验收记录

工作分支 `site/next-1101`。仅使用仓库与 `docs/facts/`；插画由内置 `image_gen` 生成。未部署、推送或提交 IndexNow / GSC / Bing 请求，未实施候选合并。

## 实现与证据

- 页面预算：`tools/check_page_budget.py`、`tools/test_page_budget.py`、`tools/publish.sh`、`CLAUDE.md`、`docs/page-budget.md`。
- 统计：新增 `assets/analytics/firebase-web-v2.js`，保留 v1；生成器与全部 117 页引用 v2。`ANALYTICS.md`、浏览器测试与离线排除测试同步更新。
- 榜单：`tools/build_tools.py` 与英文、葡语现有榜单。七款英文数据和四款共有 App 的美区数据逐项匹配 lookup；葡语巴西历史数据未被冒充为美区当日数据。自家 App 为 1.4.30、27 个美区评分、4.6 星（原值 4.62962 四舍五入）。两页 hreflang 配对不变。
- 配图：榜单页「Choose by what you need」一节用 Countdown 现有插画 `assets/art/countdown/07-*.webp`（11-01 复审指出新画的一张和现有画风不一致，已删除）。
- 合并报告：`consolidation-candidates-2026-11-01.md`（含 GSC 数字，放在仓库外的报表目录）与 `tools/report_consolidation.py`。覆盖 117 页，3 个有条件候选；全部承接后预计 114 页，当前可直接实施 0 页。逐页掉量前曝光/排名没有数据，明确未知；未把缺行补零。

## 检查结论

```text
python3 -m unittest discover -s tools -p 'test_page_budget.py'
Ran 29 tests / OK

python3 -m unittest discover -s tools -p 'test_*.py'
Ran 63 tests / OK

node tools/test_analytics_exclusion.mjs
Analytics exclusion: 29 checks passed (offline VM, mocked SDK imports only)

python3 tools/check_structure.py .
结构审计：页面 117，sitemap 117 条，全部通过

python3 tools/check_page_budget.py
页面预算检查：通过；可索引 117 页，本次新增/正文变化 4 页，独有率未达标 0 页，存量警告 7 页。

python3 tools/report_consolidation.py
Consolidation report: 117 pages; 3 conditional candidates; projected 114; immediately executable 0

python3 tools/indexnow.py --dry-run
IndexNow（dry-run）：sitemap 共 117 页，新增 0 · 修改 5 · 删除 0
  修改  https://beforego.art/countdown/
  修改  https://beforego.art/tools/best-countdown-widget-apps-iphone/
  修改  https://beforego.art/tools/days-until-halloween/
  修改  https://beforego.art/tools/pt-br/melhores-apps-contagem-regressiva/
  修改  https://beforego.art/tools/pt-br/quinto-dia-util/

git diff --check
通过
```

本次相对 `origin/main` 新增/移除 sitemap URL 均为 0。按发布日志基线 `ecd433cd86c7`，本次新增与滚动七天新增均为 0（预算 3）。

`_lastmod_norm` 保持原样。构建初次出现三个无实质正文变化的 lastmod 跳变；独立批量重放历史确认了应有日期。原 `git_lastmod` 吞掉 Git 读取异常后返回当天，异常原文已被旧实现丢弃，不能断言当时一定是超时。本次改为较宽的读取时限并在失败时明确停止，补了异常回归测试。最终有四页因实质正文变化将 lastmod 更新为 2026-11-01：两篇榜单、同步 1.4.30 更新说明并引用新版榜单摘要的 `/countdown/`、按当前月份滚动实际月份表的 `/tools/pt-br/quinto-dia-util/`。另有一项历史日期纠正：`/tools/days-until-halloween/` 从 2026-10-25 回改为 2026-10-18，属于纠正此前仅每日计数引起的日期漂移，不是新正文变更；IndexNow 旧记录迁移也必须识别这种回改。DailyCalorie、Réveillon、ENEM 分别保持 2026-09-26、2026-10-18、2026-10-18。

## 92 分复审修复

- 发布基线改为 `content/published-log.tsv` 最后一条成功发布提交；本地 `published` 标签不再决定基线。日志追加与记录提交仍在部署成功后、推送 main 前。
- 正文签名保留固定事实日期，仅屏蔽指定生成日期、每日计数及生成结构；正文事实日期修改会触发独有率检查。
- IndexNow 旧记录按记录提交的历史 sitemap 逐页比较 lastmod，包含向前/向后纠正，dry-run 不写状态或发请求。
- 初始被内部标记排除的页面保留 BFCache 恢复入口；别页清除标记后恢复可初始化并上报浏览与点击，旧 `internal=1` 查询参数不重复应用。
- `tools/store/countdown.json` 的 `en-US` 版本、更新说明及版本发布日期同步美区 lookup 快照：1.4.30 / 2026-10-30T15:11:22Z。更新说明为 “Updated App Store information. App features and functionality are unchanged.”，不含价格。`releaseMetadataSource` 与 `releaseMetadataChecked` 记录该部分来源和核验日；旧 `fetched` 保留，用于区分未重抓的其他缓存字段。其他地区无本次本地化快照，保留原始商店记录。第 5 步单独造成的正文变化页为 `/countdown/`。
- 合并报告重新从最终 HTML 生成：Halloween 独有率 44.63%，壁纸生成器 83.54%；token 语料 SHA-256 为 `4fd787040c73c20baa9675c00360c01abd5850e8cce7e097a53d33765fa54f64`。仍为 3 个有条件候选、预计 114 页。

## 先前环境验收记录

以下为此前尝试记录。用户本轮提供的 92 分复审已采用 117 页 CDP 通过记录、视觉与手机项满分；本轮按要求仅运行指定离线验证，不另做审核，不提交。

`bash tools/publish.sh --check` 的构建、结构、预算步骤通过，手机步骤未通过：`Error: Chrome 没起来`。`node tools/test_analytics.mjs` 无法监听本地端口：`listen EPERM: operation not permitted 127.0.0.1`。浏览器测试已改成拦截所有外部请求并模拟 Firebase SDK，本次没有真实发送 GA4 测试数据。桌面模板截图、375px 手机布局及浏览器统计集成须在允许本地服务/Chrome 的环境补验。

独立 review 完成源码、事实与结构核验，指出的葡语 FAQ 日期歧义已修复。视觉/手机 35 分尚未实测，不能宣称达到仓库 `tools/REVIEW.md` 所要求的“总分 > 95 才能 commit + 部署”。当时因此保留所有工作区改动、不提交。`.git` 暂存曾实际成功，随后撤销本次暂存；当时未提交的原因是验收门槛未满足，不能误报为 `.git` 写入被拒绝。本轮不提交的依据是用户明确指令。
