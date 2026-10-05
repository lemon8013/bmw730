import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { apiBaseUrl } from '@/api/client'

/**
 * Application level store.
 *
 * Authentication state belongs to the phase that freezes its contract; tool and
 * usage state live in the pages that own them.
 */
export const useAppStore = defineStore('app', () => {
  const applicationName = ref('VCTN Tools')
  const buildPhase = ref('工具门户')
  const apiPrefix = computed(() => apiBaseUrl)
  const isDevelopment = computed(() => import.meta.env.DEV)

  return { applicationName, buildPhase, apiPrefix, isDevelopment }
})
