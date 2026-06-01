import { defineStore } from 'pinia'
import { getEntryDetail, listEntries, updateEntryDeleted, updateEntrySelection } from '../api/entries'
import type { EntryDetail, EntryQuery, SourceType } from '../api/types'

export const useEntriesStore = defineStore('entries', {
  state: () => ({
    items: [] as Record<string, unknown>[],
    total: 0,
    detail: null as EntryDetail | null,
    loading: false,
    detailLoading: false,
    error: null as string | null
  }),
  actions: {
    async loadEntries(sourceType: SourceType, query: EntryQuery = {}) {
      this.loading = true
      this.error = null
      try {
        const result = await listEntries(sourceType, query)
        this.items = result.items
        this.total = result.total
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
    async loadDetail(sourceType: SourceType, id: number) {
      this.detailLoading = true
      try {
        this.detail = await getEntryDetail(sourceType, id)
      } finally {
        this.detailLoading = false
      }
    },
    updateEntrySelection,
    updateEntryDeleted
  }
})

