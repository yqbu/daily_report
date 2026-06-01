import { apiGet, apiMode, apiPut } from './client'
import { mockSettings } from './mock'
import { callTypedBridge } from './bridge'

export async function getSettings(): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return mockSettings()
  if (apiMode() === 'qwebchannel') return callTypedBridge('getSettings', {}) as unknown as Record<string, unknown>
  return apiGet<Record<string, unknown>>('/api/settings')
}

export async function saveSettings(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  if (apiMode() === 'mock') return payload
  if (apiMode() === 'qwebchannel') return callTypedBridge('saveSettings', payload as never) as unknown as Record<string, unknown>
  return apiPut<Record<string, unknown>>('/api/settings', payload)
}
