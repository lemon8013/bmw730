#!/usr/bin/env bash
# Authenticated diagnostics: proves whether a deep link renders the real page.
set -u

BASE="${VCTN_BASE_URL:-http://localhost:5173}"
PW="${PLAYWRIGHT_CLI:-playwright-cli}"
OUT=".playwright-cli"
mkdir -p "$OUT"

if [[ -z "${VCTN_TOKEN:-}" ]]; then
  echo "VCTN_TOKEN required" >&2
  exit 2
fi

"$PW" open "$BASE/login" >/dev/null 2>&1
sleep 4
"$PW" eval "(function(){sessionStorage.setItem('vctn.admin.access_token','${VCTN_TOKEN}');sessionStorage.setItem('vctn.admin.refresh_token','diag');sessionStorage.setItem('vctn.admin.access_expires_at',String(Date.now()+900000));return 'seeded';})()" 2>&1 | tail -2

echo "--- auth/me from inside the browser ---"
"$PW" eval "(async()=>{try{const t=sessionStorage.getItem('vctn.admin.access_token');const r=await fetch('/api/v1/admin/auth/me',{headers:{Authorization:'Bearer '+t}});const j=await r.json();return 'me status='+r.status+' code='+j.code+' perms='+(((j.data||{}).permissions||[]).length);}catch(e){return 'me err '+e.message;}})()" 2>&1 | tail -3

echo "--- auth/permissions from inside the browser ---"
"$PW" eval "(async()=>{try{const t=sessionStorage.getItem('vctn.admin.access_token');const r=await fetch('/api/v1/admin/auth/permissions',{headers:{Authorization:'Bearer '+t}});const j=await r.json();const d=j.data||{};return 'perm status='+r.status+' code='+j.code+' menus='+((d.menus||[]).length);}catch(e){return 'perm err '+e.message;}})()" 2>&1 | tail -3

echo "--- /version probe from inside the browser ---"
"$PW" eval "(async()=>{try{const r=await fetch('/version');const j=await r.json();return 'version status='+r.status+' code='+j.code+' v='+((j.data||{}).version);}catch(e){return 'version err '+e.message;}})()" 2>&1 | tail -3

for route in /logs/audit /system/dictionaries /tools/access-policies; do
  echo "--- goto $route ---"
  "$PW" goto "$BASE$route" >/dev/null 2>&1
  sleep 5
  "$PW" eval "'PATH='+location.pathname+' TEXT='+document.body.innerText.replace(/\n/g,' / ').slice(0,220)" 2>&1 | tail -3
done

echo "--- console errors ---"
cat "$OUT"/console-*.log 2>/dev/null | grep -viE 'favicon' | grep -iE 'error|404|500' | sort -u | head -10 || true
