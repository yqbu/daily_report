import type {
  AnyRecord,
  BridgeMethodPayloadMap,
  BridgeMethodResultMap,
  BridgeResponse,
  DashboardSummary,
  HealthPayload,
  LocalSettingsPayload,
  OverviewPayload,
  PromptPreviewPayload,
  SourceType,
  TimelineEvent
} from './types'
import { apiGet, apiMode, apiPatch, apiPost, apiPut } from './client'
import {
  mockBuildPrompt,
  mockEntries,
  mockEntryDetail,
  mockGenerateReport,
  mockHealth,
  mockLatestReport,
  mockOverview,
  mockSettings,
  mockTimeline
} from './mock'

type BridgeSlot = (payload: string, callback: (response: string) => void) => void
type BridgeSignalSlot = (payload: string) => void
type BridgeSignal = {
  connect: (callback: BridgeSignalSlot) => void
  disconnect?: (callback: BridgeSignalSlot) => void
}

interface WebChannel {
  objects: {
    pyBridge?: Record<string, BridgeSlot | BridgeSignal | unknown>
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
const DEFAULT_BRIDGE_TIMEOUT_MS = 30000

interface BridgeJobStart<T> {
  job_id: string
  status?: string
  result?: T
}

interface BridgeJobResult<T> {
  ok: boolean
  jobId?: string
  result?: T
  error?: string
}

export async function callBridge<T = unknown>(method: string, payload: unknown = {}): Promise<T> {
  if (apiMode() !== 'qwebchannel') {
    return callApiModeFallback<T>(method, payload)
  }

  const bridge = await getBridge()

  if (!bridge) {
    return getBrowserFallback<T>(method, payload)
  }

  const slot = bridge[method]
  if (typeof slot !== 'function') {
    if (method === 'getDataCenterSummary' || method === 'getDataCenterAnalytics') {
      return getBrowserFallback<T>(method, payload)
    }
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

async function callApiModeFallback<T>(method: string, payload: unknown): Promise<T> {
  if (apiMode() === 'mock') {
    return getMockFallback<T>(method, payload)
  }
  return callHttpFallback<T>(method, payload)
}

async function callHttpFallback<T>(method: string, payload: unknown): Promise<T> {
  const date = getPayloadDate(payload)
  switch (method) {
    case 'getOverview':
      return apiGet<T>('/api/overview', { date })
    case 'getTimeline':
      return apiGet<T>('/api/timeline', timelineParams(payload))
    case 'listEntries':
      return listEntriesHttp<T>(payload)
    case 'getEntryDetail':
      return getEntryDetailHttp<T>(payload)
    case 'updateEntrySelection':
      return apiPatch<T>(`/api/entries/${getPayloadSourceType(payload)}/${getPayloadNumber(payload, 'id', 0)}/selection`, {
        selected: Boolean(getPayloadValue(payload, 'selected'))
      })
    case 'markEntryDeleted':
      return apiPatch<T>(`/api/entries/${getPayloadSourceType(payload)}/${getPayloadNumber(payload, 'id', 0)}/deleted`, {
        deleted: true
      })
    case 'getDataCenterSummary':
      return buildDataCenterSummaryHttp<T>(payload)
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
      return { summary: await buildDataCenterSummaryHttp(payload), charts: {} } as T
    case 'getReportMaterials':
      return buildReportMaterialsHttp<T>(payload)
    case 'batchUpdateEntrySelection':
      return { ok: true, updated: 0 } as T
    case 'updateEntryAnnotation':
    case 'updateEntrySensitive':
    case 'listAppProfiles':
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
    case 'select_directory':
    case 'select_json_file':
      return getBrowserFallback<T>(method, payload)
    default:
      return getBrowserFallback<T>(method, payload)
  }
}

function getMockFallback<T>(method: string, payload: unknown): T {
  const date = getPayloadDate(payload)
  switch (method) {
    case 'getOverview':
      return mockOverview(date) as T
    case 'getTimeline':
      return mockTimeline(date) as T
    case 'listEntries':
      return mockEntries(getPayloadSourceType(payload), date) as T
    case 'getEntryDetail':
      return mockEntryDetail(getPayloadSourceType(payload), getPayloadNumber(payload, 'id', 0)) as T
    case 'buildPrompt':
      return { ...mockBuildPrompt(date, String(getPayloadValue(payload, 'templateName') || 'daily_standard')), prompt: mockBuildPrompt(date).prompt_text } as T
    case 'generateReport':
      return mockGenerateReport(date) as T
    case 'getLatestReport':
      return mockLatestReport(date).report as T
    case 'getSettings':
      return mockSettings() as T
    case 'saveSettings':
      return payload as T
    case 'getHealth':
    case 'get_collector_status':
      return mockHealth() as T
    default:
      return getBrowserFallback<T>(method, payload)
  }
}

function timelineParams(payload: unknown): Record<string, unknown> {
  const filters = isObjectRecord(getPayloadValue(payload, 'filters')) ? getPayloadValue(payload, 'filters') as AnyRecord : {}
  const sourceTypes = getPayloadValue(filters, 'sourceTypes') || getPayloadValue(filters, 'source_types')
  const firstSource = Array.isArray(sourceTypes) && sourceTypes.length === 1 ? sourceTypes[0] : 'all'
  return {
    date: getPayloadValue(payload, 'date') || getPayloadValue(payload, 'startDate') || getPayloadValue(payload, 'start_date'),
    source_type: firstSource || 'all',
    selected: getPayloadValue(filters, 'selected'),
    sensitive: getPayloadValue(filters, 'sensitive'),
    keyword: getPayloadValue(filters, 'keyword'),
    limit: getPayloadNumber(payload, 'pageSize', getPayloadNumber(payload, 'limit', 500)),
    offset: getPayloadNumber(payload, 'offset', getPayloadNumber(payload, 'cursor', 0)),
    order: getPayloadValue(filters, 'sortOrder') || getPayloadValue(filters, 'sort_order') || 'asc'
  }
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
    limit: pageSize,
    offset: (page - 1) * pageSize
  })
}

async function getEntryDetailHttp<T>(payload: unknown): Promise<T> {
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
    summary.sensitive += item.sensitive_count || 0
    const dayCount = (item.app_session_count || 0) + (item.browser_count || 0) + (item.clipboard_count || 0) + (item.ai_prompt_count || 0)
    summary.days.push({ date: item.date, count: dayCount })
    for (const category of item.category_distribution || []) {
      categories.set(category.category, (categories.get(category.category) || 0) + category.count)
    }
  }
  summary.total = summary.app + summary.browser + summary.clipboard + summary.ai_prompt
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
      title: item.title,
      summary: item.content_preview || item.subtitle || '',
      evidence: item.content_preview || '',
      category: item.category || '其他',
      time_range: item.start_time,
      importance: 0,
      is_sensitive: item.is_sensitive,
      is_selected: item.is_selected
    })),
    hasMore: false
  } as T
}

function getPayloadSourceType(payload: unknown): SourceType {
  const raw = String(getPayloadValue(payload, 'sourceType') || getPayloadValue(payload, 'source_type') || 'app')
  return (raw === 'ai' ? 'ai_prompt' : raw) as SourceType
}

function dateRangeDays(payload: unknown): string[] {
  const start = String(getPayloadValue(payload, 'startDate') || getPayloadValue(payload, 'start_date') || getPayloadDate(payload)).slice(0, 10)
  const end = String(getPayloadValue(payload, 'endDate') || getPayloadValue(payload, 'end_date') || start).slice(0, 10)
  const startDate = new Date(`${start}T00:00:00`)
  const endDate = new Date(`${end}T00:00:00`)
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return [getPayloadDate(payload)]
  const first = startDate <= endDate ? startDate : endDate
  const last = startDate <= endDate ? endDate : startDate
  const days: string[] = []
  const cursor = new Date(first)
  while (cursor <= last && days.length < 367) {
    days.push(cursor.toISOString().slice(0, 10))
    cursor.setDate(cursor.getDate() + 1)
  }
  return days
}

export function callTypedBridge<Method extends keyof BridgeMethodPayloadMap>(
  method: Method,
  payload: BridgeMethodPayloadMap[Method]
): Promise<BridgeMethodResultMap[Method]> {
  return callBridge<BridgeMethodResultMap[Method]>(method, payload)
}

export async function callBridgeJob<T = unknown>(
  method: string,
  payload: unknown = {},
  timeoutMs = DEFAULT_BRIDGE_TIMEOUT_MS
): Promise<T> {
  const bridge = await getBridge()
  const signal = bridge?.jobFinished
  if (!isBridgeSignal(signal)) {
    const result = await callBridge<BridgeJobStart<T> | T>(method, payload)
    if (isBridgeJobStart<T>(result)) {
      throw new Error('Python bridge job signal is not available.')
    }
    return result as T
  }

  const jobSignal = signal
  return new Promise<T>((resolve, reject) => {
    let jobId = ''
    const pendingJobPayloads: BridgeJobResult<T>[] = []

    const timer = window.setTimeout(() => {
      cleanup()
      reject(new Error(`Python bridge job timed out: ${method}`))
    }, timeoutMs)

    const handler: BridgeSignalSlot = (rawPayload) => {
      let jobPayload: BridgeJobResult<T>
      try {
        jobPayload = unwrapBridgeJobResult<T>(rawPayload)
      } catch (error) {
        cleanup()
        reject(error)
        return
      }

      if (!jobId) {
        pendingJobPayloads.push(jobPayload)
        return
      }

      if (jobPayload.jobId !== jobId) {
        return
      }

      settleJob(jobPayload)
    }

    function cleanup(): void {
      window.clearTimeout(timer)
      jobSignal.disconnect?.(handler)
    }

    function settleJob(jobPayload: BridgeJobResult<T>): void {
      cleanup()
      if (jobPayload.ok) {
        resolve(jobPayload.result as T)
      } else {
        reject(new Error(jobPayload.error || `Python bridge job failed: ${jobId}`))
      }
    }

    jobSignal.connect(handler)

    callBridge<BridgeJobStart<T> | T>(method, payload)
      .then((start) => {
        if (!isBridgeJobStart<T>(start)) {
          cleanup()
          resolve(start as T)
          return
        }
        jobId = start.job_id
        const pendingPayload = pendingJobPayloads.find((jobPayload) => jobPayload.jobId === jobId)
        if (pendingPayload) {
          settleJob(pendingPayload)
        }
      })
      .catch((error) => {
        cleanup()
        reject(error)
      })
  })
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

function unwrapBridgeJobResult<T>(rawPayload: string): BridgeJobResult<T> {
  let response: unknown

  try {
    response = JSON.parse(rawPayload)
  } catch {
    throw new Error(`Invalid Python bridge job response: ${rawPayload}`)
  }

  if (!isObjectRecord(response)) {
    throw new Error('Invalid Python bridge job response shape.')
  }

  if (isBridgeResponse<T>(response)) {
    const data = isObjectRecord(response.data) ? response.data : undefined
    return {
      ok: response.ok,
      jobId: getJobId(data) || getJobId(response),
      result: (data?.result ?? response.data) as T,
      error: response.error
    }
  }

  return {
    ok: Boolean(response.ok),
    jobId: getJobId(response),
    result: response.result as T,
    error: typeof response.error === 'string' ? response.error : undefined
  }
}

function isBridgeJobStart<T>(value: BridgeJobStart<T> | T): value is BridgeJobStart<T> {
  return isObjectRecord(value) && typeof value.job_id === 'string' && value.job_id.length > 0
}

function isBridgeSignal(value: unknown): value is BridgeSignal {
  return isObjectRecord(value) && typeof value.connect === 'function'
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function getJobId(value: unknown): string | undefined {
  if (!isObjectRecord(value)) {
    return undefined
  }
  return typeof value.job_id === 'string' ? value.job_id : undefined
}

function getBrowserFallback<T>(method: string, payload: unknown): T {
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
      return { message: '浏览器预览模式未连接 Python bridge，已跳过真实模型测试。' } as T
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

function emptyDataCenterSummary() {
  return {
    total: 0,
    app: 0,
    browser: 0,
    clipboard: 0,
    ai_prompt: 0,
    sensitive: 0,
    deleted: 0,
    categories: []
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
