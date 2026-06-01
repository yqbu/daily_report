import { apiGet, apiMode, apiPatch } from './client'
import { mockEntries, mockEntryDetail } from './mock'
import type { EntryDetail, EntryQuery, PagedResult, SourceType } from './types'
import { callTypedBridge } from './bridge'

export async function listEntries(
  sourceType: SourceType,
  query: EntryQuery = {}
): Promise<PagedResult<Record<string, unknown>>> {
  if (apiMode() === 'mock') return mockEntries(sourceType, query.date)
  if (apiMode() === 'qwebchannel') {
    const pageSize = query.limit ?? 50
    const page = Math.floor((query.offset ?? 0) / pageSize) + 1
    const response = await callTypedBridge('listEntries', {
      sourceType,
      date: query.date,
      filters: {
        selected: query.selected ?? undefined,
        sensitive: query.sensitive ?? undefined,
        keyword: query.keyword
      },
      page,
      pageSize
    })
    return { items: response.items, total: response.total }
  }
  return apiGet<PagedResult<Record<string, unknown>>>(`/api/entries/${sourceType}`, query as Record<string, unknown>)
}

export async function getEntryDetail(sourceType: SourceType, id: number): Promise<EntryDetail> {
  if (apiMode() === 'mock') return mockEntryDetail(sourceType, id) as unknown as EntryDetail
  if (apiMode() === 'qwebchannel') {
    const detail = await callTypedBridge('getEntryDetail', { sourceType, id })
    return { source_type: sourceType, id, detail: (detail || {}) as Record<string, unknown> }
  }
  return apiGet<EntryDetail>(`/api/entries/${sourceType}/${id}`)
}

export async function updateEntrySelection(sourceType: SourceType, id: number, selected: boolean): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { source_type: sourceType, id, selected }
  if (apiMode() === 'qwebchannel') return callTypedBridge('updateEntrySelection', { sourceType, id, selected })
  return apiPatch<Record<string, unknown>>(`/api/entries/${sourceType}/${id}/selection`, { selected })
}

export async function updateEntryDeleted(sourceType: SourceType, id: number, deleted: boolean): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { source_type: sourceType, id, deleted }
  if (apiMode() === 'qwebchannel') return callTypedBridge('markEntryDeleted', { sourceType, id })
  return apiPatch<Record<string, unknown>>(`/api/entries/${sourceType}/${id}/deleted`, { deleted })
}
