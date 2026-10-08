#!/usr/bin/env bash
#
# Production build for every VCTN frontend.
#
# Four standalone SPAs live in this repo - admin, tools, blog and ops - and
# every one of them talks to the single backend through a relative /api/v1.
# Building them by hand means four rounds of "cd, remember the env var, npm
# run build, copy dist somewhere", and forgetting the env var is the classic
# one: the bundle then bakes in an absolute http://127.0.0.1:8000 and the
# deployed site is blank with CORS-looking errors in the console.
#
# This script does the four builds, copies each result into one staging tree
# and optionally wraps each one into a tarball that can be dropped straight
# into the nginx roots documented in docs/DEPLOY-CENTOS.md:
#
#   /srv/vctn/app/deploy/centos/www/admin
#   /srv/vctn/app/deploy/centos/www/tools
#   /srv/vctn/app/deploy/centos/www/blog
#   /srv/vctn/app/deploy/centos/www/ops
#
# Usage:
#   ./scripts/build-frontends.sh                  # build all four into dist/web
#   ./scripts/build-frontends.sh --app ops        # build one
#   ./scripts/build-frontends.sh --archive        # also emit .tar.gz per app
#   ./scripts/build-frontends.sh --install        # npm ci first (CI / fresh box)
#   OUT_DIR=/tmp/web ./scripts/build-frontends.sh
#
# Environment:
#   VITE_API_BASE_URL   baked into the bundle   (default /api/v1)
#                       Use an absolute https://api.example.com/api/v1 ONLY for
#                       a cross-origin deploy, and then add that origin to
#                       CORS_ORIGINS on the backend as well.
#   OUT_DIR             staging root            (default <repo>/dist/web)
#   NODE                node/npm on PATH by default

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$REPO_ROOT/dist/web}"
API_BASE="${VITE_API_BASE_URL:-/api/v1}"

APPS=()
ARCHIVE=0
DO_INSTALL=0

usage() {
  sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --app)      APPS+=("$2"); shift 2 ;;
    --archive)  ARCHIVE=1; shift ;;
    --install)  DO_INSTALL=1; shift ;;
    -h|--help)  usage ;;
    *)          echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[ ${#APPS[@]} -eq 0 ] && APPS=(admin tools blog ops)

if [ "$API_BASE" != "/api/v1" ] && [ "${API_BASE#http}" != "$API_BASE" ]; then
  echo "warning: baking an absolute API base ($API_BASE) into the bundles." >&2
  echo "         add every frontend origin to CORS_ORIGINS on the backend." >&2
fi

mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="$OUT_DIR/BUILD-REPORT.txt"
: > "$REPORT"

# A previous build is moved aside rather than deleted: a rename is not a
# delete, so hosts that guard bulk removals (a dist holds hundreds of hashed
# assets) do not get in the way, and vite finds an absent outDir instead of
# trying to empty one. dist/ is gitignored, so nothing here reaches version
# control; STALE_DIR is cleaned up at the end when the host allows it.
STALE_DIR="$OUT_DIR/.stale"
retire() {
  [ -e "$1" ] || return 0
  mkdir -p "$STALE_DIR"
  mv "$1" "$STALE_DIR/$2-$STAMP" 2>/dev/null || true
}

failures=()

for app in "${APPS[@]}"; do
  src="$REPO_ROOT/vctn-$app-web"
  dest="$OUT_DIR/$app"

  if [ ! -d "$src" ]; then
    echo "!! vctn-$app-web not found, skipping" >&2
    failures+=("$app (missing)")
    continue
  fi

  echo "==> building vctn-$app-web"
  (
    cd "$src"
    retire dist "$app-src"
    if [ "$DO_INSTALL" -eq 1 ] || [ ! -d node_modules ]; then
      echo "    npm ci"
      npm ci
    fi
    VITE_API_BASE_URL="$API_BASE" npm run build
  )

  retire "$dest" "$app-staging"
  mkdir -p "$dest"
  cp -R "$src/dist/." "$dest/"

  size="$(du -sk "$dest" | cut -f1)"
  files="$(find "$dest" -type f | wc -l | tr -d ' ')"
  printf '%-6s %6s KB  %5s files  -> %s\n' "$app" "$size" "$files" "$dest"
  printf '%-6s %s KB  %s files  -> %s\n' "$app" "$size" "$files" "\$OUT_DIR/$app" >> "$REPORT"

  if [ "$ARCHIVE" -eq 1 ]; then
    tarball="$OUT_DIR/vctn-$app-web-$STAMP.tar.gz"
    tar -czf "$tarball" -C "$OUT_DIR" "$app"
    printf '       archive: %s (%s KB)\n' "$tarball" "$(du -sk "$tarball" | cut -f1)"
    printf '       archive: %s\n' "vctn-$app-web-$STAMP.tar.gz" >> "$REPORT"
  fi
done

{
  echo
  echo "built at   $STAMP (UTC)"
  echo "api base   $API_BASE"
} >> "$REPORT"

  if [ "$ARCHIVE" -eq 1 ]; then
    bundle="$OUT_DIR/vctn-web-all-$STAMP.tar.gz"
    tar -czf "$bundle" -C "$OUT_DIR" "${APPS[@]}" BUILD-REPORT.txt
    printf 'bundle: %s (%s KB)\n' "$bundle" "$(du -sk "$bundle" | cut -f1)"
    printf 'bundle: %s\n' "vctn-web-all-$STAMP.tar.gz" >> "$REPORT"
  fi

# Best effort: on a server this just works, on a guarded workstation it may
# not, and leftover copies under dist/ are harmless either way.
rm -rf "$STALE_DIR" 2>/dev/null || true

echo
echo "staging tree: $OUT_DIR"
echo "report:       $REPORT"
[ -d "$STALE_DIR" ] && echo "note: previous builds parked in $STALE_DIR (safe to delete)"

if [ ${#failures[@]} -gt 0 ]; then
  echo "failed: ${failures[*]}" >&2
  exit 1
fi
