#!/usr/bin/env bash
# Authenticated page sweep for the admin console.
#
# Visits every registered page in a real browser and reports, per page, the
# landing route, whether an error state or a permission wall was rendered, and
# any console error. The caller supplies a valid access token, so the sweep does
# not need a password:
#
#   VCTN_TOKEN="$(cat token.txt)" bash scripts/browser-pages.sh
#
# Requires `playwright-cli` on PATH and the dev server on the port below.

set -u

BASE_URL="${VCTN_BASE_URL:-http://localhost:5173}"
PW="${PLAYWRIGHT_CLI:-playwright-cli}"
OUT=".playwright-cli"
mkdir -p "$OUT"

if [[ -z "${VCTN_TOKEN:-}" ]]; then
  echo "VCTN_TOKEN is required" >&2
  exit 2
fi

PAGES=(
  /dashboard
  /system/users
  /system/departments
  /system/roles
  /system/permissions
  /system/dictionaries
  /system/config
  /system/feature-flags
  /system/notifications
  /sessions/online
  /sessions
  /logs/audit
  /logs/access
  /logs/security
  /logs/operation
  /logs/application
  /tools
  /tools/categories
  /tools/versions
  /tools/access-policies
  /tools/statistics
  /analytics
  /blog/articles
  /blog/review
  /blog/authors
  /blog/categories
  /blog/comments
  /growth
  /growth/points
  /growth/levels
  /growth/tasks
  /growth/achievements
  /growth/cosmetics
  /ops/jobs
  /ops/files
  /ops/exports
)

rm -f "$OUT"/console-*.log "$OUT"/page-*.yml

# Seed the session, then reload so the router guard sees the credentials.
"$PW" open "$BASE_URL/login" >/dev/null 2>&1
sleep 3
"$PW" eval "(function(){sessionStorage.setItem('vctn.admin.access_token', '${VCTN_TOKEN}');sessionStorage.setItem('vctn.admin.refresh_token', 'sweep');sessionStorage.setItem('vctn.admin.access_expires_at', String(Date.now()+900000));return 'seeded';})()" >/dev/null 2>&1

printf '%-26s %-16s %s\n' "PAGE" "LANDED" "RESULT"
printf '%s\n' "----------------------------------------------------------------------"

for path in "${PAGES[@]}"; do
  "$PW" goto "$BASE_URL$path" >/dev/null 2>&1
  sleep 2
  marker="$OUT/page-$(echo "$path" | tr '/' '_').yml"
  "$PW" snapshot --filename="$marker" >/dev/null 2>&1
  landed=$("$PW" eval "location.pathname" 2>/dev/null | grep -oE '/[A-Za-z0-9_/-]*' | head -1)

  result="OK"
  if grep -qE '"(加载失败|页面未接入)"' "$marker" 2>/dev/null; then
    result="ERROR-STATE"
  elif grep -qE '"403"' "$marker" 2>/dev/null; then
    result="NO-PERMISSION"
  fi
  if grep -qE 'Trace ID' "$marker" 2>/dev/null; then
    result="$result+TRACE"
  fi

  printf '%-26s %-16s %s\n' "$path" "${landed:-?}" "$result"
done

echo
echo "=== console errors (excluding favicon) ==="
cat "$OUT"/console-*.log 2>/dev/null | grep -viE 'favicon' | grep -iE 'error|failed|uncaught' | sort -u | head -20 || echo "(none)"
echo "=== end ==="
