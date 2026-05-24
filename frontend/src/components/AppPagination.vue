<script setup lang="ts">
/**
 * 分页组件骨架。
 *
 * 作用：
 * - 保留 page/pageSize/total 输入
 * - 保留页码和页大小变更事件
 * - 具体分页控件由后续实现补充
 */

withDefaults(defineProps<{
  page: number
  pageSize: number
  total: number
  compact?: boolean
}>(), {
  compact: false
})

defineEmits<{
  'size-change': [value: number]
  'current-change': [value: number]
}>()
</script>

<template>
  <div class="app-pagination">
    <!-- 待实现：分页总数、页大小选择、上一页/下一页/跳页控件。 -->
    <slot />
  </div>
</template>

<style scoped>
.app-pagination {
  min-width: 0;
}
</style>
