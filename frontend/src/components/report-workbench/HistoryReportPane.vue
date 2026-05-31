<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'

import ReportHistoryDetail from './ReportHistoryDetail.vue'
import ReportHistoryList from './ReportHistoryList.vue'
import { useReportWorkbenchStore } from '../../stores/reportWorkbench'
import type { ReportHistoryFilters, ReportHistoryRow } from '../../types/reportWorkbench'

const store = useReportWorkbenchStore()

function updateFilters(filters: ReportHistoryFilters): void {
  store.historyFilters.dateRange = filters.dateRange
  store.historyFilters.templateName = filters.templateName
  store.historyFilters.status = filters.status
  store.historyFilters.keyword = filters.keyword
  store.historyFilters.page = filters.page
  store.historyFilters.pageSize = filters.pageSize
  void store.loadHistory()
}

async function copyText(text: string): Promise<void> {
  if (!text) {
    return
  }
  await navigator.clipboard?.writeText(text)
  ElMessage.success('内容已复制')
}

function exportReport(report: ReportHistoryRow): void {
  const blob = new Blob([report.report_markdown || ''], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `daily-report-${report.date}-${report.id}.md`
  link.click()
  URL.revokeObjectURL(url)
}

async function deleteReport(id: number): Promise<void> {
  await ElMessageBox.confirm('删除后该日报将从历史记录中移除，确认继续吗？', '确认删除日报', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger'
  })
  await store.removeReport(id)
  ElMessage.success('日报已删除')
}

function viewPrompt(prompt: string): void {
  store.promptText = prompt
  store.promptPreviewVisible = true
}
</script>

<template>
  <div class="history-pane">
    <ReportHistoryList
      :filters="store.historyFilters"
      :reports="store.reportList"
      :total="store.reportListTotal"
      :templates="store.templates"
      :loading="store.historyLoading"
      :active-id="store.reportDetail?.id ?? null"
      @update:filters="updateFilters"
      @refresh="store.loadHistory"
      @select="store.selectReport"
    />

    <ReportHistoryDetail
      :report="store.reportDetail"
      :loading="store.detailLoading"
      @copy="copyText"
      @export="exportReport"
      @view-prompt="viewPrompt"
      @regenerate="store.regenerateFromHistory"
      @delete="deleteReport"
    />
  </div>
</template>

<style scoped>
.history-pane {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(320px, 0.78fr) minmax(0, 1.22fr);
  gap: 14px;
  align-items: stretch;
}

@media (max-width: 1120px) {
  .history-pane {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
