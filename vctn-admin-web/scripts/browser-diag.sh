#!/usr/bin/env bash
# Diagnose why the browser's XHR times out while curl succeeds.
set -u
cd "$(dirname "$0")/.."

PLAYWRIGHT="playwright-cli"
BASE="${BASE:-http://localhost:5173}"

rm -f ./*.yml .playwright-cli/*.yml

"$PLAYWRIGHT" open "$BASE/login" >/dev/null 2>&1
sleep 5

echo "== browser side =="
"$PLAYWRIGHT" eval 'location.origin' 2>/dev/null | grep -vE '^await|^```|^###' | head -2

echo "-- fetch a same-origin static file --"
"$PLAYWRIGHT" eval '(async () => { try { const r = await fetch("/vite.svg"); return "static:" + r.status; } catch (e) { return "static-err:" + e.message; } })()' 2>/dev/null | grep -vE '^await|^```|^###' | head -3

echo "-- fetch the API through the dev proxy, timed --"
"$PLAYWRIGHT" eval '(async () => { const t=Date.now(); try { const r = await fetch("/api/v1/tools"); return "api:" + r.status + " in " + (Date.now()-t) + "ms"; } catch (e) { return "api-err:" + e.name + ":" + e.message + " after " + (Date.now()-t) + "ms"; } })()' 2>/dev/null | grep -vE '^await|^```|^###' | head -3

echo "-- POST login through the dev proxy --"
"$PLAYWRIGHT" eval '(async () => { const t=Date.now(); try { const r = await fetch("/api/v1/admin/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username:"admin",password:"VctnSeed#2026Init"})}); const j = await r.json(); return "login:" + r.status + " code=" + j.code + " in " + (Date.now()-t) + "ms"; } catch (e) { return "login-err:" + e.name + ":" + e.message + " after " + (Date.now()-t) + "ms"; } })()' 2>/dev/null | grep -vE '^await|^```|^###' | head -3

"$PLAYWRIGHT" close >/dev/null 2>&1
echo "== done =="
