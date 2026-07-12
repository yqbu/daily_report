import { apiGet } from './client'
import type { PagedResult, TimelineEvent, TimelineQuery } from './types'

export type { TimelineQuery }

export async function getTimeline(query: TimelineQuery = {}): Promise<PagedResult<TimelineEvent>> {
  return apiGet<PagedResult<TimelineEvent>>('/api/timeline', query as Record<string, unknown>)
}

