import { defineStore } from 'pinia'
import { computed, reactive, shallowRef } from 'vue'

import {
  batchUpdateEntrySelection,
  buildPrompt,
  deleteReport,
  generateReport,
  getEntryDetail,
  getReportDetail,
  getReportMaterials,
  listReports,
  saveReport,
  updateEntryAnnotation,
  updateEntrySelection,
  updateEntrySensitive
} from '../api/reportWorkbench'
import type { AnyRecord, SourceType } from '../api/types'
import type {
  BuildPromptPayload,
  DetailSavePayload,
  ListReportsPayload,
  MaterialCandidate,
  MaterialFilters,
  MaterialIdentity,
  MaterialSummary,
  PromptOptions,
  ReportDetail,
  ReportHistoryFilters,
  ReportHistoryRow,
  ReportTemplate,
  ReportWorkbenchTab
} from '../types/reportWorkbench'

const MATERIAL_PAGE_SIZE = 50

const defaultPromptOptions: PromptOptions = {
  includeMaterialSummary: true,
  includeTomorrowPlan: true,
  groupByCategory: true
}

export const defaultTemplates: ReportTemplate[] = [
  {
    id: 'daily_standard',
    name: '标准日报模板',
    description: '按工作概述、主要进展、问题处理与明日计划组织内容。',
    content: '## 今日工作概述\n\n## 主要工作内容\n\n## 问题与处理\n\n## 明日计划\n\n## 备注',
    outputStructure: 'Markdown 正文，层级清晰，语气正式。',
    builtin: true,
    isDefault: true
  },
  {
    id: 'daily_technical',
    name: '技术日报模板',
    description: '突出开发编码、问题排查、技术调研和 AI 辅助结果。',
    content: '## 技术工作概览\n\n## 开发与实现\n\n## 调研与验证\n\n## 问题排查\n\n## 后续计划',
    outputStructure: '按技术主题归纳，保留必要证据但不展开敏感原文。',
    builtin: true,
    isDefault: false
  },
  {
    id: 'daily_brief',
    name: '简洁日报模板',
    description: '输出更短的摘要式日报，适合快速同步。',
    content: '## 今日完成\n\n## 关键进展\n\n## 明日计划',
    outputStructure: '控制篇幅，优先 bullet list。',
    builtin: true,
    isDefault: false
  },
  {
    id: 'troubleshooting',
    name: '问题排查模板',
    description: '围绕现象、分析、尝试、结论和后续动作组织。',
    content: '## 问题背景\n\n## 排查过程\n\n## 处理结论\n\n## 后续动作',
    outputStructure: '强调证据链和排查步骤。',
    builtin: true,
    isDefault: false
  }
]

export const outputFocusOptions = ['完成事项', '问题排查', '技术调研', 'AI 辅助', '明日计划', '风险与阻塞']

export const categoryOptions = ['开发编码', '资料调研', 'AI 辅助', '文档整理', '沟通协作', '系统配置', '其他']

export const useReportWorkbenchStore = defineStore('reportWorkbench', () => {
  const activeTab = shallowRef<ReportWorkbenchTab>('generate')
  const selectedDate = shallowRef(toDateKey(new Date()))

  const materialFilters = reactive<MaterialFilters>({
    sourceTypes: [],
    category: null,
    sensitive: 'non_sensitive',
    keyword: ''
  })
  const materialSummary = shallowRef<MaterialSummary>(emptyMaterialSummary())
  const materialItems = shallowRef<MaterialCandidate[]>([])
  const materialLoading = shallowRef(false)
  const materialHasMore = shallowRef(false)
  const materialOffset = shallowRef(0)

  const selectedTemplateName = shallowRef(defaultTemplates[0].id)
  const templates = shallowRef<ReportTemplate[]>(loadTemplates())
  const extraRequirements = shallowRef('')
  const outputFocus = shallowRef<string[]>(['完成事项', '问题排查', '明日计划'])
  const promptOptions = reactive<PromptOptions>({ ...defaultPromptOptions })
  const promptText = shallowRef('')
  const materialSnapshotJson = shallowRef('')
  const promptLoading = shallowRef(false)
  const promptDirty = shallowRef(true)
  const promptWarnings = shallowRef<string[]>([])

  const generatedMarkdown = shallowRef('')
  const generationLoading = shallowRef(false)
  const generationSaved = shallowRef(false)
  const currentReportId = shallowRef<number | null>(null)

  const historyFilters = reactive<ReportHistoryFilters>({
    dateRange: null,
    templateName: '',
    status: 'all',
    keyword: '',
    page: 1,
    pageSize: 12
  })
  const reportList = shallowRef<ReportHistoryRow[]>([])
  const reportListTotal = shallowRef(0)
  const reportDetail = shallowRef<ReportDetail | null>(null)
  const historyLoading = shallowRef(false)
  const detailLoading = shallowRef(false)

  const templateDrawerVisible = shallowRef(false)
  const materialDetailDrawerVisible = shallowRef(false)
  const promptPreviewVisible = shallowRef(false)
  const selectedMaterialDetail = shallowRef<AnyRecord | null>(null)
  const materialDetailLoading = shallowRef(false)
  const materialDetailSaving = shallowRef(false)

  const selectedMaterials = computed(() => materialItems.value.filter((item) => item.is_selected))
  const selectedMaterialIds = computed<MaterialIdentity[]>(() =>
    selectedMaterials.value.map((item) => ({
      sourceType: item.source_type,
      id: item.source_id
    }))
  )
  const selectedMaterialCount = computed(() => materialSummary.value.selected_count || selectedMaterials.value.length)
  const canGenerate = computed(() => (selectedMaterialCount.value > 0 || materialSummary.value.total_count === 0) && !generationLoading.value)
  const selectedTemplate = computed(() => templates.value.find((item) => item.id === selectedTemplateName.value) ?? templates.value[0])

  async function loadMaterials(reset = true): Promise<void> {
    if (materialLoading.value) {
      return
    }
    materialLoading.value = true
    try {
      const nextOffset = reset ? 0 : materialOffset.value
      const result = await getReportMaterials({
        date: selectedDate.value,
        filters: {
          sourceTypes: materialFilters.sourceTypes,
          category: materialFilters.category,
          sensitive: materialFilters.sensitive,
          keyword: materialFilters.keyword.trim()
        },
        pagination: {
          offset: nextOffset,
          limit: MATERIAL_PAGE_SIZE
        }
      })
      materialSummary.value = result.summary
      materialItems.value = reset ? result.items : [...materialItems.value, ...result.items]
      materialOffset.value = nextOffset + result.items.length
      materialHasMore.value = result.hasMore
    } finally {
      materialLoading.value = false
    }
  }

  async function refreshMaterials(): Promise<void> {
    await loadMaterials(true)
  }

  async function changeDate(date: string): Promise<void> {
    selectedDate.value = date
    generatedMarkdown.value = ''
    currentReportId.value = null
    generationSaved.value = false
    markPromptDirty()
    await loadMaterials(true)
  }

  async function toggleMaterial(item: MaterialCandidate, selected: boolean): Promise<void> {
    await updateEntrySelection({ sourceType: item.source_type, id: item.source_id, ids: item.source_ids, selected })
    materialItems.value = materialItems.value.map((row) =>
      row.source_type === item.source_type && row.source_id === item.source_id ? { ...row, is_selected: selected } : row
    )
    updateSelectedSummary(selected ? 1 : -1)
    markPromptDirty()
  }

  async function batchSelect(items: MaterialCandidate[], selected: boolean): Promise<void> {
    const identities = items.map((item) => ({ sourceType: item.source_type, id: item.source_id }))
    await batchUpdateEntrySelection({ items: identities, selected })
    const keys = new Set(identities.map((item) => materialKey(item.sourceType, item.id)))
    materialItems.value = materialItems.value.map((item) =>
      keys.has(materialKey(item.source_type, item.source_id)) ? { ...item, is_selected: selected } : item
    )
    await loadMaterials(true)
    markPromptDirty()
  }

  async function openMaterialDetail(item: MaterialCandidate): Promise<void> {
    materialDetailDrawerVisible.value = true
    materialDetailLoading.value = true
    selectedMaterialDetail.value = null
    try {
      selectedMaterialDetail.value = await getEntryDetail({
        sourceType: item.source_type,
        id: item.source_id
      })
    } finally {
      materialDetailLoading.value = false
    }
  }

  async function saveMaterialDetail(payload: DetailSavePayload): Promise<void> {
    materialDetailSaving.value = true
    try {
      await updateEntryAnnotation({
        sourceType: payload.sourceType,
        id: payload.id,
        payload: {
          category: payload.category,
          note: payload.note,
          importance: payload.importance
        }
      })
      await updateEntrySensitive({
        sourceType: payload.sourceType,
        id: payload.id,
        sensitive: payload.sensitive,
        reason: payload.sensitivityReason
      })
      selectedMaterialDetail.value = await getEntryDetail({
        sourceType: payload.sourceType,
        id: payload.id
      })
      await loadMaterials(true)
      markPromptDirty()
    } finally {
      materialDetailSaving.value = false
    }
  }

  async function buildCurrentPrompt(openPreview = false): Promise<void> {
    promptLoading.value = true
    try {
      const result = await buildPrompt(buildPromptPayload())
      promptText.value = result.prompt_text
      materialSnapshotJson.value = result.material_snapshot_json
      promptWarnings.value = result.warnings ?? []
      promptDirty.value = false
      if (openPreview) {
        promptPreviewVisible.value = true
      }
    } finally {
      promptLoading.value = false
    }
  }

  async function generateCurrentReport(): Promise<void> {
    if (selectedMaterialIds.value.length === 0 && materialSummary.value.total_count > 0) {
      return
    }
    generationLoading.value = true
    generationSaved.value = false
    try {
      if (promptDirty.value || !promptText.value) {
        await buildCurrentPrompt(false)
      }
      const result = await generateReport({
        ...buildPromptPayload(),
        promptText: promptText.value
      })
      promptText.value = result.prompt_text || promptText.value
      generatedMarkdown.value = result.report_markdown
      materialSnapshotJson.value = result.material_snapshot_json || materialSnapshotJson.value
      currentReportId.value = result.report_id ?? null
      generationSaved.value = Boolean(result.report_id && result.report_id > 0)
      await loadHistory()
    } finally {
      generationLoading.value = false
    }
  }

  async function saveCurrentReport(): Promise<void> {
    if (!generatedMarkdown.value || !promptText.value) {
      return
    }
    const result = await saveReport({
      date: selectedDate.value,
      templateName: selectedTemplateName.value,
      promptText: promptText.value,
      reportMarkdown: generatedMarkdown.value,
      materialSnapshotJson: materialSnapshotJson.value
    })
    currentReportId.value = result.report_id
    generationSaved.value = result.saved
    await loadHistory()
  }

  async function loadHistory(): Promise<void> {
    historyLoading.value = true
    try {
      const result = await listReports(historyPayload())
      reportList.value = result.items
      reportListTotal.value = result.total
      if (!reportDetail.value && result.items.length) {
        reportDetail.value = result.items[0]
      }
    } finally {
      historyLoading.value = false
    }
  }

  async function selectReport(id: number): Promise<void> {
    detailLoading.value = true
    try {
      reportDetail.value = await getReportDetail(id)
    } finally {
      detailLoading.value = false
    }
  }

  async function removeReport(id: number): Promise<void> {
    await deleteReport(id)
    if (reportDetail.value?.id === id) {
      reportDetail.value = null
    }
    await loadHistory()
  }

  async function regenerateFromHistory(report: ReportHistoryRow): Promise<void> {
    activeTab.value = 'generate'
    selectedDate.value = report.date
    selectedTemplateName.value = report.template_name || selectedTemplateName.value
    promptText.value = report.prompt_text || ''
    generatedMarkdown.value = ''
    currentReportId.value = null
    generationSaved.value = false
    promptDirty.value = true
    await loadMaterials(true)
  }

  function saveTemplate(template: ReportTemplate): void {
    const nextTemplates = [...templates.value]
    const index = nextTemplates.findIndex((item) => item.id === template.id)
    if (index >= 0) {
      nextTemplates[index] = template
    } else {
      nextTemplates.push(template)
    }
    templates.value = nextTemplates
    persistTemplates(nextTemplates)
    markPromptDirty()
  }

  function deleteTemplate(id: string): void {
    const target = templates.value.find((item) => item.id === id)
    if (!target || target.builtin) {
      return
    }
    templates.value = templates.value.filter((item) => item.id !== id)
    if (selectedTemplateName.value === id) {
      selectedTemplateName.value = templates.value.find((item) => item.isDefault)?.id ?? defaultTemplates[0].id
    }
    persistTemplates(templates.value)
    markPromptDirty()
  }

  function setDefaultTemplate(id: string): void {
    selectedTemplateName.value = id
    templates.value = templates.value.map((item) => ({ ...item, isDefault: item.id === id }))
    persistTemplates(templates.value)
    markPromptDirty()
  }

  function markPromptDirty(): void {
    promptDirty.value = true
    if (generatedMarkdown.value) {
      generationSaved.value = false
    }
  }

  function buildPromptPayload(): BuildPromptPayload {
    return {
      date: selectedDate.value,
      templateName: selectedTemplateName.value,
      selectedMaterialIds: selectedMaterialIds.value,
      extraRequirements: extraRequirements.value,
      outputFocus: outputFocus.value,
      options: { ...promptOptions }
    }
  }

  function historyPayload(): ListReportsPayload {
    const range = historyFilters.dateRange
    return {
      startDate: range ? toDateKey(range[0]) : null,
      endDate: range ? toDateKey(range[1]) : null,
      keyword: historyFilters.keyword.trim() || undefined,
      templateName: historyFilters.templateName || undefined,
      page: historyFilters.page,
      pageSize: historyFilters.pageSize
    }
  }

  function updateSelectedSummary(delta: number): void {
    materialSummary.value = {
      ...materialSummary.value,
      selected_count: Math.max(0, materialSummary.value.selected_count + delta)
    }
  }

  return {
    activeTab,
    selectedDate,
    materialFilters,
    materialSummary,
    materialItems,
    materialLoading,
    materialHasMore,
    selectedTemplateName,
    selectedTemplate,
    templates,
    extraRequirements,
    outputFocus,
    promptOptions,
    promptText,
    materialSnapshotJson,
    promptLoading,
    promptDirty,
    promptWarnings,
    generatedMarkdown,
    generationLoading,
    generationSaved,
    currentReportId,
    historyFilters,
    reportList,
    reportListTotal,
    reportDetail,
    historyLoading,
    detailLoading,
    templateDrawerVisible,
    materialDetailDrawerVisible,
    promptPreviewVisible,
    selectedMaterialDetail,
    materialDetailLoading,
    materialDetailSaving,
    selectedMaterials,
    selectedMaterialIds,
    selectedMaterialCount,
    canGenerate,
    loadMaterials,
    refreshMaterials,
    changeDate,
    toggleMaterial,
    batchSelect,
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

export function toDateKey(value: Date | string): string {
  if (typeof value === 'string') {
    return value.slice(0, 10)
  }
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function emptyMaterialSummary(): MaterialSummary {
  return {
    total_count: 0,
    selected_count: 0,
    sensitive_excluded_count: 0,
    pending_count: 0,
    estimated_prompt_chars: 0
  }
}

function materialKey(sourceType: SourceType, id: number): string {
  return `${sourceType}:${id}`
}

function loadTemplates(): ReportTemplate[] {
  const raw = window.localStorage?.getItem('daily-report.templates')
  if (!raw) {
    return defaultTemplates
  }
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return defaultTemplates
    }
    const customTemplates = parsed.filter(isReportTemplate)
    return mergeTemplates(defaultTemplates, customTemplates)
  } catch {
    return defaultTemplates
  }
}

function persistTemplates(templates: ReportTemplate[]): void {
  const customTemplates = templates.filter((item) => !item.builtin)
  window.localStorage?.setItem('daily-report.templates', JSON.stringify(customTemplates))
}

function mergeTemplates(base: ReportTemplate[], customTemplates: ReportTemplate[]): ReportTemplate[] {
  const byId = new Map(base.map((item) => [item.id, item]))
  for (const template of customTemplates) {
    byId.set(template.id, template)
  }
  return Array.from(byId.values())
}

function isReportTemplate(value: unknown): value is ReportTemplate {
  if (typeof value !== 'object' || value === null) {
    return false
  }
  const row = value as Record<string, unknown>
  return typeof row.id === 'string' && typeof row.name === 'string' && typeof row.content === 'string'
}
