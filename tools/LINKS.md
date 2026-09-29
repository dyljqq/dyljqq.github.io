# 外链模板：社媒 / 社区帖子里放官网和商店链接

通用做法写在社媒仓库 `playbook/25-外链归因.md`；这里是本站的具体链接表。

## 官网链接：给帖子对应的那一页，带 `?ref=`

- 格式：`https://beforego.art/<页面>/?ref=<平台>-<内容名>`；ref 只用小写字母、数字、连字符，最长 40 字符。
  例：`https://beforego.art/beforego/?ref=reddit-receipts-0929`
- `build_seo.py` 的 `ANALYTICS` 把**落地那一次**浏览记成 `/<页面>/~<ref>`，在 Vercel 的 Pages 里单独一行；之后在站内点开的页面照常记。
- 别用 `utm_*`：Vercel Hobby 版查 UTM 维度返回 402（要 Web Analytics Plus）。
- 只看来源（referrer）会漏：09-28 Reddit 那波约一半人来源为空（Reddit App 内置浏览器不带），带 ref 才分得清是哪一帖。

| 帖子讲的 | 落地页 |
|---|---|
| Countdown（倒数小组件） | `/countdown/`；葡语帖 `/countdown/pt-br/`，其余语言见页头语言菜单 |
| InvoiceQR（发票 / 报价单） | `/invoiceqr/`；墨西哥西语帖 `/invoiceqr/es-mx/` |
| BeforeGo（行程 / 记账） | `/beforego/` |
| 只讲某个网页工具 | 工具页本身，如 `/tools/days-until/`、`/tools/invoice-template/`、`/tools/packing-list/` |
| 讲网站本身 / 多个 app | `/` |

安卓和电脑访客在产品页首屏会看到「浏览器里就能用」的工具卡片，电脑上另有扫码下载；首页在首屏下方给非 iPhone 访客列网页工具。

查某个 ref 带来多少人（在本仓库根目录跑）：

```bash
npx -y --registry=https://registry.npmjs.org vercel@latest api "/v1/query/web-analytics/visits/aggregate?projectId=goka&slug=qinqiangji-3410&since=2026-09-29&until=2026-10-06&by=requestPath&limit=100"
```

输出里路径带 `~` 的就是带 ref 的落地；时间都是 UTC。

## 商店链接：ct 按「渠道 × app」切，不按帖子切

- 格式：`https://apps.apple.com/app/apple-store/id<appId>?pt=128309253&ct=<渠道>-<app>&mt=8`，ct 最长 30 字符。
- ASC「营销活动」里每个 ct 至少 5 次安装才显示数据，按帖子切会全部看不见；帖子之间靠官网的 ref 区分。

| app | appId | Reddit 用的链接 |
|---|---|---|
| Countdown | 6799846628 | `https://apps.apple.com/app/apple-store/id6799846628?pt=128309253&ct=reddit-countdown&mt=8` |
| InvoiceQR | 6790383156 | `https://apps.apple.com/app/apple-store/id6790383156?pt=128309253&ct=reddit-invoiceqr&mt=8` |
| BeforeGo | 6786561175 | `https://apps.apple.com/app/apple-store/id6786561175?pt=128309253&ct=reddit-beforego&mt=8` |

别的渠道把 `reddit-` 换成 `x-`、`tiktok-`、`ig-`。官网自己的按钮已经是 `web-<app>-<入口>`（`-app` / `-home` / `-tool` / `-qr`），别和社媒的混用。
