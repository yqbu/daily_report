<script setup lang="ts">
/**
 * 状态标签组件骨架。
 *
 * 作用：
 * - 保留 label/tone 输入
 * - 具体标签样式由后续实现补充
 */

withDefaults(defineProps<{
  label: string
  tone?: 'blue' | 'green' | 'orange' | 'red' | 'gray'
}>(), {
  tone: 'blue'
})
</script>

<template>
  <span class="status-badge">
    <!-- 待实现：状态文案、颜色和图标。 -->
    <slot />
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  min-width: 0;
}
</style>
