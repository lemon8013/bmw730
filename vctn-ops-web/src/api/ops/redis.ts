/**
 * Redis introspection (`app/ops/redis`).
 *
 * Read-only informational commands only. Like the PostgreSQL collector, an
 * unreachable or unconfigured cache degrades into a structured reading.
 */

import { get } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { RedisClients, RedisKeyspace, RedisMemory, RedisOverview } from '@/types/ops'

/** `GET /ops/redis/overview` */
export function fetchRedisOverview(): Promise<RedisOverview> {
  return get<RedisOverview>(opsPath('/redis/overview'))
}

/** `GET /ops/redis/keyspace` */
export function fetchRedisKeyspace(): Promise<RedisKeyspace> {
  return get<RedisKeyspace>(opsPath('/redis/keyspace'))
}

/** `GET /ops/redis/memory` */
export function fetchRedisMemory(): Promise<RedisMemory> {
  return get<RedisMemory>(opsPath('/redis/memory'))
}

/** `GET /ops/redis/clients` */
export function fetchRedisClients(): Promise<RedisClients> {
  return get<RedisClients>(opsPath('/redis/clients'))
}
