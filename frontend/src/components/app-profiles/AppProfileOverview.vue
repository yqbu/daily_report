<script setup lang="ts">
import {computed, shallowRef, watch} from 'vue'
import {CollectionTag, Refresh, Search} from '@element-plus/icons-vue'

import type {
  AppProfileClassificationFilter,
  AppProfileCounts,
  AppProfileListFilters
} from '../../api/types'

type TrackFilter = 'all' | 'tracked' | 'excluded'

const props = defineProps<{
  counts: AppProfileCounts
  filters: AppProfileListFilters
  loading: boolean
  message?: string
  error?: string
}>()

const emit = defineEmits<{
  refresh: []
  'manage-categories': []
  'update-filters': [patch: Partial<AppProfileListFilters>]
}>()

const keywordDraft = shallowRef(props.filters.keyword ?? '')

const classificationOptions = computed<Array<{
  label: string
  value: AppProfileClassificationFilter
  count: number
}>>(() => [
  {label: '全部', value: 'all', count: props.counts.all},
  {label: '已分类', value: 'classified', count: props.counts.classified},
  {label: '未分类', value: 'unclassified', count: props.counts.unclassified}
])

const trackFilter = computed<TrackFilter>(() => {
  if (props.filters.track_enabled === false) return 'excluded'
  if (props.filters.track_enabled === true) return 'tracked'
  return 'all'
})

const trackOptions: Array<{ label: string; value: TrackFilter }> = [
  {label: '全部记录', value: 'all'},
  {label: '参与统计', value: 'tracked'},
  {label: '已排除', value: 'excluded'}
]

watch(
    () => props.filters.keyword,
    (value) => {
      keywordDraft.value = value ?? ''
    }
)

function applyKeyword(): void {
  emit('update-filters', {keyword: keywordDraft.value.trim()})
}

function selectClassification(value: AppProfileClassificationFilter): void {
  emit('update-filters', {classification: value})
}

function selectTrackFilter(value: TrackFilter): void {
  const nextValue = value === 'all' ? null : value === 'tracked'
  emit('update-filters', {track_enabled: nextValue})
}
</script>

<template>
  <section class="overview-panel">
    <header class="overview-header">
      <div class="overview-heading">
        <p class="overview-kicker">应用规则</p>
        <h2 class="overview-title">配置概览</h2>
      </div>

      <div class="overview-tools">
        <form class="search-form" role="search" @submit.prevent="applyKeyword">
          <Search class="search-icon"/>
          <input
              v-model="keywordDraft"
              class="search-input"
              type="search"
              placeholder="搜索应用、进程或显示名"
              autocomplete="off"
          />
          <button class="search-button" type="submit">搜索</button>
        </form>

        <button class="manager-button" type="button" @click="emit('manage-categories')">
          <CollectionTag class="button-icon"/>
          <span>管理应用分类</span>
        </button>

        <button class="icon-button" type="button" title="刷新应用列表" :disabled="loading" @click="emit('refresh')">
          <Refresh class="button-icon"/>
        </button>
      </div>
    </header>

    <div class="filter-row">
      <div class="track-tabs" role="tablist" aria-label="统计状态筛选">
        <button
            v-for="option in trackOptions"
            :key="option.value"
            class="track-tab"
            :class="{ 'track-tab--active': trackFilter === option.value }"
            type="button"
            role="tab"
            :aria-selected="trackFilter === option.value"
            @click="selectTrackFilter(option.value)"
        >
          {{ option.label }}
        </button>
      </div>

      <div class="summary-grid" aria-label="应用配置统计">
        <button
            v-for="option in classificationOptions"
            :key="option.value"
            class="summary-item"
            :class="{ 'summary-item--active': filters.classification === option.value }"
            type="button"
            @click="selectClassification(option.value)"
        >
          <span class="summary-label">{{ option.label }}</span>
          <span class="summary-count">{{ option.count }}</span>
        </button>
      </div>
    </div>

    <p v-if="error" class="status-line status-line--error">{{ error }}</p>
    <p v-else-if="message" class="status-line status-line--success">{{ message }}</p>
  </section>
</template>

<style scoped>
.overview-panel {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto;
  gap: 12px;
  padding: 16px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.overview-header {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.overview-heading {
  min-width: 0;
}

.overview-kicker,
.overview-title,
.status-line {
  margin: 0;
}

.overview-kicker {
  color: #2563eb;
  font-size: 12px;
  font-weight: 780;
  line-height: 1.2;
}

.overview-title {
  margin-top: 4px;
  color: #172033;
  font-size: 19px;
  font-weight: 820;
  line-height: 1.2;
}

.overview-tools {
  min-width: min(680px, 100%);
  display: grid;
  grid-template-columns: minmax(220px, 1fr) auto 34px;
  align-items: center;
  gap: 8px;
}

.manager-button {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border: 1px solid #c9dcff;
  border-radius: 8px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 13px;
  font-weight: 720;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
}

.manager-button:hover {
  border-color: #93c5fd;
  background: #dbeafe;
}

.icon-button {
  width: 34px;
  height: 34px;
  display: grid;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #526179;
  background: #f8fafc;
  cursor: pointer;
}

.icon-button:hover {
  color: #2563eb;
  border-color: #c9dcff;
  background: #eff6ff;
}

.icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.56;
}

.button-icon,
.search-icon {
  width: 16px;
  height: 16px;
}

.search-form {
  height: 34px;
  min-width: 0;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  padding: 0 8px 0 12px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #f8fafc;
}

.search-icon {
  color: #667085;
}

.search-input {
  min-width: 0;
  width: 100%;
  border: 0;
  outline: 0;
  color: #172033;
  background: transparent;
  font-size: 13px;
}

.search-input::placeholder {
  color: #98a2b3;
}

.search-button {
  height: 26px;
  padding: 0 10px;
  border: 1px solid #c9dcff;
  border-radius: 7px;
  color: #1d4ed8;
  background: #eff6ff;
  font-size: 12px;
  font-weight: 720;
  cursor: pointer;
}

.filter-row {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(260px, 0.78fr) minmax(360px, 1fr);
  gap: 8px;
}

.summary-grid {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  padding: 4px;
  border: 1px solid #e6ebf3;
  border-radius: 8px;
  background: #f8fafc;
}

.summary-item,
.track-tab {
  min-width: 0;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 9px;
  border: 0;
  border-radius: 6px;
  color: #526179;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.summary-item:hover,
.summary-item--active,
.track-tab:hover,
.track-tab--active {
  color: #172033;
  background: #ffffff;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08);
}

.summary-count {
  min-width: 24px;
  color: inherit;
  font-size: 13px;
  font-weight: 840;
  line-height: 1;
  text-align: right;
}

.summary-label {
  overflow: hidden;
  color: inherit;
  font-size: 12px;
  font-weight: 680;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-tabs {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  padding: 4px;
  border: 1px solid #e6ebf3;
  border-radius: 8px;
  background: #f8fafc;
}

.status-line {
  overflow: hidden;
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-line--error {
  color: #b42318;
}

.status-line--success {
  color: #047857;
}

@media (max-width: 920px) {
  .overview-tools,
  .filter-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .overview-header {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
