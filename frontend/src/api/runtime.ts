export interface RuntimeConfig {
  api_base_url: string
  api_token?: string | null
  api_ready?: boolean
  sidecar_mode?: 'manual' | 'managed'
  last_error?: string | null
}

type TauriInvoke = <T>(command: string, args?: Record<string, unknown>) => Promise<T>

declare global {
  interface Window {
    __TAURI_INTERNALS__?: {
      invoke?: TauriInvoke
    }
    __TAURI__?: {
      core?: {
        invoke?: TauriInvoke
      }
    }
  }
}

let cachedRuntimeConfig: RuntimeConfig | null = null

export function fallbackRuntimeConfig(): RuntimeConfig {
  return {
    api_base_url: String(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8765').replace(/\/+$/, ''),
    api_token: String(import.meta.env.VITE_API_TOKEN || '').trim() || null,
    api_ready: false,
    sidecar_mode: 'manual',
    last_error: null
  }
}

export function getCachedRuntimeConfig(): RuntimeConfig | null {
  return cachedRuntimeConfig
}

export async function getRuntimeConfig(options: { refresh?: boolean } = {}): Promise<RuntimeConfig> {
  if (!options.refresh && cachedRuntimeConfig) return cachedRuntimeConfig

  const invoke = getTauriInvoke()
  if (!invoke) {
    cachedRuntimeConfig = fallbackRuntimeConfig()
    return cachedRuntimeConfig
  }

  try {
    cachedRuntimeConfig = normalizeRuntimeConfig(await invoke<RuntimeConfig>('get_runtime_config'))
  } catch {
    cachedRuntimeConfig = fallbackRuntimeConfig()
  }
  return cachedRuntimeConfig
}

export async function refreshRuntimeConfig(): Promise<RuntimeConfig> {
  return getRuntimeConfig({ refresh: true })
}

export async function checkRuntimeApiHealth(): Promise<boolean> {
  const invoke = getTauriInvoke()
  if (!invoke) return false

  try {
    const result = await invoke<{ ok: boolean }>('check_api_health')
    await refreshRuntimeConfig()
    return Boolean(result.ok)
  } catch {
    await refreshRuntimeConfig()
    return false
  }
}

function normalizeRuntimeConfig(config: RuntimeConfig): RuntimeConfig {
  const fallback = fallbackRuntimeConfig()
  return {
    api_base_url: String(config.api_base_url || fallback.api_base_url).replace(/\/+$/, ''),
    api_token: config.api_token || null,
    api_ready: Boolean(config.api_ready),
    sidecar_mode: config.sidecar_mode || 'manual',
    last_error: config.last_error || null
  }
}

function getTauriInvoke(): TauriInvoke | null {
  return window.__TAURI__?.core?.invoke || window.__TAURI_INTERNALS__?.invoke || null
}
