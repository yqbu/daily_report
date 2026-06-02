<script setup lang="ts">
import { computed, shallowRef } from 'vue'

import type { MaterialCandidate, PromptOptions, ReportTemplate } from '../../types/reportWorkbench'

type PreviewTab = 'materials' | 'config' | 'final'

const props = defineProps<{
  promptText: string
  promptDirty: boolean
  selectedMaterials: MaterialCandidate[]
  selectedTemplate: ReportTemplate | undefined
  extraRequirements: string
  outputFocus: string[]
  options: PromptOptions
}>()

const activeTab = shallowRef<PreviewTab>('final')

const groupedMaterials = computed(() => {
  const groups = new Map<string, MaterialCandidate[]>()
  for (const item of props.selectedMaterials) {
    const key = item.category || '其他'
    groups.set(key, [...(groups.get(key) ?? []), item])
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items: items.slice(0, 10), count: items.length }))
})

const configLines = computed(() => [
  `模板：${props.selectedTemplate?.name || '未选择模板'}`,
  `输出重点：${props.outputFocus.length ? props.outputFocus.join(' / ') : '未指定'}`,
  `补充要求：${props.extraRequirements.trim() || '暂无'}`,
  `包含素材摘要：${props.options.includeMaterialSummary ? '是' : '否'}`,
  `包含明日计划建议：${props.options.includeTomorrowPlan ? '是' : '否'}`,
  `按分类组织：${props.options.groupByCategory ? '是' : '否'}`
])

const fallbackPrompt = computed(() => {
  const materialLines = groupedMaterials.value
    .map((group) => `【${group.label}】\n${group.items.map((item) => `- ${item.title}：${item.summary || item.time_range || '-'}`).join('\n')}`)
    .join('\n\n')
  return [
    '【系统要求】',
    '根据用户选择的本地素材生成中文 Markdown 日报，不编造、不输出敏感内容。',
    '',
    '【Prompt 配置摘要】',
    configLines.value.join('\n'),
    '',
    '【素材摘要】',
    materialLines || '暂无已选素材'
  ].join('\n')
})

const finalText = computed(() => props.promptText || fallbackPrompt.value)
</script>

<template>
  <section class="workbench-card final-preview-card">
    <header class="preview-header">
      <div>
        <h2 class="card-title">最终提交内容预览</h2>
        <p class="card-subtitle">以下内容将作为 Prompt 提交给大模型</p>
      </div>
      <el-tag v-if="promptDirty" type="warning" effect="light" disable-transitions>需要重建</el-tag>
      <el-tag v-else type="success" effect="light" disable-transitions>可提交</el-tag>
    </header>

    <el-tabs v-model="activeTab" class="final-tabs">
      <el-tab-pane label="素材摘要" name="materials">
        <div class="preview-scroll">
          <section v-for="group in groupedMaterials" :key="group.label" class="material-group">
            <h3>{{ group.label }} <span>{{ group.count }} 条</span></h3>
            <ul>
              <li v-for="item in group.items" :key="`${item.source_type}:${item.source_id}`">
                <strong>{{ item.title }}</strong>
                <p>{{ item.summary || item.time_range || '-' }}</p>
              </li>
            </ul>
          </section>
          <el-empty v-if="!groupedMaterials.length" description="暂无已选素材" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="Prompt 配置摘要" name="config">
        <pre class="preview-scroll text-preview">{{ configLines.join('\n') }}</pre>
      </el-tab-pane>

      <el-tab-pane label="最终提交内容" name="final">
        <pre class="preview-scroll text-preview">{{ finalText }}</pre>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<style scoped>
.final-preview-card {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
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
  font-size: 16px;
  font-weight: 840;
}

.card-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}

.final-tabs {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.final-tabs :deep(.el-tabs__header) {
  margin: 0 0 10px;
}

.final-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.final-tabs :deep(.el-tab-pane) {
  height: 100%;
  min-height: 0;
}

.preview-scroll {
  height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 14px;
  border: 1px solid #e3ebf6;
  border-radius: 12px;
  background: #fbfdff;
}

.material-group {
  display: grid;
  gap: 8px;
}

.material-group + .material-group {
  margin-top: 14px;
}

.material-group h3 {
  margin: 0;
  color: #172033;
  font-size: 13px;
  font-weight: 840;
}

.material-group h3 span {
  margin-left: 6px;
  color: #667085;
  font-size: 12px;
  font-weight: 700;
}

.material-group ul {
  display: grid;
  gap: 8px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.material-group li {
  display: grid;
  gap: 4px;
}

.material-group strong {
  color: #172033;
  font-size: 12px;
}

.material-group p {
  margin: 0;
  color: #526070;
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.text-preview {
  margin: 0;
  color: #344054;
  font: inherit;
  line-height: 1.65;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
