/**
 * Locally persisted "recently used tools".
 *
 * Server side recent usage (`GET /tools/recent`) needs a signed-in business
 * user, which the console does not have yet, so the workbench records usage in
 * localStorage instead. Only slugs are stored — never tool input or output.
 */

const STORAGE_KEY = 'vctn.tools.recent'
const MAX_ENTRIES = 20

/** Most recently used slugs, newest first. */
export function readRecentSlugs(): string[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw === null) {
      return []
    }
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return []
    }
    return parsed.filter((item): item is string => typeof item === 'string')
  } catch {
    return []
  }
}

/** Record one usage; the slug moves to the front and the list is capped. */
export function recordRecentSlug(slug: string): void {
  const next = [slug, ...readRecentSlugs().filter((item) => item !== slug)].slice(0, MAX_ENTRIES)
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Storage unavailable: recents are a convenience, not a requirement.
  }
}

/** Drop every locally recorded usage. */
export function clearRecentSlugs(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing to do.
  }
}
