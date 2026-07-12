import { apiGet, apiPut } from './client'

export async function getSettings(): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>('/api/settings')
}

export async function saveSettings(payload: object): Promise<Record<string, unknown>> {
  return apiPut<Record<string, unknown>>('/api/settings', payload)
}
