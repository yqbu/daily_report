<script setup lang="ts">
/**
 * Markdown 预览组件骨架。
 *
 * 作用：
 * - 保留 markdown 输入
 * - 当前不渲染具体 Markdown，避免提前固化样式
 * - 后续可以接入安全的 Markdown renderer，注意不要直接渲染未净化 HTML
 */

defineProps<{
  markdown: string
}>()
</script>

<template>
  <article class="markdown-preview">
    <!-- 待实现：Markdown 正文预览。禁止直接对不可信内容使用 v-html。 -->
    <slot />
  </article>
</template>

<style scoped>
.markdown-preview {
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
