<template>
  <div class="app-pagination flex shrink-0 items-center gap-2 border-t border-slate-100 py-3" :class="compact ? 'justify-center px-0' : 'justify-between px-4'">
    <div v-if="!compact" class="text-sm font-medium text-slate-500">
      共 {{ total }} 条
    </div>
    <el-pagination
      background
      :small="compact"
      :layout="compact ? 'sizes, prev, pager, next' : 'sizes, prev, pager, next, jumper'"
      :pager-count="compact ? 3 : 5"
      :page-sizes="[20, 30, 50, 100]"
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      @size-change="emit('size-change', $event)"
      @current-change="emit('current-change', $event)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  page: number
  pageSize: number
  total: number
  compact?: boolean
}>()

const emit = defineEmits<{
  'size-change': [value: number]
  'current-change': [value: number]
}>()
</script>

<style scoped>
.app-pagination :deep(.el-pagination) {
  min-width: 0;
  flex-wrap: nowrap;
}
</style>
