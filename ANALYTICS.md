# beforego.art 网站埋点方案

配置：Firebase 项目 `beforegoart`，Web App `1:448278310866:web:6ec382056194132bfa620b`，GA4 Measurement ID `G-ZHCG565YKK`。网站是多页静态站；统一从 `tools/build_seo.py` 注入客户端脚本，首页、产品、工具、文章、支持与法务页，以及全部语言版本共用一套规则。新增页面按现有构建流程生成即可覆盖。

2026-10-24 后台配置已写入并读回确认：媒体资源 `560450579`，Web 数据流 `16188106745`；增强型衡量关闭，12 个事件范围自定义维度已注册，`app_store_click` 已设为关键事件。网站代码的发布状态须另行确认；后台配置完成不表示线上页面已经加载此脚本。

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

## GA4 后台配置

发布前在与 `G-ZHCG565YKK` 对应的 Web 数据流关闭增强型衡量。页面、滚动、外跳、表单由本脚本负责，自动事件并行开启会重复计算，并可能收集未经筛选的链接。客户端通过 `initializeAnalytics(..., {config: {send_page_view: false}})` 关闭默认初始浏览，只手动上报一次真实页面浏览。

把 `app_store_click` 标为关键事件。建议注册以下事件范围自定义维度：`site_platform`、`page_type`、`page_app`、`page_language`、`section`、`control_id`、`control_type`、`target_app`、`store_campaign`、`store_country`、`source_ref`、`form_id`。页面路径、会话来源、国家和设备使用 GA4 自带维度，不重复占自定义额度。自定义维度注册后才可在常规报告中使用，不能补回过去未注册的报表维度。

复核或在配置被修改后恢复：设置 `GOOGLE_SERVICE_ACCOUNT_JSON` 指向现有服务账号文件，运行 `node tools/configure_analytics.mjs` 只读查看；加 `--write` 才执行缺失项配置。脚本先校验数据流的 Measurement ID 和 Firebase App ID，限定到上面的网站媒体资源，写后读回确认。需要本机代理时按 Node 版本启用 `HTTPS_PROXY`/`--use-env-proxy`；不把凭证复制进仓库。

## 数据边界与验证

不采集控件文字、输入值、金额、发票行、清单内容、邮箱或电话。不读取 localStorage 中的工具内容。页面 URL 仅保留符合字符规则的 `utm_source/medium/campaign/content/id` 与 `ref` 营销标签，丢弃 `name/date/desde` 等工具查询值和片段；referrer 仅保留来源站点。营销标签必须使用渠道或活动名，不能放用户标识。Google signals 与广告个性化在客户端关闭；Firebase Web Analytics 使用 Cookie，八份网站隐私说明已同步。

生产仅在 `beforego.art` 启用。localhost 和 Vercel 预览默认不上报；手动验收可加 `?analytics_debug=1`，进入 Firebase DebugView。测试脚本只替换外部 SDK 传输边界，不向生产发送测试点击。

```sh
python3 tools/build_tools.py
python3 tools/build_pages.py
python3 tools/build_home.py
python3 tools/build_seo.py
python3 tools/check_structure.py .
node tools/test_analytics.mjs
```

客户端位于 `assets/analytics/firebase-web-v1.js`。assets 使用一年 immutable 缓存，修改脚本内容时必须换新文件名并同步生成器。SDK 使用固定 Firebase 12.4.0 CDN 模块；SDK 被屏蔽或初始化失败时，工具与链接仍可用，统计不保证送达。SDK 加载期间事件暂存内存，若用户在初始化完成前离开页面，该页队列可能丢失；点击意向应结合真实商店活动数据核对。

实现依据：[Firebase Web 事件](https://firebase.google.com/docs/analytics/web/events)、[Firebase Analytics JS API](https://firebase.google.com/docs/reference/js/analytics)、[GA4 页面浏览与去重](https://developers.google.com/analytics/devguides/collection/ga4/views)、[增强型衡量配置](https://developers.google.com/analytics/devguides/config/admin/v1/rest/v1alpha/EnhancedMeasurementSettings)。
