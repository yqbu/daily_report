<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Files, HomeFilled, Setting, TrendCharts } from '@element-plus/icons-vue'

/**
 * 侧边栏导航组件。
 *
 * 作用：
 * - 只保留四个正式页面入口
 * - 不展示具体业务状态，采集状态等信息应由页面自行决定是否渲染
 */

const route = useRoute()

const items = [
  { key: 'today', to: '/today', label: '今日总览', icon: HomeFilled },
  { key: 'data', to: '/data', label: '数据中心', icon: TrendCharts },
  { key: 'report', to: '/report', label: '日报工作台', icon: Files },
  { key: 'settings', to: '/settings', label: '设置', icon: Setting }
] as const

const activeKey = computed(() => {
  if (route.path === '/data') return 'data'
  if (route.path === '/report' || route.path === '/history' || route.path === '/workbench') return 'report'
  if (route.path === '/settings') return 'settings'
  return 'today'
})
</script>

<template>
  <aside class="sidebar">
    <!-- 品牌区：保留应用框架入口，视觉细节由后续界面实现决定。 -->
    <div class="sidebar__brand">
      <span class="sidebar__brand-mark">DR</span>
      <span class="sidebar__brand-name">Daily Reporter</span>
    </div>

    <!-- 主导航：只保留 MVP 的四个页面。 -->
    <nav class="sidebar__nav">
      <RouterLink
        v-for="item in items"
        :key="item.key"
        :to="item.to"
        class="sidebar__link"
        :class="{ 'sidebar__link--active': activeKey === item.key }"
      >
        <el-icon :size="18">
          <component :is="item.icon" />
        </el-icon>
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  display: flex;
  width: 240px;
  height: 100%;
  min-height: 0;
  flex-shrink: 0;
  flex-direction: column;
  gap: 24px;
  overflow: hidden;
  border-right: 1px solid var(--app-border);
  background: rgba(255, 255, 255, 0.78);
  padding: 24px 18px;
}

.sidebar__brand,
.sidebar__link {
  display: flex;
  min-width: 0;
  align-items: center;
}

.sidebar__brand {
  flex-shrink: 0;
  gap: 12px;
}

.sidebar__brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  place-items: center;
  border-radius: var(--app-radius-control);
  background: var(--app-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 900;
}

.sidebar__brand-name {
  overflow: hidden;
  color: var(--app-text);
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar__nav {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  overflow: auto;
}

.sidebar__link {
  gap: 10px;
  border-radius: var(--app-radius-control);
  color: var(--app-text-secondary);
  font-size: 14px;
  font-weight: 800;
  padding: 12px 14px;
}

.sidebar__link:hover,
.sidebar__link--active {
  background: var(--app-primary-soft);
  color: var(--app-primary);
}
</style>
