<script setup lang="ts">
import type { TimelineEvent } from '../../api/types'
import CategoryTag from './CategoryTag.vue'
import RecordActionButtons from './RecordActionButtons.vue'
import SensitiveTag from './SensitiveTag.vue'
import SourceBadge from './SourceBadge.vue'
import { browserRecordTypeLabel, formatDateTime } from './types'

const props = defineProps<{
  item: TimelineEvent
  dayAnchor?: string
}>()

defineEmits<{
  detail: [item: TimelineEvent]
  toggleSensitive: [item: TimelineEvent]
  delete: [item: TimelineEvent]
}>()

function metaText(): string {
  const parts = []
  if (props.item.end_time) {
    parts.push(`${formatDateTime(props.item.start_time).slice(11)} - ${formatDateTime(props.item.end_time).slice(11)}`)
  } else {
    parts.push(formatDateTime(props.item.start_time))
  }
  return parts.join(' / ')
}

function timeText(): string {
  return formatDateTime(props.item.start_time).slice(11, 16)
}

function secondaryText(): string {
  return props.item.subtitle || props.item.content_preview || '暂无补充信息'
}
</script>

<template>
  <el-timeline-item
    class="timeline-item"
    :data-day-anchor="dayAnchor"
    :timestamp="metaText()"
    placement="top"
  >
    <template #dot>
      <span class="timeline-dot"></span>
    </template>

    <el-card class="timeline-main" shadow="never" @click="$emit('detail', item)">
      <SourceBadge class="timeline-source" :source-type="item.source_type" icon-only />

      <div class="timeline-title-block">
        <h3 class="timeline-title">{{ item.title }}</h3>
        <p class="timeline-preview">
          {{ item.content_preview || secondaryText() }}
        </p>
      </div>

      <div class="timeline-context">
        <span v-if="(item.item_count || 1) > 1">{{ item.item_count }} 条聚合记录</span>
        <span v-else>{{ secondaryText() }}</span>
      </div>

      <div class="timeline-tags">
        <span v-if="item.record_type" class="record-type-tag">{{ browserRecordTypeLabel(item.record_type) }}</span>
        <CategoryTag :category="item.category" />
        <SensitiveTag :sensitive="item.is_sensitive" />
      </div>

      <RecordActionButtons
        class="timeline-actions"
        :sensitive="item.is_sensitive"
        :show-detail="false"
        @toggle-sensitive="$emit('toggleSensitive', item)"
        @delete="$emit('delete', item)"
      />
    </el-card>
  </el-timeline-item>
</template>

<style scoped>
.timeline-item :deep(.el-timeline-item__timestamp) {
  color: #7b8797;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.timeline-dot {
  display: block;
  width: 10px;
  height: 10px;
  border: 2px solid #86b7ff;
  border-radius: 999px;
  background: #ffffff;
}

.timeline-main {
  min-width: 0;
  min-height: 72px;
  cursor: pointer;
  animation: timeline-card-zip 340ms cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--timeline-stagger, 0ms);
}

.timeline-main :deep(.el-card__body) {
  display: grid;
  grid-template-columns: auto minmax(0, 1.45fr) minmax(120px, 0.65fr) auto auto;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
}

.timeline-main {
  border: 1px solid #dfe8f5;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(15, 31, 61, 0.04);
  transition:
    border-color 160ms ease,
    background-color 160ms ease;
}

.timeline-main:hover {
  border-color: #b9cff6;
  background: #fbfdff;
}

.timeline-source {
  align-self: center;
}

.timeline-title-block {
  min-width: 0;
}

.timeline-title {
  margin: 0;
  overflow: hidden;
  color: #1b2638;
  font-size: 13px;
  font-weight: 820;
  line-height: 1.35;
  letter-spacing: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-preview {
  margin: 4px 0 0;
  overflow: hidden;
  color: #536174;
  font-size: 12px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-context {
  min-width: 0;
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-tags {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.record-type-tag {
  height: 22px;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 12px;
  font-weight: 720;
  white-space: nowrap;
}

.timeline-actions {
  justify-self: end;
}

@media (max-width: 980px) {
  .timeline-main :deep(.el-card__body) {
    grid-template-columns: auto minmax(0, 1fr) auto;
  }

  .timeline-context {
    display: none;
  }

  .timeline-tags {
    display: none;
  }
}

@media (max-width: 680px) {
  .timeline-main :deep(.el-card__body) {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .timeline-source {
    display: none;
  }
}

@keyframes timeline-card-zip {
  from {
    opacity: 0;
    transform: translateX(14px);
  }

  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .timeline-main {
    animation: none;
  }
}
</style>
