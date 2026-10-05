import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  clearRecentSlugs,
  readRecentSlugs,
  recordRecentSlug,
} from '@/composables/recent-tools'

const KEY = 'vctn.tools.recent'

describe('local recent tools', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  afterEach(() => {
    window.localStorage.clear()
  })

  it('returns an empty list when nothing was recorded', () => {
    expect(readRecentSlugs()).toEqual([])
  })

  it('moves the newest slug to the front without duplicates', () => {
    recordRecentSlug('json-format')
    recordRecentSlug('hash-digest')
    recordRecentSlug('json-format')

    expect(readRecentSlugs()).toEqual(['json-format', 'hash-digest'])
  })

  it('caps the list at 20 entries', () => {
    for (let index = 0; index < 30; index += 1) {
      recordRecentSlug(`tool-${index}`)
    }
    const slugs = readRecentSlugs()
    expect(slugs).toHaveLength(20)
    expect(slugs[0]).toBe('tool-29')
  })

  it('ignores corrupted storage content', () => {
    window.localStorage.setItem(KEY, 'not-json')
    expect(readRecentSlugs()).toEqual([])
  })

  it('clears everything', () => {
    recordRecentSlug('json-format')
    clearRecentSlugs()
    expect(readRecentSlugs()).toEqual([])
  })
})
