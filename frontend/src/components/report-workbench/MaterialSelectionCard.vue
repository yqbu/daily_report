<script setup lang="ts">
import { computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { CircleCheck, Filter, Lock, Memo, Search } from '@element-plus/icons-vue'

import MaterialCandidateList from './MaterialCandidateList.vue'
import type { MaterialCandidate, MaterialFilters, MaterialSummary } from '../../types/reportWorkbench'
import { categoryOptions } from '../../stores/reportWorkbench'

const props = defineProps<{
  filters: MaterialFilters
  summary: MaterialSummary
  items: MaterialCandidate[]
  loading: boolean
  hasMore: boolean
  showHeader?: boolean
}>()

const emit = defineEmits<{
  'update:filters': [filters: MaterialFilters]
  refresh: []
  toggle: [item: MaterialCandidate, selected: boolean]
  detail: [item: MaterialCandidate]
  loadMore: []
}>()

const sourceOptions = [
  { label: '全部', value: '' },
  { label: '前台应用', value: 'app' },
  { label: '浏览器历史', value: 'browser' },
  { label: '剪切板', value: 'clipboard' },
  { label: 'AI 提问', value: 'ai_prompt' }
] as const

const sensitiveOptions = [
  { label: '仅非敏感', value: 'non_sensitive' },
  { label: '仅敏感', value: 'sensitive' },
  { label: '全部', value: 'all' }
] as const

const sourceValue = computed({
  get: () => props.filters.sourceTypes[0] ?? '',
  set: (value: string) => updateFilters({ sourceTypes: value ? [value as MaterialFilters['sourceTypes'][number]] : [] })
})

async function toggleMaterial(item: MaterialCandidate, selected: boolean): Promise<void> {
  if (selected && item.is_sensitive) {
    await ElMessageBox.confirm('该素材被标记为敏感，确认加入本次日报素材吗？', '敏感素材确认', {
      type: 'warning',
      confirmButtonText: '确认加入',
      cancelButtonText: '取消'
    })
  }
  emit('toggle', item, selected)
}

function updateFilters(patch: Partial<MaterialFilters>): void {
  emit('update:filters', { ...props.filters, ...patch })
}
</script>

<template>
  <section class="workbench-card material-card">
    <header v-if="showHeader !== false" class="card-header">
      <div>
        <h2 class="card-title">素材选择</h2>
        <p class="card-subtitle">从四类本地记录中筛选本次日报素材</p>
      </div>
      <el-tag disable-transitions type="success" effect="light">{{ summary.selected_count }} 已选</el-tag>
    </header>

    <div class="summary-grid">
      <div class="summary-item">
        <Memo />
        <span>素材总数</span>
        <strong>{{ summary.total_count.toLocaleString() }}</strong>
      </div>
      <div class="summary-item summary-item--success">
        <CircleCheck />
        <span>已选素材</span>
        <strong>{{ summary.selected_count.toLocaleString() }}</strong>
      </div>
      <div class="summary-item summary-item--danger">
        <Lock />
        <span>敏感已排除</span>
        <strong>{{ summary.sensitive_excluded_count.toLocaleString() }}</strong>
      </div>
      <div class="summary-item">
        <Filter />
        <span>待确认素材</span>
        <strong>{{ summary.pending_count.toLocaleString() }}</strong>
      </div>
      <div class="summary-item">
        <Search />
        <span>预计字数</span>
        <strong>{{ summary.estimated_prompt_chars.toLocaleString() }}</strong>
      </div>
    </div>

    <div class="filter-grid">
      <el-select v-model="sourceValue" placeholder="数据来源">
        <el-option v-for="item in sourceOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select
        :model-value="filters.category ?? ''"
        placeholder="全部分类"
        @update:model-value="updateFilters({ category: String($event) || null })"
      >
        <el-option label="全部分类" value="" />
        <el-option v-for="item in categoryOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select
        :model-value="filters.sensitive"
        placeholder="敏感状态"
        @update:model-value="updateFilters({ sensitive: $event as MaterialFilters['sensitive'] })"
      >
        <el-option v-for="item in sensitiveOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input
        :model-value="filters.keyword"
        clearable
        placeholder="搜索标题、摘要、URL、Prompt"
        @update:model-value="updateFilters({ keyword: String($event) })"
      />
    </div>

    <div v-loading="loading && !items.length" class="material-scroll">
      <MaterialCandidateList
        :items="items"
        :loading="loading"
        :has-more="hasMore"
        @toggle="toggleMaterial"
        @detail="emit('detail', $event)"
        @load-more="emit('loadMore')"
      />
    </div>
  </section>
</template>

<style scoped>
.material-card {
  container-type: inline-size;
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  overflow: hidden;
}

.card-header {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.card-header > div {
  min-width: 0;
}

.card-title {
  margin: 0;
  color: #172033;
  font-size: 16px;
  font-weight: 840;
}

.card-subtitle {
  margin: 5px 0 0;
  color: #667085;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 90px), 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.summary-item {
  min-width: 0;
  display: grid;
  gap: 4px;
  padding: 10px;
  border: 1px solid #e5edf7;
  border-radius: 10px;
  background: #f8fbff;
  color: #667085;
  font-size: 12px;
}

.summary-item svg {
  width: 15px;
  height: 15px;
  color: #2563eb;
}

.summary-item strong {
  color: #172033;
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.summary-item--success svg {
  color: #16a34a;
}

.summary-item--danger svg {
  color: #ef4444;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 128px), 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.filter-grid :deep(.el-select),
.filter-grid :deep(.el-input) {
  min-width: 0;
  width: 100%;
}

.material-scroll {
  min-height: 0;
  overflow: hidden;
}

@container (max-width: 520px) {
  .card-header {
    align-items: stretch;
    flex-direction: column;
  }

  .card-header :deep(.el-tag) {
    align-self: flex-start;
  }
}

@media (max-width: 900px) {
  .material-card {
    height: auto;
  }

  .material-scroll {
    max-height: clamp(260px, 48vh, 420px);
  }

  .summary-grid {
    grid-template-columns: repeat(3, minmax(90px, 1fr));
  }

  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .summary-grid,
  .filter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@container (max-width: 520px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@container (max-width: 900px) {
  .material-card {
    height: auto;
  }

  .material-scroll {
    max-height: clamp(260px, 48vh, 420px);
  }
}

@container (max-width: 340px) {
  .summary-grid,
  .filter-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
