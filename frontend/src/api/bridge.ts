import type {
  AnyRecord,
  BridgeMethodPayloadMap,
  BridgeMethodResultMap,
  BridgeResponse,
  DashboardSummary,
  HealthPayload,
  LocalSettingsPayload,
  OverviewPayload,
  PromptPreviewPayload
} from './types'

type BridgeSlot = (payload: string, callback: (response: string) => void) => void

interface WebChannel {
  objects: {
    pyBridge?: Record<string, BridgeSlot | unknown>
  }
}

type QWebChannelConstructor = new (
  transport: unknown,
  callback: (channel: WebChannel) => void
) => unknown

declare global {
  interface Window {
    qt?: {
      webChannelTransport?: unknown
    }
    QWebChannel?: QWebChannelConstructor
  }
}

let bridgePromise: Promise<Record<string, BridgeSlot | unknown> | null> | null = null

export async function callBridge<T = unknown>(method: string, payload: unknown = {}): Promise<T> {
  const bridge = await getBridge()

  if (!bridge) {
    return getBrowserFallback<T>(method, payload)
  }

  const slot = bridge[method]
  if (typeof slot !== 'function') {
    throw new Error(`Python bridge method not found: ${method}`)
  }

  const callSlot = slot as BridgeSlot

  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(`Python bridge call timed out: ${method}`))
    }, 30000)

    try {
      callSlot(encodePayload(payload), (response) => {
        window.clearTimeout(timer)
        try {
          resolve(unwrapBridgeResponse<T>(method, response))
        } catch (error) {
          reject(error)
        }
      })
    } catch (error) {
      window.clearTimeout(timer)
      reject(error)
    }
  })
}

export function callTypedBridge<Method extends keyof BridgeMethodPayloadMap>(
  method: Method,
  payload: BridgeMethodPayloadMap[Method]
): Promise<BridgeMethodResultMap[Method]> {
  return callBridge<BridgeMethodResultMap[Method]>(method, payload)
}

async function getBridge(): Promise<Record<string, BridgeSlot | unknown> | null> {
  if (typeof window === 'undefined') {
    return null
  }

  if (bridgePromise) {
    return bridgePromise
  }

  const transport = window.qt?.webChannelTransport
  const QWebChannel = window.QWebChannel
  if (!transport || !QWebChannel) {
    bridgePromise = Promise.resolve(null)
    return bridgePromise
  }

  bridgePromise = new Promise((resolve) => {
    new QWebChannel(transport, (channel) => {
      resolve(channel.objects.pyBridge ?? null)
    })
  })

  return bridgePromise
}

function encodePayload(payload: unknown): string {
  return JSON.stringify(payload ?? {})
}

function unwrapBridgeResponse<T>(method: string, rawResponse: string): T {
  let response: unknown

  try {
    response = JSON.parse(rawResponse)
  } catch {
    throw new Error(`Invalid Python bridge response for ${method}: ${rawResponse}`)
  }

  if (!isBridgeResponse<T>(response)) {
    return response as T
  }

  if (!response.ok) {
    throw new Error(response.error || `Python bridge call failed: ${method}`)
  }

  return response.data as T
}

function isBridgeResponse<T>(value: unknown): value is BridgeResponse<T> {
  return (
    typeof value === 'object' &&
    value !== null &&
    'ok' in value &&
    typeof (value as BridgeResponse<T>).ok === 'boolean'
  )
}

function getBrowserFallback<T>(method: string, payload: unknown): T {
  const date = getPayloadDate(payload)

  switch (method) {
    case 'getOverview':
      return emptyOverview(date) as T
    case 'getTimeline':
      return { items: [], total: 0 } as T
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
    case 'listAppProfiles':
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
      return { date, items: [], total: 0 } as T
    case 'buildPrompt':
      return emptyPromptPreview(date, payload) as T
    case 'generateReport':
      return {
        report_id: 0,
        prompt_text: '',
        report_markdown: ''
      } as T
    case 'getLatestReport':
      return null as T
    case 'listReports':
      return { items: [], total: 0 } as T
    case 'getSettings':
      return defaultSettings() as T
    case 'saveSettings':
      return payload as T
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

function getPayloadDate(payload: unknown): string {
  const value = getPayloadValue(payload, 'date')
  return typeof value === 'string' && value.trim() ? value : new Date().toISOString().slice(0, 10)
}

function getPayloadNumber(payload: unknown, key: string, fallback: number): number {
  const value = getPayloadValue(payload, key)
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function getPayloadValue(payload: unknown, key: string): unknown {
  if (typeof payload !== 'object' || payload === null) {
    return undefined
  }

  return (payload as AnyRecord)[key]
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
    selected_material_count: 0,
    sensitive_count: 0,
    report_status: 'not_generated',
    top_apps: [],
    source_distribution: [],
    category_distribution: [],
    hourly_activity: []
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
      ai_prompts: 0
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
