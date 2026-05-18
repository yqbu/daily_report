import type { BridgeResponse } from './types'

type PyBridge = Record<string, (...args: unknown[]) => void> & {
  jobFinished?: { connect: (callback: (payload: string) => void) => void }
}

declare global {
  interface Window {
    qt?: { webChannelTransport: unknown }
    QWebChannel?: new (transport: unknown, callback: (channel: { objects: { pyBridge: PyBridge } }) => void) => void
  }
}

let bridgePromise: Promise<PyBridge | null> | null = null
let cachedBridge: PyBridge | null = null
const jobFinishedListeners = new Set<(payload: BridgeResponse<unknown>) => void>()
let jobFinishedConnected = false

export function isBridgeAvailable() {
  return Boolean(window.qt?.webChannelTransport && window.QWebChannel)
}

export async function getBridge(): Promise<PyBridge | null> {
  if (cachedBridge) return cachedBridge
  if (!bridgePromise) {
    bridgePromise = new Promise((resolve) => {
      if (!isBridgeAvailable()) {
        resolve(null)
        return
      }
      new window.QWebChannel!(window.qt!.webChannelTransport, (channel) => {
        cachedBridge = channel.objects.pyBridge
        resolve(cachedBridge)
      })
    })
  }
  return bridgePromise
}

export async function callBridge<T>(method: string, payload: object = {}): Promise<T> {
  const bridge = await getBridge()
  if (!bridge || typeof bridge[method] !== 'function') {
    return mockResponse<T>(method)
  }
  return new Promise((resolve, reject) => {
    bridge[method](JSON.stringify(payload), (raw: string) => {
      try {
        const response = JSON.parse(raw) as BridgeResponse<T>
        if (response.ok) {
          resolve(response.data as T)
        } else {
          reject(new Error(response.error || 'Python bridge call failed'))
        }
      } catch (error) {
        reject(error)
      }
    })
  })
}

export async function onBridgeJobFinished(callback: (payload: BridgeResponse<unknown>) => void) {
  jobFinishedListeners.add(callback)
  const bridge = await getBridge()
  if (bridge?.jobFinished && !jobFinishedConnected) {
    jobFinishedConnected = true
    bridge.jobFinished.connect((raw: string) => {
      const payload = JSON.parse(raw) as BridgeResponse<unknown>
      jobFinishedListeners.forEach((listener) => listener(payload))
    })
  }
  return () => {
    jobFinishedListeners.delete(callback)
  }
}

function mockResponse<T>(method: string): T {
  const page = { items: [], total: 0, page: 1, page_size: 30 } as T
  const settings = {
    settings_path: 'data/local_settings.json',
    model: { provider: 'deepseek', model_name: 'deepseek-chat', base_url: 'https://api.deepseek.com', api_key: '', max_prompt_chars: 12000, timeout_seconds: 60, temperature: 0.3 },
    collector: { foreground_enabled: true, clipboard_enabled: true, edge_history_enabled: true, ai_prompt_enabled: true, foreground_poll_interval_sec: 2, edge_sync_interval_min: 3 },
    privacy: { hide_sensitive_by_default: true, sensitive_unselected_by_default: true, require_manual_confirm_before_llm: true, clipboard_preview_only: true, sensitive_keywords: [] },
    logging: { level: 'INFO', retention_days: 30 }
  }
  const responses: Record<string, unknown> = {
    get_dashboard_summary: {
      date: new Date().toISOString().slice(0, 10),
      metrics: { active_time: '0m', total_time: '0m', app_sessions: 0, clipboard: 0, browser: 0, ai_prompts: 0 },
      top_apps: [],
      time_distribution: Array.from({ length: 24 }, (_, index) => ({ label: `${String(index).padStart(2, '0')}:00`, active: 0 })),
      recent_activities: [],
      weekly_trend: []
    },
    get_app_sessions: page,
    get_clipboard_entries: page,
    get_browser_entries: page,
    get_ai_prompt_entries: page,
    get_materials: { items: [], total: 0, selected: 0 },
    get_report_history: page,
    get_report_detail: null,
    generate_report: { job_id: 'mock', status: 'started' },
    get_collector_status: { status: 'dev', message: 'QWebChannel is not available in browser dev mode.' },
    get_settings: settings,
    save_settings: settings,
    test_model_connection: { message: '浏览器开发模式未连接 Python 后端，无法测试真实模型。' }
  }
  return (responses[method] ?? {}) as T
}
