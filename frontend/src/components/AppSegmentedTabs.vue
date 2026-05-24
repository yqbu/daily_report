<script setup lang="ts">
/**
 * 分段 tab 组件骨架。
 *
 * 作用：
 * - 保留 tabs/modelValue/change 契约
 * - 具体 tab 样式和交互由后续实现补充
 */

export interface SegmentedTab {
  label: string
  value: string
  icon?: unknown
}

defineProps<{
  modelValue: string
  tabs: SegmentedTab[]
}>()

defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()
</script>

<template>
  <div class="segmented-tabs" role="tablist">
    <!-- 待实现：遍历 tabs，点击后触发 update:modelValue 与 change。 -->
    <slot />
  </div>
</template>

<style scoped>
.segmented-tabs {
  min-width: 0;
}
</style>
