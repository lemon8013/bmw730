/**
 * Anonymous caller identity.
 *
 * Tool execution works without signing in: the backend records usage against a
 * client generated `anonymous_id` instead of a user. The identifier is random
 * and carries no input content.
 */

const STORAGE_KEY = 'vctn.tools.anonymous_id'

function newAnonymousId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return Math.random().toString(16).slice(2).padEnd(36, '0')
}

/** Read the persisted anonymous id, creating one on first use. */
export function readAnonymousId(): string {
  let value: string | null = null
  try {
    value = window.localStorage.getItem(STORAGE_KEY)
  } catch {
    value = null
  }
  if (value !== null && value.trim() !== '') {
    return value
  }
  const created = newAnonymousId()
  try {
    window.localStorage.setItem(STORAGE_KEY, created)
  } catch {
    // Storage can be unavailable (private mode); execution still works, the
    // backend then treats every request as a fresh anonymous caller.
  }
  return created
}
