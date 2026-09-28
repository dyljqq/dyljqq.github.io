"""Codex 出的 1:1 原图 → 站点用的 4:5 webp（460 / 920 宽）。
用法：python3 tools/art/process.py <原图目录>   原图名 <app>-<键>.png，如 countdown-hero.png、invoiceqr-08.png
原图 1254×1254，居中裁成 4:5（prompt 要求主体留在中间 75% 宽度内）；写到 assets/art/<app>/<键>-460|920.webp。
prompt 原文在同目录 prompts.json；重画某一张就改那条 prompt 重新出图，再跑本脚本。"""
import sys, pathlib
from PIL import Image
ROOT = pathlib.Path(__file__).resolve().parents[2]
src = pathlib.Path(sys.argv[1])
FIT = {"countdown-04", "countdown-06", "countdown-10", "invoiceqr-07", "invoiceqr-05"}   # 09-28 评审：边上的道具（画笔、明信片、色卡）被居中裁 4:5 切掉；这几张背景是纯色，整张缩进去看不出接缝
for f in sorted(src.glob("*.png")):
    app, key = f.stem.split("-", 1)
    im = Image.open(f).convert("RGB"); w, h = im.size
    if f.stem in FIT:        # 主体铺满整个宽度的图：不裁，整张放进 4:5，上下用左上角背景色补齐
        bg = im.resize((1, 1), Image.LANCZOS, box=(0, 0, 60, 60)).getpixel((0, 0))
        can = Image.new("RGB", (w, round(w * 5 / 4)), bg); can.paste(im, (0, (can.height - h) // 2)); im = can
    else:
        cw = round(h * 4 / 5); x = (w - cw) // 2
        im = im.crop((x, 0, x + cw, h))
    out = ROOT / "assets/art" / app; out.mkdir(parents=True, exist_ok=True)
    for width in (460, 920):
        im.resize((width, round(width * 5 / 4)), Image.LANCZOS).save(out / f"{key}-{width}.webp", "WEBP", quality=82, method=6)
    print(app, key, [ (out / f"{key}-{wd}.webp").stat().st_size // 1024 for wd in (460, 920)], "KB")

# ---- 分享预览图（og:image）：1200×630，左边 app 图标、右边首屏插画，不放文字（所有语言共用一张）
import urllib.request, io
from PIL import ImageDraw, ImageFilter
ICONS = {"countdown": ROOT / "assets/countdown/icon.png", "beforego": ROOT / "assets/beforego/icon.png",
         "invoiceqr": "https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/35/13/55/35135590-cfaf-d2fb-2390-3d7bbb02f42c/AppIcon-0-0-1x_U007epad-0-1-85-220.png/512x512bb.png"}
def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, *im.size), r, fill=255); im.putalpha(m); return im
for app, icon in ICONS.items():
    hero = next(iter(sorted(src.glob(f"{app}-hero.png"))), None)
    if not hero: continue
    art = Image.open(hero).convert("RGB")
    bg = art.resize((1, 1), Image.LANCZOS, box=(0, 0, 60, 60)).getpixel((0, 0))
    can = Image.new("RGB", (1200, 630), bg)
    a = rounded(art.resize((550, 550), Image.LANCZOS).convert("RGBA"), 36)
    can.paste(a, (1200 - 550 - 50, 40), a)
    ic = Image.open(io.BytesIO(urllib.request.urlopen(icon, timeout=30).read()) if str(icon).startswith("http") else icon).convert("RGBA").resize((220, 220), Image.LANCZOS)
    sh = Image.new("RGBA", (300, 300), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle((40, 50, 260, 270), 50, fill=(0, 0, 0, 60))
    sh = sh.filter(ImageFilter.GaussianBlur(14)); can.paste(sh, (170 - 40, 205 - 40), sh)
    ic = rounded(ic, 50); can.paste(ic, (170, 205), ic)
    can.save(ROOT / "assets/art" / app / "og.jpg", "JPEG", quality=86, optimize=True)
    print(app, "og.jpg", (ROOT / "assets/art" / app / "og.jpg").stat().st_size // 1024, "KB")
