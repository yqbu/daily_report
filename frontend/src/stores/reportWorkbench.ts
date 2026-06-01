import { defineStore } from 'pinia'
import { computed, reactive, shallowRef } from 'vue'
import { buildPrompt, generateReport, getLatestReport } from '../api/reports'
import { getEntryDetail, updateEntrySelection } from '../api/entries'
import { callTypedBridge } from '../api/bridge'
import type {
  DetailSavePayload,
  MaterialCandidate,
  MaterialFilters,
  MaterialSummary,
  PromptOptions,
  ReportHistoryFilters,
  ReportHistoryRow,
  ReportTemplate,
  ReportWorkbenchTab
} from '../types/reportWorkbench'

export const categoryOptions = ['开发编码', '资料调研', 'AI 辅助', '文档整理', '沟通协作', '系统配置', '其他']
export const outputFocusOptions = ['完成事项', '问题排查', '技术调研', 'AI 辅助', '明日计划', '风险与阻塞']

const defaultTemplates: ReportTemplate[] = [
  {
    id: 'daily_standard',
    name: '标准日报',
    description: '结构清晰，适合日常同步。',
    content: '请基于已选素材生成结构化工作日报，覆盖完成事项、问题风险和明日计划。',
    outputStructure: '今日概览\n完成事项\n问题与风险\n明日计划',
    builtin: true,
    isDefault: true
  },
  {
    id: 'daily_technical',
    name: '技术日报',
    description: '突出开发、排查和技术决策。',
    content: '请生成偏技术视角的日报，重点描述代码改动、排查过程、方案取舍和后续动作。',
    outputStructure: '技术进展\n关键决策\n排查记录\n后续计划',
    builtin: true
  },
  {
    id: 'daily_brief',
    name: '简版日报',
    description: '短摘要，适合快速同步。',
    content: '请用精简项目符号输出当天最重要的工作进展和下一步。',
    outputStructure: '完成\n阻塞\n下一步',
    builtin: true
  }
]

export const useReportWorkbenchStore = defineStore('reportWorkbench', () => {
  const today = new Date().toISOString().slice(0, 10)
  const selectedDate = shallowRef(today)
  const activeTab = shallowRef<ReportWorkbenchTab>('generate')
  const templates = shallowRef<ReportTemplate[]>(defaultTemplates)
  const selectedTemplateName = shallowRef('daily_standard')
  const extraRequirements = shallowRef('')
  const outputFocus = shallowRef<string[]>([])
  const promptOptions = reactive<PromptOptions>({
    includeMaterialSummary: true,
    includeTomorrowPlan: true,
    groupByCategory: true
  })
  const materialFilters = reactive<MaterialFilters>({
    sourceTypes: [],
    category: null,
    sensitive: 'non_sensitive',
    keyword: ''
  })
  const materialSummary = reactive<MaterialSummary>({
    total_count: 0,
    selected_count: 0,
    sensitive_excluded_count: 0,
    pending_count: 0,
    estimated_prompt_chars: 0
  })
  const materialItems = shallowRef<MaterialCandidate[]>([])
  const materialLoading = shallowRef(false)
  const materialHasMore = shallowRef(false)
  const promptText = shallowRef('')
  const promptLoading = shallowRef(false)
  const promptDirty = shallowRef(true)
  const promptWarnings = shallowRef<string[]>([])
  const promptPreviewVisible = shallowRef(false)
  const generationLoading = shallowRef(false)
  const generatedMarkdown = shallowRef('')
  const generationSaved = shallowRef(false)
  const templateDrawerVisible = shallowRef(false)
  const materialDetailDrawerVisible = shallowRef(false)
  const materialDetailLoading = shallowRef(false)
  const materialDetailSaving = shallowRef(false)
  const selectedMaterialDetail = shallowRef<Record<string, unknown> | null>(null)
  const historyLoading = shallowRef(false)
  const detailLoading = shallowRef(false)
  const historyFilters = reactive<ReportHistoryFilters>({
    dateRange: null,
    templateName: '',
    status: '',
    keyword: '',
    page: 1,
    pageSize: 20
  })
  const reportList = shallowRef<ReportHistoryRow[]>([])
  const reportListTotal = shallowRef(0)
  const reportDetail = shallowRef<ReportHistoryRow | null>(null)

  const selectedTemplate = computed(
    () => templates.value.find((item) => item.id === selectedTemplateName.value) ?? templates.value[0]
  )
  const selectedMaterialCount = computed(() => materialItems.value.filter((item) => item.is_selected).length)
  const canGenerate = computed(() => selectedMaterialCount.value > 0 || materialSummary.total_count === 0)

  function changeDate(date: string): void {
    selectedDate.value = date
    markPromptDirty()
    void refreshMaterials()
    void loadLatestReportForDate()
  }

  async function refreshMaterials(): Promise<void> {
    await loadMaterials(true)
    await buildCurrentPrompt(false)
    await loadLatestReportForDate()
  }

  async function loadMaterials(reset = true): Promise<void> {
    materialLoading.value = true
    try {
      const result = await callTypedBridge('getReportMaterials', { date: selectedDate.value })
      const items = (result.items || []) as MaterialCandidate[]
      materialItems.value = applyMaterialFilters(items)
      Object.assign(materialSummary, {
        total_count: result.summary?.total_count ?? materialItems.value.length,
        selected_count: result.summary?.selected_count ?? materialItems.value.filter((item) => item.is_selected).length,
        sensitive_excluded_count: result.summary?.sensitive_excluded_count ?? 0,
        pending_count: result.summary?.pending_count ?? 0,
        estimated_prompt_chars: result.summary?.estimated_prompt_chars ?? estimatePromptChars(materialItems.value)
      })
      materialHasMore.value = !reset && Boolean(result.hasMore)
    } finally {
      materialLoading.value = false
    }
  }

  async function toggleMaterial(item: MaterialCandidate, selected: boolean): Promise<void> {
    item.is_selected = selected
    await updateEntrySelection(item.source_type, item.source_id, selected)
    materialSummary.selected_count = materialItems.value.filter((candidate) => candidate.is_selected).length
    markPromptDirty()
  }

  async function openMaterialDetail(item: MaterialCandidate): Promise<void> {
    materialDetailDrawerVisible.value = true
    materialDetailLoading.value = true
    try {
      const result = await getEntryDetail(item.source_type, item.source_id)
      selectedMaterialDetail.value = result.detail
    } finally {
      materialDetailLoading.value = false
    }
  }

  async function saveMaterialDetail(_payload: DetailSavePayload): Promise<void> {
    materialDetailSaving.value = true
    try {
      // Annotation editing remains on the QWebChannel path until the FastAPI surface exposes it.
      markPromptDirty()
    } finally {
      materialDetailSaving.value = false
    }
  }

  async function buildCurrentPrompt(openPreview = false): Promise<void> {
    promptLoading.value = true
    try {
      const result = await buildPrompt({
        date: selectedDate.value,
        template_name: selectedTemplateName.value
      })
      promptText.value = result.prompt_text
      promptDirty.value = false
      if (openPreview) promptPreviewVisible.value = true
    } finally {
      promptLoading.value = false
    }
  }

  async function generateCurrentReport(): Promise<void> {
    generationLoading.value = true
    try {
      const result = await generateReport({
        date: selectedDate.value,
        template_name: selectedTemplateName.value,
        save: true
      })
      generatedMarkdown.value = result.report_markdown
      promptText.value = result.prompt_text || promptText.value
      generationSaved.value = Boolean(result.report_id)
      await loadHistory()
    } finally {
      generationLoading.value = false
    }
  }

  async function loadLatestReportForDate(): Promise<void> {
    const result = await getLatestReport(selectedDate.value)
    if (result.report) {
      generatedMarkdown.value = result.report.report_markdown
      generationSaved.value = true
    } else {
      generatedMarkdown.value = ''
      generationSaved.value = false
    }
  }

  async function saveCurrentReport(): Promise<void> {
    generationSaved.value = true
  }

  async function loadHistory(): Promise<void> {
    historyLoading.value = true
    try {
      const latest = await getLatestReport(selectedDate.value)
      const rows = latest.report ? [toHistoryRow(latest.date, latest.report)] : []
      reportList.value = rows
      reportListTotal.value = rows.length
      reportDetail.value = rows[0] ?? null
    } finally {
      historyLoading.value = false
    }
  }

  function selectReport(id: number): void {
    reportDetail.value = reportList.value.find((item) => item.id === id) ?? null
  }

  async function removeReport(id: number): Promise<void> {
    reportList.value = reportList.value.filter((item) => item.id !== id)
    reportListTotal.value = reportList.value.length
    if (reportDetail.value?.id === id) reportDetail.value = null
  }

  async function regenerateFromHistory(): Promise<void> {
    if (reportDetail.value) {
      selectedDate.value = reportDetail.value.date
    }
    await generateCurrentReport()
  }

  function saveTemplate(template: ReportTemplate): void {
    const index = templates.value.findIndex((item) => item.id === template.id)
    templates.value = index >= 0
      ? templates.value.map((item) => (item.id === template.id ? template : item))
      : [...templates.value, template]
  }

  function deleteTemplate(id: string): void {
    templates.value = templates.value.filter((item) => item.id !== id || item.isDefault)
  }

  function setDefaultTemplate(id: string): void {
    selectedTemplateName.value = id
    markPromptDirty()
  }

  function markPromptDirty(): void {
    promptDirty.value = true
  }

  function applyMaterialFilters(items: MaterialCandidate[]): MaterialCandidate[] {
    return items.filter((item) => {
      if (materialFilters.sourceTypes.length && !materialFilters.sourceTypes.includes(item.source_type)) return false
      if (materialFilters.category && item.category !== materialFilters.category) return false
      if (materialFilters.sensitive === 'non_sensitive' && item.is_sensitive) return false
      if (materialFilters.sensitive === 'sensitive' && !item.is_sensitive) return false
      const keyword = materialFilters.keyword.trim().toLowerCase()
      if (keyword && !`${item.title} ${item.summary} ${item.evidence || ''}`.toLowerCase().includes(keyword)) return false
      return true
    })
  }

  return {
    selectedDate,
    activeTab,
    templates,
    selectedTemplateName,
    selectedTemplate,
    extraRequirements,
    outputFocus,
    promptOptions,
    materialFilters,
    materialSummary,
    materialItems,
    materialLoading,
    materialHasMore,
    selectedMaterialCount,
    promptText,
    promptLoading,
    promptDirty,
    promptWarnings,
    promptPreviewVisible,
    generationLoading,
    generatedMarkdown,
    generationSaved,
    canGenerate,
    templateDrawerVisible,
    materialDetailDrawerVisible,
    materialDetailLoading,
    materialDetailSaving,
    selectedMaterialDetail,
    historyLoading,
    detailLoading,
    historyFilters,
    reportList,
    reportListTotal,
    reportDetail,
    changeDate,
    refreshMaterials,
    loadMaterials,
    toggleMaterial,
    openMaterialDetail,
    saveMaterialDetail,
    buildCurrentPrompt,
    generateCurrentReport,
    saveCurrentReport,
    loadHistory,
    selectReport,
    removeReport,
    regenerateFromHistory,
    saveTemplate,
    deleteTemplate,
    setDefaultTemplate,
    markPromptDirty
  }
})

function estimatePromptChars(items: MaterialCandidate[]): number {
  return items.reduce((sum, item) => sum + item.title.length + item.summary.length + (item.evidence || '').length, 0)
}

function toHistoryRow(date: string, report: {
  id: number
  template_name?: string
  model_name?: string
  report_markdown: string
  created_at: string
  source_counts?: Record<string, unknown>
}): ReportHistoryRow {
  return {
    id: report.id,
    date,
    template_name: report.template_name || 'daily_standard',
    model_name: report.model_name,
    prompt_text: '',
    report_markdown: report.report_markdown,
    created_at: report.created_at,
    source_counts: report.source_counts
  }
}
