<script setup lang="ts">
import type { ReportTopbarAction } from '../../types/reportWorkbench'

defineProps<{
  selectedDate: string
  actions: ReportTopbarAction[]
}>()

const emit = defineEmits<{
  'update:selectedDate': [value: string]
  action: [id: string]
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

      <TransitionGroup name="topbar-action" tag="div" class="action-group">
        <button
          v-for="action in actions"
          :key="action.id"
          class="top-button"
          :class="{
            'top-button--primary': action.tone === 'primary',
            'top-button--success': action.tone === 'success',
            'top-button--danger': action.tone === 'danger'
          }"
          type="button"
          :disabled="action.disabled || action.loading"
          :title="action.title || action.label"
          @click="emit('action', action.id)"
        >
          <component
            :is="action.icon"
            v-if="action.icon"
            class="action-icon"
            :class="{ 'action-icon--spin': action.loading }"
          />
          <span>{{ action.label }}</span>
        </button>
      </TransitionGroup>
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
  flex: 0 0 auto;
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
  white-space: nowrap;
}

.topbar-actions {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.date-picker {
  flex: 0 0 auto;
  width: 176px;
}

.action-group {
  position: relative;
  flex: 0 1 720px;
  width: min(720px, 54vw);
  min-height: 38px;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  overflow: hidden;
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
  transition:
    color 160ms ease,
    border-color 160ms ease,
    background 160ms ease,
    opacity 160ms ease,
    transform 160ms ease;
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

.top-button--success {
  color: #15803d;
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.top-button--success:hover {
  color: #166534;
  border-color: #86efac;
  background: #dcfce7;
}

.top-button--danger {
  color: #dc2626;
  border-color: #fecaca;
  background: #fff7f7;
}

.top-button--danger:hover {
  color: #b91c1c;
  border-color: #fca5a5;
  background: #fee2e2;
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

.topbar-action-enter-active,
.topbar-action-leave-active {
  transition:
    opacity 180ms ease,
    transform 180ms ease;
}

.topbar-action-leave-active {
  position: absolute;
  right: 0;
  top: 0;
}

.topbar-action-enter-from,
.topbar-action-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.topbar-action-move {
  transition: transform 180ms ease;
}

@media (max-width: 960px) {
  .report-workbench-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .topbar-actions {
    width: 100%;
    align-items: flex-start;
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .action-group {
    flex: 1 1 100%;
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
    overflow: visible;
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
