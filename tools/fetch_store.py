"""重抓商店缓存 tools/store/<app>.json（iTunes lookup，按各语言已记录的 storefront）。
用法：python3 tools/fetch_store.py [app ...]   默认 countdown invoiceqr beforego
只覆盖 lookup 返回的字段；lookup 有几小时的缓存延迟，刚上架的版本可能还没出来。
09-28 评审发现缓存停在 09-26（三个 app 之后都发了新版），补了这个脚本。"""
import json, sys, time, urllib.request, pathlib, datetime
ROOT = pathlib.Path(__file__).resolve().parents[1]
IDS = {a["key"]: a["appId"] for a in json.loads((ROOT / "tools/site.json").read_text())["apps"] if a.get("appId")}
MAP = {"name": "trackName", "version": "version", "releaseNotes": "releaseNotes", "description": "description",
       "screenshots": "screenshotUrls", "ipad": "ipadScreenshotUrls", "icon": "artworkUrl512", "minOS": "minimumOsVersion",
       "languages": "languageCodesISO2A", "rating": "averageUserRating", "ratingCount": "userRatingCount"}
for app in sys.argv[1:] or ["countdown", "invoiceqr", "beforego"]:
    f = ROOT / f"tools/store/{app}.json"; data = json.loads(f.read_text()); changed = []
    for loc, cur in data.items():
        url = f"https://itunes.apple.com/lookup?id={IDS[app]}&country={cur['storefront']}"
        for attempt in range(3):
            try:
                r = json.loads(urllib.request.urlopen(url, timeout=30).read())["results"]; break
            except Exception as e:
                r = None; time.sleep(3)
        if not r:
            print(f"  ✗ {app} {loc} 抓取失败"); continue
        new = {k: r[0].get(v, cur.get(k)) for k, v in MAP.items()}
        if new["version"] != cur.get("version") or new["description"] != cur.get("description"):
            changed.append(f"{loc} {cur.get('version')}→{new['version']}{' 描述变' if new['description'] != cur.get('description') else ''}")
        cur.update(new); cur["fetched"] = datetime.date.today().isoformat()
        time.sleep(0.4)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    print(app, "；".join(changed) or "无变化")
