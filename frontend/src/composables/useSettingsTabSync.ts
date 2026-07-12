import { shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { normalizeSettingsTab, type SettingsTab } from '../utils/settings'

export function useSettingsTabSync() {
  const route = useRoute()
  const router = useRouter()
  const activeSettingsTab = shallowRef<SettingsTab>('collector')

  watch(
    () => route.query.tab,
    (tab) => {
      const normalizedTab = normalizeSettingsTab(tab)
      if (activeSettingsTab.value !== normalizedTab) {
        activeSettingsTab.value = normalizedTab
      }
    },
    { immediate: true }
  )

  watch(activeSettingsTab, (tab) => {
    const currentTab = normalizeSettingsTab(route.query.tab)
    if (tab !== currentTab) {
      void router.replace({ query: { ...route.query, tab } })
    }
  })

  return {
    activeSettingsTab
  }
}
