"""重抓商店缓存 tools/store/<app>.json（iTunes lookup，按各语言已记录的 storefront）。
用法：python3 tools/fetch_store.py [--dry-run] [app ...]   默认 countdown invoiceqr beforego
  --dry-run：只比对、不写文件（每周定时任务用它检测商店有没有更新）
只覆盖 lookup 返回的字段；lookup 有几小时的缓存延迟，刚上架的版本可能还没出来。
09-28 评审发现缓存停在 09-26（三个 app 之后都发了新版），补了这个脚本。
⚠ 必须带 lang：th / sg 等商店不带 lang 时返回英文（09-28 第一次重抓就把泰语页和 InvoiceQR 简中页冲成了英文、还上线了）。"""
import json, sys, time, urllib.request, pathlib, datetime
ROOT = pathlib.Path(__file__).resolve().parents[1]
IDS = {a["key"]: a["appId"] for a in json.loads((ROOT / "tools/site.json").read_text())["apps"] if a.get("appId")}
MAP = {"name": "trackName", "version": "version", "releaseNotes": "releaseNotes", "description": "description",
       "screenshots": "screenshotUrls", "ipad": "ipadScreenshotUrls", "icon": "artworkUrl512", "minOS": "minimumOsVersion",
       "languages": "languageCodesISO2A", "rating": "averageUserRating", "ratingCount": "userRatingCount"}
LANG = {"en-US": "en_us", "en-GB": "en_gb", "de-DE": "de_de", "fr-FR": "fr_fr", "it": "it_it", "es-ES": "es_es", "es-MX": "es_mx",
        "pt-BR": "pt_br", "ja": "ja_jp", "ko": "ko_kr", "zh-Hans": "zh_cn", "zh-Hant": "zh_tw", "th": "th_th"}
NON_LATIN = ("th", "ja", "ko", "zh-Hans", "zh-Hant")
def looks_english(t):
    letters = [c for c in t if c.isalpha()]
    return bool(letters) and sum(c.isascii() for c in letters) / len(letters) > 0.6
EN_WORDS = {"the", "and", "your", "you", "with", "to", "of", "for", "is", "it", "on", "in", "a", "every", "now"}
def is_english(loc, t):
    if not t.strip(): return False
    if loc in NON_LATIN: return looks_english(t)
    words = [w.strip(".,;:!?()\"'—–-").lower() for w in t.split()]
    return sum(w in EN_WORDS for w in words) / max(1, len(words)) > 0.12
DRY = "--dry-run" in sys.argv
for app in [a for a in sys.argv[1:] if not a.startswith("--")] or ["countdown", "invoiceqr", "beforego"]:
    f = ROOT / f"tools/store/{app}.json"; data = json.loads(f.read_text()); changed = []
    for loc, cur in data.items():
        url = f"https://itunes.apple.com/lookup?id={IDS[app]}&country={cur['storefront']}&lang={LANG[loc]}"
        for attempt in range(3):
            try:
                r = json.loads(urllib.request.urlopen(url, timeout=30).read())["results"]; break
            except Exception as e:
                r = None; time.sleep(3)
        if not r:
            print(f"  ✗ {app} {loc} 抓取失败"); continue
        new = {k: r[0].get(v, cur.get(k)) for k, v in MAP.items()}
        # 原来不是英文、抓回来变成英文 → 多半是 lang 没生效，拒绝覆盖（描述和更新说明都查；拉丁语系看英语虚词占比）
        flipped = [k for k in ("description", "releaseNotes") if not loc.startswith("en")
                   and is_english(loc, new.get(k) or "") and not is_english(loc, cur.get(k) or "")]
        if flipped:
            print(f"  ✗ {app} {loc} 抓回来的 {'/'.join(flipped)} 是英文，拒绝覆盖（检查 lang 参数）"); continue
        if new["version"] != cur.get("version") or new["description"] != cur.get("description"):
            changed.append(f"{loc} {cur.get('version')}→{new['version']}{' 描述变' if new['description'] != cur.get('description') else ''}")
        cur.update(new); cur["fetched"] = datetime.date.today().isoformat()
        time.sleep(0.4)
    if not DRY:
        f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(app, "；".join(changed) or "无变化")
