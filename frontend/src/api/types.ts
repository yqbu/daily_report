/**
 * Frontend/backend data contracts.
 *
 * 这个文件只描述 QWebChannel 后端接口返回的数据形态，不承载页面布局。
 * 后续实现页面时，优先从这里取类型，避免在组件里散落重复的字段定义。
 */

export interface BridgeResponse<T> {
  ok: boolean
  data?: T
  error?: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  [key: string]: unknown
}

export type SourceType = 'app' | 'browser' | 'clipboard' | 'ai_prompt'
export type TemplateName = 'daily_standard' | 'daily_technical' | 'daily_brief'

/**
 * 兼容旧页面/旧 store 的来源类型。
 * 新页面应优先使用 SourceType。
 */
export type RecordKind = 'app' | 'clipboard' | 'browser' | 'ai'

export interface OverviewPayload {
  date: string
  collector_status: string
  active_time: string
  total_time: string
  active_time_sec: number
  total_time_sec: number
  app_session_count: number
  browser_count: number
  clipboard_count: number
  ai_prompt_count: number
  selected_material_count: number
  sensitive_count: number
  report_status: string
  top_apps: Array<{
    name: string
    app_name?: string
    app_key?: string
    category?: string
    color?: string
    seconds: number
    session_count: number
  }>
  source_distribution: Array<{ source_type: SourceType; count: number }>
  category_distribution: Array<{ category: string; count: number }>
  hourly_activity: Array<{ hour: number; label: string; active_sec: number }>
}

export interface TimelineEvent {
  event_id: string
  source_type: SourceType
  source_id: number
  start_time: string
  end_time?: string | null
  title: string
  subtitle: string
  content_preview: string
  category: string
  is_selected: boolean
  is_sensitive: boolean
  is_deleted: boolean
}

export interface MaterialCard {
  source_type: SourceType
  source_id: number
  time_range: string
  category: string
  title: string
  summary: string
  evidence: string
  importance: number
  is_sensitive: boolean
}

export interface GeneratedReport {
  report_id: number
  prompt_text: string
  report_markdown: string
}

export interface ReportHistoryRow {
  id: number
  date: string
  report_type?: string
  template_name?: string
  model_provider?: string
  model_name: string
  prompt_text: string
  report_markdown: string
  material_snapshot_json?: string | null
  material_summary?: string | null
  source_counts?: Record<string, unknown>
  source_counts_json?: string
  created_at: string
  updated_at?: string
}

export interface LocalSettingsPayload {
  settings_path?: string
  settingsPath?: string
  model: {
    provider: string
    model_name: string
    base_url: string
    api_key: string
    max_prompt_chars: number
    timeout_seconds: number
    temperature: number
  }
  collector: {
    foreground_enabled: boolean
    clipboard_enabled: boolean
    edge_history_enabled: boolean
    ai_prompt_enabled: boolean
    foreground_poll_interval_sec: number
    edge_sync_interval_min: number
  }
  privacy: {
    hide_sensitive_by_default: boolean
    sensitive_unselected_by_default: boolean
    require_manual_confirm_before_llm: boolean
    clipboard_preview_only: boolean
    sensitive_keywords: string[]
  }
  yasb?: Record<string, unknown>
  logging: {
    level: string
    retention_days: number
  }
}

export interface TimelineFilters {
  source_types?: SourceType[]
  selected?: boolean
  sensitive?: boolean
  keyword?: string
  sort_order?: 'asc' | 'desc'
  limit?: number
}

export interface EntryListFilters {
  selected?: boolean
  sensitive?: boolean
  keyword?: string
}

export interface EntryAnnotationPayload {
  category?: string | null
  note?: string | null
  importance?: number | null
}

export type AppProfileClassificationFilter = 'all' | 'classified' | 'unclassified' | 'configured'
export type AppProfileSortBy = 'last_seen' | 'name' | 'duration'
export type SortDirection = 'asc' | 'desc'

export interface AppProfileListFilters {
  keyword?: string
  category?: string
  classification?: AppProfileClassificationFilter
  track_enabled?: boolean | null
  sort_by?: AppProfileSortBy
  sort_direction?: SortDirection
}

export interface AppCategoryConfig {
  id?: number
  name: string
  color: string
  sort_order: number
  is_builtin: boolean
  is_deleted: boolean
  profile_count: number
  created_at?: string
  updated_at?: string
}

export interface AppProfileConfig {
  app_key: string
  process_name: string
  exe_path?: string | null
  default_display_name: string
  display_name?: string | null
  effective_display_name: string
  category: string
  category_color: string
  color?: string | null
  effective_color: string
  icon_base64?: string | null
  track_enabled: boolean
  capture_title_enabled: boolean
  session_count: number
  total_duration_sec: number
  total_active_duration_sec: number
  last_seen_at?: string | null
  sample_window_title?: string | null
  is_configured: boolean
  is_classified: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AppProfileCounts {
  all: number
  classified: number
  unclassified: number
  configured: number
  excluded: number
}

export interface AppProfileListPayload extends PageResult<AppProfileConfig> {
  counts: AppProfileCounts
  categories: AppCategoryConfig[]
}

export interface SaveAppProfilePayload {
  app_key: string
  process_name?: string
  exe_path?: string | null
  display_name?: string | null
  category?: string | null
  color?: string | null
  icon_base64?: string | null
  track_enabled?: boolean
  capture_title_enabled?: boolean
}

export interface HealthPayload {
  ok?: boolean
  collector_status?: string
  collector_states?: unknown[]
  [key: string]: unknown
}

export interface PromptPreviewPayload {
  date: string
  template_name: TemplateName | string
  prompt: string
}

export interface MaterialListPayload {
  date?: string
  items: MaterialCard[]
  total?: number
}

export interface TimelineListPayload {
  items: TimelineEvent[]
  total: number
}

/**
 * QWebChannel 方法契约。
 *
 * 页面骨架中保留这些调用点；具体 UI 完成时只需要把状态渲染出来，
 * 不需要重新确认 Python bridge 方法名和 payload 结构。
 */
export interface BridgeMethodPayloadMap {
  getOverview: { date?: string | null }
  getTimeline: { date?: string | null; filters?: TimelineFilters }
  listEntries: {
    sourceType: SourceType
    date?: string | null
    filters?: EntryListFilters
    page: number
    pageSize: number
  }
  getEntryDetail: { sourceType: SourceType; id: number }
  updateEntrySelection: { sourceType: SourceType; id: number; selected: boolean }
  markEntryDeleted: { sourceType: SourceType; id: number }
  updateEntryAnnotation: { sourceType: SourceType; id: number; payload: EntryAnnotationPayload }
  listAppProfiles: {
    filters?: AppProfileListFilters
    page?: number
    pageSize?: number
    include_unobserved?: boolean
  }
  saveAppProfile: SaveAppProfilePayload
  resetAppProfile: { app_key: string }
  deleteAppRecords: { app_key: string; date?: string | null; hard_delete?: boolean }
  listAppCategories: { include_deleted?: boolean }
  saveAppCategory: { name: string; color?: string | null; sort_order?: number }
  deleteAppCategory: { name: string; fallback_category?: string }
  getReportMaterials: { date?: string | null }
  buildPrompt: { date?: string | null; templateName: TemplateName | string }
  generateReport: { date?: string | null; templateName: TemplateName | string }
  getLatestReport: { date?: string | null }
  listReports: { startDate?: string | null; endDate?: string | null }
  getSettings: Record<string, never>
  saveSettings: LocalSettingsPayload
  getHealth: Record<string, never>
}

export interface BridgeMethodResultMap {
  getOverview: OverviewPayload
  getTimeline: TimelineListPayload
  listEntries: PageResult<AnyRecord>
  getEntryDetail: AnyRecord | null
  updateEntrySelection: { ok?: boolean }
  markEntryDeleted: { ok?: boolean }
  updateEntryAnnotation: { ok?: boolean }
  listAppProfiles: AppProfileListPayload
  saveAppProfile: AppProfileConfig
  resetAppProfile: AppProfileConfig
  deleteAppRecords: { app_key: string; deleted_count: number }
  listAppCategories: { items: AppCategoryConfig[]; total: number }
  saveAppCategory: AppCategoryConfig
  deleteAppCategory: { name: string; deleted: boolean; fallback_category: string }
  getReportMaterials: MaterialListPayload
  buildPrompt: PromptPreviewPayload
  generateReport: GeneratedReport
  getLatestReport: ReportHistoryRow | null
  listReports: { items: ReportHistoryRow[]; total?: number }
  getSettings: LocalSettingsPayload
  saveSettings: LocalSettingsPayload
  getHealth: HealthPayload
}

/**
 * 旧页面/旧 store 兼容类型。新页面不再依赖这些类型，但先保留，避免破坏历史代码。
 */
export interface DashboardSummary {
  date: string
  metrics: {
    active_time: string
    total_time: string
    app_sessions: number
    clipboard: number
    browser: number
    ai_prompts: number
  }
  top_apps: Array<{ name: string; seconds: number; session_count: number }>
  time_distribution: Array<{ label: string; active: number }>
  recent_activities: Array<{ time: string; title: string; source: string; duration_sec: number }>
  weekly_trend: Array<{ date: string; count: number }>
}

export interface MaterialRow {
  key: string
  selected: boolean
  time: string
  source_type: string
  preview: string
  source: string
  sensitive: boolean
}

export type AnyRecord = Record<string, unknown>
