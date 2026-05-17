<template>
  <div class="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/78 p-1.5 shadow-card">
    <el-date-picker
      :model-value="modelValue"
      type="date"
      value-format="YYYY-MM-DD"
      :clearable="false"
      style="width: 150px"
      @update:model-value="emit('update:modelValue', String($event))"
    />
    <el-button class="primary-gradient" :icon="Refresh" @click="emit('refresh')">刷新</el-button>
  </div>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; refresh: [] }>()
</script>
