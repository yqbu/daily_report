<script setup lang="ts">
import { useTemplateRef, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import Sidebar from '../components/Sidebar.vue'

/**
 * 应用外壳组件。
 *
 * 作用：
 * - 固定承载左侧导航
 * - 提供路由页面渲染区
 * - 路由切换时重置页面滚动位置
 *
 * 这里不放具体业务 UI，业务页面由 RouterView 渲染。
 */

const route = useRoute()
const contentRef = useTemplateRef<HTMLElement>('contentRef')

watch(
  () => route.fullPath,
  () => {
    if (contentRef.value) contentRef.value.scrollTop = 0
  }
)
</script>

<template>
  <div class="app-shell">
    <!-- 左侧导航框架，具体页面内容不要放在 Sidebar 中。 -->
    <Sidebar />
    <main ref="contentRef" class="page-host">
      <!-- 当前路由页面挂载点。 -->
      <RouterView v-slot="{ Component }">
        <component :is="Component" />
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
.page-host {
  min-width: 0;
  min-height: 0;
  flex: 1;
  overflow: hidden;
  padding: 24px;
}
</style>
