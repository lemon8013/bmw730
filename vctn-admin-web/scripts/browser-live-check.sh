#!/usr/bin/env bash
# Search the LIVE page for markers. Uses `find`, which queries the live
# accessibility tree, instead of relying on a snapshot file.
set -u

BASE="${VCTN_BASE_URL:-http://localhost:5173}"
PW="${PLAYWRIGHT_CLI:-playwright-cli}"

if [[ -z "${VCTN_TOKEN:-}" ]]; then
  echo "VCTN_TOKEN required" >&2
  exit 2
fi

"$PW" open "$BASE/login" >/dev/null 2>&1
sleep 4
"$PW" eval "(function(){sessionStorage.setItem('vctn.admin.access_token','${VCTN_TOKEN}');sessionStorage.setItem('vctn.admin.refresh_token','live');sessionStorage.setItem('vctn.admin.access_expires_at',String(Date.now()+900000));return 'ok';})()" >/dev/null 2>&1

check() {
  local route="$1"; shift
  echo "=================== $route"
  "$PW" goto "$BASE$route" >/dev/null 2>&1
  sleep 5
  "$PW" find "$(echo "$*")" 2>&1 | grep -vE '^```|^await |^###[[:space:]]*$|^$' | head -14
  echo
}

check /logs/audit          "审计日志|时间范围|列设置|查询"
check /system/dictionaries "字典管理|字典编码|列设置"
check /tools/access-policies "访问策略|列设置"
check /system/permissions  "树形结构|列表|权限"
check /dashboard           "仪表盘|超级管理员"
