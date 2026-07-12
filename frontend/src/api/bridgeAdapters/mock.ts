import {
  mockBuildPrompt,
  mockEntries,
  mockEntryDetail,
  mockGenerateReport,
  mockHealth,
  mockLatestReport,
  mockOverview,
  mockSettings,
  mockTimeline
} from '../mock'
import { getBrowserFallback } from './fallback'
import { getPayloadDate, getPayloadNumber, getPayloadSourceType, getPayloadValue } from './shared'

export async function callMockBridge<T>(method: string, payload: unknown): Promise<T> {
  const date = getPayloadDate(payload)
  switch (method) {
    case 'getOverview':
      return mockOverview(date) as T
    case 'getTimeline':
      return mockTimeline(date) as T
    case 'listEntries':
      return mockEntries(getPayloadSourceType(payload), date) as T
    case 'getEntryDetail':
      return mockEntryDetail(getPayloadSourceType(payload), getPayloadNumber(payload, 'id', 0)) as T
    case 'buildPrompt':
      return {
        ...mockBuildPrompt(date, String(getPayloadValue(payload, 'templateName') || 'daily_standard')),
        prompt: mockBuildPrompt(date).prompt_text
      } as T
    case 'generateReport':
      return mockGenerateReport(date) as T
    case 'getLatestReport':
      return mockLatestReport(date).report as T
    case 'getSettings':
      return mockSettings() as T
    case 'saveSettings':
      return payload as T
    case 'getHealth':
    case 'get_collector_status':
      return mockHealth() as T
    default:
      return getBrowserFallback<T>(method, payload)
  }
}
