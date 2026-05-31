<script setup lang="ts">
import GenerateReportPane from './GenerateReportPane.vue'
import HistoryReportPane from './HistoryReportPane.vue'
import type { ReportWorkbenchTab } from '../../types/reportWorkbench'

defineProps<{
  activeTab: ReportWorkbenchTab
}>()

const emit = defineEmits<{
  'update:activeTab': [value: ReportWorkbenchTab]
}>()
</script>

<template>
  <el-tabs
    :model-value="activeTab"
    class="report-tabs"
    @update:model-value="emit('update:activeTab', $event as ReportWorkbenchTab)"
  >
    <el-tab-pane label="日报生成" name="generate">
      <div class="report-tab-pane-scroll">
        <GenerateReportPane />
      </div>
    </el-tab-pane>
    <el-tab-pane label="历史日报" name="history">
      <div class="report-tab-pane-scroll">
        <HistoryReportPane />
      </div>
    </el-tab-pane>
  </el-tabs>
</template>

<style scoped>
.report-tabs {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.report-tabs :deep(.el-tabs__header) {
  flex: 0 0 auto;
  margin: 0;
  padding: 0 16px;
  border-bottom: 1px solid #e4ebf5;
}

.report-tabs :deep(.el-tabs__content) {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  padding: 14px;
}

.report-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}

.report-tab-pane-scroll {
  height: 100%;
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-gutter: stable;
}
</style>
