import type { AnyRecord, SourceType } from '../types'

export type BridgeSlot = (payload: string, callback: (response: string) => void) => void
export type BridgeSignalSlot = (payload: string) => void

export type BridgeSignal = {
  connect: (callback: BridgeSignalSlot) => void
  disconnect?: (callback: BridgeSignalSlot) => void
}

export interface BridgeJobStart<T> {
  job_id: string
  status?: string
  result?: T
}

export interface BridgeJobResult<T> {
  ok: boolean
  jobId?: string
  result?: T
  error?: string
}

export const DEFAULT_BRIDGE_TIMEOUT_MS = 30000

export function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export function getPayloadDate(payload: unknown): string {
  const value = getPayloadValue(payload, 'date')
  return typeof value === 'string' && value.trim() ? value : new Date().toISOString().slice(0, 10)
}

export function getPayloadNumber(payload: unknown, key: string, fallback: number): number {
  const value = getPayloadValue(payload, key)
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

export function getPayloadValue(payload: unknown, key: string): unknown {
  if (!isObjectRecord(payload)) {
    return undefined
  }

  return (payload as AnyRecord)[key]
}

export function getPayloadSourceType(payload: unknown): SourceType {
  const raw = String(getPayloadValue(payload, 'sourceType') || getPayloadValue(payload, 'source_type') || 'app')
  if (raw === 'browser_events') return 'browser_event'
  return (raw === 'ai' ? 'ai_prompt' : raw) as SourceType
}

export function getPayloadEntryKey(payload: unknown): string | null {
  const value = getPayloadValue(payload, 'entryKey') || getPayloadValue(payload, 'entry_key')
  return typeof value === 'string' && value.trim() ? value.trim() : null
}

export function dateRangeDays(payload: unknown): string[] {
  const start = String(
    getPayloadValue(payload, 'startDate') || getPayloadValue(payload, 'start_date') || getPayloadDate(payload)
  ).slice(0, 10)
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
