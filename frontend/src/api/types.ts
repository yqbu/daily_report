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
  top_apps: Array<{ name: string; app_name?: string; seconds: number; session_count: number }>
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
