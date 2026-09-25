# go ka 官网路线图

线上：https://goka-xi.vercel.app （Vercel 项目 `goka`；`dyljqq.github.io` 同步 main 作为旧链接兜底）
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

## v1.2 Countdown：场景页 + 巴西（10-04 ~ 10-17）

依据：Countdown 是唯一有量的 app，App 引荐（含 ChatGPT）14 天 73 次，是搜索之外最大的来源；巴西是唯一付费 + 五星都出现过的市场。

1. **场景页 6 个**（en + pt-BR 各一套）：birthday / wedding / baby due date / retirement / vacation / exam countdown。
   每页：这个场景怎么数 → app 里对应模板怎么放上主屏（3 步）→ FAQ。对应 app 内 36 个模板，文案只写 app 真有的功能。
2. **节日页**（赶在搜索高峰前 4–6 周被收录）：Black Friday（11-27，en + pt-BR）、Natal 2026（pt-BR）。不做美国专属节日（流量目标是非美国用户）。
3. **pt-BR 版计算器和榜单**：`/tools/pt-br/quantos-dias-faltam/`、`/tools/pt-br/melhores-apps-contagem-regressiva/`。

判据（10-17）：这批页在 Search Console 的展示数；`site-countdown-*` 活动下载；巴西 Web / 活动下载。

## v1.3 InvoiceQR：按投放市场做「报价单 / 收据」模板页（10-18 ~ 10-31）

依据：报价单（quotation）意图在 TH / MX / HK 都出过活；InvoiceQR 的广告主力市场是 MX / TH / HK / MY。

1. 复用发票模板组件，出三种文档：报价单、收据、送货单。
2. 按市场语言各一页：es-MX「formato de cotización / nota de venta」、th「ใบเสนอราคา」、zh-Hant「報價單範本」、en（MY / SG）「quotation template」。
3. 每页挂同语言的 InvoiceQR 承载页 + 活动链接。

判据（10-31）：这些市场的活动下载；同市场广告与自然搜索是否一起涨。

## v1.4 BeforeGo（11 月上半，范围受限）

约束：BeforeGo 的买家 10/10 是简体中文用户，但 vercel.app 在中国大陆打不开、大陆也用不了 Google，网页覆盖不到主力买家 —— 那条线靠小红书。
网页只做：按目的地的打包清单（日本 / 泰国 / 韩国，en + zh-Hant），面向港台新马的中文用户和英语用户。

## 持续基建（穿插在各版本里）

| 项 | 做什么 | 时机 |
|---|---|---|
| 发布前检查进仓库 | `tools/check.py`：结构审计 + 手机宽度溢出（真实 375 视口量 scrollWidth）+ 关键模板截图巡检；发布脚本不过检不发 | v1.1 一起做（09-26 那个按钮事故就是缺这一步） |
| 商店文案自动同步 | 每周重抓商店缓存，有变化就重建 + 发布，网站永远和商店一致 | v1.2 |
| 自有域名 | `apps.jiqinqiang.com` → Vercel（CNAME `cname.vercel-dns.com`），主域有备案永远不动 | 能进 DNSPod 时 |
| ASC 链接 | 各 app 下个版本把营销 / 支持链接改成新站；隐私链接可随时改 | 随版本 |
| 外链 | 免费目录 / 榜单收录申请（不买付费位） | v1.2 起每版 2–3 个 |

不做：其余 4 个 app（DailyCalorie / QR Studio / 单词兽 / Repdex）的新版页面 —— 冻结项目，不投入。

## 节奏与决策点

- **每周一次发布**，发布后当天推 IndexNow、日报记一行。
- **10-05 第一次复盘**：收录页数、展示、活动下载 → 决定 v1.2 页数加减。
- **11-01 第二次复盘**：决定工具页要不要铺 pt-BR 以外的语言。
- **止损线**：某一类页上线 4 周仍 0 展示 → 停止加这类页，先查收录和站点权重，不再堆量。
