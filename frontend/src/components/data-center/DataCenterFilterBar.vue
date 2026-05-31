<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'

import type { DataCenterFilters, SensitiveFilter } from './types'
import { CATEGORY_OPTIONS, SOURCE_OPTIONS } from './types'

const filters = defineModel<DataCenterFilters>({ required: true })

defineEmits<{
  reset: []
}>()

const sensitiveOptions: Array<{ label: string; value: SensitiveFilter }> = [
  { label: '全部', value: 'all' },
  { label: '敏感', value: 'sensitive' },
  { label: '非敏感', value: 'normal' }
]
</script>

<template>
  <section class="filter-card">
    <div class="filter-grid">
      <label class="filter-field filter-field--source">
        <span class="filter-label">数据来源</span>
        <el-select v-model="filters.sourceTypes" multiple collapse-tags collapse-tags-tooltip>
          <el-option
            v-for="source in SOURCE_OPTIONS"
            :key="source.value"
            :label="source.label"
            :value="source.value"
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
  padding: 14px 16px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
}

.filter-grid {
  display: grid;
  grid-template-columns: minmax(220px, 1.25fr) 140px 150px minmax(240px, 1.5fr) auto;
  gap: 12px;
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

@media (max-width: 1180px) {
  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
</style>
