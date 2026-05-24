<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'

import { callTypedBridge } from '../api/bridge'
import type { GeneratedReport, MaterialCard, ReportHistoryRow, TemplateName } from '../api/types'
import PageLayout from '../layouts/PageLayout.vue'

/**
 * 日报工作台页骨架。
 *
 * 页面职责：
 * - 读取日报素材：getReportMaterials
 * - 构建 Prompt 预览：buildPrompt
 * - 调用模型生成日报：generateReport
 * - 读取最新日报与历史日报：getLatestReport / listReports
 *
 * 布局实现建议：
 * - 顶部：日期、模板、刷新素材、生成、复制、导出
 * - 三栏：素材列表、Prompt 预览、Markdown 预览
 * - 底部或侧边：历史日报列表
 */

const today = new Date().toISOString().slice(0, 10)

const date = shallowRef(today)
const templateName = shallowRef<TemplateName>('daily_standard')
const loading = shallowRef(false)
const generating = shallowRef(false)
const lastError = shallowRef('')
const materials = shallowRef<MaterialCard[]>([])
const prompt = shallowRef('')
const markdown = shallowRef('')
const reports = shallowRef<ReportHistoryRow[]>([])

async function refreshWorkbench(): Promise<void> {
  loading.value = true
  lastError.value = ''

  try {
    const [materialPayload, promptPayload, latestReport, reportPayload] = await Promise.all([
      callTypedBridge('getReportMaterials', { date: date.value }),
      callTypedBridge('buildPrompt', {
        date: date.value,
        templateName: templateName.value
      }),
      callTypedBridge('getLatestReport', { date: date.value }),
      callTypedBridge('listReports', {
        startDate: null,
        endDate: null
      })
    ])

    materials.value = materialPayload.items
    prompt.value = promptPayload.prompt
    markdown.value = latestReport?.report_markdown || ''
    reports.value = reportPayload.items
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function generateReport(): Promise<GeneratedReport | null> {
  generating.value = true
  lastError.value = ''

  try {
    const result = await callTypedBridge('generateReport', {
      date: date.value,
      templateName: templateName.value
    })
    prompt.value = result.prompt_text
    markdown.value = result.report_markdown
    await refreshReportHistory()
    return result
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
    return null
  } finally {
    generating.value = false
  }
}

async function refreshReportHistory(): Promise<void> {
  const payload = await callTypedBridge('listReports', {
    startDate: null,
    endDate: null
  })
  reports.value = payload.items
}

async function copyMarkdown(): Promise<void> {
  if (!markdown.value) return
  await navigator.clipboard?.writeText(markdown.value)
}

function exportMarkdown(): void {
  if (!markdown.value) return

  const blob = new Blob([markdown.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `daily-report-${date.value}.md`
  link.click()
  URL.revokeObjectURL(url)
}

function selectReport(row: ReportHistoryRow): void {
  date.value = row.date || date.value
  templateName.value = (row.template_name as TemplateName) || templateName.value
  prompt.value = row.prompt_text || ''
  markdown.value = row.report_markdown || ''
}

onMounted(refreshWorkbench)

defineExpose({
  date,
  templateName,
  loading,
  generating,
  lastError,
  materials,
  prompt,
  markdown,
  reports,
  refreshWorkbench,
  generateReport,
  refreshReportHistory,
  copyMarkdown,
  exportMarkdown,
  selectReport
})
</script>

<template>
  <PageLayout title="日报工作台" scrollable>
    <section class="page-skeleton" v-loading="loading">
      <!--
        数据状态：
        - materials: MaterialCard[]
        - prompt: string
        - markdown: string
        - reports: ReportHistoryRow[]
        - lastError: string

        后端接口：
        - getReportMaterials({ date }) -> { items: MaterialCard[] }
        - buildPrompt({ date, templateName }) -> { prompt: string }
        - generateReport({ date, templateName }) -> GeneratedReport
        - getLatestReport({ date }) -> ReportHistoryRow | null
        - listReports({ startDate, endDate }) -> { items: ReportHistoryRow[] }

        待实现页面区域：
        1. 日期与模板操作栏
        2. 素材统计和素材列表
        3. Prompt 预览
        4. Markdown 预览
        5. 历史日报列表
      -->
    </section>
  </PageLayout>
</template>

<style scoped>
.page-skeleton {
  min-height: 100%;
}
</style>
