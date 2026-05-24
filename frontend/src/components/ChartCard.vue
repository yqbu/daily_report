<script setup lang="ts">
/**
 * 图表容器骨架。
 *
 * 作用：
 * - 为 ECharts 或其它图表预留标题、操作区和内容插槽
 * - 不内置任何具体图表实现
 */

defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <section class="chart-card app-card">
    <!-- 标题区和操作区可按需要重做。 -->
    <header class="chart-card__header">
      <div class="chart-card__title">
        <h2>{{ title }}</h2>
        <p v-if="subtitle">
          {{ subtitle }}
        </p>
      </div>
      <slot name="actions" />
    </header>

    <!-- 图表挂载区：后续可以放 ECharts canvas/svg 容器。 -->
    <div class="chart-card__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.chart-card {
  min-width: 0;
  min-height: 0;
}

.chart-card__header {
  display: flex;
  min-width: 0;
  justify-content: space-between;
  gap: 12px;
}

.chart-card__title {
  min-width: 0;
}

.chart-card__title h2,
.chart-card__title p {
  margin: 0;
}

.chart-card__body {
  min-width: 0;
  min-height: 0;
}
</style>
