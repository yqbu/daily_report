import type { Component } from 'vue'
import type { AnyRecord, SourceType } from '../api/types'

export type ReportWorkbenchTab = 'generate' | 'history'
export type SensitiveMaterialFilter = 'non_sensitive' | 'sensitive' | 'all'
export type ReportResultView = 'preview' | 'markdown' | 'prompt'
export type GenerateStep = 0 | 1 | 2 | 3
export type ReportTopbarActionTone = 'default' | 'primary' | 'success' | 'danger'

export interface ReportTopbarAction {
  id: string
  label: string
  title?: string
  icon?: Component
  disabled?: boolean
  loading?: boolean
  tone?: ReportTopbarActionTone
}

export interface ReportTemplate {
  id: string
  name: string
  description: string
  content: string
  outputStructure?: string
  builtin?: boolean
  isDefault?: boolean
}

export interface PromptOptions {
  includeMaterialSummary: boolean
  includeTomorrowPlan: boolean
  groupByCategory: boolean
}

export interface MaterialFilters {
  sourceTypes: SourceType[]
  category: string | null
  sensitive: SensitiveMaterialFilter
  keyword: string
}

export interface MaterialPagination {
  offset: number
  limit: number
}

export interface MaterialSummary {
  total_count: number
  selected_count: number
  sensitive_excluded_count: number
  pending_count: number
  estimated_prompt_chars: number
}

export interface MaterialCandidate {
  source_type: SourceType
  source_id: number
  source_ids?: number[]
  title: string
  summary: string
  evidence?: string
  time_range: string
  category: string
  importance?: number
  is_sensitive: boolean
  sensitivity_reason?: string | null
  is_selected: boolean
  meta?: Record<string, unknown>
}

export interface ReportMaterialsPayload {
  date: string
  filters?: Partial<MaterialFilters>
  pagination?: Partial<MaterialPagination>
}

export interface ReportMaterialsResult {
  summary: MaterialSummary
  items: MaterialCandidate[]
  hasMore: boolean
}

export interface MaterialIdentity {
  sourceType: SourceType
  id: number
}

export interface BuildPromptPayload {
  date: string
  templateName: string
  selectedMaterialIds: MaterialIdentity[]
  extraRequirements: string
  outputFocus: string[]
  options: PromptOptions
}

export interface BuildPromptResult {
  prompt_text: string
  material_snapshot_json: string
  estimated_tokens?: number
  warnings?: string[]
}

export interface GenerateReportPayload extends BuildPromptPayload {
  promptText?: string
}

export interface GenerateReportResult {
  report_id?: number
  prompt_text: string
  report_markdown: string
  material_snapshot_json: string
  created_at: string
  warnings?: string[]
}

export interface SaveReportPayload {
  date: string
  templateName: string
  promptText: string
  reportMarkdown: string
  materialSnapshotJson: string
}

export interface SaveReportResult {
  report_id: number
  saved: boolean
}

export interface ReportHistoryFilters {
  dateRange: [Date | string, Date | string] | null
  templateName: string
  status: 'all' | 'saved'
  keyword: string
  page: number
  pageSize: number
}

export interface ReportHistoryRow {
  id: number
  date: string
  report_type?: string
  template_name: string
  model_provider?: string
  model_name?: string
  prompt_text?: string
  report_markdown?: string
  material_snapshot_json?: string | null
  material_summary?: string | null
  source_counts?: Record<string, unknown>
  source_counts_json?: string
  created_at: string
  updated_at?: string
}

export interface ListReportsPayload {
  startDate?: string | null
  endDate?: string | null
  keyword?: string
  templateName?: string
  page?: number
  pageSize?: number
}

export interface ListReportsResult {
  items: ReportHistoryRow[]
  total: number
}

export type ReportDetail = ReportHistoryRow

export interface DetailSavePayload {
  sourceType: SourceType
  id: number
  category: string | null
  note: string | null
  importance: number
  sensitive: boolean
  sensitivityReason: string | null
}

export type MaterialDetailRecord = AnyRecord | null
