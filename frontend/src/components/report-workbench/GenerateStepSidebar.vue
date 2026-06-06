<script setup lang="ts">
import { computed } from 'vue'

import type { GenerateStep } from '../../types/reportWorkbench'

interface StepItem {
  title: string
  description: string
}

const props = defineProps<{
  selectedDate: string
  activeStep: GenerateStep
  completedSteps: number[]
  disabledSteps?: number[]
}>()

const emit = defineEmits<{
  'update:selectedDate': [value: string]
  change: [step: GenerateStep]
}>()

const steps: StepItem[] = [
  { title: '素材选择', description: '选择用于日报的本地记录' },
  { title: 'Prompt 配置', description: '配置日报模板与生成要求' },
  { title: '内容确认', description: '确认最终提交内容' },
  { title: '结果预览', description: '查看生成后的日报' }
]

const completedSet = computed(() => new Set(props.completedSteps))
const disabledSet = computed(() => new Set(props.disabledSteps ?? []))

function stepStatus(index: number): 'success' | 'process' | 'wait' {
  if (index === props.activeStep) return 'process'
  return completedSet.value.has(index) ? 'success' : 'wait'
}

function selectStep(index: number): void {
  if (disabledSet.value.has(index)) {
    return
  }
  emit('change', index as GenerateStep)
}
</script>

<template>
  <aside class="generate-step-sidebar">
    <div class="step-date-panel">
      <el-date-picker
        :model-value="selectedDate"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        :clearable="false"
        class="step-date-picker"
        @update:model-value="emit('update:selectedDate', String($event))"
      />
    </div>

    <div class="step-sidebar-header">
      <span>日报流程</span>
      <strong>{{ activeStep + 1 }} / {{ steps.length }}</strong>
    </div>

    <el-steps class="generate-steps" direction="vertical" :active="activeStep" finish-status="success">
      <el-step
        v-for="(step, index) in steps"
        :key="step.title"
        :class="{ 'generate-step--line-done': index < activeStep }"
        :status="stepStatus(index)"
      >
        <template #title>
          <button
            class="step-button"
            :class="{
              'step-button--active': index === activeStep,
              'step-button--disabled': disabledSet.has(index)
            }"
            type="button"
            :disabled="disabledSet.has(index)"
            @click="selectStep(index)"
          >
            {{ step.title }}
          </button>
        </template>
        <template #description>
          <span class="step-description">{{ step.description }}</span>
        </template>
      </el-step>
    </el-steps>
  </aside>
</template>

<style scoped>
.generate-step-sidebar {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 12px;
  padding: 16px;
  border: 1px solid #dfe8f5;
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
}

.step-date-panel {
  min-width: 0;
  display: grid;
  gap: 7px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5edf7;
}

.step-date-panel > span {
  color: #667085;
  font-size: 12px;
  font-weight: 760;
}

.step-date-picker {
  width: 100%;
}

.generate-step-sidebar :deep(.step-date-picker.el-date-editor.el-input) {
  height: 38px;
  width: 100%;
}

.generate-step-sidebar :deep(.step-date-picker.el-date-editor .el-input__wrapper) {
  height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 0 0 1px #dce3ee inset;
}

.generate-step-sidebar :deep(.step-date-picker.el-date-editor .el-input__wrapper:hover),
.generate-step-sidebar :deep(.step-date-picker.el-date-editor .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #c9dcff inset;
}

.generate-step-sidebar :deep(.step-date-picker.el-date-editor .el-input__inner) {
  height: 38px;
  color: #172033;
  font-size: 13px;
  line-height: 38px;
}

.generate-step-sidebar :deep(.step-date-picker.el-date-editor .el-input__prefix),
.generate-step-sidebar :deep(.step-date-picker.el-date-editor .el-input__suffix) {
  color: #7b8797;
}

.generate-step-sidebar :deep(.step-date-picker.el-date-editor .el-input__prefix-inner > :last-child) {
  margin-right: 6px;
}

.step-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #667085;
  font-size: 12px;
  font-weight: 760;
}

.step-sidebar-header strong {
  color: #2563eb;
  font-variant-numeric: tabular-nums;
}

.generate-steps {
  min-height: 0;
}

.generate-steps :deep(.el-step__main) {
  min-width: 0;
  padding-bottom: 28px;
}

.generate-steps :deep(.el-step__title) {
  line-height: 1.2;
}

.step-button {
  max-width: 100%;
  padding: 0;
  border: 0;
  color: #526070;
  background: transparent;
  font: inherit;
  font-size: 14px;
  font-weight: 820;
  line-height: 1.25;
  text-align: left;
  cursor: pointer;
}

.step-button:hover,
.step-button--active {
  color: #2563eb;
}

.step-button--disabled {
  color: #a1a9b5;
  cursor: not-allowed;
}

.step-button--disabled:hover {
  color: #a1a9b5;
}

.generate-steps :deep(.generate-step--line-done .el-step__line-inner) {
  height: 100% !important;
  border-color: #67c23a;
  transition:
    height 260ms ease,
    border-color 260ms ease;
}

.generate-steps :deep(.generate-step--line-done .el-step__line) {
  background-color: #67c23a;
  transition: background-color 180ms ease;
}

.step-description {
  display: block;
  max-width: 148px;
  margin-top: 5px;
  color: #8792a2;
  font-size: 12px;
  line-height: 1.45;
}
</style>
