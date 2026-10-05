#!/usr/bin/env bash
# Real-browser smoke test for the VCTN admin console.
#
# Runs the whole flow in one process so the playwright-cli daemon stays alive:
# open the console, sign in as the seeded administrator, then report the
# landing route, the sidebar menu and any console error.
set -u

cd "$(dirname "$0")/.."

PLAYWRIGHT="playwright-cli"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-VctnSeed#2026Init}"
BASE="${BASE:-http://localhost:5173}"

rm -f ./*.yml .playwright-cli/*.yml

echo "== 1. open login page =="
"$PLAYWRIGHT" open "$BASE/login" >/dev/null 2>&1
sleep 5
"$PLAYWRIGHT" snapshot --filename=login.yml >/dev/null 2>&1

USER_REF=$(grep -oE 'textbox "\*用户名" \[ref=e[0-9]+\]' login.yml | grep -oE 'e[0-9]+' | head -1)
PASS_REF=$(grep -oE 'textbox "\*密码" \[ref=e[0-9]+\]' login.yml | grep -oE 'e[0-9]+' | head -1)
BTN_REF=$(grep -oE 'button "登录" \[ref=e[0-9]+\]' login.yml | grep -oE 'e[0-9]+' | head -1)
echo "   refs: username=$USER_REF password=$PASS_REF button=$BTN_REF"

if [ -z "$USER_REF" ] || [ -z "$PASS_REF" ] || [ -z "$BTN_REF" ]; then
  echo "   FAIL: login form not found"
  exit 1
fi

echo "== 2. sign in =="
"$PLAYWRIGHT" fill "$USER_REF" "$ADMIN_USER" >/dev/null 2>&1
"$PLAYWRIGHT" fill "$PASS_REF" "$ADMIN_PASS" >/dev/null 2>&1
"$PLAYWRIGHT" click "$BTN_REF" >/dev/null 2>&1
sleep 8

echo "== 3. resulting route =="
"$PLAYWRIGHT" eval 'location.pathname' 2>/dev/null | grep -vE '^await|^```' | head -2

"$PLAYWRIGHT" snapshot --filename=after.yml >/dev/null 2>&1

echo "== 4. page headings =="
grep -oE 'heading "[^"]+"' after.yml | head -6

echo "== 5. sidebar entries =="
grep -oE '"[^"]*(仪表盘|系统管理|日志中心|工具管理|数据分析|内容管理|成长体系|运维中心)[^"]*"' after.yml | head -12

echo "== 6. console errors =="
LATEST_CONSOLE=$(ls -t .playwright-cli/console-*.log 2>/dev/null | head -1)
if [ -n "$LATEST_CONSOLE" ]; then
  grep -c 'ERROR' "$LATEST_CONSOLE" 2>/dev/null | sed 's/^/   error lines: /'
  grep 'ERROR' "$LATEST_CONSOLE" 2>/dev/null | head -5
else
  echo "   no console log"
fi

echo "== 7. screenshot =="
mkdir -p .playwright-cli
"$PLAYWRIGHT" screenshot --filename=.playwright-cli/admin-after-login.png >/dev/null 2>&1
ls -la .playwright-cli/admin-after-login.png 2>/dev/null || echo "   screenshot failed"

"$PLAYWRIGHT" close >/dev/null 2>&1
echo "== done =="
