import { defineStore } from 'pinia'
import { getOverview } from '../api/overview'
import type { OverviewDTO } from '../api/types'

export const useOverviewStore = defineStore('overview', {
  state: () => ({
    overview: null as OverviewDTO | null,
    loading: false,
    error: null as string | null,
    selectedDate: new Date().toISOString().slice(0, 10)
  }),
  actions: {
    async loadOverview(date?: string) {
      this.loading = true
      this.error = null
      if (date) this.selectedDate = date
      try {
        this.overview = await getOverview(this.selectedDate)
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
    async refresh() {
      await this.loadOverview(this.selectedDate)
    }
  }
})

