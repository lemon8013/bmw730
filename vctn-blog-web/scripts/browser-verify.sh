#!/usr/bin/env bash
# Blog page verification on the standalone blog frontend.
#
# The blog reads the catalogue anonymously, so no token is needed. Walks the
# given routes and reports the rendered title, whether the real page or an error
# state is showing, and any console errors collected meanwhile.
#
#   bash scripts/browser-verify.sh / /authors /category/BLOG_TECH
set -u

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${VCTN_BASE_URL:-http://localhost:5175}"
PW="${PLAYWRIGHT_CLI:-playwright-cli}"
OUT=".playwright-cli"
mkdir -p "$OUT"
rm -f "$OUT"/console-*.log

cd "$PROJECT"

ROUTES=("$@")
if [[ ${#ROUTES[@]} -eq 0 ]]; then
  ROUTES=(/ "/search?keyword=Python" /authors /category/BLOG_TECH)
fi

"$PW" open "$BASE/" >/dev/null 2>&1
sleep 4

printf '%-30s %-30s %s\n' "ROUTE" "BODY" "VERDICT"
printf '%s\n' "-------------------------------------------------------------------------------"

for route in "${ROUTES[@]}"; do
  "$PW" goto "$BASE$route" >/dev/null 2>&1
  sleep 5
  info="$("$PW" eval "'BODY>>>'+document.body.innerText.slice(0,80).replace(/\n/g,' | ')+'<<<URL>>>'+location.pathname" 2>&1 | grep -oE 'BODY>>>.*<<<URL>>>[^`]*' | head -1)"
  body="${info#BODY>>>}"; body="${body%%<<<URL>>>*}"
  verdict="OK"
  if [[ "$body" == *"加载失败"* ]]; then
    verdict="LOAD-FAILED"
  elif [[ "$body" == *"暂无数据"* || "$body" == *"没有匹配"* || "$body" == *"还没有使用记录"* ]]; then
    verdict="EMPTY"
  elif [[ "$body" == *"加载中"* ]]; then
    verdict="STILL-LOADING"
  fi
  printf '%-30s %-30s %s\n' "$route" "${body:0:30}" "$verdict"
done

echo
echo "=== console errors (excluding favicon) ==="
cat "$OUT"/console-*.log 2>/dev/null | grep -viE 'favicon' | grep -iE 'error|404|500' | sort -u | head -12 || true
echo "=== end ==="
