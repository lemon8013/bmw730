# 08 System API

## Health / version

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /health | Public | 进程存活 |
| GET | /ready | Public | DB/Redis 等必要依赖就绪状态 |
| GET | /version | Public | 应用版本 |

## Files

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| POST | /files/presign-upload | Auth/Public按业务策略 | FileService 生成上传授权 |
| POST | /files/complete | Auth/Public按业务策略 | 校验上传完成并保存 metadata |
| GET | /files/{id} | Auth/Public按策略 | metadata |
| GET | /files/{id}/download | Auth/Public按策略 | 下载/签名 URL |
| DELETE | /files/{id} | Auth | 权限校验后删除 |

## Notifications

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /notifications | Auth | 当前用户通知 |
| POST | /notifications/{id}/read | Auth | 仅本人 |
| POST | /notifications/read-all | Auth | 全部已读 |

## Search

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /search | Public/Auth | SearchService 聚合查询；V1 使用 PostgreSQL |

## Jobs

| Method | Path | Auth | 逻辑 |
|---|---|---|---|
| GET | /jobs/{id} | Auth | 仅允许访问自己的 job |
| POST | /jobs/{id}/cancel | Auth | 仅允许取消自己的可取消 job |
