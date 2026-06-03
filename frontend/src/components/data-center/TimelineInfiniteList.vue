<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, shallowRef, watch} from 'vue'
import {SortDown, SortUp} from '@element-plus/icons-vue'

import type {TimelineEvent} from '../../api/types'
import TimelineRecordItem from './TimelineRecordItem.vue'

const props = defineProps<{
  items: TimelineEvent[]
  dayCounts: Array<{ date: string; count: number }>
  activeDay: string | null
  loading: boolean
  hasMore: boolean
}>()

const emit = defineEmits<{
  loadMore: []
  selectDay: [day: string, append?: boolean]
  detail: [item: TimelineEvent]
  toggleSensitive: [item: TimelineEvent]
  delete: [item: TimelineEvent]
}>()

const sentinel = shallowRef<HTMLElement | null>(null)
const listEl = shallowRef<HTMLElement | null>(null)
const daySortBy = shallowRef<'date' | 'count'>('date')
const daySortOrder = shallowRef<'asc' | 'desc'>('desc')
const nextBoundaryScrolls = shallowRef(0)
const previousBoundaryScrolls = shallowRef(0)
let observer: IntersectionObserver | null = null
const boundaryThreshold = 6
const dayFormatter = new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  weekday: 'short'
})

const dayGroups = computed(() => {
  return props.dayCounts
      .filter((item) => item.date && item.count > 0)
      .map((item) => ({
        day: item.date,
        label: formatDayLabel(item.date),
        count: item.count
      }))
      .sort((left, right) => {
        const direction = daySortOrder.value === 'asc' ? 1 : -1
        if (daySortBy.value === 'count') {
          return (left.count - right.count || left.day.localeCompare(right.day)) * direction
        }
        return left.day.localeCompare(right.day) * direction
      })
})
const nextDay = computed(() => {
  const index = dayGroups.value.findIndex((group) => group.day === props.activeDay)
  return index >= 0 ? dayGroups.value[index + 1]?.day ?? null : null
})
const previousDay = computed(() => {
  const index = dayGroups.value.findIndex((group) => group.day === props.activeDay)
  return index > 0 ? dayGroups.value[index - 1]?.day ?? null : null
})
const nextBoundaryHint = computed(() => boundaryHint('继续向下加载下一天', nextBoundaryScrolls.value))
const previousBoundaryHint = computed(() => boundaryHint('继续向上加载上一天', previousBoundaryScrolls.value))

function bindObserver(): void {
  observer?.disconnect()
  if (!sentinel.value) {
    return
  }
  observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      if (props.hasMore) {
        emit('loadMore')
      }
    }
  }, {root: listEl.value, rootMargin: '160px'})
  observer.observe(sentinel.value)
}

onMounted(bindObserver)
onBeforeUnmount(() => observer?.disconnect())
watch([sentinel, listEl], bindObserver)
watch(
  () => [props.activeDay, props.hasMore, props.loading],
  () => resetBoundaryScrolls()
)

function formatDayLabel(day: string): string {
  const date = new Date(`${day}T00:00:00`)
  return Number.isNaN(date.getTime()) ? day : dayFormatter.format(date)
}

function selectDay(day: string): void {
  if (day !== props.activeDay) {
    listEl.value?.scrollTo({top: 0})
    emit('selectDay', day, false)
  }
}

function toggleSortOrder(): void {
  daySortOrder.value = daySortOrder.value === 'desc' ? 'asc' : 'desc'
}

function timelineItemStyle(index: number): Record<string, string> {
  return {'--timeline-stagger': `${Math.min(index, 12) * 28}ms`}
}

function handleTimelineWheel(event: WheelEvent): void {
  const list = listEl.value
  if (!list || props.loading) {
    return
  }
  const atTop = list.scrollTop <= 4
  const atBottom = list.scrollTop + list.clientHeight >= list.scrollHeight - 4

  if (event.deltaY > 0 && atBottom && !props.hasMore && nextDay.value) {
    event.preventDefault()
    previousBoundaryScrolls.value = 0
    nextBoundaryScrolls.value += 1
    if (nextBoundaryScrolls.value >= boundaryThreshold) {
      const target = nextDay.value
      resetBoundaryScrolls()
      emit('selectDay', target, false)
    }
    return
  }

  if (event.deltaY < 0 && atTop && previousDay.value) {
    event.preventDefault()
    nextBoundaryScrolls.value = 0
    previousBoundaryScrolls.value += 1
    if (previousBoundaryScrolls.value >= boundaryThreshold) {
      const target = previousDay.value
      resetBoundaryScrolls()
      emit('selectDay', target, false)
    }
    return
  }

  if (event.deltaY > 0) {
    previousBoundaryScrolls.value = 0
  } else if (event.deltaY < 0) {
    nextBoundaryScrolls.value = 0
  }
}

function boundaryHint(base: string, count: number): string {
  if (count <= 0) {
    return base
  }
  return `${base}，再滚动 ${Math.max(boundaryThreshold - count, 0)} 次`
}

function resetBoundaryScrolls(): void {
  nextBoundaryScrolls.value = 0
  previousBoundaryScrolls.value = 0
}
</script>

<template>
  <section class="timeline-panel">
    <div v-if="!items.length && !loading" class="timeline-empty">
      <el-empty description="暂无匹配记录"/>
    </div>
    <div v-else class="timeline-outer">
      <aside v-if="dayGroups.length > 1" class="timeline-jump-list" aria-label="日期快速定位">
        <div class="timeline-jump-toolbar">
          <el-select v-model="daySortBy" size="small" class="timeline-sort-select" aria-label="日期排序方式">
            <el-option label="按日期" value="date"/>
            <el-option label="按数量" value="count"/>
          </el-select>
          <el-button
              class="timeline-sort-order"
              size="small"
              :icon="daySortOrder === 'desc' ? SortDown : SortUp"
              :title="daySortOrder === 'desc' ? '降序' : '升序'"
              @click="toggleSortOrder"
          />
        </div>

        <div class="timeline-jump-scroll">
          <button
              v-for="group in dayGroups"
              :key="group.day"
              class="timeline-jump-button"
              :class="{ 'timeline-jump-button--active': group.day === activeDay }"
              type="button"
              @click="selectDay(group.day)"
          >
            <span>{{ group.label }}</span>
            <strong>{{ group.count }}</strong>
          </button>
        </div>
      </aside>
      <div
        ref="listEl"
        class="timeline-list"
        :class="{ 'timeline-list--empty': !items.length && !loading }"
        @wheel="handleTimelineWheel"
      >
        <button
          v-if="previousDay"
          class="timeline-day-boundary timeline-day-boundary--top"
          type="button"
          @click="$emit('selectDay', previousDay, false)"
        >
          {{ previousBoundaryHint }}
        </button>

        <el-timeline class="timeline-el">
          <TimelineRecordItem
              v-for="(item, index) in items"
              :key="item.event_id"
              :day-anchor="item.start_time.slice(0, 10)"
              :item="item"
              :style="timelineItemStyle(index)"
              @detail="$emit('detail', $event)"
              @toggle-sensitive="$emit('toggleSensitive', $event)"
              @delete="$emit('delete', $event)"
          />
        </el-timeline>

        <div v-if="loading || items.length || nextDay" ref="sentinel" class="timeline-sentinel">
          <el-skeleton v-if="loading" :rows="3" animated/>
          <button
            v-else-if="items.length && !hasMore && nextDay"
            class="timeline-day-boundary timeline-day-boundary--bottom"
            type="button"
            @click="$emit('selectDay', nextDay, false)"
          >
            {{ nextBoundaryHint }}
          </button>
          <span v-else-if="items.length && !hasMore" class="timeline-end">已加载选中日期的全部记录</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.timeline-panel {
  height: 100%;
  min-height: 0;
  min-width: 0;
  padding: 14px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
}

.timeline-outer {
  height: 100%;
  min-height: 0;
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  overflow: hidden;
}

.timeline-list {
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: auto;
  padding-right: 6px;
  scrollbar-gutter: stable;
}

.timeline-list--empty {
  display: grid;
  width: 100%;
  place-items: center;
  align-items: center;
  justify-items: center;
}

.timeline-empty {
  width: 100%;
  height: 100%;
  animation: timeline-empty-rise 300ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.timeline-el {
  padding: 4px 0 0 4px;
}

.timeline-jump-list {
  width: 148px;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 8px;
  overflow: hidden;
}

.timeline-jump-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 30px;
  gap: 6px;
  padding-right: 4px;
}

.timeline-sort-select {
  min-width: 0;
}

.timeline-sort-order {
  width: 30px;
  padding: 0;
}

.timeline-jump-scroll {
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 6px;
  overflow: auto;
  padding-right: 4px;
  scrollbar-gutter: stable;
}

.timeline-jump-button {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #526179;
  background: #ffffff;
  font-size: 12px;
  cursor: pointer;
  animation: timeline-jump-rise 260ms cubic-bezier(0.22, 1, 0.36, 1) both;
  transition: border-color 160ms ease,
  background-color 160ms ease,
  color 160ms ease;
}

.timeline-jump-button:hover {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.timeline-jump-button--active {
  color: #1d4ed8;
  border-color: #93c5fd;
  background: #dbeafe;
  box-shadow: inset 3px 0 0 #2563eb;
}

.timeline-jump-button strong {
  color: #172033;
  font-variant-numeric: tabular-nums;
}

.timeline-sentinel {
  min-height: 58px;
  padding: 10px 0 4px;
  text-align: center;
}

.timeline-end {
  color: #a3adbc;
  font-size: 13px;
}

.timeline-day-boundary {
  width: min(420px, 100%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  padding: 0 16px;
  border: 0;
  color: #98a2b3;
  background: transparent;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.timeline-day-boundary:hover {
  color: #7b8797;
  background: transparent;
}

.timeline-day-boundary--top {
  display: flex;
  margin: 0 auto 12px;
}

.timeline-day-boundary--bottom {
  display: flex;
  margin: 0 auto;
}

@media (max-width: 900px) {
  .timeline-panel {
    grid-template-columns: minmax(0, 1fr);
  }

  .timeline-jump-list {
    width: 100%;
    grid-template-rows: auto auto;
  }

  .timeline-jump-scroll {
    display: flex;
    overflow-x: auto;
  }

  .timeline-jump-button {
    flex: 0 0 auto;
  }
}

@keyframes timeline-jump-rise {
  from {
    opacity: 0;
    transform: translateX(-6px);
  }

  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes timeline-empty-rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .timeline-jump-button,
  .timeline-empty {
    animation: none;
  }
}
</style>
