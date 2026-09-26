# 发布前 review 评分表

规矩（用户 2026-09-26 定）：每次发布前开一个**独立子 agent** 按本表打分，**总分 > 95 才能 commit + 部署**。
子 agent 只读，不改任何文件；报告只要「分数表 + 缺陷清单」。

## 怎么看

- 本地预览：`http://127.0.0.1:8765/`（仓库根目录的静态服务；没起来就 `python3 -m http.server 8765 --bind 127.0.0.1 --directory <仓库根>` 后台起）
- 页面清单：`sitemap.xml`（`<loc>` 去掉域名即本地路径）
- 桌面截图：`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --window-size=1280,<高> --virtual-time-budget=5000 --screenshot=<png> <url>`，然后 Read 图片
- 手机：**不要**用 `--window-size=390` 截图判断布局（桌面 Chrome 最小窗口约 500px，会误判溢出）。
  手机布局用 `node tools/check_mobile.mjs http://127.0.0.1:8765 <路径...>`（CDP 真实 375 视口，量溢出、按钮尺寸）；
  需要看手机画面时同样用 CDP 设备模拟截图，或只看桌面截图 + 该脚本的结论。
- 自动审计：`python3 tools/check_structure.py .`
- 事实依据：`tools/store/<app>.json`（各语言 App Store 商店描述缓存）、`tools/store/subtitles.json`
- **例外（用户 09-26 指定）**：BeforeGo 的截图和「功能图文」用 1.2.0（尚未上线）的截图与文案，依据是 `tools/store/beforego-1.2.0.json`（ASC 1.2.0 的描述与更新说明）；其余文字仍以线上商店为准。
- 页面结构（参照 EasyNotes 官网与 11 个同类 app 官网调研）：产品页 = 首屏 → 功能图文（浅底圆角卡片：商店截图中部的手机界面按 4:5 裁切、不带宣传大字 + 标题 + 两三句，参照 EasyNotes）→ 截图画廊 → 商店原文细节 → 当前版本更新内容 → FAQ → 指南与免费工具 → 其他 app；语言切换只在页头（参照 GoFasting 的「EN ⌄」菜单），页面底部不再列语言；另有 `/blog/`（英文指南）与 `/tools/`。

## 评分（满分 100）

| # | 维度 | 分 | 扣分依据（每条缺陷按严重度扣 1–10） |
|---|---|---|---|
| 1 | 视觉与布局 | 25 | 抽查每种模板（首页 en + 至少 3 个语言首页、产品页 3 个 app 各 1–2 个语言、工具页 ≥3、法务页 1）的桌面截图：元素错位、图标/按钮尺寸异常、文字溢出或被截断、空白块、图片不显示、明显难看 |
| 2 | 手机端 | 10 | check_mobile.mjs 结论；页头在手机上是否可用（品牌、导航、语言切换不重叠） |
| 3 | 语言切换 | 10 | 每类页面页头都有切换器；列出的语言与该页真实存在的版本一致；当前语言标记正确；每个链接 200；切换后落到同一内容的对应语言版本 |
| 4 | 本地化质量 | 20 | 功能图文、更新内容、指南区块的译文也算；语言首页没有残留英文句子（app 名、品牌名除外）；译文自然、不是机翻腔；**es-MX 重点**：不把我们的 app 说成开「factura」（墨西哥 factura = CFDI，我们不开），用 nota de venta / cotización / remisión；用墨西哥说法；FAQ 与商店描述一致 |
| 5 | 事实准确 | 15 | 包括 /blog/ 每篇文章；页面上关于功能、价格、免费额度、语言、系统版本的每句话都能在 `tools/store/` 的对应语言商店描述里找到依据；找不到或矛盾的逐条扣分 |
| 6 | SEO / GEO 技术项 | 15 | check_structure.py 通过；hreflang 互返（首页 12 语、产品页各家族）；每页 canonical 自指；JSON-LD 可解析且与可见内容一致；title ≤ 70、description ≤ 170；llms.txt / sitemap 覆盖新页面 |
| 7 | 链接与归因 | 5 | 站内无死链；页面上的 App Store 按钮带 `pt=128309253&ct=web-*`；结构化数据里是干净商店链接 |

## 报告格式

```
总分：NN / 100
| 维度 | 得分 | 主要扣分 |
缺陷清单（按严重度）：
- [严重/一般/轻微] URL — 现象 — 依据
```

只报告，不修复。
