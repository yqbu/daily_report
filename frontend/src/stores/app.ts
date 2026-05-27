import { defineStore } from 'pinia'
import { callBridge } from '../api/bridge'

type TopBarMode = 'default' | 'app-config'
type TopBarStatusTone = 'idle' | 'dirty' | 'saving' | 'saved' | 'error'

interface TopBarState {
  mode: TopBarMode
  statusText: string
  statusTone: TopBarStatusTone
  canCancel: boolean
  canRefresh: boolean
  canSave: boolean
  refreshing: boolean
  saving: boolean
  refreshRequestId: number
  saveRequestId: number
  cancelRequestId: number
}

interface TopBarPatch {
  mode?: TopBarMode
  statusText?: string
  statusTone?: TopBarStatusTone
  canCancel?: boolean
  canRefresh?: boolean
  canSave?: boolean
  refreshing?: boolean
  saving?: boolean
}

function defaultTopBarState(): TopBarState {
  return {
    mode: 'default',
    statusText: '',
    statusTone: 'idle',
    canCancel: false,
    canRefresh: false,
    canSave: false,
    refreshing: false,
    saving: false,
    refreshRequestId: 0,
    saveRequestId: 0,
    cancelRequestId: 0
  }
}

export const useAppStore = defineStore('app', {
  state: () => ({
    currentDate: new Date().toISOString().slice(0, 10),
    collectorStatus: null as Record<string, unknown> | null,
    globalLoading: false,
    lastError: '',
    topBar: defaultTopBarState()
  }),
  actions: {
    async refreshCollectorStatus() {
      try {
        this.collectorStatus = await callBridge<Record<string, unknown>>('get_collector_status', { date: this.currentDate })
      } catch (error) {
        this.lastError = error instanceof Error ? error.message : String(error)
      }
    },
    setTopBarState(patch: TopBarPatch) {
      this.topBar = {
        ...this.topBar,
        ...patch
      }
    },
    resetTopBarState() {
      this.topBar = defaultTopBarState()
    },
    requestTopBarSave() {
      if (!this.topBar.canSave || this.topBar.saving) return
      this.topBar.saveRequestId += 1
    },
    requestTopBarCancel() {
      if (!this.topBar.canCancel || this.topBar.saving) return
      this.topBar.cancelRequestId += 1
    },
    requestTopBarRefresh() {
      if (!this.topBar.canRefresh || this.topBar.refreshing || this.topBar.saving) return
      this.topBar.refreshRequestId += 1
    }
  }
})
