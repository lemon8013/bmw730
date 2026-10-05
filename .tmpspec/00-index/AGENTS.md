# VCTN Master Agent Protocol

## Highest priority

业务冻结规则 > 数据库基线 > API Contract > 模块 Spec > Agent implementation preference.

## Architecture

Admin Web and Tools Web are separate applications and must remain isolated.

## Database

Use the V3.1 unified database package as the current database baseline. Do not create duplicate identity models.

## Security

Backend authorization is authoritative. Frontend visibility is UX only.

## Sensitive data

Never log passwords, MFA secrets, full tokens, API keys, JWT raw values, cookies, tool raw inputs/outputs, user code or uploaded file content.

## Stop conditions

If requirements, DB, API or existing code conflict, stop the affected Phase and report:

- conflict
- evidence
- impact
- options
- required decision

Do not silently invent a solution.
