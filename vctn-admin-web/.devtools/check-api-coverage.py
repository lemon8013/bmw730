"""Cross-check every REST path the admin console calls against the live OpenAPI schema.

Reports any frontend path that has no matching server route, so a missing or
renamed endpoint is caught without clicking through the UI.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]  # vctn-admin-web/
SRC = ROOT / "src"
API_ROOT = "/api/v1"
OPENAPI_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/openapi.json"

CALL = re.compile(r"\b(?:get|post|put|patch|del)\b(?:<[^>]*>)?\s*\(\s*['\"]([^'\"]+)['\"]")


def collect() -> dict[str, list[str]]:
    calls: dict[str, list[str]] = {}
    for f in SRC.rglob("*"):
        if f.suffix not in (".ts", ".vue"):
            continue
        if "tests" in f.parts:
            continue
        text = f.read_text(encoding="utf-8")
        for match in CALL.finditer(text):
            path = match.group(1)
            if not path.startswith("/") or path in ("/",):
                continue
            if "${" in path:  # built from variables, checked separately
                continue
            calls.setdefault(path, []).append(f.as_posix())
    return calls


def main() -> int:
    spec = json.load(urllib.request.urlopen(OPENAPI_URL, timeout=30))
    api = set(spec["paths"].keys())
    calls = collect()

    missing = {p: locs for p, locs in calls.items() if (API_ROOT + p) not in api}

    print(f"frontend distinct paths : {len(calls)}")
    print(f"openapi paths           : {len(api)}")
    print()
    if not missing:
        print("OK: every frontend path resolves to a server route.")
        return 0
    print("=== frontend paths with NO server route ===")
    for path, locs in sorted(missing.items()):
        print(f"{path:58s} <- {locs[0]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
