<script setup lang="ts">
import { onMounted, reactive, shallowRef } from 'vue'

import { callTypedBridge } from '../api/bridge'
import type {
  AnyRecord,
  EntryAnnotationPayload,
  EntryListFilters,
  SourceType,
  TimelineEvent,
  TimelineFilters
} from '../api/types'
import PageLayout from '../layouts/PageLayout.vue'

/**
 * 数据中心页骨架。
 *
 * 页面职责：
 * - 统一查看四类来源的时间线：getTimeline
 * - 按来源分页查看原始记录：listEntries
 * - 读取详情、更新选中状态、软删除、更新分类备注
 *
 * 布局实现建议：
 * - 顶部：日期、来源、选中、敏感、关键词筛选
 * - 主体：时间线 tab + 四类来源表格 tab
 * - 右侧：详情抽屉，展示原始字段、分类、备注、重要性
 */

type DataCenterTab = 'timeline' | SourceType

const today = new Date().toISOString().slice(0, 10)

const activeTab = shallowRef<DataCenterTab>('timeline')
const loading = shallowRef(false)
const lastError = shallowRef('')
const timeline = shallowRef<TimelineEvent[]>([])
const entries = shallowRef<AnyRecord[]>([])
const detail = shallowRef<AnyRecord | TimelineEvent | null>(null)

const filters = reactive<{
  date: string
  sourceType?: SourceType
  selected?: boolean
  sensitive?: boolean
  keyword: string
}>({
  date: today,
  keyword: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 30,
  total: 0
})

function buildTimelineFilters(): TimelineFilters {
  return {
    source_types: filters.sourceType ? [filters.sourceType] : undefined,
    selected: filters.selected,
    sensitive: filters.sensitive,
    keyword: filters.keyword || undefined,
    sort_order: 'asc',
    limit: 500
  }
}

function buildEntryFilters(): EntryListFilters {
  return {
    selected: filters.selected,
    sensitive: filters.sensitive,
    keyword: filters.keyword || undefined
  }
}

async function loadData(): Promise<void> {
  loading.value = true
  lastError.value = ''

  try {
    if (activeTab.value === 'timeline') {
      const payload = await callTypedBridge('getTimeline', {
        date: filters.date,
        filters: buildTimelineFilters()
      })
      timeline.value = payload.items
      pagination.total = payload.total
      return
    }

    const payload = await callTypedBridge('listEntries', {
      sourceType: activeTab.value,
      date: filters.date,
      filters: buildEntryFilters(),
      page: pagination.page,
      pageSize: pagination.pageSize
    })
    entries.value = payload.items
    pagination.total = payload.total
  } catch (error) {
    lastError.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

async function openDetail(sourceType: SourceType, id: number): Promise<void> {
  detail.value = await callTypedBridge('getEntryDetail', { sourceType, id })
}

async function updateSelection(sourceType: SourceType, id: number, selected: boolean): Promise<void> {
  await callTypedBridge('updateEntrySelection', { sourceType, id, selected })
  await loadData()
}

async function markDeleted(sourceType: SourceType, id: number): Promise<void> {
  await callTypedBridge('markEntryDeleted', { sourceType, id })
  await loadData()
}

async function updateAnnotation(
  sourceType: SourceType,
  id: number,
  payload: EntryAnnotationPayload
): Promise<void> {
  await callTypedBridge('updateEntryAnnotation', { sourceType, id, payload })
  await loadData()
}

onMounted(loadData)

defineExpose({
  activeTab,
  loading,
  lastError,
  filters,
  pagination,
  timeline,
  entries,
  detail,
  loadData,
  openDetail,
  updateSelection,
  markDeleted,
  updateAnnotation
})
</script>

<template>
  <PageLayout title="数据中心" scrollable>
    <section class="page-skeleton" v-loading="loading">
      <!--
        数据状态：
        - activeTab: 'timeline' | SourceType
        - filters: date/sourceType/selected/sensitive/keyword
        - timeline: TimelineEvent[]
        - entries: Record<string, unknown>[]
        - detail: 当前详情记录

        后端接口：
        - getTimeline({ date, filters }) -> { items: TimelineEvent[], total: number }
        - listEntries({ sourceType, date, filters, page, pageSize }) -> PageResult<Record<string, unknown>>
        - getEntryDetail({ sourceType, id }) -> Record<string, unknown> | null
        - updateEntrySelection({ sourceType, id, selected })
        - markEntryDeleted({ sourceType, id })
        - updateEntryAnnotation({ sourceType, id, payload })

        待实现页面区域：
        1. 顶部筛选工具条
        2. 时间线列表
        3. app/browser/clipboard/ai_prompt 表格
        4. 分页
        5. 详情抽屉与备注编辑区
      -->
    </section>
  </PageLayout>
</template>

<style scoped>
.page-skeleton {
  min-height: 100%;
}
</style>
