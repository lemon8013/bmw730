#!/usr/bin/env bash
#
# Restore a VCTN PostgreSQL dump.
#
# THIS DESTROYS THE TARGET DATABASE. It is guarded by an explicit
# confirmation and, by default, by an interactive prompt that requires the
# database name to be typed back.
#
# Usage:
#   ./scripts/restore-db.sh backups/vctn-20261007T010000Z.dump
#   RESTORE_DB=vctn_restore ./scripts/restore-db.sh <file>
#   ./scripts/restore-db.sh --dry-run <file>      # list contents only
#
# Environment:
#   DB_HOST DB_PORT DB_USER PGPASSWORD   connection
#   RESTORE_DB       target database     (default: the database in the dump)

set -euo pipefail

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-vctn}"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 [--dry-run] <dump-file>" >&2
  exit 2
fi

DRY_RUN=0
if [[ "${1}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

dump="${1:?a dump file is required}"
if [[ ! -f "${dump}" ]]; then
  echo "error: ${dump} does not exist." >&2
  exit 2
fi

if [[ -f "${dump}.sha256" ]]; then
  echo "==> verifying checksum"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum --check "${dump}.sha256"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 --check "${dump}.sha256"
  fi
else
  echo "warning: no checksum sidecar for ${dump}." >&2
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "==> contents of ${dump}"
  pg_restore --list "${dump}"
  exit 0
fi

RESTORE_DB="${RESTORE_DB:-${DB_NAME:-vctn}}"

if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "error: PGPASSWORD is not set." >&2
  exit 2
fi

cat <<WARN
About to restore into "${RESTORE_DB}" on ${DB_HOST}:${DB_PORT}.

  --clean --if-exists drops every existing object in that database first.
  Stop the API before you continue, otherwise it keeps writing into the
  database you are rebuilding.

WARN

if [[ "${FORCE_RESTORE:-}" != "1" ]]; then
  read -r -p "Type the database name to confirm: " typed
  if [[ "${typed}" != "${RESTORE_DB}" ]]; then
    echo "aborted: '${typed}' does not match '${RESTORE_DB}'." >&2
    exit 1
  fi
fi

echo "==> restoring into ${RESTORE_DB}"
pg_restore \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --dbname="${RESTORE_DB}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --single-transaction \
  "${dump}"

echo "==> restore finished. Apply any pending migrations next:"
echo "    docker compose run --rm api migrate"
