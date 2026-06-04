import type { AnyRecord, SourceType, TimelineEvent } from '../../api/types'

export type DataCenterView = 'timeline' | 'analysis'
export type SensitiveFilter = 'all' | 'sensitive' | 'normal'

export interface DataCenterFilters {
  dateRange: [Date, Date]
  sourceTypes: SourceType[]
  sensitive: SensitiveFilter
  categories: string[]
  keyword: string
  sortOrder: 'asc' | 'desc'
}

export interface RecordActionPayload {
  sourceType: SourceType
  id: number
}

export interface DetailSavePayload {
  sourceType: SourceType
  id: number
  category: string | null
  note: string | null
  importance: number
  sensitive: boolean
  sensitivityReason: string | null
}

export type DataCenterRecord = TimelineEvent | AnyRecord

export const SOURCE_OPTIONS: Array<{ label: string; value: SourceType }> = [
  { label: '前台应用', value: 'app' },
  { label: '浏览器历史', value: 'browser' },
  { label: '剪切板', value: 'clipboard' },
  { label: 'AI 提问', value: 'ai_prompt' },
  { label: '浏览器事件', value: 'browser_event' }
]

export const CATEGORY_OPTIONS = [
  '开发编码',
  '资料调研',
  'AI 辅助',
  '文档整理',
  '沟通协作',
  '系统配置',
  '其他'
]

export function sourceLabel(sourceType: string): string {
  return SOURCE_OPTIONS.find((item) => item.value === sourceType)?.label ?? sourceType
}

export function recordId(record: DataCenterRecord): number {
  const sourceId = record.source_id
  if (typeof sourceId === 'number') {
    return sourceId
  }
  const id = getValue(record, 'id')
  return typeof id === 'number' ? id : Number(id || 0)
}

export function recordSource(record: DataCenterRecord): SourceType {
  const sourceType = String(record.source_type || 'app')
  if (sourceType === 'browser_events') {
    return 'browser_event'
  }
  return (sourceType === 'ai' ? 'ai_prompt' : sourceType) as SourceType
}

export function recordTitle(record: DataCenterRecord): string {
  const sourceType = recordSource(record)
  if (typeof record.title === 'string' && record.title.trim()) {
    return record.title
  }
  if (sourceType === 'app') {
    return String(getValue(record, 'app_name') || getValue(record, 'process_name') || '前台应用')
  }
  if (sourceType === 'browser') {
    return String(record.title || getValue(record, 'domain') || '浏览器历史')
  }
  if (sourceType === 'clipboard') {
    return '剪切板文本'
  }
  if (sourceType === 'browser_event') {
    return String(getValue(record, 'search_query') || getValue(record, 'title') || getValue(record, 'domain') || '浏览器事件')
  }
  return `${String(getValue(record, 'platform') || 'AI')} 提问`
}

export function recordPreview(record: DataCenterRecord): string {
  return String(
    record.content_preview ||
      getValue(record, 'prompt_preview') ||
      getValue(record, 'content') ||
      getValue(record, 'prompt_text') ||
      getValue(record, 'search_query') ||
      record.subtitle ||
      getValue(record, 'window_title') ||
      getValue(record, 'url') ||
      ''
  )
}

export function recordTime(record: DataCenterRecord): string {
  return String(
    record.start_time ||
      getValue(record, 'visit_time') ||
      getValue(record, 'first_seen_at') ||
      getValue(record, 'last_seen_at') ||
      getValue(record, 'timestamp') ||
      ''
  )
}

export function isSensitive(record: DataCenterRecord): boolean {
  return Boolean(record.is_sensitive)
}

export function recordCategory(record: DataCenterRecord): string {
  return String(record.category || '其他')
}

export function formatDateTime(value: unknown): string {
  const text = String(value || '')
  if (!text) {
    return '-'
  }
  return text.replace('T', ' ').slice(0, 19)
}

export function formatDuration(seconds: unknown): string {
  const value = Number(seconds || 0)
  if (!Number.isFinite(value) || value <= 0) {
    return '0s'
  }
  const minutes = Math.floor(value / 60)
  const rest = Math.round(value % 60)
  if (minutes < 1) {
    return `${rest}s`
  }
  const hours = Math.floor(minutes / 60)
  if (hours < 1) {
    return `${minutes}m ${rest}s`
  }
  return `${hours}h ${minutes % 60}m`
}

export function dateRangeToPayload(filters: DataCenterFilters): {
  startDate: string
  endDate: string
} {
  const [start, end] = filters.dateRange
  return {
    startDate: toDateKey(start),
    endDate: toDateKey(end)
  }
}

export function toDateKey(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getValue(record: DataCenterRecord, key: string): unknown {
  return (record as Record<string, unknown>)[key]
}
