<script setup lang="ts">
/**
 * 图标徽标组件骨架。
 *
 * 作用：
 * - 保留 icon/label/tone/size 输入
 * - 具体视觉样式由后续实现补充
 */

withDefaults(defineProps<{
  icon?: unknown
  label?: string
  tone?: 'blue' | 'green' | 'purple' | 'orange' | 'gray' | 'red'
  size?: 'sm' | 'md' | 'lg'
}>(), {
  tone: 'blue',
  size: 'md'
})
</script>

<template>
  <span class="icon-badge">
    <!-- 待实现：优先渲染 icon，否则渲染 label。 -->
    <slot />
  </span>
</template>

<style scoped>
.icon-badge {
  display: inline-grid;
  min-width: 0;
  place-items: center;
}
</style>
