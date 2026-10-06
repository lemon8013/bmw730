<script setup lang="ts">
/**
 * Breadcrumb whose first crumb always points back to the portal home.
 *
 * Every page reachable from a card / search result renders this so the visitor
 * never has to hunt for the header link to get back to `/`.
 */
import { RouterLink } from 'vue-router'

export interface BreadcrumbEntry {
  /** Rendered text. When `to` is absent it renders as the current page. */
  label: string
  /** Target route; omit for the trailing (current) crumb. */
  to?: { name: string; params?: Record<string, string>; query?: Record<string, string> }
}

defineProps<{
  entries: readonly BreadcrumbEntry[]
}>()
</script>

<template>
  <nav class="app-breadcrumb" aria-label="面包屑">
    <RouterLink :to="{ name: 'home' }" class="app-breadcrumb__link">首页</RouterLink>
    <template v-for="(entry, index) in entries" :key="`${entry.label}-${index}`">
      <span class="app-breadcrumb__sep">/</span>
      <RouterLink v-if="entry.to !== undefined" :to="entry.to" class="app-breadcrumb__link">
        {{ entry.label }}
      </RouterLink>
      <span v-else class="app-breadcrumb__current">{{ entry.label }}</span>
    </template>
  </nav>
</template>

<style scoped>
.app-breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--vctn-space-2);
  margin-bottom: var(--vctn-space-4);
  color: var(--vctn-text-secondary);
  font-size: var(--vctn-text-sm);
}

.app-breadcrumb__link {
  color: var(--vctn-text-secondary);
  text-decoration: none;
  transition: color var(--vctn-duration-fast) var(--vctn-ease);
}

.app-breadcrumb__link:hover {
  color: var(--vctn-brand);
}

.app-breadcrumb__current {
  color: var(--vctn-text-strong);
  font-weight: 500;
}

.app-breadcrumb__sep {
  color: var(--vctn-text-muted);
}
</style>
