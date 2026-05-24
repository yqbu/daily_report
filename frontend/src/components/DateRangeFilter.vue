<script setup lang="ts">
/**
 * 日期范围筛选组件骨架。
 *
 * 作用：
 * - 保留日期范围和快捷范围的双向绑定契约
 * - 具体日期选择器 UI 由后续实现补充
 */

export type DateRangeShortcut = 'today' | 'week' | 'month' | 'custom'

withDefaults(defineProps<{
  modelValue: string[]
  activeShortcut?: DateRangeShortcut
  currentDate?: string
}>(), {
  activeShortcut: 'today',
  currentDate: ''
})

defineEmits<{
  'update:modelValue': [value: string[]]
  'update:activeShortcut': [value: DateRangeShortcut]
  change: [value: string[]]
}>()
</script>

<template>
  <div class="date-range-filter">
    <!-- 待实现：日期范围选择器，以及 today/week/month/custom 快捷按钮。 -->
    <slot />
  </div>
</template>

<style scoped>
.date-range-filter {
  min-width: 0;
}
</style>
