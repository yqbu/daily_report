<template>
  <header class="flex h-20 shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/70 px-8 backdrop-blur">
    <div>
      <h1 class="text-2xl font-extrabold tracking-tight">{{ title }}</h1>
      <p class="mt-1 text-sm text-slate-500">PySide6 + QWebEngine + Vue Web UI</p>
    </div>
    <div class="flex items-center gap-3">
      <input v-model="app.currentDate" type="date" class="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-blue-500" />
      <button class="h-10 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-600 hover:bg-slate-50" @click="app.refreshCollectorStatus">
        刷新状态
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../stores/app'

const route = useRoute()
const app = useAppStore()
const title = computed(() => String(route.meta.title || 'Daily Reporter'))
</script>
