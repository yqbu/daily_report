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

export type AnyRecord = Record<string, unknown>
