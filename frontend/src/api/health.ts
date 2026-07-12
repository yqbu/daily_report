import { apiGet } from './client'

export async function getHealth(): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>('/api/health')
}

export async function getCollectorHealth(): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>('/api/health/collectors')
}

