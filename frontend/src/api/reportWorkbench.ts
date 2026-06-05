import { callBridge, callBridgeJob } from './bridge'
import type { AnyRecord } from './types'
import type {
  BuildPromptPayload,
  BuildPromptResult,
  GenerateReportPayload,
  GenerateReportResult,
  ListReportsPayload,
  ListReportsResult,
  MaterialIdentity,
  ReportDetail,
  ReportMaterialsPayload,
  ReportMaterialsResult,
  SaveReportPayload,
  SaveReportResult
} from '../types/reportWorkbench'

export async function getReportMaterials(payload: ReportMaterialsPayload): Promise<ReportMaterialsResult> {
  const response = await callBridge<Partial<ReportMaterialsResult> & { items?: unknown[]; total?: number }>('getReportMaterials', payload)
  return {
    summary: {
      total_count: Number(response.summary?.total_count ?? response.total ?? response.items?.length ?? 0),
      selected_count: Number(response.summary?.selected_count ?? 0),
      sensitive_excluded_count: Number(response.summary?.sensitive_excluded_count ?? 0),
      pending_count: Number(response.summary?.pending_count ?? 0),
      estimated_prompt_chars: Number(response.summary?.estimated_prompt_chars ?? 0)
    },
    items: Array.isArray(response.items) ? response.items as ReportMaterialsResult['items'] : [],
    hasMore: Boolean(response.hasMore)
  }
}

export async function updateEntrySelection(payload: MaterialIdentity & { selected: boolean; ids?: number[] }): Promise<void> {
  await callBridge('updateEntrySelection', payload)
}

export async function batchUpdateEntrySelection(payload: { items: MaterialIdentity[]; selected: boolean }): Promise<void> {
  await callBridge('batchUpdateEntrySelection', payload)
}

export async function getEntryDetail(payload: MaterialIdentity): Promise<AnyRecord | null> {
  return callBridge<AnyRecord | null>('getEntryDetail', payload)
}

export async function updateEntryAnnotation(payload: {
  sourceType: string
  id: number
  entryKey?: string | null
  payload: Record<string, unknown>
}): Promise<void> {
  await callBridge('updateEntryAnnotation', payload)
}

export async function updateEntrySensitive(payload: {
  sourceType: string
  id: number
  entryKey?: string | null
  sensitive: boolean
  reason?: string | null
}): Promise<void> {
  await callBridge('updateEntrySensitive', payload)
}

export async function buildPrompt(payload: BuildPromptPayload): Promise<BuildPromptResult> {
  const response = await callBridge<Partial<BuildPromptResult> & { prompt?: string; template_name?: string }>('buildPrompt', payload)
  const promptText = String(response.prompt_text ?? response.prompt ?? '')
  return {
    prompt_text: promptText,
    material_snapshot_json: String(response.material_snapshot_json ?? ''),
    estimated_tokens: response.estimated_tokens,
    warnings: response.warnings
  }
}

export async function generateReport(payload: GenerateReportPayload): Promise<GenerateReportResult> {
  const response = await callBridgeJob<Partial<GenerateReportResult> & { report_id?: number }>('generateReport', payload, 180000)
  return normalizeGenerateResult(response)
}

export async function saveReport(payload: SaveReportPayload): Promise<SaveReportResult> {
  return callBridge<SaveReportResult>('saveReport', payload)
}

export async function listReports(payload: ListReportsPayload): Promise<ListReportsResult> {
  const response = await callBridge<Partial<ListReportsResult> & { items?: unknown[]; total?: number }>('listReports', payload)
  return {
    items: Array.isArray(response.items) ? response.items as ListReportsResult['items'] : [],
    total: Number(response.total ?? response.items?.length ?? 0)
  }
}

export async function getReportDetail(id: number): Promise<ReportDetail | null> {
  return callBridge<ReportDetail | null>('getReportDetail', { id })
}

export async function deleteReport(id: number): Promise<void> {
  await callBridge('deleteReport', { id })
}

function normalizeGenerateResult(response: Partial<GenerateReportResult>): GenerateReportResult {
  return {
    report_id: response.report_id,
    prompt_text: String(response.prompt_text ?? ''),
    report_markdown: String(response.report_markdown ?? ''),
    material_snapshot_json: String(response.material_snapshot_json ?? ''),
    created_at: String(response.created_at ?? new Date().toISOString()),
    warnings: response.warnings
  }
}
