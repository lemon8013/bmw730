#!/usr/bin/env bash
# Quick authenticated page check for a handful of routes.
#
#   VCTN_TOKEN="..." bash scripts/browser-check.sh /logs/audit /growth

set -u

BASE_URL="${VCTN_BASE_URL:-http://localhost:5173}"
PW="${PLAYWRIGHT_CLI:-playwright-cli}"
OUT=".playwright-cli"
mkdir -p "$OUT"
rm -f "$OUT"/console-*.log "$OUT"/check-*.yml

if [[ -z "${VCTN_TOKEN:-}" ]]; then
  echo "VCTN_TOKEN is required" >&2
  exit 2
fi

"$PW" open "$BASE_URL/login" >/dev/null 2>&1
sleep 3
"$PW" eval "(function(){sessionStorage.setItem('vctn.admin.access_token','${VCTN_TOKEN}');sessionStorage.setItem('vctn.admin.refresh_token','check');sessionStorage.setItem('vctn.admin.access_expires_at',String(Date.now()+900000));return 1;})()" >/dev/null 2>&1

for path in "$@"; do
  "$PW" goto "$BASE_URL$path" >/dev/null 2>&1
  sleep 3
  marker="$OUT/check-$(echo "$path" | tr '/' '_').yml"
  "$PW" snapshot --filename="$marker" >/dev/null 2>&1
  landed=$("$PW" eval "location.pathname" 2>/dev/null | grep -oE '/[A-Za-z0-9_/-]*' | head -1)
  echo "--- $path  -> landed=${landed:-?}"
  grep -oE '"(加载失败|页面未接入|403|暂无数据|请求超时[^"]*|无法连接[^"]*)"' "$marker" 2>/dev/null | sort -u | sed 's/^/      marker: /'
  grep -oE 'Trace ID: [A-Za-z0-9-]+' "$marker" 2>/dev/null | head -1 | sed 's/^/      /'
  grep -oE '"(确定|保存|列设置|全选|反选|取消全选|新建|新增)"' "$marker" 2>/dev/null | sort -u | tr '\n' ' ' | sed 's/^/      actions: /'
  echo
done

echo "=== console errors ==="
cat "$OUT"/console-*.log 2>/dev/null | grep -viE 'favicon' | grep -iE 'error|uncaught' | sort -u | head -15 || echo "(none)"
