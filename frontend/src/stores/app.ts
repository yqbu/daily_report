import { defineStore } from 'pinia'
import { callBridge } from '../api/bridge'

export const useAppStore = defineStore('app', {
  state: () => ({
    currentDate: new Date().toISOString().slice(0, 10),
    collectorStatus: null as Record<string, unknown> | null,
    globalLoading: false,
    lastError: ''
  }),
  actions: {
    async refreshCollectorStatus() {
      try {
        this.collectorStatus = await callBridge<Record<string, unknown>>('get_collector_status', { date: this.currentDate })
      } catch (error) {
        this.lastError = error instanceof Error ? error.message : String(error)
      }
    }
  }
})
