<template>
  <aside class="sidebar flex h-full w-[240px] shrink-0 flex-col border-r border-slate-200/75 bg-white/82 px-5 py-6 backdrop-blur-xl">
    <div class="mb-9">
      <div class="text-xl font-black tracking-tight text-slate-950">Daily Reporter</div>
      <div class="mt-2 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-bold text-blue-600">v0.1.0</div>
    </div>

    <nav class="space-y-2">
      <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="nav-link">
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="mt-auto rounded-lg border border-slate-200 bg-white/88 p-4 shadow-card">
      <div class="flex items-center gap-2 text-sm font-bold text-emerald-600">
        <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
        采集服务：运行中
      </div>
      <p class="mt-3 text-sm leading-6 text-slate-500">采集状态正常，数据实时更新。</p>
      <RouterLink to="/settings" class="mt-3 inline-block text-sm font-bold text-blue-600">查看运行设置</RouterLink>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { DataLine, Document, Files, HomeFilled, Setting } from '@element-plus/icons-vue'

const items = [
  { path: '/dashboard', label: '今日总览', icon: HomeFilled },
  { path: '/data', label: '数据中心', icon: DataLine },
  { path: '/workbench', label: '日报工作台', icon: Files },
  { path: '/history', label: '历史日报', icon: Document },
  { path: '/settings', label: '设置', icon: Setting }
]
</script>

<style scoped>
.sidebar {
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.4);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 8px;
  padding: 12px 14px;
  color: #475569;
  font-weight: 760;
  transition: all .16s ease;
}

.nav-link:hover {
  background: #eff6ff;
  color: #1d4ed8;
}

.nav-link.router-link-active {
  background: linear-gradient(135deg, #eaf2ff 0%, #eef5ff 100%);
  color: #1d4ed8;
}
</style>
