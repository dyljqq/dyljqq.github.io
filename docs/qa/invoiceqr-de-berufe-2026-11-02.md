# InvoiceQR 德语两页验证记录 · 2026-11-02 · 第二轮

本轮完成内容修订与重建，没有部署、推送或向搜索引擎提交。法律依据包含用户补入事实文件的 § 35a Abs. 4、§ 14a Abs. 5 Satz 2、§ 2 Abs. 7；生成器注释已补对应关系。

| 页面 | 全站独有率 |
| --- | --- |
| `/tools/de/rechnungsvorlage-handwerker/` | 85.78% |
| `/tools/de/rechnungsvorlage-freiberufler/` | 86.88% |
| `/tools/de/rechnungsvorlage/` | 67.95% |
| `/tools/de/rechnungsvorlage-kleinunternehmer/` | 70.65% |

先顺序运行 `build_tools.py`、`build_pages.py`、`build_home.py`、`build_seo.py`，再执行结构、预算、Python 与无浏览器 Node 测试。整组命令退出 0：

```text
结构审计：页面 119，sitemap 119 条，全部通过
页面预算：本次新增 2；滚动新增 2 / 3
页面预算检查：通过；可索引 119 页，本次新增/正文变化 6 页，独有率未达标 0 页，存量警告 7 页。
Ran 70 tests in 14.079s
OK
收据：tests 5 / pass 5 / fail 0
Analytics exclusion: 39 checks passed (offline VM, mocked SDK imports only)
German invoice editor: 28 checks passed (offline VM; not a browser/PDF layout test)
```

7 个存量警告来自未改动的 `/blog/`、`/countdown/privacy-policy/`、`/invoiceqr/es-mx/`、`/invoiceqr/es/`、`/invoiceqr/privacy-policy/`、`/qrcodestudio/privacy-policy/`、`/tools/th/`。四个既有德语 InvoiceQR 工具页无独有率警告。

静态核对通过：新增问答在旧条目之后；两页 lede 后直接进入编辑器；独立可编辑的 `Leistungszeitraum` 在单据头部，第一行不再携带日期；单据及引用提示采用 Sie；App 段落保持原样；description 为 Handwerker 151 字符、Freiberufler 158 字符。原四页定义除两个 more 列表外不变；`INVOICE_JS`、`DE_NOTE` 和共享 FAQ 生成逻辑未改。

Arbeitskosten 仍手动维护，只陈述构成：450,00 € netto zzgl. 85,50 € USt (19 %)。没有自动人工费小计，也不判断客户应以哪个金额抵税。

浏览器边界：第一轮沙箱内 Chrome/localhost 被阻断；用户在第二轮开始时报告已在沙箱外跑过完整 `--check`，结构、预算、独有率及手机端 119 页全部通过。该结果属于用户对上一轮产物的验证。本轮按用户要求不重试 Chrome，不将离线 VM 检查当作当前版浏览器或实际 PDF 导出验证。
