<script setup lang="ts">
import { computed } from 'vue'
import { Document, MagicStick, Tickets } from '@element-plus/icons-vue'

import type { PromptOptions, ReportTemplate } from '../../types/reportWorkbench'

const props = defineProps<{
  template: ReportTemplate | undefined
  extraRequirements: string
  outputFocus: string[]
  options: PromptOptions
  selectedMaterialCount: number
  estimatedPromptChars: number
  promptDirty: boolean
  showActions?: boolean
}>()

const emit = defineEmits<{
  previous: []
  next: []
  buildPrompt: []
}>()

const outputStructureItems = computed(() =>
  String(props.template?.content || props.template?.outputStructure || '')
    .split('\n')
    .map((line) => line.replace(/^#+\s*/, '').trim())
    .filter(Boolean)
    .slice(0, 7)
)

const optionLines = computed(() => [
  props.options.includeMaterialSummary ? '包含素材摘要' : '不包含素材摘要',
  props.options.includeTomorrowPlan ? '包含明日计划建议' : '不包含明日计划建议',
  props.options.groupByCategory ? '按分类组织内容' : '不按分类组织内容'
])
</script>

<template>
  <section class="workbench-card prompt-preview-card">
    <header class="preview-header">
      <div>
        <h2 class="card-title">Prompt 组织预览</h2>
        <p class="card-subtitle">当前 Prompt 配置被组织后的结构摘要</p>
      </div>
      <el-tag v-if="promptDirty" type="warning" effect="light" disable-transitions>需要重建</el-tag>
      <el-tag v-else type="success" effect="light" disable-transitions>已构建</el-tag>
    </header>

    <div class="preview-grid">
      <div class="preview-block preview-block--system">
      <h3><MagicStick />系统要求</h3>
      <ul>
        <li>根据用户选择的素材生成中文日报</li>
        <li>不编造、不夸大、不输出敏感内容</li>
        <li>只使用当前日期和已选择素材</li>
      </ul>
      </div>

      <div class="preview-block">
        <h3><Document />输出结构</h3>
        <ol>
          <li v-for="item in outputStructureItems" :key="item">{{ item }}</li>
          <li v-if="!outputStructureItems.length">使用所选模板的 Markdown 结构</li>
        </ol>
      </div>
    </div>

    <div class="preview-block">
      <h3><Tickets />写作重点</h3>
      <p>{{ outputFocus.length ? outputFocus.join(' / ') : '未指定输出重点' }}</p>
      <p>{{ extraRequirements.trim() || '暂无补充要求' }}</p>
    </div>

    <div class="prompt-preview-summary">
      <span>
        <em>素材</em>
        <strong>{{ selectedMaterialCount.toLocaleString() }} 条</strong>
      </span>
      <span>
        <em>预计字数</em>
        <strong>{{ estimatedPromptChars.toLocaleString() }}</strong>
      </span>
      <span>
        <em>内容选项</em>
        <strong>{{ optionLines.length }} 项</strong>
      </span>
    </div>

    <footer v-if="showActions !== false" class="preview-actions">
      <el-button plain @click="emit('previous')">上一步：素材选择</el-button>
      <el-button :icon="MagicStick" @click="emit('buildPrompt')">构建 Prompt</el-button>
      <el-button type="primary" @click="emit('next')">下一步：内容确认</el-button>
    </footer>
  </section>
</template>

<style scoped>
.prompt-preview-card {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto auto minmax(0, 1fr);
  gap: 10px;
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  margin: 0;
  color: #172033;
  font-size: 15px;
  font-weight: 840;
}

.card-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}

.preview-grid {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 0.88fr) minmax(0, 1.12fr);
  gap: 10px;
}

.preview-block {
  min-width: 0;
  display: grid;
  gap: 7px;
  padding: 11px 12px;
  border: 1px solid #e3ebf6;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff, #f8fbff);
}

.preview-block--system {
  background: linear-gradient(135deg, #f8fbff, #f1f7ff);
}

.preview-block h3 {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 840;
}

.preview-block svg {
  width: 15px;
  height: 15px;
  color: #2563eb;
}

.preview-block ul,
.preview-block ol {
  display: grid;
  gap: 4px;
  padding-left: 18px;
  margin: 0;
  color: #526070;
  font-size: 12px;
  line-height: 1.5;
}

.preview-block p {
  margin: 0;
  color: #526070;
  font-size: 12px;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.prompt-preview-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.prompt-preview-summary span {
  display: grid;
  gap: 3px;
  padding: 9px 10px;
  border: 1px solid #e5edf7;
  border-radius: 10px;
  background: linear-gradient(135deg, #fbfdff, #f6f9ff);
}

.prompt-preview-summary em {
  color: #667085;
  font-size: 11px;
  font-style: normal;
}

.prompt-preview-summary strong {
  color: #172033;
  font-size: 14px;
  font-weight: 840;
}

.preview-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 720px) {
  .preview-header {
    flex-direction: column;
  }

  .preview-grid,
  .prompt-preview-summary {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
