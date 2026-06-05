<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { Clock, CollectionTag, DataAnalysis, Delete, Select } from '@element-plus/icons-vue'

import type { MaterialCandidate, MaterialSummary } from '../../types/reportWorkbench'

type OrganizeMode = 'category' | 'source' | 'time'

const props = defineProps<{
  items: MaterialCandidate[]
  summary: MaterialSummary
  loading: boolean
  showActions?: boolean
}>()

const emit = defineEmits<{
  next: []
  clearSelection: []
  selectNonSensitive: []
}>()

const mode = shallowRef<OrganizeMode>('category')

const modeOptions = [
  { label: '按分类', value: 'category' },
  { label: '按来源', value: 'source' },
  { label: '按时间', value: 'time' }
] as const

const sourceLabels: Record<string, string> = {
  app: '前台应用',
  browser: '浏览器',
  clipboard: '剪切板',
  ai_prompt: '浏览器',
  browser_event: '浏览器'
}

const selectedItems = computed(() => props.items.filter((item) => item.is_selected))

const groupedItems = computed(() => {
  const groups = new Map<string, MaterialCandidate[]>()
  for (const item of selectedItems.value) {
    const key = groupKey(item)
    groups.set(key, [...(groups.get(key) ?? []), item])
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items: items.slice(0, 8), count: items.length }))
})

function groupKey(item: MaterialCandidate): string {
  if (mode.value === 'source') return sourceLabels[item.source_type] ?? item.source_type
  if (mode.value === 'time') return item.time_range?.slice(0, 5) || '未记录时间'
  return item.category || '其他'
}
</script>

<template>
  <section class="workbench-card organized-preview-card">
    <header class="preview-header">
      <div>
        <h2 class="card-title">素材组织预览</h2>
        <p class="card-subtitle">按分类整理本次将用于日报的素材</p>
      </div>
      <el-segmented v-model="mode" :options="modeOptions" size="small" />
    </header>

    <div class="preview-stats">
      <span>
        <DataAnalysis />
        <strong>{{ summary.total_count.toLocaleString() }}</strong>
        <em>素材总数</em>
      </span>
      <span>
        <Select />
        <strong>{{ summary.selected_count.toLocaleString() }}</strong>
        <em>已选素材</em>
      </span>
      <span>
        <Clock />
        <strong>{{ summary.estimated_prompt_chars.toLocaleString() }}</strong>
        <em>预计字数</em>
      </span>
    </div>

    <div v-loading="loading" class="organized-list">
      <section v-for="group in groupedItems" :key="group.label" class="organized-group">
        <header>
          <span><CollectionTag />{{ group.label }}</span>
          <em>{{ group.count }} 条</em>
        </header>
        <ul>
          <li v-for="item in group.items" :key="`${item.source_type}:${item.source_id}`">
            <strong>{{ item.title }}</strong>
            <span>{{ item.summary || item.time_range || '-' }}</span>
          </li>
        </ul>
      </section>

      <el-empty v-if="!groupedItems.length && !loading" description="请先在左侧选择素材" />
    </div>

    <footer v-if="showActions !== false" class="preview-actions">
      <el-button :icon="Delete" plain :disabled="selectedItems.length === 0" @click="emit('clearSelection')">
        清空选择
      </el-button>
      <el-button plain @click="emit('selectNonSensitive')">仅选择非敏感</el-button>
      <el-button type="primary" @click="emit('next')">下一步：配置 Prompt</el-button>
    </footer>
  </section>
</template>

<style scoped>
.organized-preview-card {
  min-width: 0;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 10px;
  overflow: hidden;
}

.preview-header {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 2px;
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

.preview-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.preview-stats span {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  column-gap: 8px;
  row-gap: 2px;
  align-items: center;
  padding: 10px 11px;
  border: 1px solid #e5edf7;
  border-radius: 10px;
  background: linear-gradient(135deg, #fbfdff, #f6f9ff);
}

.preview-stats svg {
  grid-row: span 2;
  width: 15px;
  height: 15px;
  color: #2563eb;
}

.preview-stats strong {
  color: #172033;
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.preview-stats em {
  color: #667085;
  font-size: 11px;
  font-style: normal;
}

.organized-list {
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 9px;
  padding-right: 2px;
  overflow-x: hidden;
  overflow-y: auto;
}

.organized-group {
  display: grid;
  gap: 7px;
  padding: 11px 12px;
  border: 1px solid #e3ebf6;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff, #f8fbff);
}

.organized-group header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.organized-group header span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #172033;
  font-size: 13px;
  font-weight: 820;
}

.organized-group header svg {
  width: 14px;
  height: 14px;
  color: #2563eb;
}

.organized-group header em {
  color: #667085;
  font-size: 12px;
  font-style: normal;
}

.organized-group ul {
  display: grid;
  gap: 7px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.organized-group li {
  min-width: 0;
  display: grid;
  gap: 2px;
  padding: 7px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
}

.organized-group li strong,
.organized-group li span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.organized-group li strong {
  color: #1e2a3b;
  font-size: 12.5px;
}

.organized-group li span {
  color: #667085;
  font-size: 12px;
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

  .preview-stats {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
