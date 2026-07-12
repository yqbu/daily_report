import type {
  DashboardSummary,
  HealthPayload,
  LocalSettingsPayload,
  OverviewPayload,
  PromptPreviewPayload
} from '../types'
import { getPayloadDate, getPayloadNumber, getPayloadValue } from './shared'

export function getBrowserFallback<T>(method: string, payload: unknown): T {
  const date = getPayloadDate(payload)

  switch (method) {
    case 'getOverview':
      return emptyOverview(date) as T
    case 'getTimeline':
      return { items: [], total: 0, nextCursor: null, hasMore: false } as T
    case 'listEntries':
      return {
        items: [],
        total: 0,
        page: getPayloadNumber(payload, 'page', 1),
        page_size: getPayloadNumber(payload, 'pageSize', 30)
      } as T
    case 'getEntryDetail':
      return null as T
    case 'updateEntrySelection':
    case 'markEntryDeleted':
    case 'updateEntryAnnotation':
      return { ok: true } as T
    case 'updateEntrySensitive':
      return {
        source_type: String(getPayloadValue(payload, 'sourceType') || 'app'),
        id: getPayloadNumber(payload, 'id', 0),
        is_sensitive: Boolean(getPayloadValue(payload, 'sensitive')),
        sensitivity_reason: getPayloadValue(payload, 'reason') || null
      } as T
    case 'getDataCenterSummary':
      return emptyDataCenterSummary() as T
    case 'getDataCenterAnalytics':
      return { summary: emptyDataCenterSummary(), charts: {} } as T
    case 'listAppProfiles':
    case 'extractAppProfiles':
      return {
        items: [],
        total: 0,
        page: getPayloadNumber(payload, 'page', 1),
        page_size: getPayloadNumber(payload, 'pageSize', 100),
        counts: emptyAppProfileCounts(),
        categories: []
      } as T
    case 'saveAppProfile':
    case 'resetAppProfile':
      return emptyAppProfileConfig(payload) as T
    case 'deleteAppRecords':
      return { app_key: String(getPayloadValue(payload, 'app_key') || ''), deleted_count: 0 } as T
    case 'listAppCategories':
      return { items: [], total: 0 } as T
    case 'saveAppCategory':
      return emptyAppCategoryConfig(payload) as T
    case 'deleteAppCategory':
      return {
        name: String(getPayloadValue(payload, 'name') || ''),
        deleted: true,
        fallback_category: '其他'
      } as T
    case 'getReportMaterials':
      return {
        summary: {
          total_count: 0,
          selected_count: 0,
          sensitive_excluded_count: 0,
          pending_count: 0,
          estimated_prompt_chars: 0
        },
        items: [],
        hasMore: false
      } as T
    case 'batchUpdateEntrySelection':
      return { ok: true, updated: 0 } as T
    case 'buildPrompt':
      return emptyPromptPreview(date, payload) as T
    case 'generateReport':
      return {
        report_id: 0,
        prompt_text: '',
        report_markdown: '',
        material_snapshot_json: '',
        created_at: new Date().toISOString()
      } as T
    case 'saveReport':
      return { report_id: 0, saved: true } as T
    case 'getLatestReport':
      return null as T
    case 'listReports':
      return { items: [], total: 0 } as T
    case 'getReportDetail':
      return null as T
    case 'deleteReport':
      return { ok: true } as T
    case 'getSettings':
      return defaultSettings() as T
    case 'saveSettings':
      return payload as T
    case 'test_model_connection':
      return { message: '浏览器预览模式未连接 Python bridge, 已跳过真实模型测试.' } as T
    case 'select_directory':
    case 'select_json_file':
      return { path: '' } as T
    case 'getHealth':
      return emptyHealth() as T
    case 'get_dashboard_summary':
      return emptyDashboardSummary(date) as T
    case 'get_collector_status':
      return emptyHealth() as T
    case 'start_collector_service':
    case 'stop_collector_service':
      return { ok: true } as T
    default:
      return {} as T
  }
}

function emptyOverview(date: string): OverviewPayload {
  return {
    date,
    collector_status: 'browser-dev',
    active_time: '0m',
    total_time: '0m',
    active_time_sec: 0,
    total_time_sec: 0,
    app_session_count: 0,
    browser_count: 0,
    clipboard_count: 0,
    ai_prompt_count: 0,
    browser_event_count: 0,
    selected_material_count: 0,
    sensitive_count: 0,
    report_status: 'not_generated',
    top_apps: [],
    source_distribution: [],
    category_distribution: [],
    hourly_activity: []
  }
}

function emptyDataCenterSummary() {
  return {
    total: 0,
    app: 0,
    browser: 0,
    clipboard: 0,
    ai_prompt: 0,
    browser_event: 0,
    sensitive: 0,
    deleted: 0,
    categories: [],
    days: []
  }
}

function emptyPromptPreview(date: string, payload: unknown): PromptPreviewPayload {
  const templateName = getPayloadValue(payload, 'templateName')

  return {
    date,
    template_name: typeof templateName === 'string' ? templateName : 'daily_standard',
    prompt: ''
  }
}

function emptyDashboardSummary(date: string): DashboardSummary {
  return {
    date,
    metrics: {
      active_time: '0m',
      total_time: '0m',
      app_sessions: 0,
      clipboard: 0,
      browser: 0,
      ai_prompts: 0,
      browser_events: 0
    },
    top_apps: [],
    time_distribution: [],
    recent_activities: [],
    weekly_trend: []
  }
}

function emptyAppProfileCounts() {
  return {
    all: 0,
    classified: 0,
    unclassified: 0,
    configured: 0,
    excluded: 0
  }
}

function emptyAppProfileConfig(payload: unknown) {
  const appKey = String(getPayloadValue(payload, 'app_key') || '')
  const processName = String(getPayloadValue(payload, 'process_name') || appKey)

  return {
    app_key: appKey,
    process_name: processName,
    exe_path: null,
    default_display_name: processName,
    display_name: null,
    effective_display_name: processName,
    category: '其他',
    category_color: '#8F98A8',
    color: null,
    effective_color: '#8F98A8',
    icon_base64: null,
    icon_path: null,
    icon_url: null,
    track_enabled: true,
    capture_title_enabled: true,
    session_count: 0,
    total_duration_sec: 0,
    total_active_duration_sec: 0,
    last_seen_at: null,
    sample_window_title: null,
    is_configured: false,
    is_classified: false,
    created_at: null,
    updated_at: null
  }
}

function emptyAppCategoryConfig(payload: unknown) {
  return {
    name: String(getPayloadValue(payload, 'name') || ''),
    color: String(getPayloadValue(payload, 'color') || '#8F98A8'),
    sort_order: Number(getPayloadValue(payload, 'sort_order') || 100),
    is_builtin: false,
    is_deleted: false,
    profile_count: 0
  }
}

function emptyHealth(): HealthPayload {
  return {
    ok: false,
    collector_status: 'browser-dev',
    collector_states: []
  }
}

function defaultSettings(): LocalSettingsPayload {
  return {
    model: {
      provider: 'deepseek',
      model_name: 'deepseek-chat',
      base_url: 'https://api.deepseek.com',
      api_key: '',
      max_prompt_chars: 12000,
      timeout_seconds: 60,
      temperature: 0.3
    },
    collector: {
      foreground_enabled: true,
      clipboard_enabled: true,
      edge_history_enabled: true,
      ai_prompt_enabled: true,
      foreground_poll_interval_sec: 2,
      edge_sync_interval_min: 3
    },
    privacy: {
      hide_sensitive_by_default: true,
      sensitive_unselected_by_default: true,
      require_manual_confirm_before_llm: true,
      clipboard_preview_only: true,
      sensitive_keywords: []
    },
    yasb: {
      status_cli_command: 'daily-report status --json',
      status_json_path: ''
    },
    logging: {
      level: 'INFO',
      retention_days: 30
    }
  }
}
