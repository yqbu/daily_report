<script setup lang="ts">
import GenerateReportPane from './GenerateReportPane.vue'
import HistoryReportPane from './HistoryReportPane.vue'
import type { GenerateStep, ReportWorkbenchTab } from '../../types/reportWorkbench'

defineProps<{
  activeTab: ReportWorkbenchTab
  selectedDate: string
  generateStep: GenerateStep
  completedSteps: number[]
  disabledSteps: number[]
  modelLabel?: string
}>()

const emit = defineEmits<{
  'update:selectedDate': [value: string]
  'update:generateStep': [value: GenerateStep]
  buildPrompt: []
  generate: []
}>()
</script>

<template>
  <div class="report-workbench-panel">
    <GenerateReportPane
      v-if="activeTab === 'generate'"
      :selected-date="selectedDate"
      :active-step="generateStep"
      :completed-steps="completedSteps"
      :disabled-steps="disabledSteps"
      :model-label="modelLabel"
      @update:selected-date="emit('update:selectedDate', $event)"
      @update:active-step="emit('update:generateStep', $event)"
      @build-prompt="emit('buildPrompt')"
      @generate="emit('generate')"
    />
    <HistoryReportPane v-else />
  </div>
</template>

<style scoped>
.report-workbench-panel {
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}
</style>
