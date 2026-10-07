# VCTN Seed Data Report

- Status: **FAIL**
- Mode: `system`
- Command: `python -m app.scripts.seed --mode=system --runs=1`
- Administrator: `admin` (password NOT SHOWN)

## Runs

| Run | Created | Skipped |
| --- | --- | --- |
| 1 | 254 | 1144 |

- Idempotency: **PASS**

## Row counts

| Collection | Rows |
| --- | --- |
| Departments | 1 |
| Roles | 3 |
| Permissions | 534 |
| Permission Matrix | 64 |
| Runtime-Extra Permissions | 35 |
| API Permissions | 327 |
| API Permissions Guarded | 233 |
| Dictionary Types | 27 |
| Dictionary Items | 95 |
| Configs | 38 |
| Feature Flags | 4 |
| Levels | 6 |
| Growth Rules | 5 |
| Point Rules | 5 |
| Cosmetics | 6 |
| Tasks | 3 |
| Achievements | 3 |
| Tool Categories | 11 |
| Tools | 23 |
| Tool Versions | 23 |
| Tool Components | 18 |
| Tool Policies | 46 |
| Blog Categories | 4 |

## Checks

| Check | Result | Detail |
| --- | --- | --- |
| super_admin_state | FAIL | ACTIVE / SUPER_ADMIN / must_change_password |
| security | PASS | administrator password is stored as a hash only |
| super_admin_grants | PASS | 534/534 permissions granted |
| tool_graph_complete | PASS | all tools have category+version+component+policy |
| levels_present | PASS | 6 level(s) |
| growth_rules_event_bound | PASS | 5 growth rule(s) |
| tasks_event_bound | PASS | 3 task(s) |
| achievements_event_bound | PASS | 3 achievement(s) |
| permission_matrix_complete | PASS | 64 frozen codes present |
| runtime_extra_permissions_present | PASS | 35 matrix-external codes seeded |
| route_guards_known | PASS | 83 distinct guard code(s) all exist |
| api_endpoint_coverage | PASS | 327 live endpoint(s) have an API permission |
| api_permission_tree_linked | PASS | 233/233 guarded endpoint(s) attached to their permission |

> Passwords, password hashes, tokens, secrets and connection strings are never rendered in this report.
