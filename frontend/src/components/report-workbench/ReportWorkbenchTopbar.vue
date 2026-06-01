<script setup lang="ts">
import { Refresh, Select } from '@element-plus/icons-vue'

defineProps<{
  selectedDate: string
  loading: boolean
  generating: boolean
  canGenerate: boolean
}>()

const emit = defineEmits<{
  'update:selectedDate': [value: string]
  refresh: []
  generate: []
}>()
</script>

<template>
  <header class="report-workbench-topbar">
    <div class="topbar-title">
      <span class="workspace-label">Daily Report</span>
      <h1 class="page-title">日报工作台</h1>
    </div>

    <div class="topbar-actions">
      <el-date-picker
        :model-value="selectedDate"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        :clearable="false"
        class="date-picker"
        @update:model-value="emit('update:selectedDate', String($event))"
      />
      <button
        class="top-button"
        type="button"
        :disabled="loading"
        title="刷新当前日报素材"
        @click="emit('refresh')"
      >
        <Refresh class="action-icon" :class="{ 'action-icon--spin': loading }" />
        <span>刷新素材</span>
      </button>
      <button
        class="top-button top-button--primary"
        type="button"
        :disabled="generating || !canGenerate"
        title="生成当前日期日报"
        @click="emit('generate')"
      >
        <Select class="action-icon" />
        <span>生成日报</span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.report-workbench-topbar {
  flex: 0 0 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
  padding: 14px 18px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
}

.topbar-title {
  min-width: 0;
}

.workspace-label {
  display: block;
  color: #667085;
  font-size: 12px;
  line-height: 1.2;
}

.page-title {
  margin: 4px 0 0;
  color: #172033;
  font-size: 22px;
  font-weight: 720;
  line-height: 1.15;
  letter-spacing: 0;
}

.topbar-actions {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.date-picker {
  width: 176px;
}

.report-workbench-topbar :deep(.date-picker.el-date-editor.el-input) {
  height: 38px;
}

.report-workbench-topbar :deep(.date-picker.el-date-editor .el-input__wrapper) {
  height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 0 0 1px #dce3ee inset;
}

.report-workbench-topbar :deep(.date-picker.el-date-editor .el-input__wrapper:hover),
.report-workbench-topbar :deep(.date-picker.el-date-editor .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #c9dcff inset;
}

.report-workbench-topbar :deep(.date-picker.el-date-editor .el-input__inner) {
  height: 38px;
  color: #172033;
  font-size: 13px;
  line-height: 38px;
}

.report-workbench-topbar :deep(.date-picker.el-date-editor .el-input__prefix),
.report-workbench-topbar :deep(.date-picker.el-date-editor .el-input__suffix) {
  color: #7b8797;
}

.report-workbench-topbar :deep(.date-picker.el-date-editor .el-input__prefix-inner > :last-child) {
  margin-right: 6px;
}

.top-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #526179;
  background: #ffffff;
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
}

.top-button:hover {
  color: #2563eb;
  border-color: #c9dcff;
  background: #eff6ff;
}

.top-button--primary {
  color: #ffffff;
  border-color: #2563eb;
  background: #2563eb;
}

.top-button--primary:hover {
  color: #ffffff;
  border-color: #1d4ed8;
  background: #1d4ed8;
}

.top-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.action-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.action-icon--spin {
  animation: report-workbench-spin 900ms linear infinite;
}

@media (max-width: 760px) {
  .report-workbench-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .topbar-actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}

@keyframes report-workbench-spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}
</style>
