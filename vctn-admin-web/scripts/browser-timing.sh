#!/usr/bin/env bash
# Time every request the login flow makes, so the slow one is unambiguous.
set -u
cd "$(dirname "$0")/.."

PLAYWRIGHT="playwright-cli"
BASE="${BASE:-http://localhost:5173}"

rm -f ./*.yml .playwright-cli/*.yml

"$PLAYWRIGHT" open "$BASE/login" >/dev/null 2>&1
sleep 5

"$PLAYWRIGHT" eval '(async () => {
  const out = [];
  const time = async (label, fn) => {
    const t = Date.now();
    try { const r = await fn(); out.push(label + " -> " + r + " (" + (Date.now() - t) + "ms)"); }
    catch (e) { out.push(label + " -> ERR " + e.name + " " + (Date.now() - t) + "ms"); }
  };
  let token = null;
  await time("POST /admin/auth/login", async () => {
    const r = await fetch("/api/v1/admin/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: "admin", password: "VctnSeed#2026Init" }) });
    const j = await r.json();
    token = j?.data?.token?.access_token ?? null;
    return "http " + r.status + " code " + j.code;
  });
  const auth = token ? { Authorization: "Bearer " + token } : {};
  await time("GET  /admin/auth/me", async () => {
    const r = await fetch("/api/v1/admin/auth/me", { headers: auth });
    const j = await r.json();
    return "http " + r.status + " code " + j.code + " perms " + (j?.data?.permissions?.length ?? "-");
  });
  await time("GET  /admin/auth/permissions", async () => {
    const r = await fetch("/api/v1/admin/auth/permissions", { headers: auth });
    const j = await r.json();
    return "http " + r.status + " code " + j.code + " menus " + (j?.data?.menus?.length ?? "-");
  });
  await time("GET  /admin/permissions/resources p1", async () => {
    const r = await fetch("/api/v1/admin/permissions/resources?page=1&page_size=100", { headers: auth });
    const j = await r.json();
    return "http " + r.status + " code " + j.code + " items " + (j?.data?.items?.length ?? "-") + " total " + (j?.data?.total ?? "-");
  });
  return out.join("\n");
})()' 2>/dev/null | grep -vE '^await|^```|^###' | head -12

"$PLAYWRIGHT" close >/dev/null 2>&1
echo "== done =="
