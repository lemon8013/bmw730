#!/usr/bin/env bash
#
# PostgreSQL backup for VCTN.
#
# Produces a compressed, custom format dump plus a sidecar checksum, then
# removes backups older than the retention window.
#
# A dump that has never been restored is not a backup. Run
# scripts/restore-db.sh against a scratch database regularly - see RUNBOOK.
#
# Usage:
#   ./scripts/backup-db.sh                 # uses env or defaults
#   BACKUP_DIR=/mnt/backups ./scripts/backup-db.sh
#
# Environment:
#   DB_HOST DB_PORT DB_NAME DB_USER PGPASSWORD   connection
#   BACKUP_DIR        target directory          (default ./backups)
#   RETENTION_DAYS    delete older than this    (default 30)
#   S3_DESTINATION    optional "s3://bucket/prefix" to mirror to object storage

set -euo pipefail

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-vctn}"
DB_USER="${DB_USER:-vctn}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_DESTINATION="${S3_DESTINATION:-}"

if [[ -z "${PGPASSWORD:-}" ]]; then
  echo "error: PGPASSWORD is not set. Export it or use a .pgpass file." >&2
  exit 2
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "error: pg_dump not found. Install the PostgreSQL client tools." >&2
  exit 2
fi

mkdir -p "${BACKUP_DIR}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="${BACKUP_DIR}/${DB_NAME}-${stamp}.dump"
# Written before the dump so that an interrupted run never leaves a file that
# looks complete.
partial="${target}.partial"

echo "==> dumping ${DB_NAME} from ${DB_HOST}:${DB_PORT}"
if ! pg_dump \
  --host="${DB_HOST}" \
  --port="${DB_PORT}" \
  --username="${DB_USER}" \
  --dbname="${DB_NAME}" \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-acl \
  --file="${partial}"; then
  echo "error: pg_dump failed; nothing was promoted to a backup." >&2
  rm -f "${partial}"
  exit 1
fi

mv "${partial}" "${target}"

# Verify the archive is readable. pg_restore --list reads the table of
# contents without touching a database.
if ! pg_restore --list "${target}" >/dev/null 2>&1; then
  echo "error: the dump is not readable - treating it as failed." >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${target}" > "${target}.sha256"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "${target}" > "${target}.sha256"
fi

size="$(du -h "${target}" | cut -f1)"
echo "==> backup written: ${target} (${size})"

if [[ -n "${S3_DESTINATION}" ]]; then
  if command -v aws >/dev/null 2>&1; then
    echo "==> mirroring to ${S3_DESTINATION}"
    aws s3 cp "${target}" "${S3_DESTINATION}/"
  else
    echo "warning: S3_DESTINATION is set but the aws cli is missing." >&2
  fi
fi

if [[ "${RETENTION_DAYS}" -gt 0 ]]; then
  echo "==> removing backups older than ${RETENTION_DAYS} days"
  find "${BACKUP_DIR}" -maxdepth 1 -type f \
    \( -name "${DB_NAME}-*.dump" -o -name "${DB_NAME}-*.sha256" \) \
    -mtime "+${RETENTION_DAYS}" -print -delete
fi

echo "==> done"
