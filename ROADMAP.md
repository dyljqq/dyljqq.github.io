# go ka 官网路线图

线上：https://beforego.art （09-26 起；Vercel 项目 `goka`，旧别名 goka-xi.vercel.app 与 www 均 301 过来；`dyljqq.github.io` 同步 main 作为旧链接兜底）
源码：本仓库 `main`。发布 = `build_pages.py` → `build_tools.py` → `build_seo.py` → 审计 → `vercel --prod` → IndexNow。

---

## v1.0（2026-09-26 已上线）

| 部分 | 内容 |
|---|---|
| 首页 | go ka 品牌页，7 个 app 卡片（文案 = 商店副标题 + 描述首段），FAQ，Organization / ItemList / FAQPage |
| 产品承载页 | Countdown 10 语、InvoiceQR 11 语、BeforeGo 12 语；正文全部取自各语言商店描述；预览视频 + 10 张截图 + 功能 + FAQ |
| 工具页 `/tools/` | days-until 计算器、圣诞 / 万圣节 / 新年倒数、ENEM 2026、Réveillon + Carnaval 2027（pt-BR）、发票模板、如何写发票、打包清单生成器、倒数日 app 榜单（含 6 个竞品） |
| 抓取入口 | sitemap 64 条（已提交 Google 并读取成功）、IndexNow 已推、robots 放行 11 个 AI 爬虫、llms.txt |
| 质量 | 线上 64 页全 200、canonical 自指、hreflang 33 组互返；Lighthouse 手机端性能 99–100 / SEO 100 / 无障碍 100 |

## 北极星指标与基线

**主指标：网站带来的 App Store 下载。** 09-13 ~ 09-26 共 14 天，三个 app 的下载来源：

| app | 搜索 | App 引荐 | Web 引荐 |
|---|---|---|---|
| Countdown | 257 | 73 | 1 |
| InvoiceQR | 31 | 2 | 0 |
| BeforeGo | 21 | 3 | 0 |

⚠ 苹果把「iPhone 上非 Safari 浏览器里点进来的」算作 **App 引荐**，不算 Web 引荐。所以网站的量会混进 App 引荐（和 ChatGPT 混在一起），
只看 Web 引荐会严重低估。**必须给网站上的每个 App Store 链接加活动参数（`pt` + `ct`），在 ASC「营销活动」里单独计数** —— 这是 v1.1 的第一件事。

次指标：Google 已编入索引页数 / 展示 / 点击（Search Console）；网站访问量与来源（chatgpt.com、perplexity.ai、google）。

---

## v1.1 看得见（09-27 ~ 10-03）

没有测量，后面加的每一页都是盲投。

1. **活动链接**：所有 App Store 按钮带 `pt=<provider token>&ct=site-<app>-<位置>`（如 `site-countdown-hero`、`site-tools-christmas`）。
   provider token 在 ASC → App Analytics → 营销活动 → 生成链接；由 Claude 用 Chrome 取，生成器统一注入。
2. **访问统计**：开 Vercel Web Analytics（无 cookie，不需要同意弹窗，不影响性能分）。看访问量、来源、国家、各页面。
3. **收录**：Search Console 每天用满「请求编入索引」配额，顺序：首页 → `/tools/` → 三个 app 英文页 → 各工具页 → pt-BR 页。
   Bing Webmaster Tools 从 Search Console 导入（需一次 Google 登录授权）。
4. **日报加一行「网站」**：活动下载、Web 引荐下载、访问量 Top 来源。

验收（10-03）：能回答「这周网站带来几次下载、从哪个页面、哪个来源」。

## v1.1.5 配图与页脚（09-28 上线）

- 用户 09-28：配图一律用 Codex 重画，不用商店截图。产品页首屏 + 功能图文 + 博客配图共 25 张插画（`assets/art/`，prompt 在 `tools/art/prompts.json`），截图画廊取消，Countdown 预览视频挪到「See it in action」一节；分享预览图（og:image）换成「图标 + 首屏插画」。
- 页脚重做（用户嫌乱）：隐私与条款三列对齐、社媒胶囊、底栏；链接不带下划线。
- 借势第一页：`/tools/days-until-diwali/`（排灯节 11-08，搜索高峰就在现在）。
- SEO 修复：`/xxx/index.html` 301 到目录 URL；Repdex 补分享图。

---

## 借势原则（09-28 定）

「蹭流量」＝在已经有人搜的日子和问题上，提前 4–6 周放一页能被收录的答案页，页里给出别人不给的东西：**把这个倒数放上 iPhone 主屏的小组件**。
依据（09-28 调研，Google 联想词 + 首页竞争抽查）：节日 / 考试倒数的首页多被小型倒数站占着，**没有一家给 app 或小组件入口**；
「formato de cotización / 報價單範本」首页是模板聚合站，同样没有 app 入口。英文通用词（quotation template、packing list）被 Canva / HubSpot / 大媒体垄断，不碰。

| 截止上线 | 市场 | 页面 | 依据（联想词 / 日期来源） | app |
|---|---|---|---|---|
| ✅ 09-28 | IN / 全球英文 | Diwali 2026（11-08） | 「diwali 2026 date」联想词丰富；维基 + farmersalmanac | Countdown |
| 10-17 | BR | Black Friday 2026（11-27）pt-BR | 与原 v1.2 计划吻合 | Countdown |
| 10-24 | BR | Natal 2026「quantos dias faltam para o natal」 | 11–12 月是全年峰值 | Countdown |
| 11-08 | MX | Aguinaldo 2026（12-20 截止，LFT 第 87 条）+ Navidad 2026，es-MX | 「fecha limite aguinaldo 2026」是首位联想词；expansion.mx | Countdown |
| 12-05 | JP | 共通テスト 2027（01-16~17）ja | resemom；Countdown 日本真人靠小组件留存 | Countdown |
| 12-26 | HK / TW | 農曆新年 2027（02-06）zh-Hant | 「2027年春节」联想词丰富 | Countdown |

不做：Dia das Crianças（10-12）和 Día de Muertos（11-02）窗口已过；수능（11-19）韩国不是主市场、Google 份额低；
Loy Krathong 人搜的是日期和仪式，不是倒数；Countdown 竞品替代词（Dreamdays / TimeUntil 等）联想词里没有需求证据。

## GEO 基线（09-28 实测）与打法

**实测（Perplexity，不登录，6 个问题）：我们 0 次被提到、0 次被引用。**

| 问题 | 被引用的来源 |
|---|---|
| best countdown widget app for iPhone with unlimited events and free widgets | 8 个竞品美区 App Store 页 + 1 Play + iosapplists 榜单文 |
| melhor app de contagem regressiva para iPhone com widget grátis | 全是名字带「Contagem regressiva」的 App Store 页（我们 BR 名也带，照样没召回） |
| iPhone invoice app that adds a payment QR code to invoices | 3 个 App Store 页 + **2 个 app 官网**（myinvoice.biz、invoiceyou.app） |
| app para hacer cotizaciones y notas de venta en iPhone | App Store 页 |
| app that turns a screenshot of a travel post into a day by day itinerary iPhone | 6 个竞品 App Store 页（含「GoDay: Turn posts into trips」）+ getplotline 榜单文 + **2 个官网**（rhyme.travel、trippocket.app）——这题几乎是 BeforeGo 的原话 |
| how many days until Diwali 2026 | almanac.com |

**结论**：AI 先用网页搜索召回 → App Store 页是主来源，其次是榜单文和 app 官网。我们三处都不在：
1. **Bing 0 收录**（`site:beforego.art` 无结果）——ChatGPT 搜索大量依赖 Bing，这是第一卡点。IndexNow 09-28 已推 2 次；
   ✅ 09-28 已接上 Bing Webmaster Tools（用户用 Google 账号登录；从 Search Console 导入 beforego.art / dyljqq.github.io / goka-xi.vercel.app，
   授权账号 jiqinqiang@polarisup.com）：sitemap 已导入（Processing），**全站 83 个网址已用「网址提交」一次推完**（每天配额 100）。
   Bing「AI Performance（Beta）」= Copilot 等 AI 答案引用我们的次数，09-28 基线 **0**（近 3 个月）——10-05 复盘一起看。
2. Google 收录中：09-28 已对 12 个关键页请求编入索引（排灯节、万圣节、ENEM、圣诞、新年、计算器、榜单页、/tools/、/beforego/、/blog/、/pt-br/、旅行截图那篇博客）。
3. 站内已具备：AI 爬虫全部放行（7 种 UA 实测 200）、llms.txt 有每个 app 的「免费 / 付费 / 适合谁」事实清单、FAQ 与 JSON-LD。

**打法（按性价比）**
- **字面词**：AI 按字面品类词匹配。BeforeGo 美区商店描述里「itinerary」出现 0 次（只在名字里），全文写的是 trip plan；
  下个 BeforeGo 版本的英文描述逐字加上「day-by-day itinerary」「turn a travel post / screenshot into an itinerary」（描述不进 App Store 搜索索引，改它零 ASO 风险）。
- **官网答案页**：发票、旅行两类问题里官网会被引用 → `/beforego/` 与 `/blog/travel-post-screenshot-to-itinerary/`、`/invoiceqr/` 与 `/blog/payment-qr-code-on-invoice/` 已在收录流程里；v1.3 的「Invoice Simple 替代」页同理。
- **自己当榜单**：`/tools/best-countdown-widget-apps-iphone/` 是给 AI 引用的榜单页（已请求收录）；v1.2 加 pt-BR 版。
- **第三方免费目录**：每版 2–3 个免费收录（不买付费位，iosapplists 付费评测用户已否决）。
- **复测**：10-05 复盘时把上面 6 个问题原样再问一遍，记「被提到 / 被引用」；之后每月一次。

## v1.2 巴西借势（10-04 ~ 10-17）

1. **pt-BR Black Friday 2026** 倒数页（复用节日模板，带 `ct=web-...`）。
2. **pt-BR Natal 2026** 倒数页（可以和 Black Friday 同批上，比截止早两周）。
3. **pt-BR 场景页 3 个**，标题直接对准联想词：「contagem regressiva para aniversário / casamento / viagem」+ 小组件步骤；en 版同批。原计划的 6 个里其余 3 个（baby / retirement / exam）等首批有展示再做。
4. **pt-BR 计算器 + 榜单**：`/tools/pt-br/quantos-dias-faltam/`、`/tools/pt-br/melhores-apps-contagem-regressiva/`（ChatGPT 推荐是 Countdown 最大的非搜索来源，榜单页是给 AI 引用的）。

判据（10-17）：Google `site:` 收录这批页；`web-*` 活动下载；巴西自然 / 活动下载。

## v1.3 墨西哥双线（10-18 ~ 10-31）

一个 es-MX 工具目录 `/tools/es-mx/` 同时服务两个 app：
1. Countdown：**Aguinaldo 2026**（日期 + 怎么算：15 天工资、12-20 前付，引 LFT 第 87 条原文）+ **Navidad 2026** 倒数。
2. InvoiceQR：**formato de cotización** 与 **nota de venta** 模板页（复用发票模板组件，可在线填写 + 下载，页里给 InvoiceQR 入口）；不写「factura」。
   同批出 zh-Hant **報價單範本**（HK / TW）和 th **ใบเสนอราคา**（首页竞争 10 月上旬先抽查）。
3. InvoiceQR 英文替代词页 **「Invoice Simple / Zoho Invoice / Invoice2go alternative」**：联想词有需求；只写可核实的功能 / 价格对比，竞品信息取自其商店页当日版本并注明日期。

依据：IQ-MX 的 cotización 广告 09-27 已按用户要求重开，网页和广告吃同一个意图；报价单意图在 TH / MX / HK 都出过活。
判据（10-31）：MX / HK / TH 的活动下载；`site:beforego.art/tools/es-mx/` 收录。

## v1.4 日本 + 农历年（11 月）

1. ja **共通テスト 2027** 倒数（12-05 前上线）+ ja 工具目录。
2. zh-Hant **農曆新年 2027**（12-26 前）；BeforeGo 同批出 zh-Hant **行李清單**（日本 / 韓國出國檢查表），面向港台新马中文用户（大陆打不开本站，那条线靠小红书）。

## 持续基建（穿插在各版本里）

| 项 | 做什么 | 时机 |
|---|---|---|
| 发布前检查进仓库 | `tools/check.py`：结构审计 + 手机宽度溢出（真实 375 视口量 scrollWidth）+ 关键模板截图巡检；发布脚本不过检不发 | v1.1 一起做（09-26 那个按钮事故就是缺这一步） |
| 商店文案自动同步 | 每周重抓商店缓存，有变化就重建 + 发布，网站永远和商店一致 | v1.2 |
| 自有域名 | ✅ 09-26 已切到 beforego.art；jiqinqiang.com 主域有备案永远不动 | 已完成 |
| ASC 链接 | 各 app 下个版本把营销 / 支持链接改成新站；隐私链接可随时改 | 随版本 |
| 外链 | 免费目录 / 榜单收录申请（不买付费位） | v1.2 起每版 2–3 个 |

不做：其余 4 个 app（DailyCalorie / QR Studio / 单词兽 / Repdex）的新版页面 —— 冻结项目，不投入。

## 节奏与决策点

- **每周一次发布**，发布后当天推 IndexNow、日报记一行。
- **10-05 第一次复盘**：收录页数、展示、活动下载 → 决定 v1.2 页数加减。
- **11-01 第二次复盘**：决定工具页要不要铺 pt-BR 以外的语言。
- **止损线**：某一类页上线 4 周仍 0 展示 → 停止加这类页，先查收录和站点权重，不再堆量。
