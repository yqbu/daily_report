<script setup lang="ts">
/**
 * 顶部栏组件骨架。
 *
 * 作用：
 * - 兼容旧布局 import
 * - 当前主布局使用 Sidebar + PageLayout，是否需要顶部栏由后续界面实现决定
 */
</script>

<template>
  <header class="top-bar">
    <!-- 待实现：全局日期、刷新状态、用户设置入口等。 -->
    <slot />
  </header>
</template>

<style scoped>
.top-bar {
  min-width: 0;
}
</style>
