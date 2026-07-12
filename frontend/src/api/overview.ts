import { apiGet } from './client'
import type { OverviewDTO } from './types'

export async function getOverview(date?: string): Promise<OverviewDTO> {
  return apiGet<OverviewDTO>('/api/overview', { date })
}

