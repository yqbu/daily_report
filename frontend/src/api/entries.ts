import { apiGet, apiPatch } from './client'
import type { EntryDetail, EntryQuery, PagedResult, SourceType } from './types'

export async function listEntries(
  sourceType: SourceType,
  query: EntryQuery = {}
): Promise<PagedResult<Record<string, unknown>>> {
  return apiGet<PagedResult<Record<string, unknown>>>(`/api/entries/${sourceType}`, query as Record<string, unknown>)
}

export async function getEntryDetail(sourceType: SourceType, id: number): Promise<EntryDetail> {
  return apiGet<EntryDetail>(`/api/entries/${sourceType}/${id}`)
}

export async function updateEntrySelection(sourceType: SourceType, id: number, selected: boolean): Promise<Record<string, unknown>> {
  return apiPatch<Record<string, unknown>>(`/api/entries/${sourceType}/${id}/selection`, { selected })
}

export async function updateEntryDeleted(sourceType: SourceType, id: number, deleted: boolean): Promise<Record<string, unknown>> {
  return apiPatch<Record<string, unknown>>(`/api/entries/${sourceType}/${id}/deleted`, { deleted })
}
