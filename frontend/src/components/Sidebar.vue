<template>
  <aside class="flex w-64 shrink-0 flex-col border-r border-slate-200/80 bg-white/90 px-5 py-6">
    <div class="mb-10">
      <div class="flex items-center gap-3">
        <div class="grid h-10 w-10 place-items-center rounded-2xl bg-blue-600 font-bold text-white shadow-lg shadow-blue-500/25">D</div>
        <div>
          <div class="text-lg font800 font-bold tracking-tight">Daily Reporter</div>
          <div class="text-xs text-blue-600">v0.1.0</div>
        </div>
      </div>
    </div>

    <nav class="space-y-2">
      <RouterLink v-for="item in items" :key="item.path" :to="item.path" class="nav-link">
        <span class="grid h-8 w-8 place-items-center rounded-xl bg-slate-100 text-sm">{{ item.icon }}</span>
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="mt-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
      <div class="flex items-center gap-2 text-sm font-semibold text-emerald-600">
        <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
        采集服务
      </div>
      <p class="mt-2 text-sm leading-6 text-slate-500">数据实时更新，状态可在设置页查看。</p>
      <RouterLink to="/settings" class="mt-3 inline-block text-sm font-semibold text-blue-600">查看设置</RouterLink>
    </div>
  </aside>
</template>

<script setup lang="ts">
const items = [
  { path: '/dashboard', label: '今日总览', icon: '⌂' },
  { path: '/data', label: '数据中心', icon: '▦' },
  { path: '/workbench', label: '日报工作台', icon: '✎' },
  { path: '/history', label: '历史日报', icon: '◷' },
  { path: '/settings', label: '设置', icon: '⚙' }
]
</script>

<style scoped>
.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  border-radius: 14px;
  padding: 10px 12px;
  color: #475569;
  font-weight: 650;
  transition: all .16s ease;
}

.nav-link:hover {
  background: #eff6ff;
  color: #1d4ed8;
}

.nav-link.router-link-active {
  background: #eaf2ff;
  color: #1d4ed8;
}

.nav-link.router-link-active span:first-child {
  background: #2563eb;
  color: #fff;
}
</style>
