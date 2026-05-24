<script setup lang="ts">
/**
 * 页面基础布局组件。
 *
 * 作用：
 * - 提供统一的页面标题、说明、顶部操作区和内容区插槽
 * - 不关心具体页面业务字段
 * - 后续具体布局可以在默认 slot 中自由实现
 */

defineProps<{
  title: string
  subtitle?: string
  scrollable?: boolean
}>()
</script>

<template>
  <section class="page-layout">
    <header class="page-header">
      <!-- 页面标题区域：只保留页面级框架，不承载业务控件。 -->
      <div class="page-title">
        <h1>{{ title }}</h1>
        <p v-if="subtitle">
          {{ subtitle }}
        </p>
      </div>
      <!-- 页面操作区：日期选择、刷新、保存、生成等按钮可以从页面传入。 -->
      <div v-if="$slots.actions" class="page-actions">
        <slot name="actions" />
      </div>
    </header>
    <!-- 页面主体：具体 UI 由各页面自行实现。 -->
    <div class="page-content" :class="{ 'page-content--scroll': scrollable }">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.page-layout {
  display: flex;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.page-header {
  display: flex;
  min-width: 0;
  min-height: 58px;
  flex-shrink: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.page-title {
  min-width: 0;
}

.page-title h1 {
  margin: 0;
  overflow: hidden;
  color: var(--app-text);
  font-size: 30px;
  font-weight: 900;
  letter-spacing: 0;
  line-height: 1.18;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-title p {
  margin: 8px 0 0;
  overflow: hidden;
  color: var(--app-text-secondary);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-actions {
  display: flex;
  max-width: 58%;
  min-width: 0;
  flex-shrink: 0;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.page-content {
  min-width: 0;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.page-content--scroll {
  overflow: auto;
}

@media (max-width: 960px) {
  .page-header {
    min-height: auto;
    flex-wrap: wrap;
  }

  .page-actions {
    width: 100%;
    max-width: none;
    justify-content: flex-start;
  }
}
</style>
