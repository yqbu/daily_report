import type { SourceType } from '../api/types'

export type ReportWorkbenchTab = 'generate' | 'history'
export type ReportResultView = 'preview' | 'markdown' | 'prompt'

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
  sensitive: 'non_sensitive' | 'sensitive' | 'all'
  keyword: string
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
  title: string
  summary: string
  evidence?: string
  time_range: string
  category: string
  importance: number
  is_sensitive: boolean
  sensitivity_reason?: string | null
  is_selected: boolean
}

export interface ReportHistoryFilters {
  dateRange: [string, string] | null
  templateName: string
  status: string
  keyword: string
  page: number
  pageSize: number
}

export interface ReportHistoryRow {
  id: number
  date: string
  template_name: string
  model_name?: string
  prompt_text: string
  report_markdown: string
  created_at: string
  source_counts?: Record<string, unknown>
}

export interface DetailSavePayload {
  sourceType: SourceType
  id: number
  category: string | null
  note: string | null
  importance: number
  sensitive: boolean
  sensitivityReason: string | null
}
