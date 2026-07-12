import { computed } from 'vue'
import { useRoute } from 'vue-router'

type SettingsTab = 'collector' | 'privacy' | 'model' | 'system'

const tabs = new Set<SettingsTab>(['collector', 'privacy', 'model', 'system'])

export function useSettingsTabSync() {
  const route = useRoute()
  const activeSettingsTab = computed<SettingsTab>(() => {
    const tab = String(route.query.tab || 'collector') as SettingsTab
    return tabs.has(tab) ? tab : 'collector'
  })

  return {
    activeSettingsTab
  }
}

