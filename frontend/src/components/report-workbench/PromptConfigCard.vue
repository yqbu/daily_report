<script setup lang="ts">
import { computed } from 'vue'
import { Calendar, CollectionTag, Document, InfoFilled, MagicStick, Tickets, View } from '@element-plus/icons-vue'

import type { PromptOptions, ReportTemplate } from '../../types/reportWorkbench'
import { outputFocusOptions } from '../../stores/reportWorkbench'

const props = defineProps<{
  templates: ReportTemplate[]
  selectedTemplateName: string
  extraRequirements: string
  outputFocus: string[]
  options: PromptOptions
  promptDirty: boolean
  promptLoading: boolean
  selectedMaterialCount: number
  estimatedPromptChars: number
  modelLabel?: string
  showHeader?: boolean
  showActions?: boolean
}>()

const emit = defineEmits<{
  'update:selectedTemplateName': [value: string]
  'update:extraRequirements': [value: string]
  'update:outputFocus': [value: string[]]
  'update:options': [value: PromptOptions]
  openTemplates: []
  previewPrompt: []
}>()

const selectedTemplate = computed(() => props.templates.find((item) => item.id === props.selectedTemplateName) ?? props.templates[0])
const selectedFocusCount = computed(() => props.outputFocus.length)
const estimatedDurationLabel = computed(() => {
  const chars = Math.max(props.estimatedPromptChars, 800)
  const seconds = Math.ceil(chars / 24) + 35
  const minutes = Math.max(1, Math.ceil(seconds / 60))
  if (minutes <= 1) return '约 1 分钟'
  if (minutes <= 3) return '2-3 分钟'
  return `${minutes - 1}-${minutes} 分钟`
})
const summaryCards = computed(() => [
  {
    label: '聚焦素材',
    value: `${props.selectedMaterialCount.toLocaleString()} 条`,
    caption: '已选择素材'
  },
  {
    label: '预计字数',
    value: `${props.estimatedPromptChars.toLocaleString()} 字`,
    caption: '基于当前配置'
  },
  {
    label: '预计时长',
    value: estimatedDurationLabel.value,
    caption: '按字数估算'
  },
  {
    label: '模型',
    value: props.modelLabel || 'deepseek-chat',
    caption: props.modelLabel ? '来自设置' : '默认模型'
  }
])

function updateOption(key: keyof PromptOptions, value: boolean): void {
  emit('update:options', { ...props.options, [key]: value })
}

function optionCardClass(active: boolean): Record<string, boolean> {
  return {
    'option-card--active': active
  }
}

function focusDescription(value: string): string {
  const descriptions: Record<string, string> = {
    '完成事项': '今日完成的工作内容',
    '问题排查': '遇到的问题及解决过程',
    '技术调研': '技术学习与调研内容',
    'AI 辅助': 'AI 工具使用与提问总结',
    '明日计划': '下一步工作安排',
    '风险与阻塞': '风险识别与阻塞事项'
  }
  return descriptions[value] ?? '本次日报重点内容'
}
</script>

<template>
  <section class="workbench-card prompt-card">
    <header v-if="showHeader !== false" class="card-header">
      <div class="header-copy">
        <h2 class="card-title">Prompt 配置</h2>
        <p class="card-subtitle">配置本次日报的模板与内容要求</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Tickets" class="header-template-button" @click="emit('openTemplates')">
          模板管理
        </el-button>
        <el-tag disable-transitions v-if="promptDirty" class="dirty-tag" type="warning" effect="light">需重新构建</el-tag>
        <el-tag disable-transitions v-else type="success" effect="light">Prompt 已构建</el-tag>
      </div>
    </header>

    <div class="prompt-top-grid">
      <div class="prompt-section prompt-section--template">
        <h3 class="section-title">1. 日报模板</h3>
        <div class="template-row">
          <div class="template-select-shell">
            <Document class="template-icon" />
            <el-select
              :model-value="selectedTemplateName"
              class="template-select"
              @update:model-value="emit('update:selectedTemplateName', String($event))"
            >
              <el-option v-for="item in templates" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
            <p class="template-desc">{{ selectedTemplate?.description }}</p>
          </div>

          <aside class="template-note">
            <strong><InfoFilled />模板说明</strong>
            <span>摘要式输出，重点突出</span>
            <span>结构清晰，阅读友好</span>
            <span>适合团队快速同步</span>
          </aside>
        </div>
      </div>

      <div class="prompt-section">
        <h3 class="section-title">2. 补充要求 <span>可选</span></h3>
        <div class="requirement-row">
          <el-input
            :model-value="extraRequirements"
            type="textarea"
            :rows="4"
            resize="none"
            maxlength="500"
            show-word-limit
            placeholder="请输入本次日报的补充要求，例如：突出今日完成的开发工作、弱化浏览记录、输出风格偏正式。"
            @update:model-value="emit('update:extraRequirements', String($event))"
          />
          <aside class="writing-tip">
            <strong><MagicStick />写作建议</strong>
            <p>描述希望强调的内容、弱化的内容、风格偏好等，模型会根据你的要求生成更贴合需求的日报。</p>
            <em>示例：“重点突出今日完成的功能开发”“将 AI 提问归纳为技术调研内容”</em>
          </aside>
        </div>
      </div>
    </div>

    <div class="prompt-section">
      <h3 class="section-title">3. 输出重点 <span>可多选</span></h3>
      <div class="focus-layout">
        <el-checkbox-group
          :model-value="outputFocus"
          class="focus-card-grid"
          @update:model-value="emit('update:outputFocus', $event as string[])"
        >
          <el-checkbox
            v-for="item in outputFocusOptions"
            :key="item"
            class="focus-card"
            :class="{ 'focus-card--active': outputFocus.includes(item) }"
            :label="item"
            :value="item"
          >
            <strong>{{ item }}</strong>
            <span>{{ focusDescription(item) }}</span>
          </el-checkbox>
        </el-checkbox-group>

        <aside class="focus-note-panel">
          <strong><CollectionTag />聚焦重点</strong>
          <p>选择你希望在日报中重点体现的方面，模型会围绕这些维度组织内容。</p>
          <span>已选择 {{ selectedFocusCount }} 项</span>
        </aside>
      </div>
    </div>

    <div class="prompt-section">
      <h3 class="section-title">4. 内容选项</h3>
      <div class="option-grid">
        <button
          class="option-card"
          :class="optionCardClass(options.includeMaterialSummary)"
          type="button"
          @click="updateOption('includeMaterialSummary', !options.includeMaterialSummary)"
        >
          <el-checkbox :model-value="options.includeMaterialSummary" @click.stop @update:model-value="updateOption('includeMaterialSummary', Boolean($event))" />
          <span>
            <strong>包含素材摘要</strong>
            <small>在日报中包含本次使用的素材来源摘要</small>
          </span>
          <Document />
        </button>
        <button
          class="option-card"
          :class="optionCardClass(options.includeTomorrowPlan)"
          type="button"
          @click="updateOption('includeTomorrowPlan', !options.includeTomorrowPlan)"
        >
          <el-checkbox :model-value="options.includeTomorrowPlan" @click.stop @update:model-value="updateOption('includeTomorrowPlan', Boolean($event))" />
          <span>
            <strong>包含明日计划建议</strong>
            <small>基于今日工作内容生成明日计划建议</small>
          </span>
          <Calendar />
        </button>
        <button
          class="option-card"
          :class="optionCardClass(options.groupByCategory)"
          type="button"
          @click="updateOption('groupByCategory', !options.groupByCategory)"
        >
          <el-checkbox :model-value="options.groupByCategory" @click.stop @update:model-value="updateOption('groupByCategory', Boolean($event))" />
          <span>
            <strong>按分类组织</strong>
            <small>按工作分类组织内容，结构更清晰</small>
          </span>
          <CollectionTag />
        </button>
      </div>
    </div>

    <div class="prompt-summary">
      <div v-for="item in summaryCards" :key="item.label" class="summary-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.caption }}</small>
      </div>
      <div class="summary-card summary-card--prompt" :class="{ 'summary-card--ready': !promptDirty }">
        <span>{{ promptDirty ? '需要重新构建 Prompt' : 'Prompt 已构建' }}</span>
        <strong>{{ promptDirty ? '配置已修改' : '可提交' }}</strong>
        <small>{{ promptDirty ? '请先点击构建 Prompt' : '当前配置已同步' }}</small>
      </div>
    </div>

    <div v-if="showActions !== false" class="prompt-actions">
      <el-button :icon="View" :loading="promptLoading" @click="emit('previewPrompt')">
        预览 Prompt
      </el-button>
      <el-button :icon="MagicStick" type="primary" :loading="promptLoading" @click="emit('previewPrompt')">
        构建 Prompt
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.prompt-card {
  min-width: 0;
  height: 100%;
  display: grid;
  grid-template-rows: auto auto auto auto auto;
  gap: 8px;
  align-content: start;
  overflow-x: hidden;
  overflow-y: auto;
}

.card-header,
.prompt-actions {
  display: flex;
  gap: 12px;
}

.card-header {
  min-width: 0;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 2px;
}

.header-copy {
  min-width: 0;
  flex: 1 1 auto;
}

.card-title {
  margin: 0;
  color: #172033;
  font-size: 16px;
  font-weight: 840;
}

.card-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
  line-height: 1.45;
}

.header-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-template-button {
  flex: 0 0 auto;
}

.dirty-tag {
  flex: 0 0 auto;
}

.prompt-section {
  min-width: 0;
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #e3ebf6;
  border-radius: 12px;
  background: #fff;
}

.prompt-top-grid {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
  align-items: stretch;
}

.section-title {
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 860;
}

.section-title span {
  color: #667085;
  font-weight: 720;
}

.template-row,
.requirement-row {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 12px;
  align-items: stretch;
}

.template-select-shell {
  min-width: 0;
  position: relative;
  display: grid;
  gap: 5px;
  min-height: 66px;
  align-content: center;
  padding: 10px 10px 10px 40px;
  border: 1px solid #dfe8f5;
  border-radius: 10px;
  background: #fbfdff;
}

.template-icon {
  position: absolute;
  left: 12px;
  top: 16px;
  width: 18px;
  height: 18px;
  color: #2563eb;
}

.template-select {
  width: 100%;
}

.template-select :deep(.el-select__wrapper) {
  padding: 0;
  min-height: 24px;
  border: 0;
  background: transparent;
  box-shadow: none;
  font-weight: 820;
}

.template-desc {
  margin: 0;
  color: #667085;
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-note,
.writing-tip {
  display: grid;
  min-width: 0;
  align-content: start;
  gap: 5px;
  padding: 11px 12px;
  border-radius: 10px;
  color: #526070;
  font-size: 12px;
  line-height: 1.42;
  background: linear-gradient(135deg, #f8fbff, #f4f7ff);
}

.template-note strong,
.writing-tip strong {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #172033;
  font-size: 12px;
}

.template-note strong svg,
.writing-tip strong svg {
  width: 14px;
  height: 14px;
  color: #2563eb;
}

.template-note span {
  position: relative;
  padding-left: 14px;
}

.template-note span::before {
  content: "";
  position: absolute;
  left: 2px;
  top: 7px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #9ec5ff;
}

.writing-tip p {
  margin: 0;
}

.writing-tip em {
  color: #667085;
  font-size: 11px;
  font-style: normal;
}

.focus-layout {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 12px;
  align-items: stretch;
}

.focus-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.focus-card {
  height: auto;
  min-width: 0;
  margin: 0;
}

.focus-card :deep(.el-checkbox__label) {
  min-width: 0;
  display: grid;
  gap: 3px;
  color: #172033;
}

.focus-card :deep(.el-checkbox__label span) {
  color: #667085;
  font-size: 12px;
  white-space: normal;
}

.focus-card :deep(.el-checkbox__input) {
  align-self: center;
}

.focus-card :deep(.el-checkbox__inner) {
  width: 18px;
  height: 18px;
}

.focus-card :deep(.el-checkbox__label) {
  line-height: 1.25;
}

.focus-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #dfe8f5;
  border-radius: 8px;
  background: #fbfdff;
}

.focus-card--active {
  border-color: #9ec5ff;
  background: #f1f7ff;
}

.focus-note-panel {
  min-width: 0;
  display: grid;
  align-content: center;
  gap: 8px;
  padding: 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, #fbf7ff, #f6f3ff);
  color: #526070;
  font-size: 12px;
  line-height: 1.45;
}

.focus-note-panel strong {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #5b21b6;
  font-size: 12px;
}

.focus-note-panel svg {
  width: 14px;
  height: 14px;
}

.focus-note-panel p {
  margin: 0;
}

.focus-note-panel span {
  color: #2563eb;
  font-weight: 820;
}

.option-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.option-card {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  padding: 9px;
  border: 1px solid #dfe8f5;
  border-radius: 10px;
  color: #526070;
  text-align: left;
  background: #fbfdff;
  cursor: pointer;
}

.option-card--active {
  border-color: #9ec5ff;
  background: #f1f7ff;
}

.option-card strong,
.option-card small {
  display: block;
}

.option-card strong {
  color: #172033;
  font-size: 12px;
}

.option-card small {
  margin-top: 3px;
  color: #667085;
  font-size: 11px;
  line-height: 1.35;
}

.option-card > svg {
  width: 18px;
  height: 18px;
  color: #2563eb;
}

.prompt-summary {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  align-items: stretch;
  padding: 0;
  border: 1px solid #dfe8f5;
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(135deg, #fbfdff, #f7fbff);
}

.summary-card {
  min-width: 0;
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-right: 1px solid #e3ebf6;
}

.summary-card:last-child {
  border-right: 0;
}

.summary-card span,
.summary-card small {
  color: #667085;
  font-size: 11px;
}

.summary-card strong {
  color: #172033;
  font-size: 15px;
  font-weight: 860;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-card--prompt {
  background: #fff7ed;
}

.summary-card--prompt strong {
  color: #d97706;
}

.summary-card--ready {
  background: #f0fdf4;
}

.summary-card--ready strong {
  color: #16a34a;
}

.prompt-actions {
  align-items: center;
  justify-content: stretch;
  flex-wrap: wrap;
}

.prompt-actions .el-button {
  flex: 1 1 160px;
}

@media (max-width: 1080px) {
  .template-row,
  .requirement-row,
  .focus-layout,
  .prompt-summary {
    grid-template-columns: minmax(0, 1fr);
  }

  .summary-card {
    border-right: 0;
    border-bottom: 1px solid #e3ebf6;
  }

  .summary-card:last-child {
    border-bottom: 0;
  }
}

@media (max-width: 760px) {
  .card-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .focus-card-grid,
  .option-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
