<script setup lang="ts">
import { computed } from 'vue'
import { Calendar, Filter, Search } from '@element-plus/icons-vue'

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
const statusOptions = [
  { label: '全部状态', value: 'all' },
  { label: '已保存', value: 'saved' }
] as const

function updateFilters(patch: Partial<ReportHistoryFilters>): void {
  emit('update:filters', { ...props.filters, ...patch })
}

function materialCount(row: ReportHistoryRow): number {
  const counts = row.source_counts ?? {}
  return ['app', 'browser', 'clipboard', 'ai_prompt'].reduce((total, key) => total + Number(counts[key] || 0), 0)
}

function createdTime(row: ReportHistoryRow): string {
  return row.created_at?.slice(11, 16) || '--:--'
}

function wordCount(row: ReportHistoryRow): number {
  return (row.report_markdown || '').length
}

function weekday(date: string): string {
  const parsed = new Date(`${date}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(parsed)
}
</script>

<template>
  <section class="history-list-card">
    <header class="history-card-header">
      <div>
        <h2 class="history-title">历史日报</h2>
        <p class="history-subtitle">查看、管理和重新生成已保存的日报</p>
      </div>
    </header>

    <el-input
      :model-value="filters.keyword"
      class="history-search"
      clearable
      placeholder="搜索模板名称、日期或内容..."
      @update:model-value="updateFilters({ keyword: String($event), page: 1 })"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
    </el-input>

    <div class="history-filter-row">
      <el-date-picker
        :model-value="filters.dateRange"
        type="daterange"
        class="date-range-filter"
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
        <el-option label="全部模板" value="" />
        <el-option v-for="item in templateOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>

      <el-select
        :model-value="filters.status"
        placeholder="生成状态"
        @update:model-value="updateFilters({ status: $event as ReportHistoryFilters['status'], page: 1 })"
      >
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>

      <el-button :icon="Filter" :loading="loading" @click="emit('refresh')">筛选</el-button>
    </div>

    <div class="history-list-toolbar">
      <span>共 {{ total }} 篇日报</span>
      <el-button plain size="small" :loading="loading" @click="emit('refresh')">按日期降序</el-button>
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
        <span class="history-item-icon"><Calendar /></span>
        <span class="history-item-main">
          <strong>{{ item.date }} <em>{{ weekday(item.date) }}</em></strong>
          <span>{{ item.template_name || 'daily_standard' }} · {{ item.model_name || '模型未记录' }}</span>
          <small>{{ createdTime(item) }} · {{ wordCount(item).toLocaleString() }} 字 · {{ materialCount(item) }} 条素材</small>
        </span>
        <el-tag class="history-status" size="small" type="success" effect="light">已保存</el-tag>
      </button>

      <el-empty v-if="!reports.length && !loading" description="暂无历史日报" />
    </div>

    <el-pagination
      v-if="total > filters.pageSize"
      class="history-pagination"
      layout="prev, pager, next, ->, total, sizes"
      :current-page="filters.page"
      :page-size="filters.pageSize"
      :page-sizes="[10, 12, 20, 50]"
      :total="total"
      @current-change="updateFilters({ page: $event })"
      @size-change="updateFilters({ pageSize: $event, page: 1 })"
    />
  </section>
</template>

<style scoped>
.history-list-card {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto auto minmax(0, 1fr) auto;
  gap: 12px;
  padding: 16px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
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
  font-size: 20px;
  font-weight: 840;
}

.history-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
}

.history-search,
.date-range-filter {
  width: 100%;
}

.history-list-card :deep(.el-input__wrapper),
.history-list-card :deep(.el-select__wrapper) {
  min-height: 38px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dce3ee inset;
}

.history-filter-row {
  display: grid;
  grid-template-columns: minmax(190px, 1.4fr) minmax(120px, 0.75fr) minmax(112px, 0.7fr) auto;
  gap: 8px;
}

.history-list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #526179;
  font-size: 12px;
}

.history-list {
  min-height: 0;
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 10px;
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 2px;
}

.history-item {
  min-width: 0;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid #e3ebf6;
  border-radius: 8px;
  color: #526070;
  text-align: left;
  background: #fbfdff;
  cursor: pointer;
  transition:
    border-color 160ms ease,
    background-color 160ms ease,
    box-shadow 160ms ease;
}

.history-item:hover,
.history-item--active {
  border-color: #66a8ff;
  background: #f4f9ff;
}

.history-item--active {
  box-shadow: inset 3px 0 0 #1d72f3;
}

.history-item-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #2563eb;
  background: #eff6ff;
}

.history-item-icon svg {
  width: 18px;
  height: 18px;
}

.history-item-main {
  min-width: 0;
  display: grid;
  gap: 5px;
}

.history-item-main strong,
.history-item-main span,
.history-item-main small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item-main strong {
  color: #172033;
  font-size: 13px;
}

.history-item-main em {
  margin-left: 4px;
  color: #2563eb;
  font-style: normal;
}

.history-item-main span,
.history-item-main small {
  color: #526070;
  font-size: 12px;
}

.history-status {
  align-self: end;
}

.history-pagination {
  min-width: 0;
}

@media (max-width: 760px) {
  .history-filter-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .history-item {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .history-status {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
