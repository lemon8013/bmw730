# CentOS 部署手册

适用：CentOS 7 / CentOS Stream 8 / 9、Rocky Linux、AlmaLinux，单机或两台（应用 + 数据库）。
本文的目标是**照着做就能起来**，每条命令都说明了为什么，出问题知道去哪看。

---

## 0. 先选路线

| 路线 | 适合 | 代价 |
| --- | --- | --- |
| **A. 容器（推荐）** | 绝大多数场景，尤其是 CentOS 7 | 需要 Docker；数据库也在容器里（或接托管库） |
| **B. 裸机 systemd** | 无法装容器、要复用现有 PG/Nginx 的环境 | 需自行准备 Python 3.13 / Node 22 |

> **CentOS 7 必须走容器路线。** CentOS 7 的 OpenSSL 是 1.0.2，Python 3.13 在其上编译出的 ssl 模块不满足现代 TLS 要求，而裸机路线绕不开 Python 3.13（项目依赖 `asyncpg`、`APScheduler`，Python 最低要求 3.13）。CentOS Stream 9 / Rocky 9 两条路线都可以。

先填下面的信息，后面所有命令都引用它们：

| 项 | 示例 | 说明 |
| --- | --- | --- |
| 管理端域名 | `admin.example.com` | 后台管理（5173 对应 containers → `web-admin`） |
| 工具站域名 | `tools.example.com` | 匿名可用 |
| 博客域名 | `www.example.com` | |
| 运维域名 | `ops.example.com` | 报表/告警控制台 |
| API 域名 | `api.example.com` | 后端，四个前端都把 `/api/` 打到它身上 |
| 服务器 | 4C8G 起 | PG + Redis + 8 容器同机时建议 8C16G |

**四个前端全部通过相对路径 `/api/v1` 调后端，没有反向代理就是白屏** —— 这是最容易踩的一颗雷，本文第 4 节专门处理。

---

## 1. 系统基线（两条路线都要做）

```bash
# 1.1 时间必须准：token 过期、审计时间戳、指标分桶全部依赖它
yum install -y chrony
systemctl enable --now chronyd
chronyc tracking | grep "Reference ID"   # 有输出即已同步；空的先把 NTP 放行

# 1.2 部署用户：不要用 root 跑应用
useradd -r -m -d /srv/vctn -s /bin/bash vctn
mkdir -p /srv/vctn/{app,storage,exports,backups,logs}
chown -R vctn:vctn /srv/vctn

# 1.3 防火墙：只开 80/443，数据库端口绝不对外
systemctl enable --now firewalld
firewall-cmd --permanent --add-service=http --add-service=https
firewall-cmd --reload
firewall-cmd --list-all      # 必须只有 http https ssh

# 1.4 文件句柄：8 个容器 +nginx+uvicorn，默认的 1024 会先被打满
cat >/etc/security/limits.d/90-vctn.conf <<'EOF'
* soft nofile 65535
* hard nofile 65535
EOF

# 1.5 CentOS 7 已经 EOL，官方源下线，先换源再装任何东西（略过这步会卡在 yum）
# Stream 8/9、Rocky、Alma 不需要执行
curl -sSfL -o /etc/yum.repos.d/CentOS-Base.repo https://mirrors.aliyun.com/repo/Centos-7.repo
yum clean all && yum makecache
```

SELinux：**保持开启**，不要图省事关掉。CentOS 7/8 上 nginx 反代本机端口会被拦，第 4.3 节有对应放行命令；关掉 SELinux 换来的是一次说不清的安全审计问题。

---

## 2. 路线 A：容器部署

### 2.1 安装 Docker CE 与 compose 插件

```bash
yum install -y yum-utils device-mapper-persistent-data lvm2
yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo
sed -i 's+download.docker.com+mirrors.aliyun.com/docker-ce+' /etc/yum.repos.d/docker-ce.repo

yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

# 国内镜像加速（可选，能省一半构建时间）
mkdir -p /etc/docker
cat >/etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://docker.m.daocloud.io"],
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "7" },
  "live-restore": true
}
EOF
systemctl restart docker
docker compose version    # 必须输出 v2.x，compose 文件路径带 "-" 而非 "docker-compose"
```

> CentOS 7 若报 `container-selinux` 冲突：先 `yum install -y https://mirrors.aliyun.com/centos/7/extras/x86_64/Packages/container-selinux-2.107-3.el7.noarch.rpm`。

### 2.2 放代码、填配置

```bash
su - vctn
cd /srv/vctn/app
git clone <你的仓库地址> .            # 或 rsync/scp 上传后 chown -R vctn:vctn

cp deploy/.env.deploy.example .env
vi .env                                # 逐项填写，下面这几项填错的概率最高
#   ADMIN_HOST / TOOLS_HOST / BLOG_HOST / OPS_HOST / API_HOST   → 你的四个域名
#   ALLOWED_HOSTS                                              → 同上五个，逗号分隔，不带协议不带端口
#   CORS_ORIGINS                                               → https://域名，必须是浏览器实际地址栏里的 origin
#   AUTH_JWT_SECRET                                            → 生成一次，永久保存
#   DB_PASSWORD / REDIS_PASSWORD                               → 真随机口令
#   S3_ACCESS_KEY / S3_SECRET_KEY                              → 对象存储凭据，不能用 rustfsadmin 样例值
openssl rand -base64 36                # 用它生成 DB_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # 生成 AUTH_JWT_SECRET

chmod 600 .env                         # 里面有口令，只允许部署用户读
```

`.env` 的其余关键项（已在模板里注释）：`SNOWFLAKE_NODE_ID` 多副本时**每个实例必须不同**，否则主键静默冲突；`OPS_SCHEDULER_ENABLED=true` 打开周期性任务（调度器已在 `docker-compose.yml` 里默认打开）。

### 2.3 构建前端

镜像构建会把源码打包进去，所以前端必须在构建之前编译：

```bash
cd /srv/vctn/app
for app in admin tools blog ops; do
  ( cd vctn-$app-web && npm ci --omit=dev && VITE_API_BASE_URL=/api/v1 npm run build )
done
```

`VITE_API_BASE_URL` 必须是 `/api/v1`（同域部署）。跨域部署才写全 URL，且必须同时在 `CORS_ORIGINS` 里。

### 2.4 迁移、初始化、启动

```bash
cd /srv/vctn/app
docker compose run --rm api migrate                    # alembic upgrade head
VCTN_SEED_ADMIN_PASSWORD='<强口令>' \
  docker compose run --rm -e VCTN_SEED_ADMIN_PASSWORD api seed --mode=system
docker compose up -d

docker compose ps                                      # 8 个服务全部 Up
docker compose logs -f api                             # ctrl+c 退出，出现 Application startup complete 即可
```

> **种子跑完后立即改掉管理员密码** —— 它出现在 shell history、CI 日志和命令行里。用种子密码登录一次，改密码，再删除 history 条目。

### 2.5 日常运维

```bash
docker compose logs -f --tail=200 api      # 看日志
docker compose restart api                 # 重启单个服务
docker compose run --rm api clean --dry-run  # 保留清理先看数字，去掉 --dry-run 才真删
scripts/backup-db.sh                       # 备份（见 RUNBOOK.md）
```

---

## 3. 路线 B：裸机 systemd（Stream 8/9、Rocky、Alma）

### 3.1 安装运行时

```bash
# PostgreSQL 18（官方源，别用系统自带的 9.x/10）
dnf install -y https://download.postgresql.org/pub/repos/yum/repo/redhat/rhel-9-x86_64/pgdg-redhat-repo-latest.noarch.rpm
dnf -qy module disable postgresql
dnf install -y postgresql18-server postgresql18 redis nginx git gcc make openssl-devel libpq-devel
/usr/pgsql-18/bin/postgresql-18-setup initdb
systemctl enable --now postgresql-18 redis nginx

# Node 22（前端构建）
dnf module reset nodejs -y && dnf module enable nodejs:22 -y && dnf install -y nodejs

# Python 3.13
dnf install -y python3.13 python3.13-devel || {
  # Stream 8 没有 3.13 包时走源码，装到独立前缀，绝不动系统 python
  cd /usr/src && curl -sSfLO https://www.python.org/ftp/python/3.13.3/Python-3.13.3.tgz \
    && tar xf Python-3.13.3.tgz && cd Python-3.13.3 \
    && ./configure --prefix=/opt/py313 --enable-optimizations && make -j"$(nproc)" && make altinstall
}
```

### 3.2 建库

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE vctn LOGIN PASSWORD '换成强口令';
CREATE DATABASE vctn OWNER vctn ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';
SQL
# client_min_messages / max_connections 建议：连接池 20×实例 + 富余，PG 默认 100 偏紧
grep -q max_connections /var/lib/pgsql/18/data/postgresql.conf \
  && sed -i "s/^#\?max_connections.*/max_connections = 200/" /var/lib/pgsql/18/data/postgresql.conf
systemctl restart postgresql-18
```

### 3.3 部署后端

```bash
su - vctn
cd /srv/vctn/app/vctn-api
/opt/py313/bin/python3.13 -m venv .venv            # 或 python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.lock.txt

cat > /srv/vctn/app/vctn-api/.env <<'EOF'
# 与 deploy/.env.deploy.example 同结构，DB_HOST=127.0.0.1、REDIS_HOST=127.0.0.1
APP_ENV=production
...
EOF
chmod 600 .env

alembic upgrade head
VCTN_SEED_ADMIN_PASSWORD='<强口令>' python -m app.scripts.seed --mode=system
```

systemd 单元（已放在 `scripts/deploy/centos/vctn-api.service`）：

```bash
sudo cp /srv/vctn/app/scripts/deploy/centos/vctn-api.service /etc/systemd/system/
sudo sed -i 's#/srv/vctn/app#/srv/vctn/app#' /etc/systemd/system/vctn-api.service
sudo systemctl daemon-reload && sudo systemctl enable --now vctn-api
sudo systemctl status vctn-api
journalctl -u vctn-api -f
```

> **worker 数量**：单元文件里 `--workers 1`，因为内置调度器在进程内。要多核就先把 `OPS_SCHEDULER_ENABLED` 关掉，只在一个实例/进程上留 true。

### 3.4 前端与 Nginx

```bash
cd /srv/vctn/app
for app in admin tools blog ops; do
  ( cd vctn-$app-web && npm ci && VITE_API_BASE_URL=/api/v1 npm run build \
    && rsync -a --delete dist/ /srv/vctn/app/deploy/centos/www/$app/ )
done
sudo cp scripts/deploy/centos/nginx-vctn.conf /etc/nginx/conf.d/vctn.conf
sudo nginx -t && sudo systemctl reload nginx
```

多 localhost 端口（8000）被 SELinux 拦的典型表现是 nginx 日志 `Permission denied` 而后端毫无访问记录：

```bash
sudo setsebool -P httpd_can_network_connect 1
```

---

## 4. TLS 与反向代理（两条路线都要 —— 这一步没做前端就是白屏）

### 4.1 签证书

```bash
yum install -y certbot python3-certbot-nginx      # Stream 8/9
# CentOS 7 用 certbot-auto 或手动签发
certbot certonly --nginx -d admin.example.com -d tools.example.com \
                          -d www.example.com -d ops.example.com -d api.example.com
# 续期（certbot 已自带 timer）
systemctl status certbot-renew.timer
```

### 4.2 容器路线

容器路线用仓库里的 `deploy/nginx/templates/vctn.https.conf.template`（compose 的 gateway 容器负责反向代理），只需把证书挂进去：

```bash
docker compose down gateway
# 在 compose 的 gateway.volumes 增加证书挂载后 up -d（HTTPS 模板已在 deploy/nginx/templates 下）
```

### 4.3 必须存在的几条转发规则

```nginx
location /api/     { proxy_pass http://api:8000/api/; }   # 容器；裸机改成 http://127.0.0.1:8000/api/
location /health   { proxy_pass http://api:8000/health; }
location /ready    { proxy_pass http://api:8000/ready; }
location /version  { proxy_pass http://api:8000/version; }
location /         { try_files $uri $uri/ /index.html; }  # SPA 刷新 404 的修法
```

裸机路线直接用 `scripts/deploy/centos/nginx-vctn.conf`，里面已经按五个域名写好了。

## 4.4 对象存储（RustFS，S3 兼容）

所有上传的文件与图片都走后端的对象存储抽象层（`app/shared/storage/`），两个实现：

| provider | 适用 | 说明 |
| --- | --- | --- |
| `s3` / `rustfs` | **生产默认** | 任意 S3 兼容端点：RustFS、MinIO、Ceph RGW、云厂商 OSS。多副本看到同一份数据 |
| `local` | 单机试点 | 落在 `FILE_STORAGE_ROOT` 下。**两副本就是两份互不相干的数据，容器重启即丢** |

`rustfs` 与 `s3` 是同一个后端，只是写起来更清楚；`minio` 作为历史别名继续可用，`sys_file.storage_provider` 里记录的统一是 `s3`。

裸机路线不含对象存储服务：单独用容器或二进制起一个 RustFS（只在 127.0.0.1 监听 9000），
然后把 `S3_ENDPOINT` 指向它。多副本部署**不能**用 `local`。

容器路线已在 `docker-compose.yml` 里排好：一个 `rustfs` 服务（只在 `backend` 私有网络，不对外发布端口）+ 一个一次性的 `rustfs-chown`（RustFS 以 uid 10001 运行，新卷默认是 root 的）+ api 的 `S3_*` 环境变量。只需在 `.env` 里填凭据。

**凭据不要用样例值。** RustFS 的快速启动默认是 `rustfsadmin` / `rustfsadmin`，后端在 `APP_ENV=production` 下会直接拒绝启动（MinIO 的 `minioadmin` 同样在黑名单里）：

```bash
openssl rand -base64 36    # 用它生成 S3_SECRET_KEY，至少 12 位
```

填进 `.env`（`/srv/vctn/app/.env`）：

```dotenv
FILE_STORAGE_PROVIDER=rustfs
RUSTFS_IMAGE=rustfs/rustfs:latest       # 上线前固定成具体 tag 或 digest
RUSTFS_CORS_ALLOWED_ORIGINS=https://admin.example.com
S3_ENDPOINT=http://rustfs:9000          # 容器内用服务名；外部 S3 填 https://…
S3_BUCKET=vctn
S3_REGION=us-east-1
S3_ACCESS_KEY=vctn-api
S3_SECRET_KEY=<上面生成的随机串>
S3_SECURE=false                          # 走 TLS 前置代理时改 true
S3_ADDRESSING_STYLE=path                 # 裸主机名用 path；virtual 需要 *.rustfs 泛解析
S3_AUTO_CREATE_BUCKET=true               # 首次启动由 API 建桶
```

浏览器直传还差一条：RustFS 要允许管理端域名的跨域 PUT，否则控制台里的上传会卡在 CORS 报错上（看不出来是对象存储的问题）。compose 里就是 `RUSTFS_CORS_ALLOWED_ORIGINS`，改完 `docker compose up -d rustfs` 生效。

**几个 RustFS 特有的点**：

- 健康检查是 `curl -fsS http://127.0.0.1:9000/health`（不是 MinIO 的 `/minio/health/live`），compose 已按这个写；
- 数据目录属主必须是 `10001:10001`，否则容器起来但写不进去 —— 用 bind mount 时先 `chown -R 10001:10001 /path`；
- 控制台在 9001，**不要发布到 0.0.0.0**，需要时走 SSH 隧道：`ssh -L 9001:rustfs:9001 user@host`；
- 它只有一对凭据，没有 MinIO 那种 `mc admin user svcacct add` 的服务账号体系，所以这对密钥的轮换要自己排期。

填完凭据后立刻自检（写、读、删一个探针对象，失败会给出明确原因）：

```bash
docker compose run --rm api check-storage        # 容器
# 裸机：
cd /srv/vctn/app/vctn-api && python -m app.scripts.storage_check
```

可以用 `--only export_objects` 单独清理过期导出对象（`python -m app.scripts.cleanup --dry-run` 先看数量）。

---

## 5. 上线验收清单

按顺序跑一遍，任何一条不过都别对外开放：

```bash
# 1. 探针
curl -i --noproxy '*' https://api.example.com/health          # 200
curl -i --noproxy '*' https://api.example.com/ready           # 200，DB/Redis 不通会返回非 200

# 2. 安全头（-I 里必须看到 X-Content-Type-Options / X-Frame-Options / Referrer-Policy）
curl -I https://api.example.com/health

# 3. 生产必须关文档
curl -o /dev/null -s -w "%{http_code}\n" https://api.example.com/docs      # 404
curl -o /dev/null -s -w "%{http_code}\n" https://api.example.com/openapi.json  # 404

# 4. 四个前端能登录 / 匿名可用；ops 登录后落地页是报表页
# 5. ops 控制台「可用性」里出现 vctn_api_self_health 且每分钟有新结果 → 调度器在跑
# 6. 备份：scripts/backup-db.sh，然后在另一台机器按 RUNBOOK.md 恢复一次
# 7. 对象存储：管理端「文件管理 → 上传文件」，再点「下载」必须拿到同一个文件
curl -s --noproxy '*' https://api.example.com/ready \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['checks']['object_storage'])"
```

ops 权限目前只授予 `SUPER_ADMIN`，用种子管理员登录即可看到全部运维页面。

---

## 6. 排障速查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 前端能打开，所有请求 404/CORS 报错 | 反向代理缺 `/api/` 转发 | 第 4.3 节 |
| 后端返回 400 且 body 提到 Host | `ALLOWED_HOSTS` 没包含实际域名 | 改 `.env` 后 `docker compose up -d api` |
| 容器起不来，日志：`DB_PASSWORD is required` | `.env` 没放到仓库根目录 | compose 读的是仓库根的 `.env` |
| nginx 502 | api 未健康 | `docker compose logs api`，多数是数据库未就绪或迁移未跑 |
| nginx `Permission denied`（裸机） | SELinux | `setsebool -P httpd_can_network_connect 1` |
| 上传成功但打开 403 / `SignatureDoesNotMatch` | 端点填错或 `S3_ADDRESSING_STYLE` 与桶名 DNS 不匹配 | 改用 `path`；确认 `S3_ENDPOINT` 是浏览器/容器真正访问到的地址 |
| 控制台上传卡在 CORS | RustFS 未放行管理端 origin | 设 `RUSTFS_CORS_ALLOWED_ORIGINS` 后 `docker compose up -d rustfs` |
| 后台日志 `object storage is not ready` | 桶不存在或凭据错 | `docker compose run --rm api check-storage` |
| ops 页面全是空 | 调度器未开或没数据源 | `.env` 里 `OPS_SCHEDULER_ENABLED=true`，确认 seed 已跑出自监控检查项 |
| 多副本后偶发主键冲突 | `SNOWFLAKE_NODE_ID` 重复 | 每个实例不同值 |
| 表越查越慢 | 清理任务没跑 | `docker compose run --rm api clean --dry-run`，并确认调度器开启 |

---

## 7. 升级与回滚

```bash
# 升级
docker compose run --rm api clean --dry-run            # 可选：先看数据量
scripts/backup-db.sh                                    # 必须：先备份
git pull                                                # 拉代码
for app in admin tools blog ops; do ( cd vctn-$app-web && npm ci && npm run build ); done
IMAGE_TAG=$(git rev-parse --short HEAD) docker compose up -d --build
docker compose run --rm api migrate                     # 迁移在服务启动之后跑
curl -fsS https://api.example.com/ready                 # 冒烟

# 回滚
IMAGE_TAG=<上一个 tag> docker compose up -d             # 回滚代码
# 迁移降级见 docs/RUNBOOK.md；数据回滚只能用第 5 步的备份
```

---

## 附：本文引用的文件

| 文件 | 作用 |
| --- | --- |
| `scripts/deploy/centos/bootstrap.sh` | 系统基线一键准备（chrony / firewall / limits / vctn 用户 / Docker） |
| `scripts/deploy/centos/vctn-api.service` | 裸机路线的 systemd 单元 |
| `scripts/deploy/centos/nginx-vctn.conf` | 裸机路线的 nginx 站点（含 `/api/` 转发与 SPA fallback） |
| `docker-compose.yml` | 容器路线全栈编排 |
| `deploy/.env.deploy.example` | 部署变量清单 |
| `docs/RUNBOOK.md` | 值班手册、备份恢复、回滚 |
| `GO-LIVE-CHECKLIST.md` | 上线待办与验收标准 |
