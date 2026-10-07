#!/usr/bin/env bash
#
# Prepare a CentOS / Rocky / AlmaLinux host for VCTN.
#
# Everything here is idempotent: re-running it after a partial failure is the
# intended recovery, not a mistake. It never touches PostgreSQL data, never
# disables SELinux and never opens a port that is not needed.
#
# Usage:
#   sudo ./scripts/deploy/centos/bootstrap.sh
#   sudo ./scripts/deploy/centos/bootstrap.sh --with-docker
#
# Options:
#   --with-docker     install Docker CE and the compose v2 plugin
#   --user NAME       service account        (default vctn)
#   --root DIR        deployment root        (default /srv/vctn)
#   --no-firewall     leave firewalld alone  (a cloud security group is in front)
#   --help

set -euo pipefail

USER_NAME="vctn"
ROOT_DIR="/srv/vctn"
WITH_DOCKER="false"
WITH_FIREWALL="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-docker) WITH_DOCKER="true"; shift ;;
    --user) USER_NAME="${2:?--user needs a value}"; shift 2 ;;
    --root) ROOT_DIR="${2:?--root needs a value}"; shift 2 ;;
    --no-firewall) WITH_FIREWALL="false"; shift ;;
    --help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "error: unknown option $1" >&2; exit 2 ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "error: run as root (the script creates a service account and writes /etc)" >&2
  exit 2
fi

# shellcheck disable=SC1091
. /etc/os-release
OS_ID="${ID:-unknown}"
OS_MAJOR="${VERSION_ID%%.*}"
echo "==> detected ${PRETTY_NAME:-$OS_ID}"

case "$OS_ID" in
  centos | rhel | rocky | almalinux) ;;
  *) echo "error: unsupported distribution '$OS_ID'. This script targets rpm based hosts." >&2
     exit 2 ;;
esac

step() { printf '\n==> %s\n' "$*"; }

# --------------------------------------------------------------------------
# 1. CentOS 7 repositories
#    CentOS 7 reached end of life in 2024 and its mirrors were removed, so a
#    plain `yum install` fails before anything else can be done.
# --------------------------------------------------------------------------
if [[ "$OS_ID" == "centos" && "$OS_MAJOR" == "7" ]]; then
  step "pointing CentOS 7 at the vault / mirror repositories"
  mkdir -p /etc/yum.repos.d/disabled
  mv -f /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/disabled/ 2>/dev/null || true
  if [[ ! -f /etc/yum.repos.d/CentOS-Base.repo ]]; then
    curl -sSfL -o /etc/yum.repos.d/CentOS-Base.repo \
      https://mirrors.aliyun.com/repo/Centos-7.repo
  fi
  yum clean all >/dev/null 2>&1 || true
  yum makecache >/dev/null 2>&1 || true
fi

# --------------------------------------------------------------------------
# 2. Base packages
# --------------------------------------------------------------------------
step "installing base packages"
if command -v dnf >/dev/null 2>&1; then
  dnf install -y curl wget git tar chrony policycoreutils setools-console \
    >/dev/null
else
  yum install -y curl wget git tar chrony policycoreutils setools-console \
    >/dev/null
fi
if [[ "$WITH_FIREWALL" == "true" ]]; then
  yum install -y firewalld >/dev/null 2>&1 || dnf install -y firewalld >/dev/null 2>&1 || true
fi

# --------------------------------------------------------------------------
# 3. Clock
#    Token expiry, audit timestamps and metric buckets all assume a correct
#    clock; a drifting host produces alerts nobody can correlate.
# --------------------------------------------------------------------------
step "enabling NTP synchronisation"
systemctl enable --now chronyd >/dev/null 2>&1 || systemctl enable --now chronyd.service
chronyc tracking >/dev/null 2>&1 || true

# --------------------------------------------------------------------------
# 4. Service account and layout
# --------------------------------------------------------------------------
step "creating the service account and directories"
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd -r -m -d "$ROOT_DIR" -s /bin/bash "$USER_NAME"
fi
install -d -o "$USER_NAME" -g "$USER_NAME" -m 0750 \
  "$ROOT_DIR/app" "$ROOT_DIR/storage" "$ROOT_DIR/exports" \
  "$ROOT_DIR/backups" "$ROOT_DIR/logs"

# --------------------------------------------------------------------------
# 5. File descriptors
#    Eight containers plus nginx plus uvicorn exhaust the 1024 default long
#    before CPU does, and the failure looks like random connection resets.
# --------------------------------------------------------------------------
step "raising the file descriptor limit"
cat >/etc/security/limits.d/90-vctn.conf <<'EOF'
* soft nofile 65535
* hard nofile 65535
EOF

# --------------------------------------------------------------------------
# 6. Firewall: publish 80/443 only, never the database
# --------------------------------------------------------------------------
if [[ "$WITH_FIREWALL" == "true" ]] && command -v firewall-cmd >/dev/null 2>&1; then
  step "opening http and https"
  systemctl enable --now firewalld >/dev/null 2>&1 || true
  firewall-cmd --permanent --add-service=http >/dev/null
  firewall-cmd --permanent --add-service=https >/dev/null
  firewall-cmd --reload >/dev/null
  echo "    open services: $(firewall-cmd --list-services)"
fi

# --------------------------------------------------------------------------
# 7. Docker (container deployments)
# --------------------------------------------------------------------------
if [[ "$WITH_DOCKER" == "true" ]]; then
  step "installing Docker CE and the compose plugin"
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "    already installed: $(docker --version)"
  else
    if [[ "$OS_ID" == "centos" && "$OS_MAJOR" == "7" ]]; then
      yum install -y yum-utils device-mapper-persistent-data lvm2 >/dev/null
      if ! rpm -q container-selinux >/dev/null 2>&1; then
        yum install -y \
          https://mirrors.aliyun.com/centos/7/extras/x86_64/Packages/container-selinux-2.107-3.el7.noarch.rpm \
          >/dev/null 2>&1 || true
      fi
    else
      dnf install -y dnf-plugins-core >/dev/null
    fi

    if command -v dnf >/dev/null 2>&1; then
      dnf config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    else
      yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
    fi
    sed -i 's+download.docker.com+mirrors.aliyun.com/docker-ce+' \
      /etc/yum.repos.d/docker-ce.repo

    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin \
      || dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    install -d -m 0755 /etc/docker
    cat >/etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"],
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "7" },
  "live-restore": true
}
EOF
    systemctl daemon-reload
    systemctl enable --now docker
  fi
  usermod -aG docker "$USER_NAME" || true
  echo "    docker: $(docker --version 2>/dev/null || echo 'not available')"
fi

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
cat <<EOF

Bootstrap complete.

  deployment root   ${ROOT_DIR}
  service account   ${USER_NAME}

Next steps (container route):
  su - ${USER_NAME}
  cd ${ROOT_DIR}/app && git clone <repository> .
  cp deploy/.env.deploy.example .env && vi .env && chmod 600 .env
  for app in admin tools blog ops; do
    ( cd vctn-\${app}-web && npm ci && VITE_API_BASE_URL=/api/v1 npm run build )
  done
  docker compose run --rm api migrate
  docker compose up -d

Bare metal route and TLS setup: docs/DEPLOY-CENTOS.md
EOF
