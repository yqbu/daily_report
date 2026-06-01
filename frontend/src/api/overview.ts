import { apiGet, apiMode } from './client'
import { mockOverview } from './mock'
import type { OverviewDTO } from './types'
import { callTypedBridge } from './bridge'

export async function getOverview(date?: string): Promise<OverviewDTO> {
  if (apiMode() === 'mock') return mockOverview(date)
  if (apiMode() === 'qwebchannel') return callTypedBridge('getOverview', { date })
  return apiGet<OverviewDTO>('/api/overview', { date })
}

