<template>
  <header class="top-bar flex h-16 shrink-0 items-center justify-between border-b border-slate-200/70 bg-white/55 px-7 backdrop-blur-xl">
    <div class="flex min-w-0 items-center gap-3">
      <span class="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-blue-600 text-sm font-black text-white shadow-lg shadow-blue-500/25">D</span>
      <span class="truncate text-sm font-bold text-slate-700">Daily Reporter - 智能日报生成工具</span>
    </div>
    <div class="flex shrink-0 items-center gap-2">
      <el-date-picker
        v-model="app.currentDate"
        type="date"
        value-format="YYYY-MM-DD"
        :clearable="false"
        size="default"
        style="width: 150px"
      />
      <el-button class="glass-button" :icon="Refresh" @click="app.refreshCollectorStatus">刷新状态</el-button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { useAppStore } from '../stores/app'

const app = useAppStore()
</script>
