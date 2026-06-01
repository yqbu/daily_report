import { defineStore } from 'pinia'
import { getSettings, saveSettings as saveSettingsApi } from '../api/settings'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    settings: null as Record<string, unknown> | null,
    loading: false,
    saving: false,
    error: null as string | null
  }),
  actions: {
    async loadSettings() {
      this.loading = true
      this.error = null
      try {
        this.settings = await getSettings()
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
    async saveSettings(payload: Record<string, unknown>) {
      this.saving = true
      this.error = null
      try {
        this.settings = await saveSettingsApi(payload)
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
        throw error
      } finally {
        this.saving = false
      }
    }
  }
})

