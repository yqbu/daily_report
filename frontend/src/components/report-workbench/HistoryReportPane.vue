<script setup lang="ts">
import ReportHistoryDetail from './ReportHistoryDetail.vue'
import ReportHistoryList from './ReportHistoryList.vue'
import { useReportWorkbenchStore } from '../../stores/reportWorkbench'
import type { ReportHistoryFilters } from '../../types/reportWorkbench'

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

</script>

<template>
  <div class="history-pane">
    <ReportHistoryList
      :filters="store.historyFilters"
      :reports="store.reportList"
      :total="store.reportListTotal"
      :templates="store.templates"
      :loading="store.historyLoading"
      :active-date="store.reportDetail?.date ?? null"
      @update:filters="updateFilters"
      @refresh="store.loadHistory"
      @select="store.selectReport"
    />

    <ReportHistoryDetail
      :report="store.reportDetail"
      :report-versions="store.reportVersions"
      :source-totals="store.reportSourceTotals"
      :loading="store.detailLoading"
      @select-version="store.selectReport"
    />
  </div>
</template>

<style scoped>
.history-pane {
  height: 100%;
  min-height: 0;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(320px, clamp(336px, 29vw, 416px)) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
  overflow: hidden;
}

@media (max-width: 1120px) {
  .history-pane {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
