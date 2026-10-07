/**
 * Collection agents (`app/ops/agents`).
 *
 * `POST /agents/heartbeat` is intentionally absent: it is the agent's own
 * endpoint, authenticated by the agent credential rather than by an
 * administrator session, so a console must never call it.
 *
 * The plain token exists in exactly one response —
 * {@link AgentRegisterResult} — and is never persisted by the backend.
 */

import { get, post } from '@/api/client'
import { opsPath } from '@/api/ops/shared'
import type { Page } from '@/types/api'
import type { Agent, AgentCreateRequest, AgentHeartbeat, AgentRegisterResult } from '@/types/ops'

/** Filters accepted by `GET /ops/agents`. */
export interface AgentFilters {
  keyword?: string
  status?: string
  enabled?: boolean
}

/** `GET /ops/agents` */
export function listAgents(
  page = 1,
  pageSize = 20,
  filters: AgentFilters = {},
): Promise<Page<Agent>> {
  return get<Page<Agent>>(opsPath('/agents'), {
    params: {
      page,
      page_size: pageSize,
      keyword: filters.keyword ?? undefined,
      status: filters.status ?? undefined,
      enabled: filters.enabled ?? undefined,
    },
  })
}

/** `GET /ops/agents/{agent_id}` */
export function getAgent(agentId: string): Promise<Agent> {
  return get<Agent>(opsPath(`/agents/${encodeURIComponent(agentId)}`))
}

/** `POST /ops/agents` — requires `OPS_AGENT_MANAGE`. Returns the token once. */
export function registerAgent(payload: AgentCreateRequest): Promise<AgentRegisterResult> {
  return post<AgentRegisterResult>(opsPath('/agents'), payload)
}

/** `POST /ops/agents/{agent_id}/enable` — requires `OPS_AGENT_MANAGE`. */
export function enableAgent(agentId: string): Promise<Agent> {
  return post<Agent>(opsPath(`/agents/${encodeURIComponent(agentId)}/enable`), undefined)
}

/** `POST /ops/agents/{agent_id}/disable` — requires `OPS_AGENT_MANAGE`. */
export function disableAgent(agentId: string): Promise<Agent> {
  return post<Agent>(opsPath(`/agents/${encodeURIComponent(agentId)}/disable`), undefined)
}

/** `GET /ops/agents/{agent_id}/heartbeats` */
export function listHeartbeats(
  agentId: string,
  page = 1,
  pageSize = 20,
  hours = 24,
): Promise<Page<AgentHeartbeat>> {
  return get<Page<AgentHeartbeat>>(opsPath(`/agents/${encodeURIComponent(agentId)}/heartbeats`), {
    params: { page, page_size: pageSize, hours },
  })
}
