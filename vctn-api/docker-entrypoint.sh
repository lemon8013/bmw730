#!/bin/sh
# Container entrypoint for vctn-api.
#
# The first argument selects the role; anything else is executed verbatim so
# that ad-hoc debugging stays possible (`docker compose run --rm api bash`).
#
#   serve          run the HTTP server                     (default)
#   migrate        apply Alembic migrations
#   seed           load the idempotent system catalogue
#   clean          purge data past its retention window
#   check-storage  put / get / delete a probe object in the object store
#
# Every tunable comes from the environment. Nothing is baked in.
set -eu

case "${1:-serve}" in
  serve)
    shift || true
    # --proxy-headers is required: behind the reverse proxy the socket peer is
    # the proxy, not the browser, and without it every request looks like it
    # came from the container network over plain HTTP.
    exec uvicorn app.main:app \
      --host 0.0.0.0 \
      --port "${PORT:-8000}" \
      --workers "${UVICORN_WORKERS:-1}" \
      --proxy-headers \
      --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
      --timeout-keep-alive "${UVICORN_KEEPALIVE:-65}" \
      "$@"
    ;;
  migrate)
    shift || true
    exec python -m alembic upgrade "$@" head
    ;;
  seed)
    shift || true
    exec python -m app.scripts.seed "$@"
    ;;
  clean)
    shift || true
    exec python -m app.scripts.cleanup "$@"
    ;;
  check-storage)
    shift || true
    exec python -m app.scripts.storage_check "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
