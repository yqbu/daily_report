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

export async function callBridge<T>(method: string, payload: Record<string, unknown> = {}): Promise<T> {
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
  const bridge = await getBridge()
  bridge?.jobFinished?.connect((raw: string) => {
    callback(JSON.parse(raw) as BridgeResponse<unknown>)
  })
}

function mockResponse<T>(method: string): T {
  const page = { items: [], total: 0, page: 1, page_size: 30 } as T
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
    get_settings: {}
  }
  return (responses[method] ?? {}) as T
}
