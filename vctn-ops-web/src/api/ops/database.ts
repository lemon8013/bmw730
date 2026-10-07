/**
 * PostgreSQL introspection (`app/ops/database`).
 *
 * Read-only by design: there is no SQL console. Every reading shares one
 * degradation envelope, so an unreachable instance reports `UNKNOWN` plus an
 * `error` string instead of failing the request.
 */

import { get } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type {
  DatabaseCache,
  DatabaseConnections,
  DatabaseLocks,
  DatabaseOverview,
  DatabaseSlowQueries,
  DatabaseStorage,
  DatabaseTransactions,
} from '@/types/ops'

/** `GET /ops/database/overview` */
export function fetchDatabaseOverview(): Promise<DatabaseOverview> {
  return get<DatabaseOverview>(opsPath('/database/overview'))
}

/** `GET /ops/database/connections` */
export function fetchDatabaseConnections(): Promise<DatabaseConnections> {
  return get<DatabaseConnections>(opsPath('/database/connections'))
}

/** `GET /ops/database/transactions` */
export function fetchDatabaseTransactions(): Promise<DatabaseTransactions> {
  return get<DatabaseTransactions>(opsPath('/database/transactions'))
}

/** `GET /ops/database/locks` */
export function fetchDatabaseLocks(limit = 20): Promise<DatabaseLocks> {
  return get<DatabaseLocks>(opsPath('/database/locks'), { params: { limit } })
}

/** `GET /ops/database/slow-queries` */
export function fetchDatabaseSlowQueries(limit = 20): Promise<DatabaseSlowQueries> {
  return get<DatabaseSlowQueries>(opsPath('/database/slow-queries'), { params: { limit } })
}

/** `GET /ops/database/storage` */
export function fetchDatabaseStorage(limit = 20): Promise<DatabaseStorage> {
  return get<DatabaseStorage>(opsPath('/database/storage'), { params: { limit } })
}

/** `GET /ops/database/cache` */
export function fetchDatabaseCache(): Promise<DatabaseCache> {
  return get<DatabaseCache>(opsPath('/database/cache'))
}
