#!/usr/bin/env python3
"""从英文首页模板（index.html）生成各语言首页 /<lang>/index.html。

  python3 tools/build_home.py      # 然后必须跑 tools/build_seo.py（head、app 卡片、FAQ、页脚、语言切换由它按语言填）

只替换模板里我们自己写的句子（tools/i18n/home.json，英文源在 home.en.json）；
app 卡片是各语言商店的名字 / 副标题 / 描述首段，由 build_seo.py 的 home_card() 填。
每处替换都断言恰好命中，模板改了措辞而这里没跟上会直接报错，不会悄悄留下英文。
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N = json.loads((ROOT / "tools/i18n/home.json").read_text(encoding="utf-8"))
EN = json.loads((ROOT / "tools/i18n/home.en.json").read_text(encoding="utf-8"))
LANGS = ("de", "fr", "it", "es", "es-MX", "pt-BR", "ja", "ko", "zh-Hans", "zh-Hant", "th")
TOOLS_HUB = {"pt-BR": "/tools/pt-br/"}          # 有本语言工具目录的才换，其它指英文目录

e = lambda s: html.escape(s, quote=False)
ea = lambda s: html.escape(s, quote=True)

def localize(tpl, lang):
    t = I18N[lang]
    hub = TOOLS_HUB.get(lang, "/tools/")
    pairs = [
        ('<html lang="en">', f'<html lang="{lang}">'),
        ('>Skip to the apps</a>', f'>{e(t["skip"])}</a>'),
        ('<small>IPHONE APPS</small>', f'<small>{e(t["brand_small"])}</small>'),
        ('<a href="#apps">Apps</a>', f'<a href="#apps">{e(t["nav_apps"])}</a>'),
        ('    <a href="/tools/">Tools</a>', f'    <a href="{hub}">{e(t["nav_tools"])}</a>'),
        ('<a href="/blog/">Blog</a>', f'<a href="/blog/">{e(t["nav_blog"])}</a>'),
        ('<a href="#contact">Contact</a>', f'<a href="#contact">{e(t["nav_contact"])}</a>'),
        ('<h1 id="hero-title">Small apps for<br>everyday things.</h1>',
         f'<h1 id="hero-title">{e(t["h1_line1"])}<br>{e(t["h1_line2"])}</h1>'),
        ('aria-label="A line drawing of rolling hills, a rising sun and a small bird. Tap it to say hello."',
         f'aria-label="{ea(t["scene_label"])}"'),
        ('<span class="hint">Tap the hills to say hello</span>', f'<span class="hint">{e(t["scene_hint"])}</span>'),
        ('↻ Draw again', f'↻ {e(t["redraw"])}'),
        ('aria-label="Scroll to the apps"', f'aria-label="{ea(t["scroll_label"])}"'),
        ('<h2 class="outline" id="apps-title">Apps</h2>', f'<h2 class="outline" id="apps-title">{e(t["nav_apps"])}</h2>'),
        ('<p>Seven apps. One everyday thing each.</p>', f'<p>{e(t["apps_sub"])}</p>'),
        ('See all seven apps on the App Store ↗', f'{e(t["see_all"])} ↗'),
        ('<p class="label" style="margin:0">About go ka</p>', f'<p class="label" style="margin:0">{e(t["about_label"])}</p>'),
        (f'>{EN["quote"]}</h2>', f'>{e(t["quote"])}</h2>'),
        (f'<p>{EN["about_p1"]}</p>', f'<p>{e(t["about_p1"])}</p>'),
        (f'<p>{EN["about_p2"]}</p>', f'<p>{e(t["about_p2"])}</p>'),
        ('<p class="sign">Small apps. Everyday things.</p>', f'<p class="sign">{e(t["about_sign"])}</p>'),
        ('<h2 class="outline" id="faq-title">FAQ</h2>', f'<h2 class="outline" id="faq-title">{e(t["faq_title"])}</h2>'),
        ('<p>Short answers to what people ask.</p>', f'<p>{e(t["faq_sub"])}</p>'),
        ('<p class="label" style="margin:0">Contact</p>', f'<p class="label" style="margin:0">{e(t["contact_label"])}</p>'),
        ('<h2 id="contact-title">Say hello.</h2>', f'<h2 id="contact-title">{e(t["contact_h"])}</h2>'),
        (f'<p>{EN["contact_p"]}</p>', f'<p>{e(t["contact_p"])}</p>'),
        ('<h2>Privacy &amp; terms</h2>', f'<h2>{e(t["legal_h"])}</h2>'),
        ('<a href="/tools/">Free tools &amp; guides</a>', f'<a href="{hub}">{e(t["tools_link"])}</a>'),
        ('<p class="copy social">Follow go ka: ', f'<p class="copy social">{e(t["follow"])}{"：" if lang.startswith(("zh", "ja")) else ("\u00a0: " if lang == "fr" else ": ")}'),
    ]
    out = tpl
    for old, new in pairs:
        n = out.count(old)
        if n != 1:
            raise SystemExit(f"[{lang}] 模板里「{old[:50]}」命中 {n} 次（应为 1），模板措辞变了要同步本文件")
        out = out.replace(old, new)
    # 首屏副标题跨两行，按正则换
    out, n = re.subn(r'<p><span class="hl">Seven small iPhone apps, each made for one everyday thing\.</span>\s*'
                     r'<span class="hl">Counting down, travelling, invoicing, eating, scanning, learning, lifting\.</span></p>',
                     lambda m: f'<p><span class="hl">{e(t["hero_p1"])}</span>\n     <span class="hl">{e(t["hero_p2"])}</span></p>', out)
    if n != 1:
        raise SystemExit(f"[{lang}] 首屏副标题没命中")
    if lang.startswith("zh"):
        out = out.replace(">RedNote (小红书)</a>", ">小紅書</a>" if lang == "zh-Hant" else ">小红书</a>")
    # 页头、页脚的品牌 logo 回到本语言首页（两处）
    if out.count('<a class="brand" href="/">') != 2:
        raise SystemExit(f"[{lang}] 品牌链接应有 2 处")
    out = out.replace('<a class="brand" href="/">', f'<a class="brand" href="/{lang.lower()}/">')
    # 暂停按钮的 aria 文案在 HTML 和脚本里各出现一次
    for key, en in (("pause_label", "Pause the animation"), ("play_label", "Play the animation")):
        if en not in out:
            raise SystemExit(f"[{lang}] 找不到「{en}」")
        out = out.replace(en, t[key].replace("'", "’"))
    return out

def main():
    tpl = (ROOT / "index.html").read_text(encoding="utf-8")
    missing = [l for l in LANGS if l not in I18N]
    if missing:
        raise SystemExit(f"tools/i18n/home.json 缺语言：{missing}")
    for lang in LANGS:
        need = set(EN) - set(I18N[lang])
        if need:
            raise SystemExit(f"[{lang}] 缺字段：{sorted(need)}")
        d = ROOT / lang.lower()
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(localize(tpl, lang), encoding="utf-8")
        print(f"  /{lang.lower()}/")
    print(f"生成 {len(LANGS)} 个语言首页；接着跑 tools/build_seo.py")

if __name__ == "__main__":
    main()
