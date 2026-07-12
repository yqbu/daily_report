<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, reactive, shallowRef, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Collection,
  CopyDocument,
  DataAnalysis,
  Download,
  Link,
  List,
  Monitor,
  Refresh
} from '@element-plus/icons-vue'

import { callTypedDesktopApi } from '../api/desktop'
import type { AnyRecord, DataCenterSummaryPayload, SourceType, TimelineEvent } from '../api/types'
import DateRangePicker from '../components/DateRangePicker.vue'
import DataCenterFilterBar from '../components/data-center/DataCenterFilterBar.vue'
import RecordDetailDrawer from '../components/data-center/RecordDetailDrawer.vue'
import TimelineInfiniteList from '../components/data-center/TimelineInfiniteList.vue'
import type { DataCenterFilters, DataCenterView, DetailSavePayload } from '../components/data-center/types'
import { SOURCE_OPTIONS, dateRangeToPayload, recordId, recordSource, toDateKey } from '../components/data-center/types'

const today = new Date()
const startOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0)
const endOfDay = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 23, 59, 59)

let filters = reactive<DataCenterFilters>({
  dateRange: [startOfDay, endOfDay],
  sourceTypes: SOURCE_OPTIONS.map((item) => item.value),
  sensitive: 'all',
  categories: [],
  keyword: '',
  sortOrder: 'desc',
  browserRecordType: ''
})

const activeView = shallowRef<DataCenterView>('timeline')
const DataAnalysisView = defineAsyncComponent(() => import('../components/data-center/DataAnalysisView.vue'))
const summary = shallowRef<DataCenterSummaryPayload>(emptySummary())
const summaryLoading = shallowRef(false)
const timelineItems = shallowRef<TimelineEvent[]>([])
const timelineLoading = shallowRef(false)
const timelineCursor = shallowRef<string | null>(null)
const timelineHasMore = shallowRef(true)
const timelineActiveDay = shallowRef<string | null>(null)
const selectedRecord = shallowRef<AnyRecord | null>(null)
const drawerOpen = shallowRef(false)
const drawerLoading = shallowRef(false)
const drawerSaving = shallowRef(false)
const refreshKey = shallowRef(0)
let summaryRequestId = 0
let timelineRequestId = 0
let detailRequestId = 0
let filterRefreshTimer: number | null = null

const viewTabs = [
  { label: '时间线视图', value: 'timeline', icon: List },
  { label: '分析统计', value: 'analysis', icon: DataAnalysis }
] as const

const summaryItems = computed(() => [
  { key: 'total', label: '共', suffix: '条记录', value: summary.value.total, icon: Collection, tone: 'slate' },
  { key: 'app', label: '应用', suffix: '', value: summary.value.app, icon: Monitor, tone: 'blue' },
  { key: 'browser', label: '浏览器', suffix: '', value: summary.value.browser, icon: Link, tone: 'green' },
  { key: 'clipboard', label: '剪贴板', suffix: '', value: summary.value.clipboard, icon: CopyDocument, tone: 'orange' }
])

const apiFilters = computed(() => ({
  sourceTypes: filters.sourceTypes,
  sensitive: filters.sensitive === 'all' ? undefined : filters.sensitive === 'sensitive',
  categories: filters.categories,
  keyword: filters.keyword.trim() || undefined,
  sortOrder: filters.sortOrder,
  recordType: filters.sourceTypes.length === 1 && filters.sourceTypes.includes('browser') ? filters.browserRecordType || undefined : undefined
}))
const filterSignature = computed(() => {
  const range = dateRangeToPayload(filters)
  return JSON.stringify({
    ...range,
    sourceTypes: [...filters.sourceTypes],
    sensitive: filters.sensitive,
    categories: [...filters.categories],
    keyword: filters.keyword.trim(),
    sortOrder: filters.sortOrder,
    browserRecordType: filters.browserRecordType
  })
})
async function refreshAll(): Promise<void> {
  refreshKey.value += 1
  await loadSummary()
  await resetTimeline()
}

async function loadSummary(): Promise<void> {
  const requestId = summaryRequestId + 1
  summaryRequestId = requestId
  summaryLoading.value = true
  try {
    const range = dateRangeToPayload(filters)
    const response = await callTypedDesktopApi('getDataCenterSummary', {
      ...range,
      filters: apiFilters.value
    })
    if (requestId === summaryRequestId) {
      summary.value = response
    }
  } finally {
    if (requestId === summaryRequestId) {
      summaryLoading.value = false
    }
  }
}

async function resetTimeline(): Promise<void> {
  const requestId = timelineRequestId + 1
  timelineRequestId = requestId
  timelineItems.value = []
  timelineCursor.value = null
  timelineActiveDay.value = preferredTimelineDay()
  timelineHasMore.value = Boolean(timelineActiveDay.value)
  timelineLoading.value = false
  await loadMoreTimeline(requestId)
}

async function loadMoreTimeline(requestId = timelineRequestId): Promise<void> {
  const activeDay = timelineActiveDay.value
  if (timelineLoading.value || !timelineHasMore.value || !activeDay) {
    return
  }
  timelineLoading.value = true
  try {
    const response = await callTypedDesktopApi('getTimeline', {
      startDate: activeDay,
      endDate: activeDay,
      filters: apiFilters.value,
      cursor: timelineCursor.value,
      pageSize: 28
    })
    if (requestId === timelineRequestId) {
      timelineItems.value = [...timelineItems.value, ...response.items]
      timelineCursor.value = response.nextCursor ?? null
      timelineHasMore.value = Boolean(response.hasMore)
    }
  } finally {
    if (requestId === timelineRequestId) {
      timelineLoading.value = false
    }
  }
}

async function selectTimelineDay(day: string): Promise<void> {
  if (timelineLoading.value && day === timelineActiveDay.value) {
    return
  }
  const requestId = timelineRequestId + 1
  timelineRequestId = requestId
  timelineActiveDay.value = day
  timelineCursor.value = null
  timelineHasMore.value = true
  timelineLoading.value = false
  timelineItems.value = []
  await loadMoreTimeline(requestId)
}

async function openDetail(sourceType: SourceType, id: number, ids?: number[], entryKey?: string | null): Promise<void> {
  const requestId = detailRequestId + 1
  detailRequestId = requestId
  selectedRecord.value = null
  drawerLoading.value = true
  drawerOpen.value = true
  await nextTick()
  await new Promise<void>((resolve) => window.requestAnimationFrame(() => resolve()))
  try {
    const detail = await callTypedDesktopApi('getEntryDetail', { sourceType, id, ids, entryKey })
    if (requestId === detailRequestId) {
      selectedRecord.value = detail
    }
  } finally {
    if (requestId === detailRequestId) {
      drawerLoading.value = false
    }
  }
}

function openTimelineDetail(item: TimelineEvent): void {
  void openDetail(item.source_type, item.source_id, item.source_ids, item.entry_key)
}

async function toggleSensitive(sourceType: SourceType, id: number, nextValue: boolean, ids?: number[], entryKey?: string | null): Promise<void> {
  await callTypedDesktopApi('updateEntrySensitive', {
    sourceType,
    id,
    ids,
    entryKey,
    sensitive: nextValue,
    reason: nextValue ? '用户标记' : null
  })
  ElMessage.success(nextValue ? '已标记为敏感' : '已取消敏感')
  removeIfFilterNoLongerMatches(sourceType, id, nextValue)
  await loadSummary()
  refreshKey.value += 1
}

function toggleTimelineSensitive(item: TimelineEvent): void {
  void toggleSensitive(item.source_type, item.source_id, !item.is_sensitive, item.source_ids, item.entry_key)
}

async function deleteRecord(sourceType: SourceType, id: number, entryKey?: string | null): Promise<void> {
  await ElMessageBox.confirm('删除后记录会被软删除，不会从数据库物理移除。', '确认删除记录', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger'
  })
  await callTypedDesktopApi('markEntryDeleted', { sourceType, id, entryKey })
  timelineItems.value = timelineItems.value.filter((item) => !(item.source_type === sourceType && item.source_id === id))
  if (selectedRecord.value && recordSource(selectedRecord.value) === sourceType && recordId(selectedRecord.value) === id) {
    drawerOpen.value = false
    selectedRecord.value = null
  }
  ElMessage.success('记录已删除')
  await loadSummary()
  refreshKey.value += 1
}

async function saveDetail(payload: DetailSavePayload): Promise<void> {
  drawerSaving.value = true
  try {
    await callTypedDesktopApi('updateEntryAnnotation', {
      sourceType: payload.sourceType,
      id: payload.id,
      entryKey: payload.entryKey,
      payload: {
        category: payload.category,
        note: payload.note,
        importance: payload.importance,
        is_selected_override: payload.selected
      }
    })
    await callTypedDesktopApi('updateEntrySensitive', {
      sourceType: payload.sourceType,
      id: payload.id,
      entryKey: payload.entryKey,
      sensitive: payload.sensitive,
      reason: payload.sensitivityReason
    })
    selectedRecord.value = await callTypedDesktopApi('getEntryDetail', {
      sourceType: payload.sourceType,
      id: payload.id,
      entryKey: payload.entryKey
    })
    ElMessage.success('修改已保存')
    await loadSummary()
    await resetTimeline()
    refreshKey.value += 1
  } finally {
    drawerSaving.value = false
  }
}

function resetFilters(): void {
  filters.dateRange = [startOfDay, endOfDay]
  filters.sourceTypes = SOURCE_OPTIONS.map((item) => item.value)
  filters.sensitive = 'all'
  filters.categories = []
  filters.keyword = ''
  filters.sortOrder = 'desc'
  filters.browserRecordType = ''
}

async function exportData(): Promise<void> {
  const range = dateRangeToPayload(filters)
  const response = await callTypedDesktopApi('getTimeline', {
    ...range,
    filters: apiFilters.value,
    offset: 0,
    limit: 5000
  })
  const blob = new Blob([JSON.stringify(response.items, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `data-center-${toDateKey(filters.dateRange[0])}-${toDateKey(filters.dateRange[1])}.json`
  link.click()
  URL.revokeObjectURL(url)
}

function removeIfFilterNoLongerMatches(sourceType: SourceType, id: number, sensitive: boolean): void {
  timelineItems.value = timelineItems.value
    .map((item) => (item.source_type === sourceType && item.source_id === id ? { ...item, is_sensitive: sensitive } : item))
    .filter((item) => {
      if (filters.sensitive === 'sensitive') {
        return item.is_sensitive
      }
      if (filters.sensitive === 'normal') {
        return !item.is_sensitive
      }
      return true
    })
}

function emptySummary(): DataCenterSummaryPayload {
  return {
    total: 0,
    app: 0,
    browser: 0,
    browser_event: 0,
    clipboard: 0,
    ai_prompt: 0,
    browser_record_type_counts: {},
    sensitive: 0,
    deleted: 0,
    categories: [],
    days: []
  }
}

function preferredTimelineDay(): string | null {
  const days = summary.value.days.map((item) => item.date)
  if (timelineActiveDay.value && days.includes(timelineActiveDay.value)) {
    return timelineActiveDay.value
  }
  return days[0] ?? null
}

function scheduleFilterRefresh(): void {
  if (filterRefreshTimer !== null) {
    window.clearTimeout(filterRefreshTimer)
  }
  filterRefreshTimer = window.setTimeout(() => {
    filterRefreshTimer = null
    void refreshAll()
  }, 120)
}

watch(
  filterSignature,
  scheduleFilterRefresh,
  { immediate: true }
)

watch(
  drawerOpen,
  (open) => {
    if (!open) {
      detailRequestId += 1
      drawerLoading.value = false
      selectedRecord.value = null
    }
  }
)

onBeforeUnmount(() => {
  if (filterRefreshTimer !== null) {
    window.clearTimeout(filterRefreshTimer)
  }
})
</script>

<template>
  <div class="data-center-page">
    <header class="datacenter-topbar">
      <div class="title-block">
        <span class="workspace-label">Daily Report</span>
        <h1 class="page-title">数据中心</h1>
      </div>

      <div class="top-actions">
        <DateRangePicker v-model="filters.dateRange" class="date-picker" />

        <button class="top-button" type="button" :disabled="summaryLoading || timelineLoading" title="刷新当前筛选结果" @click="refreshAll">
          <Refresh class="action-icon" :class="{ 'action-icon--spin': summaryLoading || timelineLoading }" />
          <span>刷新</span>
        </button>

        <button class="top-button top-button--primary" type="button" title="导出当前筛选结果" @click="exportData">
          <Download class="action-icon" />
          <span>导出数据</span>
        </button>
      </div>
    </header>

    <DataCenterFilterBar v-model="filters" @reset="resetFilters" />

    <section v-loading="summaryLoading" class="view-tabs-card">
      <el-segmented v-model="activeView" :options="viewTabs">
        <template #default="{ item }">
          <span class="view-tab-option">
            <el-icon><component :is="item.icon" /></el-icon>
            {{ item.label }}
          </span>
        </template>
      </el-segmented>

      <div class="summary-strip" aria-label="当前筛选统计">
        <span v-for="item in summaryItems" :key="item.key" class="summary-chip" :class="`summary-chip--${item.tone}`">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <span v-if="item.suffix">{{ item.suffix }}</span>
        </span>
      </div>
    </section>

    <section class="data-view-shell">
      <TimelineInfiniteList
        v-if="activeView === 'timeline'"
        :items="timelineItems"
        :day-counts="summary.days"
        :active-day="timelineActiveDay"
        :loading="timelineLoading"
        :has-more="timelineHasMore"
        @load-more="loadMoreTimeline"
        @select-day="selectTimelineDay"
        @detail="openTimelineDetail"
        @toggle-sensitive="toggleTimelineSensitive"
        @delete="deleteRecord($event.source_type, $event.source_id, $event.entry_key)"
      />

      <DataAnalysisView
        v-else-if="activeView === 'analysis'"
        :filters="filters"
        :active="activeView === 'analysis'"
        :refresh-key="refreshKey"
      />
    </section>

    <RecordDetailDrawer
      v-model="drawerOpen"
      :record="selectedRecord"
      :loading="drawerLoading"
      :saving="drawerSaving"
      @save="saveDetail"
      @delete="deleteRecord"
    />
  </div>
</template>

<style scoped>
.data-center-page {
  --datacenter-text: #172033;
  --datacenter-muted: #667085;
  --datacenter-border: #dce3ee;
  --datacenter-blue: #409eff;
  --datacenter-green: #67c23a;
  --datacenter-orange: #e6a23c;
  --datacenter-purple: #f56c6c;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 12px;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  color: var(--datacenter-text);
  background: #fbfcfd;
}

.datacenter-topbar,
.view-tabs-card {
  border: 1px solid var(--datacenter-border);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
}

.datacenter-topbar {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
}

.title-block {
  min-width: 0;
}

.workspace-label {
  display: block;
  color: var(--datacenter-muted);
  font-size: 12px;
  line-height: 1.2;
}

.page-title {
  margin: 4px 0 0;
  color: var(--datacenter-text);
  font-size: 22px;
  font-weight: 720;
  line-height: 1.15;
  letter-spacing: 0;
}

.top-actions {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.top-button {
  height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid var(--datacenter-border);
  border-radius: 8px;
  color: #526179;
  background: #fff;
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
}

.top-button:hover {
  color: var(--datacenter-blue);
  border-color: #c9dcff;
  background: #eff6ff;
}

.top-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.top-button--primary {
  color: #fff;
  border-color: #2563eb;
  background: #2563eb;
}

.top-button--primary:hover {
  color: #fff;
  border-color: #1d4ed8;
  background: #1d4ed8;
}

.action-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

.action-icon--spin {
  animation: datacenter-spin 900ms linear infinite;
}

.date-picker {
  width: 274px;
}

.data-center-page :deep(.el-date-editor.el-input__wrapper) {
  height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--datacenter-border) inset;
}

.data-center-page :deep(.el-date-editor.el-input__wrapper:hover),
.data-center-page :deep(.el-date-editor.el-input__wrapper.is-active) {
  box-shadow: 0 0 0 1px #c9dcff inset;
}

.data-center-page :deep(.el-date-editor .el-range-input) {
  color: var(--datacenter-text);
  font-size: 13px;
}

.view-tabs-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-width: 0;
  padding: 12px;
}

.view-tab-option {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-width: 96px;
  justify-content: center;
}

.summary-strip {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 4px 10px;
  min-width: 0;
  color: #526179;
  font-size: 12px;
}

.summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.summary-chip + .summary-chip::before {
  margin-right: 6px;
  color: #c4ccd8;
  content: '|';
}

.summary-chip :deep(svg) {
  width: 14px;
  height: 14px;
}

.summary-chip strong {
  color: var(--datacenter-text);
  font-size: 13px;
  font-weight: 820;
  font-variant-numeric: tabular-nums;
}

.summary-chip--blue :deep(svg) {
  color: var(--datacenter-blue);
}

.summary-chip--slate :deep(svg) {
  color: #526179;
}

.summary-chip--green :deep(svg) {
  color: var(--datacenter-green);
}

.summary-chip--orange :deep(svg) {
  color: var(--datacenter-orange);
}

.summary-chip--purple :deep(svg) {
  color: var(--datacenter-purple);
}

.data-view-shell {
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

@keyframes datacenter-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 760px) {
  .datacenter-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .top-actions,
  .view-tabs-card {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .date-picker {
    width: min(100%, 320px);
  }
}
</style>
