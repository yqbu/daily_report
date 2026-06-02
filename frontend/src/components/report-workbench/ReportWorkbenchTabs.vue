<script setup lang="ts">
import GenerateReportPane from './GenerateReportPane.vue'
import HistoryReportPane from './HistoryReportPane.vue'
import type { GenerateStep, ReportWorkbenchTab } from '../../types/reportWorkbench'

defineProps<{
  activeTab: ReportWorkbenchTab
  generateStep: GenerateStep
  completedSteps: number[]
  disabledSteps: number[]
  modelLabel?: string
}>()

const emit = defineEmits<{
  'update:activeTab': [value: ReportWorkbenchTab]
  'update:generateStep': [value: GenerateStep]
  buildPrompt: []
  generate: []
}>()
</script>

<template>
  <el-tabs
    :model-value="activeTab"
    type="card"
    class="report-tabs"
    @update:model-value="emit('update:activeTab', $event as ReportWorkbenchTab)"
  >
    <el-tab-pane label="日报生成" name="generate">
      <div class="report-tab-pane-shell">
        <GenerateReportPane
          :active-step="generateStep"
          :completed-steps="completedSteps"
          :disabled-steps="disabledSteps"
          :model-label="modelLabel"
          @update:active-step="emit('update:generateStep', $event)"
          @build-prompt="emit('buildPrompt')"
          @generate="emit('generate')"
        />
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
  margin: 0 0 14px;
  padding: 0 2px;
}

.report-tabs :deep(.el-tabs__content) {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  padding: 0;
}

.report-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}

.report-tab-pane-shell,
.report-tab-pane-scroll {
  height: 100%;
  min-width: 0;
}

.report-tab-pane-shell {
  overflow: hidden;
}

.report-tab-pane-scroll {
  overflow-x: hidden;
  overflow-y: auto;
}
</style>
