import { apiGet, apiMode, apiPost } from './client'
import { mockBuildPrompt, mockGenerateReport, mockLatestReport } from './mock'
import type {
  BuildPromptRequest,
  BuildPromptResponse,
  GenerateReportRequest,
  GenerateReportResponse,
  LatestReportResponse
} from './types'
import { callTypedBridge } from './bridge'

export async function buildPrompt(payload: BuildPromptRequest = {}): Promise<BuildPromptResponse> {
  if (apiMode() === 'mock') return mockBuildPrompt(payload.date, payload.template_name)
  if (apiMode() === 'qwebchannel') {
    const response = await callTypedBridge('buildPrompt', {
      date: payload.date,
      templateName: payload.template_name || 'daily_standard'
    })
    return {
      date: response.date,
      template_name: response.template_name,
      prompt_text: response.prompt
    }
  }
  return apiPost<BuildPromptResponse>('/api/reports/build-prompt', payload)
}

export async function generateReport(payload: GenerateReportRequest = {}): Promise<GenerateReportResponse> {
  if (apiMode() === 'mock') return mockGenerateReport(payload.date)
  if (apiMode() === 'qwebchannel') {
    const response = await callTypedBridge('generateReport', {
      date: payload.date,
      templateName: payload.template_name || 'daily_standard'
    })
    return {
      date: payload.date || new Date().toISOString().slice(0, 10),
      report_id: response.report_id,
      report_markdown: response.report_markdown,
      prompt_text: response.prompt_text
    }
  }
  return apiPost<GenerateReportResponse>('/api/reports/generate', payload)
}

export async function getLatestReport(date?: string): Promise<LatestReportResponse> {
  if (apiMode() === 'mock') return mockLatestReport(date)
  if (apiMode() === 'qwebchannel') {
    const report = await callTypedBridge('getLatestReport', { date })
    return { date: date || new Date().toISOString().slice(0, 10), report: report as unknown as LatestReportResponse['report'] }
  }
  return apiGet<LatestReportResponse>('/api/reports/latest', { date })
}
