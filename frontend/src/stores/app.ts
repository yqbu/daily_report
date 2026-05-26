import { defineStore } from 'pinia'
import { callBridge } from '../api/bridge'

type TopBarMode = 'default' | 'app-config'
type TopBarStatusTone = 'idle' | 'dirty' | 'saving' | 'saved' | 'error'

interface TopBarState {
  mode: TopBarMode
  statusText: string
  statusTone: TopBarStatusTone
  canCancel: boolean
  canSave: boolean
  saving: boolean
  saveRequestId: number
  cancelRequestId: number
}

interface TopBarPatch {
  mode?: TopBarMode
  statusText?: string
  statusTone?: TopBarStatusTone
  canCancel?: boolean
  canSave?: boolean
  saving?: boolean
}

function defaultTopBarState(): TopBarState {
  return {
    mode: 'default',
    statusText: '',
    statusTone: 'idle',
    canCancel: false,
    canSave: false,
    saving: false,
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
    }
  }
})
