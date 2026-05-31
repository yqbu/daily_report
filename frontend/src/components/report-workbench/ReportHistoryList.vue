<script setup lang="ts">
import { computed } from 'vue'
import { Calendar, Search } from '@element-plus/icons-vue'

import type { ReportHistoryFilters, ReportHistoryRow, ReportTemplate } from '../../types/reportWorkbench'

const props = defineProps<{
  filters: ReportHistoryFilters
  reports: ReportHistoryRow[]
  total: number
  templates: ReportTemplate[]
  loading: boolean
  activeId?: number | null
}>()

const emit = defineEmits<{
  'update:filters': [filters: ReportHistoryFilters]
  refresh: []
  select: [id: number]
}>()

const templateOptions = computed(() => props.templates.map((item) => ({ label: item.name, value: item.id })))

function updateFilters(patch: Partial<ReportHistoryFilters>): void {
  emit('update:filters', { ...props.filters, ...patch })
}

function materialCount(row: ReportHistoryRow): number {
  const counts = row.source_counts ?? {}
  return ['app', 'browser', 'clipboard', 'ai_prompt'].reduce((total, key) => total + Number(counts[key] || 0), 0)
}
</script>

<template>
  <section class="history-list-card">
    <header class="history-card-header">
      <div>
        <h2 class="history-title">历史日报</h2>
        <p class="history-subtitle">查看、筛选和选择已保存的日报</p>
      </div>
      <el-button :icon="Search" :loading="loading" @click="emit('refresh')">筛选</el-button>
    </header>

    <div class="history-filters">
      <el-date-picker
        :model-value="filters.dateRange"
        type="daterange"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        @update:model-value="updateFilters({ dateRange: $event as ReportHistoryFilters['dateRange'], page: 1 })"
      />
      <el-select
        :model-value="filters.templateName"
        clearable
        placeholder="模板类型"
        @update:model-value="updateFilters({ templateName: String($event || ''), page: 1 })"
      >
        <el-option v-for="item in templateOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input
        :model-value="filters.keyword"
        clearable
        placeholder="关键词搜索"
        @update:model-value="updateFilters({ keyword: String($event), page: 1 })"
      />
    </div>

    <div v-loading="loading" class="history-list">
      <button
        v-for="item in reports"
        :key="item.id"
        class="history-item"
        :class="{ 'history-item--active': item.id === activeId }"
        type="button"
        @click="emit('select', item.id)"
      >
        <span class="history-date"><Calendar />{{ item.date }}</span>
        <strong>{{ item.template_name || '日报模板' }}</strong>
        <span>{{ item.created_at.slice(11, 16) }} · {{ (item.report_markdown || '').length }} 字 · {{ materialCount(item) }} 条素材</span>
        <el-tag size="small" type="success" effect="light">已保存</el-tag>
      </button>

      <el-empty v-if="!reports.length && !loading" description="暂无历史日报，生成并保存日报后会显示在这里。" />
    </div>

    <el-pagination
      v-if="total > filters.pageSize"
      small
      layout="prev, pager, next"
      :current-page="filters.page"
      :page-size="filters.pageSize"
      :total="total"
      @current-change="updateFilters({ page: $event })"
    />
  </section>
</template>

<style scoped>
.history-list-card {
  min-width: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 12px;
  padding: 16px;
  border: 1px solid #dfe8f5;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 31, 61, 0.04);
}

.history-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.history-title {
  margin: 0;
  color: #172033;
  font-size: 16px;
  font-weight: 840;
}

.history-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}

.history-filters {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr) minmax(0, 1fr);
  gap: 8px;
}

.history-list {
  min-height: 240px;
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 10px;
  overflow: auto;
}

.history-item {
  min-width: 0;
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid #e3ebf6;
  border-radius: 10px;
  color: #526070;
  text-align: left;
  background: #fbfdff;
  cursor: pointer;
}

.history-item:hover,
.history-item--active {
  border-color: #9ec5ff;
  background: #f1f7ff;
}

.history-item strong {
  color: #172033;
}

.history-date {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 800;
}

.history-date svg {
  width: 14px;
  height: 14px;
}

@media (max-width: 760px) {
  .history-filters {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
