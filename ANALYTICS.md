# beforego.art 网站埋点方案

配置：Firebase 项目 `beforegoart`，Web App `1:448278310866:web:6ec382056194132bfa620b`，GA4 Measurement ID `G-ZHCG565YKK`。网站是多页静态站；统一从 `tools/build_seo.py` 注入客户端脚本，首页、产品、工具、文章、支持与法务页，以及全部语言版本共用一套规则。新增页面按现有构建流程生成即可覆盖。

2026-10-24 后台配置已写入并读回确认：媒体资源 `560450579`，Web 数据流 `16188106745`；增强型衡量关闭，12 个事件范围自定义维度已注册，`app_store_click` 已设为关键事件。网站代码已于同日发布到 https://beforego.art，生产部署 `goka-jgylkyxfy-qinqiangji-3410.vercel.app`，代码提交 `90dd46f`。155 页结构和手机端检查全部通过，生产浏览器已核验真实 Firebase 页面浏览、商店点击和资源 hash。详见 `tools/analytics-validation.json`。

`dyljqq.github.io` 的发布源码与同次发布保持一致；仓库 `CNAME` 指向 `beforego.art`，旧域名按相同路径跳转到正式站。首页、`/beforego/`、`/countdown/zh-hant/` 已在生产浏览器验证，避免两套网站内容分叉。后续继续使用 `tools/publish.sh` 同步发布和 GitHub main。

## 要回答的问题

1. 哪些来源、国家、设备和语言带来访问？使用 GA4 的会话来源、媒介、活动、国家和设备维度，补充 `source_ref` 读取已有 `?ref=` 渠道标签。
2. 用户在什么页面停下，是否使用工具、展开内容或切换语言？查看页面浏览、滚动深度和交互事件。
3. 哪个应用、页面、按钮位置把用户送到 App Store？以 `app_store_click` 为网站的关键意向事件，按 `target_app × page_path × section × control_id` 分析。
4. 用户看到了下载按钮却没有点击，还是根本没有看到？用 `app_store_impression` 的用户数与点击用户数对照。展示定义为按钮至少 50% 进入视口，每个按钮每次文档加载仅记一次；没有停留时长要求。

## 事件字典

| 事件 | 触发与口径 | 额外参数 |
| --- | --- | --- |
| `page_view` | 每次文档打开一次；浏览器从往返缓存恢复时再记一次 | `page_title` |
| `app_store_impression` | 自家 App 的商店链接至少 50% 进入视口 | 控件参数、商店参数 |
| `app_store_click` | 自家 App Store 链接点击，包括 SVG 子元素、键盘激活、中键 | 控件参数、商店参数 |
| `competitor_store_click` | 不在本站应用清单中的商店应用链接，单独统计，不进入自家转化 | 控件参数、商店参数 |
| `button_click` | 原生按钮、按钮型 input、`role=button` 点击；动态生成按钮也覆盖 | 控件参数 |
| `navigation_click` | 站内链接或锚点点击 | 控件参数、`link_path`、`link_domain` |
| `outbound_click` | 其他站外链接，包括 Apple 开发者页 | 控件参数、`link_domain` |
| `contact_click` | 邮件或电话链接点击；不发送地址或电话号码 | 控件参数、`link_domain` 仅协议 |
| `language_switch` | 语言菜单中的链接点击 | 控件参数、`target_language` |
| `content_toggle` | details/summary 实际展开或收起 | 控件参数、`expanded` |
| `form_start` | 首次聚焦表单内控件，每个表单每次加载一次 | `form_id`、`section` |
| `form_submit` | 浏览器验证通过后的 submit；表示提交动作，不能当成工具执行成功 | `form_id`、`section` |
| `control_change` | input、select、textarea 的 change，不按每次键入上报 | `control_type`、`section` |
| `scroll_depth` | 首次达到 25/50/75/90%，每档每次加载一次 | `percent_scrolled` |

公共参数：`site_platform=web`、`tracking_version=1`、`page_path`、`page_type`（home/product/tool/blog/legal/support 等）、`page_app`、`page_language`、`page_location`、`page_referrer`、`source_ref`。`page_app` 表示当前页面关联应用，`target_app` 表示所点的应用；跨产品入口不能把两者混用。

控件参数：`section` 识别 header/hero/end/footer 或所在区块；`control_id` 优先使用代码中的 `data-track-id`/id，否则使用标签及 DOM 顺序；`control_type` 为元素类型。需要长期对比的重要新控件可以显式添加 `data-track-id`，不必改跟踪器。`data-track-section` 可以覆盖区块名称。

商店参数：`target_app`、`app_store_id`、`store_campaign`（原链接 `ct`）、`store_country`。同一次商店点击只发一个语义事件，不再同时发 `button_click` 或 `outbound_click`。相同 `ct=web-beforego-app` 的首屏和底部 CTA 可由 `section=hero/end` 区分。原有 `pt`/`ct`/`mt` 和跳转行为保持不变。

## 分析口径

- 页面到商店点击率：同一会话内看过该页面且点击自家商店入口的会话数 ÷ 看过该页面的会话数。可以按页面、页面语言、设备、来源和目标应用拆分。
- 按钮点击率：点击指定页面、区块、控件的用户数 ÷ 看过同一按钮的用户数；只比较相同时间窗口和筛选条件。重复点击不当成新增用户。
- 工具路径：落地页 → `form_start` → `form_submit` → `app_store_click`；没有表单的工具用 `button_click`/`control_change`。GA4 漏斗需设为同一会话、依时间顺序。
- 内容路径：文章/工具页 → 产品页 → 自家商店点击；支持直接从工具页去商店的支路。
- 商店下载：继续看 App Store Connect 的活动归因与实际下载。网页无法确认用户是否打开商店、安装或付款；`app_store_click` 仅为点击意向，不能写成下载、首开或收入。
- 旧 Vercel 的 `~out-*` 行仍用于历史点击趋势。计算 Vercel PV 时须剔除这些虚拟行；Firebase PV 不包含虚拟点击页面。不要把两套平台 PV 相加。

## 工具专项：倒数壁纸生成器（2026-10-25 起）

页面 `/tools/countdown-wallpaper-maker/`，不改跟踪器，全部用现有事件 + 显式 `data-track-id`：

| 步骤 | 事件与筛选 | 说明 |
| --- | --- | --- |
| 榜单页入口 | `navigation_click`，`page_path=/tools/best-countdown-widget-apps-iphone/`、`control_id=wp-entry-best-apps` | `link_path=/tools/countdown-wallpaper-maker/`；站内链接不带 UTM |
| 英文首页入口 | `navigation_click`，`page_path=/`、`control_id=wp-entry-home` | `link_path=/tools/countdown-wallpaper-maker/`；站内链接不带 UTM |
| 落地 | `page_view`，`page_path=/tools/countdown-wallpaper-maker/` | `source_ref=wallpaper-share` = 别人分享的链接打开的（分享链接自带 `ref=wallpaper-share`；标题、日期参数不上报） |
| 开始填 | `form_start`，`form_id=wallpaper` | 每次加载一次 |
| 快捷日期 | `button_click`，`control_id=wp-preset-christmas / newyear / thanksgiving / valentines / halloween` | |
| 加照片 | `control_change`，`section=wallpaper`、`control_type=file` | 只记有选择动作，不记文件名或内容；照片不离开浏览器 |
| 保存 | `button_click`，`control_id=wp-download`，`section=wallpaper-stage` | 10-25 晚起预览实时更新，没有单独的「生成」步骤；保存是普通按钮、不发 `form_submit`（避免在输入框按回车误保存）；iPhone 走系统分享面板，网页拿不到用户最后是否点了「存储图像」 |
| 分享 | `button_click`，`control_id=wp-share-link` | 对方打开记在 `source_ref=wallpaper-share` |
| 去商店 | `app_store_impression` / `app_store_click`，`section=wallpaper-next`、`store_campaign=web-countdown-wallpaper` | 生成后才露出；页尾卡片仍是 `web-countdown-tool` |

漏斗（同一会话、按时间顺序）：`page_view` → `button_click(wp-download)`（= 保存）→ `app_store_click(web-countdown-wallpaper)`。10-25 晚之前的数据里 `form_submit` 是「生成」，之后不再有 `form_submit`。下载量以 App Store Connect 的活动 `web-countdown-wallpaper` 为准。

## 工具专项：Pagewren 里程碑卡片（2026-10-25 起）

页面 `/tools/de/meilensteinkarten-baby/`（德）与 `/tools/baby-milestone-cards/`（英），同一套脚本。起因：10-24 有德国访客从 chatgpt.com 进 `/pagewren/de/` 点了商店按钮，当天 Pagewren 有 1 个德国首次打开。

| 步骤 | 事件与筛选 |
| --- | --- |
| 落地 | `page_view`，按 `page_path` 分德 / 英 |
| 开始填 | `form_start`，`form_id=milestone` |
| 选里程碑 / 加照片 | `control_change`，`section=milestone`（`control_type=select-one` / `file`）|
| 保存卡片 | `button_click`，`control_id=mk-download`，`section=milestone-stage`（10-25 晚起没有单独的「生成」步骤，保存不发 `form_submit`）|
| 打印 13 张 | `button_click`，`control_id=mk-print` |
| 去商店 | `app_store_impression` / `app_store_click`，`section=milestone-next`，`store_campaign=web-pagewren-milestone` |

漏斗：`page_view` → `button_click(mk-download)`（= 保存）或 `mk-print` → `app_store_click(web-pagewren-milestone)`。下载以 ASC 活动 `web-pagewren-milestone` 为准；Pagewren App 的 GA4 资源是 559322873。

## 各工具的固定控件 ID（2026-10-25 补齐）

页面一改，没有 `id` / `data-track-id` 的按钮会退回「标签名 + DOM 序号」（如 `button_3`），前后版本对不上。10-25 全站审计后补齐，`lastmod` / IndexNow 比较时会忽略 `data-track-*` 属性，只补埋点不刷修改日期。

| 页面 | 关键动作 | `control_id` |
| --- | --- | --- |
| 各「还有几天」计算器（`/tools/days-until/`、pt-BR、ja） | 计算 | `calc-submit`（同时有 `form_submit`，`form_id=calc`）；分享链接 `share` |
| pt-BR 生日 / 假期 / 恋爱天数 | 计算 | `bday-submit` / `ferias-submit` / `namoro-submit` |
| 打包清单（通用、Disney） | 生成清单 | `pack-submit` |
| 单据模板（报价单、收据、发票、Angebot 等 contenteditable 页） | 打印 / 存 PDF、加一行 | `print`、`addrow`；英文发票表单 `print-invoice`、`add-invoice-item`、`inv-remove-item` |
| 泰语报价单 / 收据 | 切换单据类型 | `th-doc-quote` / `th-doc-receipt` |
| 倒数壁纸生成器 | 见上节 | `wp-*` |
| Pagewren 里程碑卡片 | 见上节 | `mk-*` |
| 产品页预览视频 | 播放 | `video-play` |

已知盲区：contenteditable 单据页里的打字没有 `change` 事件，网页只知道打开了页面和点了打印，不知道用户填了多少；要量「开始填写」得给跟踪器加接口（换 `firebase-web-v2.js` 文件名、全站重建），这次没做。

## 同批页面调整（2026-10-25）

- 巴西 5 个分州假期页并入 `/tools/pt-br/quantos-dias-faltam-para-as-ferias/`（301）；泰语收据页并入 `/tools/th/bai-sanoe-rakha/?doc=receipt`（301），页面上切换单据类型记 `button_click`，`control_id=th-doc-quote / th-doc-receipt`。旧网址的历史数据按旧 `page_path` 查。
- 新增 `/about/`，`page_type=about`。

## GA4 后台配置

发布前在与 `G-ZHCG565YKK` 对应的 Web 数据流关闭增强型衡量。页面、滚动、外跳、表单由本脚本负责，自动事件并行开启会重复计算，并可能收集未经筛选的链接。客户端通过 `initializeAnalytics(..., {config: {send_page_view: false}})` 关闭默认初始浏览，只手动上报一次真实页面浏览。

把 `app_store_click` 标为关键事件。建议注册以下事件范围自定义维度：`site_platform`、`page_type`、`page_app`、`page_language`、`section`、`control_id`、`control_type`、`target_app`、`store_campaign`、`store_country`、`source_ref`、`form_id`。页面路径、会话来源、国家和设备使用 GA4 自带维度，不重复占自定义额度。自定义维度注册后才可在常规报告中使用，不能补回过去未注册的报表维度。

复核或在配置被修改后恢复：设置 `GOOGLE_SERVICE_ACCOUNT_JSON` 指向现有服务账号文件，运行 `node tools/configure_analytics.mjs` 只读查看；加 `--write` 才执行缺失项配置。脚本先校验数据流的 Measurement ID 和 Firebase App ID，限定到上面的网站媒体资源，写后读回确认。需要本机代理时按 Node 版本启用 `HTTPS_PROXY`/`--use-env-proxy`；不把凭证复制进仓库。

## 数据边界与验证

不采集控件文字、输入值、金额、发票行、清单内容、邮箱或电话。不读取 localStorage 中的工具内容。页面 URL 仅保留符合字符规则的 `utm_source/medium/campaign/content/id` 与 `ref` 营销标签，丢弃 `name/date/desde` 等工具查询值和片段；referrer 仅保留来源站点。营销标签必须使用渠道或活动名，不能放用户标识。Google signals 与广告个性化在客户端关闭；Firebase Web Analytics 使用 Cookie，八份网站隐私说明已同步。

生产仅在 `beforego.art` 启用。localhost 和 Vercel 预览默认不上报；手动验收可加 `?analytics_debug=1`，进入 Firebase DebugView。

2026-11-01 起排除自家流量：`navigator.webdriver === true` 的自动化浏览器不加载 Firebase、不初始化统计、不发送事件，`analytics_debug=1` 也不能绕过。人工自测先访问 `https://beforego.art/?internal=1`，脚本将 `gk_analytics_internal=1` 存入 localStorage；该浏览器同源后续访问继续排除，直到访问 `?internal=0` 清除标记。此标记按浏览器配置与站点源隔离，不会同步到其他设备；localStorage 被禁用时，`internal=1` 仍排除当前页面，但不能保证后续访问持久排除。SDK 导入、支持检测完成后以及每次发送前都重新检查排除状态，避免等待期间启用排除后仍发送队列事件。

往返缓存恢复时重新读取当前排除状态：最初因 `internal=1` 或持久标记跳过初始化的页面，在另一页用 `internal=0` 清除标记后恢复，会初始化统计并记录本次 `page_view` 和后续交互。SDK 等待期间因排除标记中止的初始化，也会在清除标记后的恢复时重试。恢复不会再次应用缓存页 URL 中的旧 `internal=1`；存储读取仍被禁用时保留原页面的排除状态。如果 `internal=1` 写入失败（包括配额耗尽但读取正常），当前文档始终排除，缓存恢复不会解除；需显式访问 `?internal=0` 打开新文档恢复统计。监听安装与 SDK 启动分别管理，重复恢复只补记页面浏览，不重复安装交互监听或初始化已就绪的 SDK。

测试不允许发送真实 GA4 数据：`tools/test_analytics.mjs` 在导航前拦截所有页面网络请求，两个 Firebase 模块使用本地模拟响应，其他非本地请求一律阻断。测试先验证真实 headless 身份被排除，再仅在这个受拦截的上下文中模拟普通浏览器以检查正常事件。`tools/test_analytics_exclusion.mjs` 在离线 VM 中模拟 SDK 与 DOM，覆盖持久标记、清除、存储异常、SDK 等待竞态与往返缓存恢复；不会加载任何远程模块。

```sh
python3 tools/build_tools.py
python3 tools/build_pages.py
python3 tools/build_home.py
python3 tools/build_seo.py
python3 tools/check_structure.py .
node tools/test_analytics.mjs
node tools/test_analytics_exclusion.mjs
```

客户端位于 `assets/analytics/firebase-web-v3.js`，旧 `firebase-web-v1.js` 保留供缓存页面使用。assets 使用一年 immutable 缓存，修改脚本内容时必须换新文件名并同步生成器。SDK 使用固定 Firebase 12.4.0 CDN 模块；SDK 被屏蔽或初始化失败时，工具与链接仍可用，统计不保证送达。SDK 加载期间事件暂存内存，若用户在初始化完成前离开页面，该页队列可能丢失；点击意向应结合真实商店活动数据核对。

实现依据：[Firebase Web 事件](https://firebase.google.com/docs/analytics/web/events)、[Firebase Analytics JS API](https://firebase.google.com/docs/reference/js/analytics)、[GA4 页面浏览与去重](https://developers.google.com/analytics/devguides/collection/ga4/views)、[增强型衡量配置](https://developers.google.com/analytics/devguides/config/admin/v1/rest/v1alpha/EnhancedMeasurementSettings)。

## InvoiceQR 德语人群页（2026-11-02）

`/tools/de/rechnungsvorlage-handwerker/`、`/tools/de/rechnungsvorlage-freiberufler/` 沿用 contenteditable 单据编辑器的 `print`、`addrow`，以及商店归因 `ct=web-invoiceqr-tool`。输入与发票数据不上报；人工费备注由用户手动更新，不新增计算事件。

- 正文与 FAQ 站内链接：`iq-hw-*` / `iq-fb-*`（`navigation_click`），后缀为 `pflichtangaben`、`kleinunternehmer`、`angebot`、`app`、`iphone-guide`、另一人群名，以及 `faq-erechnung` / `b2b-fristen`。
- 法条来源链接：`iq-hw-source-*` / `iq-fb-source-*`（`outbound_click`），后缀为条文编号。
- 通用与 Kleinunternehmer 页在原有 more 条目之后追加完整问答，回答中的链接沿用：`iq-more-handwerker`、`iq-more-freiberufler`（`navigation_click`）；若独有率检查要求撤回旧页链接，则这些 ID 暂不生成。

新页署名区使用 `iq-berufe-contact`（`contact_click`）及 `iq-berufe-about`（`navigation_click`）。沿用自动生成的 FAQ 展开、页头/页尾、hub 和商店卡片埋点；无需更改跟踪器。

## Ahrefs 与 Vercel 边界（2026-11-06）

Ahrefs key按项目设置页核对，SDK仅在正式域名且非内部/自动化访问时载入。通过临时data-key手动发送pageview、tool_open、tool_action、tool_result和app_store_click；SDK默认链接/表单回调不持有key，不发送任意href/action。工具动作是点击意图；壁纸结果区分download_started/share_completed/cancelled/preview_opened/failed，不把请求或取消标记为已保存。props全为固定字符串，数量如有需转字符串。

Referrer-Policy部署改strict-origin。来源地址仍带query/hash/凭据或无效时，Ahrefs保守跳过该页采集；GA来源只取origin。Vercel beforeSend也排除内部/webdriver/敏感来源，并剔除URL所有查询和片段（仍保留固定ref路径归因）。Vercel脚本资源仍可能加载，不能把零事件说成零第三方网络请求。来源被排除的访问不是零真实访问；统计工具屏蔽/网络失败也会漏记。

离线真实Ahrefs SDK契约测试：node tools/test_ahrefs.cjs；fixture SHA256 b270afc5f9df7bcd9239c22857fb1511bba1398a28b1c3548272d720cb433c62。完整请求在本地VM拦截，不证明后台入账。旧文件保留以兼容缓存页面。
