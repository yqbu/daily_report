import { ElMessage } from 'element-plus'
import { fallbackRuntimeConfig, getCachedRuntimeConfig, getRuntimeConfig } from './runtime'

export interface ApiResponse<T> {
  ok: boolean
  data?: T
  error?: string
  code?: string
}

export class ApiClientError extends Error {
  code: string
  status: number

  constructor(message: string, code = 'API_ERROR', status = 0) {
    super(message)
    this.name = 'ApiClientError'
    this.code = code
    this.status = status
  }
}

const DEFAULT_TIMEOUT_MS = 15000
const CONNECTION_ERROR_MESSAGE =
  '无法连接本地 Daily Report API，请确认已运行：daily-report api --host 127.0.0.1 --port 8765'

let lastMessage = ''
let lastMessageAt = 0

export function apiMode(): 'mock' | 'http' | 'qwebchannel' | 'tauri' {
  const mode = String(import.meta.env.VITE_API_MODE || 'http').toLowerCase()
  if (mode === 'mock' || mode === 'qwebchannel' || mode === 'tauri') return mode
  return 'http'
}

export function apiBaseUrl(): string {
  if (apiMode() === 'tauri') {
    return (getCachedRuntimeConfig() || fallbackRuntimeConfig()).api_base_url
  }
  return String(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8765').replace(/\/+$/, '')
}

export async function apiGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return apiRequest<T>('GET', url, undefined, params)
}

export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  return apiRequest<T>('POST', url, body)
}

export async function apiPatch<T>(url: string, body?: unknown): Promise<T> {
  return apiRequest<T>('PATCH', url, body)
}

export async function apiPut<T>(url: string, body?: unknown): Promise<T> {
  return apiRequest<T>('PUT', url, body)
}

async function apiRequest<T>(
  method: string,
  url: string,
  body?: unknown,
  params?: Record<string, unknown>
): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)

  try {
    const response = await fetch(await buildUrl(url, params), {
      method,
      headers: await buildHeaders(body),
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal
    })
    const payload = (await response.json().catch(() => null)) as ApiResponse<T> | null
    if (!response.ok) {
      throw new ApiClientError(payload?.error || `HTTP ${response.status}`, payload?.code || 'HTTP_ERROR', response.status)
    }
    if (!payload || typeof payload.ok !== 'boolean') {
      throw new ApiClientError('Invalid API response', 'INVALID_RESPONSE', response.status)
    }
    if (!payload.ok) {
      throw new ApiClientError(payload.error || 'API request failed', payload.code || 'API_ERROR', response.status)
    }
    return payload.data as T
  } catch (error) {
    const clientError = normalizeApiError(error)
    showApiError(clientError.message)
    throw clientError
  } finally {
    window.clearTimeout(timer)
  }
}

async function buildUrl(url: string, params?: Record<string, unknown>): Promise<string> {
  if (apiMode() === 'tauri') {
    await getRuntimeConfig()
  }
  const absolute = `${apiBaseUrl()}${url.startsWith('/') ? url : `/${url}`}`
  const target = new URL(absolute)
  for (const [key, value] of Object.entries(params || {})) {
    if (value === undefined || value === null || value === '') continue
    target.searchParams.set(key, String(value))
  }
  return target.toString()
}

async function buildHeaders(body: unknown): Promise<HeadersInit> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const runtime = apiMode() === 'tauri' ? await getRuntimeConfig() : null
  const token = String(runtime?.api_token || import.meta.env.VITE_API_TOKEN || '').trim()
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

function normalizeApiError(error: unknown): ApiClientError {
  if (error instanceof ApiClientError) return error
  if (error instanceof DOMException && error.name === 'AbortError') {
    return new ApiClientError('本地 Daily Report API 请求超时', 'TIMEOUT')
  }
  return new ApiClientError(CONNECTION_ERROR_MESSAGE, 'NETWORK_ERROR')
}

function showApiError(message: string): void {
  const now = Date.now()
  if (message === lastMessage && now - lastMessageAt < 2500) return
  lastMessage = message
  lastMessageAt = now
  ElMessage.error(message)
}
