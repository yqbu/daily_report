<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'

import type { DataCenterFilters, SensitiveFilter } from './types'
import { BROWSER_RECORD_TYPE_OPTIONS, CATEGORY_OPTIONS, SOURCE_OPTIONS } from './types'

const filters = defineModel<DataCenterFilters>({ required: true })

defineEmits<{
  reset: []
}>()

const sensitiveOptions: Array<{ label: string; value: SensitiveFilter }> = [
  { label: '全部', value: 'all' },
  { label: '敏感', value: 'sensitive' },
  { label: '非敏感', value: 'normal' }
]

function updateSourceTypes(value: DataCenterFilters['sourceTypes']): void {
  filters.value.sourceTypes = value
  if (!value.includes('browser')) {
    filters.value.browserRecordType = ''
  }
}

function updateBrowserRecordType(value: string): void {
  filters.value.browserRecordType = value
  if (value) {
    filters.value.sourceTypes = ['browser']
  }
}
</script>

<template>
  <section class="filter-card">
    <div class="filter-grid">
      <label class="filter-field filter-field--source">
        <span class="filter-label">数据来源</span>
        <el-select
          :model-value="filters.sourceTypes"
          multiple
          collapse-tags
          collapse-tags-tooltip
          @update:model-value="updateSourceTypes($event as DataCenterFilters['sourceTypes'])"
        >
          <el-option
            v-for="source in SOURCE_OPTIONS"
            :key="source.value"
            :label="source.label"
            :value="source.value"
          />
        </el-select>
      </label>

      <label class="filter-field filter-field--record-type">
        <span class="filter-label">浏览器类型</span>
        <el-select
          :model-value="filters.browserRecordType"
          :disabled="!filters.sourceTypes.includes('browser')"
          placeholder="全部类型"
          @update:model-value="updateBrowserRecordType(String($event || ''))"
        >
          <el-option
            v-for="item in BROWSER_RECORD_TYPE_OPTIONS"
            :key="item.value || 'all'"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-label">敏感状态</span>
        <el-select v-model="filters.sensitive">
          <el-option
            v-for="item in sensitiveOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-label">分类</span>
        <el-select v-model="filters.categories" multiple collapse-tags collapse-tags-tooltip filterable placeholder="全部分类">
          <el-option v-for="item in CATEGORY_OPTIONS" :key="item" :label="item" :value="item" />
        </el-select>
      </label>

      <label class="filter-field filter-field--keyword">
        <span class="filter-label">关键词</span>
        <el-input v-model="filters.keyword" clearable placeholder="搜索标题、URL、内容或 Prompt">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </label>

      <div class="filter-actions">
        <el-button @click="$emit('reset')">
          重新筛选
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.filter-card {
  container-type: inline-size;
  padding: 12px 14px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
}

.filter-grid {
  display: grid;
  grid-template-columns:
    minmax(124px, 0.92fr)
    minmax(116px, 0.74fr)
    minmax(104px, 0.62fr)
    minmax(116px, 0.72fr)
    minmax(180px, 1.18fr)
    auto;
  gap: 10px;
  align-items: end;
}

.filter-field {
  display: grid;
  min-width: 0;
  gap: 6px;
}

.filter-label {
  color: #526179;
  font-size: 12px;
  font-weight: 720;
}

.filter-field :deep(.el-select),
.filter-field :deep(.el-input) {
  width: 100%;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
}

.filter-actions :deep(.el-button) {
  min-height: 34px;
  margin-left: 0;
  border-radius: 8px;
}

@media (max-width: 1100px) {
  .filter-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .filter-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .filter-actions {
    justify-content: flex-start;
  }
}

@container (max-width: 1100px) {
  .filter-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@container (max-width: 680px) {
  .filter-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .filter-actions {
    justify-content: flex-start;
  }
}
</style>
