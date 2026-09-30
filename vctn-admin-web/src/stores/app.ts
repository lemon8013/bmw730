import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { apiBaseUrl } from '@/api/client'

/**
 * Application level store.
 *
 * Phase 0 keeps it free of business state: authentication, permissions and menu
 * state belong to the phases that freeze their contracts.
 */
export const useAppStore = defineStore('app', () => {
  const applicationName = ref('VCTN Admin')
  const buildPhase = ref('Phase 0 — project skeleton')
  const apiPrefix = computed(() => apiBaseUrl)
  const isDevelopment = computed(() => import.meta.env.DEV)

  return { applicationName, buildPhase, apiPrefix, isDevelopment }
})
