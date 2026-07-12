import type { AnyRecord, OverviewPayload, TimelineEvent } from '../types'
import { apiGet, apiPatch, apiPost, apiPut } from '../client'
import { getBrowserFallback } from './fallback'
import {
  dateRangeDays,
  getPayloadDate,
  getPayloadEntryKey,
  getPayloadNumber,
  getPayloadSourceType,
  getPayloadValue,
  isObjectRecord
} from './shared'

export async function callHttpBridge<T>(method: string, payload: unknown): Promise<T> {
  const date = getPayloadDate(payload)
  switch (method) {
    case 'getOverview':
      return apiGet<T>('/api/overview', { date })
    case 'getTimeline':
      return callGuiCompat<T>(method, payload)
    case 'listEntries':
      return listEntriesHttp<T>(payload)
    case 'getEntryDetail':
      return getEntryDetailHttp<T>(payload)
    case 'updateEntrySelection':
      return updateEntrySelectionHttp<T>(payload)
    case 'markEntryDeleted':
      return markEntryDeletedHttp<T>(payload)
    case 'getDataCenterSummary':
      return callGuiCompat<T>(method, payload)
    case 'buildPrompt':
      return buildPromptHttp<T>(payload)
    case 'generateReport':
      return generateReportHttp<T>(payload)
    case 'getLatestReport':
      return getLatestReportHttp<T>(payload)
    case 'getSettings':
      return apiGet<T>('/api/settings')
    case 'saveSettings':
      return apiPut<T>('/api/settings', payload)
    case 'getHealth':
    case 'get_collector_status':
      return apiGet<T>('/api/health/collectors')
    case 'getDataCenterAnalytics':
    case 'getReportMaterials':
      return callGuiCompat<T>(method, payload)
    case 'batchUpdateEntrySelection':
    case 'updateEntryAnnotation':
      return updateEntryAnnotationHttp<T>(method, payload)
    case 'updateEntrySensitive':
      return updateEntrySensitiveHttp<T>(method, payload)
    case 'listAppProfiles':
    case 'extractAppProfiles':
    case 'listAppCategories':
    case 'saveAppProfile':
    case 'resetAppProfile':
    case 'deleteAppRecords':
    case 'saveAppCategory':
    case 'deleteAppCategory':
    case 'listReports':
    case 'getReportDetail':
    case 'deleteReport':
    case 'saveReport':
    case 'test_model_connection':
      return callGuiCompat<T>(method, payload)
    case 'select_directory':
    case 'select_json_file':
      return getBrowserFallback<T>(method, payload)
    default:
      return getBrowserFallback<T>(method, payload)
  }
}

async function callGuiCompat<T>(method: string, payload: unknown): Promise<T> {
  return apiPost<T>(`/api/gui/${encodeURIComponent(method)}`, payload ?? {})
}

async function updateEntrySelectionHttp<T>(payload: unknown): Promise<T> {
  const entryKey = getPayloadEntryKey(payload)
  if (entryKey) {
    return apiPatch<T>('/api/entries/by-key/selection', {
      entry_key: entryKey,
      selected: Boolean(getPayloadValue(payload, 'selected'))
    })
  }
  return apiPatch<T>(`/api/entries/${getPayloadSourceType(payload)}/${getPayloadNumber(payload, 'id', 0)}/selection`, {
    selected: Boolean(getPayloadValue(payload, 'selected'))
  })
}

async function markEntryDeletedHttp<T>(payload: unknown): Promise<T> {
  const entryKey = getPayloadEntryKey(payload)
  if (entryKey) {
    return apiPatch<T>('/api/entries/by-key/deleted', {
      entry_key: entryKey,
      deleted: true
    })
  }
  return apiPatch<T>(`/api/entries/${getPayloadSourceType(payload)}/${getPayloadNumber(payload, 'id', 0)}/deleted`, {
    deleted: true
  })
}

async function updateEntryAnnotationHttp<T>(method: string, payload: unknown): Promise<T> {
  const entryKey = getPayloadEntryKey(payload)
  if (entryKey) {
    const annotationPayload = getPayloadValue(payload, 'payload')
    return apiPatch<T>('/api/entries/by-key/annotation', {
      entry_key: entryKey,
      ...(isObjectRecord(annotationPayload) ? annotationPayload : {})
    })
  }
  return callGuiCompat<T>(method, payload)
}

async function updateEntrySensitiveHttp<T>(method: string, payload: unknown): Promise<T> {
  const entryKey = getPayloadEntryKey(payload)
  if (entryKey) {
    return apiPatch<T>('/api/entries/by-key/sensitive', {
      entry_key: entryKey,
      sensitive: Boolean(getPayloadValue(payload, 'sensitive')),
      reason: getPayloadValue(payload, 'reason') || null
    })
  }
  return callGuiCompat<T>(method, payload)
}

async function listEntriesHttp<T>(payload: unknown): Promise<T> {
  const sourceType = getPayloadSourceType(payload)
  const pageSize = getPayloadNumber(payload, 'pageSize', getPayloadNumber(payload, 'limit', 50))
  const page = getPayloadNumber(payload, 'page', 1)
  const filters = isObjectRecord(getPayloadValue(payload, 'filters')) ? getPayloadValue(payload, 'filters') as AnyRecord : {}
  return apiGet<T>(`/api/entries/${sourceType}`, {
    date: getPayloadValue(payload, 'date') || getPayloadValue(payload, 'startDate'),
    selected: getPayloadValue(filters, 'selected'),
    sensitive: getPayloadValue(filters, 'sensitive'),
    keyword: getPayloadValue(filters, 'keyword'),
    record_type: getPayloadValue(filters, 'recordType') || getPayloadValue(filters, 'record_type'),
    limit: pageSize,
    offset: (page - 1) * pageSize
  })
}

async function getEntryDetailHttp<T>(payload: unknown): Promise<T> {
  const entryKey = getPayloadEntryKey(payload)
  if (entryKey) {
    const response = await apiGet<{ detail: unknown }>(`/api/entries/by-key/${encodeURIComponent(entryKey)}`)
    return response.detail as T
  }
  const sourceType = getPayloadSourceType(payload)
  const response = await apiGet<{ detail: unknown }>(`/api/entries/${sourceType}/${getPayloadNumber(payload, 'id', 0)}`)
  return response.detail as T
}

async function buildDataCenterSummaryHttp<T>(payload: unknown): Promise<T> {
  const days = dateRangeDays(payload)
  const overviews = await Promise.all(days.map((date) => apiGet<OverviewPayload>('/api/overview', { date })))
  const summary = {
    total: 0,
    app: 0,
    browser: 0,
    clipboard: 0,
    ai_prompt: 0,
    browser_event: 0,
    sensitive: 0,
    deleted: 0,
    categories: [] as Array<{ category: string; count: number }>,
    days: [] as Array<{ date: string; count: number }>
  }
  const categories = new Map<string, number>()
  for (const item of overviews) {
    summary.app += item.app_session_count || 0
    summary.browser += item.browser_count || 0
    summary.clipboard += item.clipboard_count || 0
    summary.ai_prompt += item.ai_prompt_count || 0
    summary.browser_event += item.browser_event_count || 0
    summary.sensitive += item.sensitive_count || 0
    const dayCount = (item.app_session_count || 0) + (item.browser_count || 0) + (item.clipboard_count || 0) + (item.ai_prompt_count || 0) + (item.browser_event_count || 0)
    summary.days.push({ date: item.date, count: dayCount })
    for (const category of item.category_distribution || []) {
      categories.set(category.category, (categories.get(category.category) || 0) + category.count)
    }
  }
  summary.total = summary.app + summary.browser + summary.clipboard + summary.ai_prompt + summary.browser_event
  summary.categories = [...categories.entries()].map(([category, count]) => ({ category, count }))
  return summary as T
}

async function buildPromptHttp<T>(payload: unknown): Promise<T> {
  const result = await apiPost<{ date: string; template_name: string; prompt_text: string }>('/api/reports/build-prompt', {
    date: getPayloadDate(payload),
    template_name: String(getPayloadValue(payload, 'templateName') || getPayloadValue(payload, 'template_name') || 'daily_standard')
  })
  return { ...result, prompt: result.prompt_text } as T
}

async function generateReportHttp<T>(payload: unknown): Promise<T> {
  return apiPost<T>('/api/reports/generate', {
    date: getPayloadDate(payload),
    template_name: String(getPayloadValue(payload, 'templateName') || getPayloadValue(payload, 'template_name') || 'daily_standard'),
    save: getPayloadValue(payload, 'save') ?? true
  })
}

async function getLatestReportHttp<T>(payload: unknown): Promise<T> {
  const result = await apiGet<{ report: unknown }>('/api/reports/latest', { date: getPayloadDate(payload) })
  return result.report as T
}

async function buildReportMaterialsHttp<T>(payload: unknown): Promise<T> {
  const timeline = await apiGet<{ items: TimelineEvent[]; total: number }>('/api/timeline', {
    date: getPayloadDate(payload),
    selected: true,
    limit: 500,
    order: 'asc'
  })
  return {
    summary: {
      total_count: timeline.total,
      selected_count: timeline.items.filter((item) => item.is_selected).length,
      sensitive_excluded_count: timeline.items.filter((item) => item.is_sensitive).length,
      pending_count: timeline.items.filter((item) => !item.is_selected).length,
      estimated_prompt_chars: timeline.items.reduce((sum, item) => sum + (item.content_preview || '').length, 0)
    },
    items: timeline.items.map((item) => ({
      source_type: item.source_type,
      source_id: item.source_id,
      entry_key: item.entry_key,
      record_type: item.record_type,
      title: item.title,
      summary: item.content_preview || item.subtitle || '',
      evidence: item.content_preview || '',
      category: item.category || '其他',
      time_range: item.start_time,
      importance: item.importance ?? 0,
      is_sensitive: item.is_sensitive,
      is_selected: item.is_selected
    })),
    hasMore: false
  } as T
}
