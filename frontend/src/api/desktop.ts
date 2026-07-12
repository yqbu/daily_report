import { apiPost } from './client'
import type { DesktopMethodPayloadMap, DesktopMethodResultMap } from './types'

export async function callDesktopApi<T = unknown>(method: string, payload: unknown = {}): Promise<T> {
  return apiPost<T>(`/api/desktop/${encodeURIComponent(method)}`, payload)
}

export function callTypedDesktopApi<Method extends keyof DesktopMethodPayloadMap>(
  method: Method,
  payload: DesktopMethodPayloadMap[Method]
): Promise<DesktopMethodResultMap[Method]> {
  return callDesktopApi<DesktopMethodResultMap[Method]>(method, payload)
}
