# DEPENDENCY-INDEX

> Agent 不得自行增加、替换、删除第三方依赖。未列出的依赖必须先修改 Spec。
> 精确版本必须在正式生成 package.json / pyproject.toml 和 lock 文件时冻结；Agent 不得自行选择版本。

## Admin Web

### Runtime
- vue
- typescript
- vite
- vue-router
- pinia
- element-plus
- @element-plus/icons-vue
- axios
- dayjs
- lodash-es
- qs
- zod
- echarts
- markdown-it
- @tiptap/vue-3
- @tiptap/starter-kit
- highlight.js
- vue-i18n
- xlsx
- openapi-typescript

### Dev/Test
- vitest
- @vue/test-utils
- jsdom
- playwright
- eslint
- typescript-eslint
- eslint-plugin-vue
- prettier
- eslint-config-prettier
- vue-tsc

## Tools Web

### Runtime
- vue
- typescript
- vite
- vue-router
- pinia
- element-plus
- @element-plus/icons-vue
- axios
- dayjs
- lodash-es
- yaml
- fast-xml-parser
- @iarna/toml
- sql-formatter
- uuid
- ulid
- nanoid
- diff
- qrcode
- jsqr
- bwip-js
- browser-image-compression
- exifr
- jwt-decode
- cron-parser
- highlight.js
- openapi-typescript

### Dev/Test
- vitest
- @vue/test-utils
- jsdom
- playwright
- eslint
- typescript-eslint
- eslint-plugin-vue
- prettier
- eslint-config-prettier
- vue-tsc

## Backend

### Runtime
- fastapi
- uvicorn
- pydantic
- pydantic-settings
- sqlalchemy
- asyncpg
- alembic
- redis
- httpx
- pwdlib
- PyJWT
- pyotp
- orjson
- Pillow
- markdown-it-py
- bleach
- openpyxl
- arq
- APScheduler

### Dev/Test
- pytest
- pytest-asyncio
- pytest-cov
- ruff
- mypy

## Python standard library first
- datetime
- zoneinfo
- json
- csv
- secrets
- uuid
- hashlib
- hmac
- base64
- re
- contextvars
- logging
- asyncio
- pathlib
- typing
- enum
- dataclasses

## Forbidden without Spec change
- another ORM
- another Redis client
- another HTTP client
- another UI framework
- another task queue
- another scheduler
- another password library
- another JWT library
