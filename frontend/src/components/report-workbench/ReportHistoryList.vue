<script setup lang="ts">
import { computed } from 'vue'
import { Calendar, Refresh, Search } from '@element-plus/icons-vue'

import DateRangePicker from '../DateRangePicker.vue'
import type { ReportHistoryFilters, ReportHistoryRow, ReportTemplate } from '../../types/reportWorkbench'

type DateRange = [Date, Date]

const props = defineProps<{
  filters: ReportHistoryFilters
  reports: ReportHistoryRow[]
  total: number
  templates: ReportTemplate[]
  loading: boolean
  activeDate?: string | null
}>()

const emit = defineEmits<{
  'update:filters': [filters: ReportHistoryFilters]
  refresh: []
  select: [id: number]
}>()

const templateOptions = computed(() => props.templates.map((item) => ({ label: item.name, value: item.id })))
const pickerDateRange = computed<DateRange>({
  get: () => {
    const range = props.filters.dateRange
    if (range) {
      return [toDate(range[0]), toDate(range[1])] as DateRange
    }
    const today = startOfToday()
    return [addDays(today, -29), today] as DateRange
  },
  set: (dateRange: DateRange) => updateFilters({ dateRange, page: 1 })
})

const dateGroups = computed(() => {
  const groups = new Map<string, ReportHistoryRow[]>()
  for (const report of props.reports) {
    const rows = groups.get(report.date) ?? []
    rows.push(report)
    groups.set(report.date, rows)
  }

  return Array.from(groups.entries())
    .map(([date, rows]) => {
      const sortedRows = [...rows].sort(compareReportDesc)
      const latest = sortedRows[0]
      return {
        date,
        latest,
        versionCount: sortedRows.length,
        materialCount: sortedRows.reduce((sum, row) => sum + materialCount(row), 0),
        templateCount: new Set(sortedRows.map((row) => row.template_name || 'daily_standard')).size,
        latestTime: createdTime(latest)
      }
    })
    .sort((left, right) => right.date.localeCompare(left.date))
})

function updateFilters(patch: Partial<ReportHistoryFilters>): void {
  emit('update:filters', { ...props.filters, ...patch })
}

function materialCount(row: ReportHistoryRow): number {
  const counts = row.source_counts ?? {}
  const browser = Number(counts.browser || 0)
  const legacyBrowser = Number(counts.ai_prompt || 0) + Number(counts.browser_event || 0)
  return Number(counts.app || 0) + Number(counts.clipboard || 0) + (browser || legacyBrowser)
}

function createdTime(row: ReportHistoryRow): string {
  return row.created_at?.slice(11, 16) || '--:--'
}

function compareReportDesc(left: ReportHistoryRow, right: ReportHistoryRow): number {
  const timeDiff = new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
  return timeDiff || right.id - left.id
}

function weekday(date: string): string {
  const parsed = new Date(`${date}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', { weekday: 'short' }).format(parsed)
}

function toDate(value: Date | string): Date {
  if (value instanceof Date) return value
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? startOfToday() : parsed
}

function startOfToday(): Date {
  const date = new Date()
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function addDays(date: Date, offset: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + offset)
  return next
}
</script>

<template>
  <section class="history-list-card">
    <div class="history-search-row">
      <el-input
        :model-value="filters.keyword"
        class="history-search"
        clearable
        placeholder="搜索日期、模板或内容..."
        @update:model-value="updateFilters({ keyword: String($event), page: 1 })"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select
        :model-value="filters.templateName"
        clearable
        placeholder="模板类型"
        @update:model-value="updateFilters({ templateName: String($event || ''), page: 1 })"
      >
        <el-option label="全部模板" value="" />
        <el-option v-for="item in templateOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
    </div>

    <div class="history-filter-row">
      <DateRangePicker v-model="pickerDateRange" class="date-range-filter" />
      <el-button
        class="history-filter-button"
        :icon="Refresh"
        :loading="loading"
        aria-label="刷新筛选结果"
        title="刷新筛选结果"
        @click="emit('refresh')"
      />
    </div>

    <div class="history-list-toolbar">
      <span>共 {{ dateGroups.length }} 天 · {{ total }} 个版本</span>
      <el-button plain size="small" :loading="loading" @click="emit('refresh')">按日期降序</el-button>
    </div>

    <div v-loading="loading" class="history-list">
      <button
        v-for="item in dateGroups"
        :key="item.date"
        class="history-item"
        :class="{ 'history-item--active': item.date === activeDate }"
        type="button"
        @click="emit('select', item.latest.id)"
      >
        <span class="history-item-icon"><Calendar /></span>
        <span class="history-item-main">
          <strong>{{ item.date }} <em>{{ weekday(item.date) }}</em></strong>
          <span>{{ item.versionCount }} 个版本 · 最新 {{ item.latestTime }}</span>
        </span>
      </button>

      <el-empty v-if="!dateGroups.length && !loading" description="暂无历史日报" />
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
  grid-template-rows: auto auto auto minmax(0, 1fr) auto;
  gap: 12px;
  padding: 16px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
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
  min-width: 0;
}

.history-list-card :deep(.el-input),
.history-list-card :deep(.el-select),
.history-list-card :deep(.el-date-editor) {
  width: 100%;
  min-width: 0;
}

.history-list-card :deep(.el-input__wrapper),
.history-list-card :deep(.el-select__wrapper),
.history-list-card :deep(.el-date-editor.el-input__wrapper) {
  min-height: 38px;
  height: 38px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dce3ee inset;
}

.history-list-card :deep(.el-date-editor .el-range-input) {
  min-width: 0;
  font-size: 13px;
}

.history-list-card :deep(.el-date-editor .el-range-separator) {
  flex: 0 0 auto;
  padding: 0 4px;
}

.history-search-row {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(116px, 0.75fr);
  gap: 8px;
  min-width: 0;
}

.history-filter-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px;
  gap: 8px;
  min-width: 0;
}

.history-filter-button {
  width: 38px;
  min-width: 38px;
  height: 38px;
  margin-left: 0;
  border-radius: 8px;
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
  grid-template-columns: 36px minmax(0, 1fr);
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

.history-pagination {
  min-width: 0;
  overflow: hidden;
}

@media (max-width: 760px) {
  .history-search-row,
  .history-filter-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .history-item {
    grid-template-columns: 36px minmax(0, 1fr);
  }

}
</style>
