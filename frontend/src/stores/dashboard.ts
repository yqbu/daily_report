import { defineStore } from 'pinia'
import { callBridge } from '../api/bridge'
import type { DashboardSummary } from '../api/types'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    summary: null as DashboardSummary | null,
    loading: false,
    error: ''
  }),
  actions: {
    async load(date: string) {
      this.loading = true
      this.error = ''
      try {
        this.summary = await callBridge<DashboardSummary>('get_dashboard_summary', { date })
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    }
  }
})
