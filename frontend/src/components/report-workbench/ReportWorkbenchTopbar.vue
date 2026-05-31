<script setup lang="ts">
import { Refresh, Select } from '@element-plus/icons-vue'

defineProps<{
  selectedDate: string
  loading: boolean
  generating: boolean
  canGenerate: boolean
}>()

const emit = defineEmits<{
  'update:selectedDate': [value: string]
  refresh: []
  generate: []
}>()
</script>

<template>
  <header class="report-workbench-topbar">
    <div class="topbar-title">
      <span class="workspace-label">Daily Report</span>
      <h1 class="page-title">日报工作台</h1>
    </div>

    <div class="topbar-actions">
      <el-date-picker
        :model-value="selectedDate"
        type="date"
        value-format="YYYY-MM-DD"
        format="YYYY-MM-DD"
        :clearable="false"
        class="date-picker"
        @update:model-value="emit('update:selectedDate', String($event))"
      />
      <el-button :icon="Refresh" :loading="loading" @click="emit('refresh')">
        刷新素材
      </el-button>
      <el-button
        :icon="Select"
        type="primary"
        :loading="generating"
        :disabled="!canGenerate"
        @click="emit('generate')"
      >
        生成日报
      </el-button>
    </div>
  </header>
</template>

<style scoped>
.report-workbench-topbar {
  flex: 0 0 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
  padding: 14px 18px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
}

.topbar-title {
  min-width: 0;
}

.workspace-label {
  display: block;
  color: #667085;
  font-size: 12px;
  line-height: 1.2;
}

.page-title {
  margin: 4px 0 0;
  color: #172033;
  font-size: 22px;
  font-weight: 720;
  line-height: 1.15;
  letter-spacing: 0;
}

.topbar-actions {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.date-picker {
  width: 164px;
}

@media (max-width: 760px) {
  .report-workbench-topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .topbar-actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
