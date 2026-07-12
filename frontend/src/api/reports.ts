import { apiGet, apiPost } from './client'
import type {
  BuildPromptRequest,
  BuildPromptResponse,
  GenerateReportRequest,
  GenerateReportResponse,
  LatestReportResponse
} from './types'

export async function buildPrompt(payload: BuildPromptRequest = {}): Promise<BuildPromptResponse> {
  return apiPost<BuildPromptResponse>('/api/reports/build-prompt', payload)
}

export async function generateReport(payload: GenerateReportRequest = {}): Promise<GenerateReportResponse> {
  return apiPost<GenerateReportResponse>('/api/reports/generate', payload)
}

export async function getLatestReport(date?: string): Promise<LatestReportResponse> {
  return apiGet<LatestReportResponse>('/api/reports/latest', { date })
}
