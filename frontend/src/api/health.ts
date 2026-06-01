import { apiGet, apiMode } from './client'
import { mockHealth } from './mock'
import { callTypedBridge } from './bridge'

export async function getHealth(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return mockHealth()
  if (apiMode() === 'qwebchannel') return callTypedBridge('getHealth', {})
  return apiGet<Record<string, unknown>>('/api/health')
}

export async function getCollectorHealth(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return { collectors: [], collector_status: 'mock' }
  if (apiMode() === 'qwebchannel') return callTypedBridge('getHealth', {})
  return apiGet<Record<string, unknown>>('/api/health/collectors')
}

