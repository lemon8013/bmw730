# syntax=docker/dockerfile:1.7

# ---------------------------------------------------------------------------
# Build stage: resolve wheels only. Keeping this separate means the runtime
# image never carries pip's cache, gcc or the package build tree.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

WORKDIR /build

COPY requirements.lock.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-compile --no-cache-dir -r requirements.lock.txt

# ---------------------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------------------
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    TZ=UTC

# A non-root user is not optional: a container escape must not land as root
# on the host.
RUN groupadd --system --gid 10001 vctn \
    && useradd --system --uid 10001 --gid vctn --no-create-home vctn \
    && mkdir -p /app /var/lib/vctn/storage /var/lib/vctn/exports \
    && chown -R vctn:vctn /app /var/lib/vctn

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=vctn:vctn . .

# The build might have lost the executable bit (Windows / some CI checkouts).
RUN chmod +x /app/docker-entrypoint.sh

USER vctn

EXPOSE 8000

# The application reads its whole configuration from the environment; there is
# deliberately no .env baked into the image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["serve"]
