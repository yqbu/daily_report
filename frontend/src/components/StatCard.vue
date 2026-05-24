<script setup lang="ts">
/**
 * 旧统计卡片骨架。
 *
 * 作用：
 * - 兼容旧页面 import
 * - 新页面建议统一使用 KpiCard 或自行实现指标组件
 */

defineProps<{
  title: string
  value: string | number
  unit?: string
  icon?: string
  iconComponent?: unknown
  tone?: 'blue' | 'green' | 'purple' | 'orange'
}>()
</script>

<template>
  <section class="stat-card app-card">
    <!-- 待实现：旧统计卡片展示。 -->
    <slot />
  </section>
</template>

<style scoped>
.stat-card {
  min-width: 0;
}
</style>
