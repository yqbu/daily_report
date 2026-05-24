<script setup lang="ts">
/**
 * 空状态组件骨架。
 *
 * 作用：
 * - 保留 title/description/compact 输入
 * - 具体空状态图形和文案样式由后续实现补充
 */

withDefaults(defineProps<{
  title: string
  description?: string
  compact?: boolean
}>(), {
  compact: false
})
</script>

<template>
  <div class="empty-state" :class="{ 'empty-state--compact': compact }">
    <!-- 待实现：空状态图标、标题、说明、操作按钮。 -->
    <slot />
  </div>
</template>

<style scoped>
.empty-state {
  min-width: 0;
  min-height: 120px;
}

.empty-state--compact {
  min-height: 80px;
}
</style>
