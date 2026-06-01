import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import { getTimeline, type TimelineQuery } from '../api/timeline'
import { updateEntryDeleted, updateEntrySelection } from '../api/entries'
import type { TimelineEvent } from '../api/types'

export const useTimelineStore = defineStore('timeline', {
  state: () => ({
    items: [] as TimelineEvent[],
    total: 0,
    loading: false,
    error: null as string | null,
    query: { source_type: 'all', limit: 500, offset: 0, order: 'asc' } as TimelineQuery
  }),
  actions: {
    async loadTimeline(query: Partial<TimelineQuery> = {}) {
      this.loading = true
      this.error = null
      this.query = { ...this.query, ...query }
      try {
        const result = await getTimeline(this.query)
        this.items = result.items
        this.total = result.total
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
    async updateSelection(event: TimelineEvent, selected: boolean) {
      const previous = event.is_selected
      event.is_selected = selected
      try {
        await updateEntrySelection(event.source_type, event.source_id, selected)
      } catch (error) {
        event.is_selected = previous
        ElMessage.error(error instanceof Error ? error.message : String(error))
      }
    },
    async markDeleted(event: TimelineEvent) {
      const previousItems = this.items
      this.items = this.items.filter((item) => item.event_id !== event.event_id)
      try {
        await updateEntryDeleted(event.source_type, event.source_id, true)
      } catch (error) {
        this.items = previousItems
        ElMessage.error(error instanceof Error ? error.message : String(error))
      }
    }
  }
})

