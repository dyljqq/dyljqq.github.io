#!/usr/bin/env bash
# 一键发布：重建 → 结构审计 → 手机端检查 → 不过就停 → Vercel 生产 → IndexNow（只推内容变了的页）→ 推 GitHub main（dyljqq.github.io 兜底）。
#   tools/publish.sh            正常发布
#   tools/publish.sh --check    只重建和检查，不发布；最后列出这次发布会向 IndexNow 推哪些 URL
set -euo pipefail
cd "$(dirname "$0")/.."
export TZ=Asia/Ho_Chi_Minh   # 日期口径固定为越南时间，不跟机器时区走（原因见 tools/build_seo.py 开头）
export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh" >/dev/null 2>&1; nvm use 22.23.1 >/dev/null 2>&1
VERCEL="npx -y --registry=https://registry.npmjs.org vercel@latest"   # 默认 npm 源 npmmirror 上解析不到 vercel@latest

python3 tools/build_tools.py | tail -1
python3 tools/build_pages.py | tail -1
python3 tools/build_home.py | tail -1
python3 tools/build_seo.py | head -1
python3 tools/check_structure.py .

PORT=$((8900 + RANDOM % 400))
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory . >/dev/null 2>&1 &
SERVER=$!; trap 'kill $SERVER 2>/dev/null || true' EXIT
sleep 1
ORIGIN=$(python3 -c "import json;print(json.load(open('tools/site.json'))['site']['origin'])")
python3 tools/sitemap.py | xargs node tools/check_mobile.mjs "http://127.0.0.1:$PORT"

[ "${1:-}" = "--check" ] && { python3 tools/indexnow.py --dry-run; echo "只检查，未发布。"; exit 0; }

if [ -n "$(git status --porcelain -- . ':!tools/gsc-indexing-log.json' ':!tools/indexnow-state.json')" ]; then
  echo "✗ 有未提交的改动，先提交再发布（发布的内容必须能在 git 里找到）。"; git status --short | head; exit 1
fi
DEPLOY_LOG=$(mktemp)
# 成功判定：整词 ready（JSON 的 "… ready." 或文本的「✓ Ready in 7s」），排除 already / not ready / error 这类失败输出
deploy_ok() { grep -Eqi '(^|[^a-z])ready([^a-z]|$)' "$1" && ! grep -Eqi 'not ready|error' "$1"; }
$VERCEL --prod --yes >"$DEPLOY_LOG" 2>&1 || true
# Vercel 偶发失败（09-26 遇到过一次，输出里只有 "retry deploy"）：自动再试一次
if ! deploy_ok "$DEPLOY_LOG"; then echo "Vercel 首次部署未就绪，重试一次…"; $VERCEL --prod --yes >"$DEPLOY_LOG" 2>&1 || true; fi
# 新版 CLI 输出 JSON（"message": "Deployment … ready."）；没有 ready 就是没部署上，停下别推 git、别报 IndexNow
if ! deploy_ok "$DEPLOY_LOG"; then echo "✗ Vercel 部署失败："; tail -20 "$DEPLOY_LOG"; exit 1; fi
grep -o '"message": "[^"]*"' "$DEPLOY_LOG" | head -1 || grep -i 'ready' "$DEPLOY_LOG" | head -1 || true

# IndexNow 只推和上次推送时比内容变了的页（新增 / 修改 / 删除，见 tools/indexnow.py）。
# 推成功才把记录提交、跟 git 一起推上去（下次从别的 worktree 发布也知道上次推过什么）；推失败或记录读不出来不拦发布，记录不提交、下次再推。
if python3 tools/indexnow.py; then
  if [ -n "$(git status --porcelain -- tools/indexnow-state.json)" ]; then
    { git add tools/indexnow-state.json && git commit -q -m "chore(indexnow): 记录本次发布后的页面 hash" -- tools/indexnow-state.json; } \
      || echo "⚠ IndexNow 记录没提交上，之后手动提交 tools/indexnow-state.json。"
  fi
else
  echo "⚠ IndexNow 没推成（原因见上一行），记录没提交；继续推 git。"
fi
git push -q origin HEAD:main && git push -q origin HEAD 2>/dev/null || true
echo "发布完成：$ORIGIN"
