import { apiGet, apiMode } from './client'
import { mockTimeline } from './mock'
import type { PagedResult, TimelineEvent, TimelineQuery } from './types'
import { callTypedBridge } from './bridge'

export type { TimelineQuery }

export async function getTimeline(query: TimelineQuery = {}): Promise<PagedResult<TimelineEvent>> {
  if (apiMode() === 'mock') return mockTimeline(query.date)
  if (apiMode() === 'qwebchannel') {
    const response = await callTypedBridge('getTimeline', {
      date: query.date,
      filters: {
        sourceTypes: query.source_type && query.source_type !== 'all' ? [query.source_type] : undefined,
        selected: query.selected ?? undefined,
        sensitive: query.sensitive ?? undefined,
        keyword: query.keyword,
        sortOrder: query.order
      },
      offset: query.offset,
      limit: query.limit,
      pageSize: query.limit
    })
    return { items: response.items, total: response.total }
  }
  return apiGet<PagedResult<TimelineEvent>>('/api/timeline', query as Record<string, unknown>)
}

