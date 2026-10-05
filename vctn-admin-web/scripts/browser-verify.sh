#!/usr/bin/env bash
# Authenticated page verification with a freshly minted token.
#
# Mints a token immediately before opening the browser so token expiry cannot be
# mistaken for a page failure, then walks the given routes and reports the
# rendered title and whether the real page or an error screen is showing.
#
#   bash scripts/browser-verify.sh /logs/audit /system/dictionaries
set -u

PROJECT_ADMIN="$(cd "$(dirname "$0")/.." && pwd)"
API_DIR="$PROJECT_ADMIN/../vctn-api"
BASE="${VCTN_BASE_URL:-http://localhost:5173}"
PW="${PLAYWRIGHT_CLI:-playwright-cli}"
OUT=".playwright-cli"
mkdir -p "$OUT"
rm -f "$OUT"/console-*.log

cd "$PROJECT_ADMIN"

TOKEN="$(cd "$API_DIR" && PYTHONPATH=. ./.venv/Scripts/python.exe .devtools/mint_token.py admin 2>/dev/null)"
if [[ -z "$TOKEN" ]]; then
  echo "could not mint a token" >&2
  exit 2
fi

ROUTES=("$@")
if [[ ${#ROUTES[@]} -eq 0 ]]; then
  ROUTES=(/dashboard /logs/audit /logs/security /system/dictionaries /system/permissions /tools/access-policies)
fi

"$PW" open "$BASE/login" >/dev/null 2>&1
sleep 4
# NOTE: the placeholder must satisfy the server's `min_length=8` constraint on
# `refresh_token`, otherwise the refresh probe itself returns 422 and the log
# looks like a product bug.
"$PW" eval "(function(){sessionStorage.setItem('vctn.admin.access_token','${TOKEN}');sessionStorage.setItem('vctn.admin.refresh_token','verify-placeholder-not-a-real-session');sessionStorage.setItem('vctn.admin.access_expires_at',String(Date.now()+900000));return 'ok';})()" >/dev/null 2>&1

printf '%-30s %-34s %s\n' "ROUTE" "TITLE" "VERDICT"
printf '%s\n' "-------------------------------------------------------------------------------"

for route in "${ROUTES[@]}"; do
  "$PW" goto "$BASE$route" >/dev/null 2>&1
  sleep 5
  info="$("$PW" eval "'TITLE>>>'+document.title+'<<<URL>>>'+location.pathname" 2>&1 | grep -oE 'TITLE>>>.*<<<URL>>>[^`]*' | head -1)"
  title="${info#TITLE>>>}"; title="${title%%<<<URL>>>*}"
  verdict="OK"
  case "$title" in
    *页面不存在*) verdict="404-PAGE" ;;
    *登录*)       verdict="LOGIN" ;;
    *无权访问*)   verdict="403-PAGE" ;;
    "")           verdict="NO-TITLE" ;;
  esac
  printf '%-30s %-34s %s\n' "$route" "$title" "$verdict"
done

echo
echo "=== console errors (excluding favicon) ==="
cat "$OUT"/console-*.log 2>/dev/null | grep -viE 'favicon' | grep -iE 'error|404|500' | sort -u | head -12 || true
echo "=== end ==="
