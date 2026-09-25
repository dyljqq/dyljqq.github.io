#!/usr/bin/env bash
# 一键发布：重建 → 结构审计 → 手机端检查 → 不过就停 → Vercel 生产 → 推 GitHub main（dyljqq.github.io 兜底）→ IndexNow。
#   tools/publish.sh            正常发布
#   tools/publish.sh --check    只重建和检查，不发布
set -euo pipefail
cd "$(dirname "$0")/.."
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh" >/dev/null 2>&1; nvm use 22.23.1 >/dev/null 2>&1
VERCEL="npx -y --registry=https://registry.npmjs.org vercel@latest"   # 默认 npm 源 npmmirror 上解析不到 vercel@latest

python3 tools/build_pages.py | tail -1
python3 tools/build_tools.py | tail -1
python3 tools/build_seo.py | head -1
python3 tools/check_structure.py .

PORT=$((8900 + RANDOM % 400))
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory . >/dev/null 2>&1 &
SERVER=$!; trap 'kill $SERVER 2>/dev/null || true' EXIT
sleep 1
ORIGIN=$(python3 -c "import json;print(json.load(open('tools/site.json'))['site']['origin'])")
python3 -c "
import re;o='$ORIGIN'
print('\n'.join(u[len(o):] for u in re.findall(r'<loc>(.*?)</loc>',open('sitemap.xml').read())))" | xargs node tools/check_mobile.mjs "http://127.0.0.1:$PORT"

[ "${1:-}" = "--check" ] && { echo "只检查，未发布。"; exit 0; }

if [ -n "$(git status --porcelain -- . ':!tools/gsc-indexing-log.json')" ]; then
  echo "✗ 有未提交的改动，先提交再发布（发布的内容必须能在 git 里找到）。"; git status --short | head; exit 1
fi
$VERCEL --prod --yes 2>&1 | grep -E '^▲ Aliased|Error' || true
git push -q origin HEAD:main && git push -q origin HEAD 2>/dev/null || true

python3 - "$ORIGIN" <<'PY'
import json, re, sys, urllib.request
origin = sys.argv[1]; host = origin.split("://")[1]
key = open("6bc0c7e758182078db2f4e3107b328d5.txt").read().strip()
urls = re.findall(r"<loc>(.*?)</loc>", open("sitemap.xml").read())
body = json.dumps({"host": host, "key": key, "keyLocation": f"{origin}/{key}.txt", "urlList": urls}).encode()
r = urllib.request.urlopen(urllib.request.Request("https://api.indexnow.org/IndexNow", data=body,
                           headers={"Content-Type": "application/json; charset=utf-8"}), timeout=30)
print(f"IndexNow {r.status}：{len(urls)} 个 URL")
PY
echo "发布完成：$ORIGIN"
