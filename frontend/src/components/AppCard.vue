<script setup lang="ts">
/**
 * 通用卡片壳层。
 *
 * 作用：
 * - 为后续页面布局提供一个可选容器
 * - 只保留标题、操作区和默认内容插槽
 * - 不包含任何具体业务展示
 */

defineProps<{
  title?: string
  subtitle?: string
  bodyClass?: string
}>()
</script>

<template>
  <section class="app-card app-card-wrapper">
    <!-- header slot 可完全接管标题区；actions slot 可放刷新、保存等操作。 -->
    <header v-if="title || subtitle || $slots.actions || $slots.header" class="app-card-header">
      <slot name="header">
        <div class="app-card-title">
          <h2 v-if="title">
            {{ title }}
          </h2>
          <p v-if="subtitle">
            {{ subtitle }}
          </p>
        </div>
        <div v-if="$slots.actions" class="app-card-actions">
          <slot name="actions" />
        </div>
      </slot>
    </header>

    <!-- 默认插槽：具体页面内容由调用方实现。 -->
    <div class="app-card-body" :class="bodyClass">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.app-card-wrapper {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
}

.app-card-header {
  display: flex;
  min-width: 0;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 18px 20px 0;
}

.app-card-title {
  min-width: 0;
}

.app-card-title h2,
.app-card-title p {
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-card-title h2 {
  color: var(--app-text);
  font-size: 17px;
  font-weight: 850;
}

.app-card-title p {
  margin-top: 5px;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.app-card-actions {
  display: flex;
  min-width: 0;
  flex-shrink: 0;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.app-card-body {
  min-width: 0;
  min-height: 0;
  flex: 1;
  overflow: hidden;
  padding: 18px 20px 20px;
}
</style>
