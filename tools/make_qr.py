#!/usr/bin/env python3
"""产品页桌面端「用 iPhone 扫码下载」的二维码：assets/qr/<app>.svg。

  python3 -m venv /tmp/qr && /tmp/qr/bin/pip install segno && /tmp/qr/bin/python tools/make_qr.py

只在 app 的 appId 变了或新增 generated app 时重跑；生成物提交进仓库，构建脚本只引用文件、不依赖 segno。
链接不带国家（扫码后 App Store 自己落到用户所在的商店），ct=web-<app>-qr 在 ASC「营销活动」里单独计数。
"""
import json
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parent.parent
PT = "128309253"   # 与 build_seo.py / build_pages.py 同一个 provider token

def qr_url(app):
    ct = f"web-{app['key']}-qr"; assert len(ct) <= 30, ct
    return f"https://apps.apple.com/app/apple-store/id{app['appId']}?pt={PT}&ct={ct}&mt=8"

def main():
    cfg = json.loads((ROOT / "tools/site.json").read_text(encoding="utf-8"))
    out = ROOT / "assets/qr"; out.mkdir(parents=True, exist_ok=True)
    for a in cfg["apps"]:
        if not a.get("generated") or not a.get("live"):
            continue
        # 纠错级别 M：页面上约 120px，手机摄像头在 30–60 cm 外能稳定识别；深色用站点的墨色
        segno.make(qr_url(a), error="m", micro=False).save(
            str(out / f"{a['key']}.svg"), kind="svg", border=2, dark="#141414", light="#ffffff",
            xmldecl=False, svgns=True, nl=False, omitsize=True, svgclass=None, lineclass=None)
        print(f"  assets/qr/{a['key']}.svg  ← {qr_url(a)}")

if __name__ == "__main__":
    main()
