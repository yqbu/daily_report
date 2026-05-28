<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { ArrowDown, ArrowUp, CollectionTag, Refresh, Search } from '@element-plus/icons-vue'

import type {
  AppProfileCounts,
  AppProfileListFilters,
  AppProfileSortBy,
  SortDirection
} from '../../api/types'

type ProfileFilterKey = 'all' | 'tracked' | 'excluded' | 'classified' | 'unclassified'

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

const filterOptions = computed<Array<{
  label: string
  value: ProfileFilterKey
  count: number
}>>(() => [
  { label: '全部记录', value: 'all', count: props.counts.all },
  { label: '参与统计', value: 'tracked', count: Math.max(0, props.counts.all - props.counts.excluded) },
  { label: '已排除', value: 'excluded', count: props.counts.excluded },
  { label: '已分类', value: 'classified', count: props.counts.classified },
  { label: '未分类', value: 'unclassified', count: props.counts.unclassified }
])

const selectedFilter = computed<ProfileFilterKey>(() => {
  if (props.filters.classification === 'classified') return 'classified'
  if (props.filters.classification === 'unclassified') return 'unclassified'
  if (props.filters.track_enabled === false) return 'excluded'
  if (props.filters.track_enabled === true) return 'tracked'
  return 'all'
})

const sortBy = computed<AppProfileSortBy>(() => props.filters.sort_by ?? 'last_seen')
const sortDirection = computed<SortDirection>(() => props.filters.sort_direction ?? 'desc')
const directionIcon = computed(() => (sortDirection.value === 'asc' ? ArrowUp : ArrowDown))
const directionLabel = computed(() => (sortDirection.value === 'asc' ? '升序' : '降序'))

const sortOptions: Array<{ label: string; value: AppProfileSortBy }> = [
  { label: '按最后一次启动时间', value: 'last_seen' },
  { label: '按首字母', value: 'name' },
  { label: '按使用时间', value: 'duration' },
  { label: '按调用次数', value: 'session_count' }
]

watch(
  () => props.filters.keyword,
  (value) => {
    keywordDraft.value = value ?? ''
  }
)

function applyKeyword(): void {
  emit('update-filters', { keyword: keywordDraft.value.trim() })
}

function selectFilter(value: ProfileFilterKey): void {
  const patchByValue: Record<ProfileFilterKey, Partial<AppProfileListFilters>> = {
    all: { classification: 'all', track_enabled: null },
    tracked: { classification: 'all', track_enabled: true },
    excluded: { classification: 'all', track_enabled: false },
    classified: { classification: 'classified', track_enabled: null },
    unclassified: { classification: 'unclassified', track_enabled: null }
  }
  emit('update-filters', patchByValue[value])
}

function selectSortBy(value: AppProfileSortBy): void {
  emit('update-filters', { sort_by: value })
}

function toggleSortDirection(): void {
  emit('update-filters', {
    sort_direction: sortDirection.value === 'asc' ? 'desc' : 'asc'
  })
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
        <el-input
          v-model="keywordDraft"
          class="search-input"
          clearable
          placeholder="搜索应用、进程或显示名"
          @clear="applyKeyword"
          @keyup.enter="applyKeyword"
        >
          <!-- <template #prefix>
            <Search class="search-icon" />
          </template> -->
          <template #append>
            <el-button :icon="Search" title="搜索" @click="applyKeyword" />
          </template>
        </el-input>

        <button class="manager-button" type="button" @click="emit('manage-categories')">
          <CollectionTag class="button-icon" />
          <span>管理应用分类</span>
        </button>

        <button class="icon-button" type="button" title="刷新应用列表" :disabled="loading" @click="emit('refresh')">
          <Refresh class="button-icon" />
        </button>
      </div>
    </header>

    <div class="filter-row">
      <div class="filter-tabs" role="tablist" aria-label="应用配置筛选">
        <button
          v-for="option in filterOptions"
          :key="option.value"
          class="filter-tab"
          :class="{ 'filter-tab--active': selectedFilter === option.value }"
          type="button"
          role="tab"
          :aria-selected="selectedFilter === option.value"
          @click="selectFilter(option.value)"
        >
          <span class="filter-label">{{ option.label }}</span>
          <span class="filter-count">{{ option.count }}</span>
        </button>
      </div>

      <div class="sort-tools" aria-label="应用配置排序">
        <el-select :model-value="sortBy" class="sort-select" @change="selectSortBy">
          <el-option
            v-for="option in sortOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button class="direction-button" :icon="directionIcon" @click="toggleSortDirection">
          {{ directionLabel }}
        </el-button>
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
  /* gap: 12px; */
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
  margin-bottom: 12px;
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
  min-width: min(720px, 100%);
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto 34px;
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

.search-icon {
  color: #667085;
}

:deep(.search-input .el-input__wrapper) {
  min-height: 34px;
  border-radius: 8px 0 0 8px;
  background: #f8fafc;
  box-shadow: 0 0 0 1px #dce3ee inset;
}

:deep(.search-input .el-input-group__append) {
  border-radius: 0 8px 8px 0;
  color: #1d4ed8;
  background: #eff6ff;
  box-shadow: 0 0 0 1px #c9dcff inset;
}

:deep(.search-input .el-input__inner) {
  color: #172033;
  font-size: 13px;
}

.filter-row {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(420px, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.filter-tabs {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
  padding: 3px;
  border: 1px solid #e6ebf3;
  border-radius: 8px;
  background: #f8fafc;
}

.filter-tab {
  min-width: 0;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 9px;
  border: 1px solid transparent;
  border-radius: 6px;
  color: #526179;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.filter-tab:hover,
.filter-tab--active {
  color: #172033;
  background: #f2f6ff;
  border-color: #d8e5ff;
  /* box-shadow: 0 6px 14px rgba(15, 23, 42, 0.08); */
}

.filter-tab--active {
  /* color: #2563eb;
  background: #eaf1ff;
  border-color: #c9dcff; */
  background: #eaf1ff;
  border-color: #c9dcff;
  /* box-shadow: inset 3px 0 0 #2563eb; */
}

.filter-label {
  min-width: 0;
  overflow: hidden;
  color: inherit;
  font-size: 12px;
  font-weight: 680;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filter-count {
  min-width: 24px;
  color: inherit;
  font-size: 13px;
  font-weight: 840;
  line-height: 1;
  text-align: right;
}

.sort-tools {
  min-width: 0;
  display: grid;
  grid-template-columns: 188px 82px;
  align-items: center;
  gap: 8px;
}

.sort-select {
  width: 188px;
}

.direction-button {
  width: 82px;
}

:deep(.sort-select .el-select__wrapper),
:deep(.direction-button.el-button) {
  min-height: 40px;
  border-radius: 8px;
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

@media (max-width: 1040px) {
  .filter-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .sort-tools {
    justify-content: end;
  }
}

@media (max-width: 920px) {
  .overview-tools {
    grid-template-columns: minmax(0, 1fr);
  }

  .overview-header {
    align-items: stretch;
    flex-direction: column;
  }
}

@media (max-width: 680px) {
  .filter-tabs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .sort-tools {
    grid-template-columns: minmax(0, 1fr) 82px;
  }

  .sort-select {
    width: 100%;
  }
}
</style>
