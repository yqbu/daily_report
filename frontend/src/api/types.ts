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

export type AnyRecord = Record<string, unknown>
