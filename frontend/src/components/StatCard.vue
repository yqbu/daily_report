<template>
  <section class="app-card flex min-w-0 items-center gap-3 p-4">
    <div class="grid h-12 w-12 shrink-0 place-items-center rounded-lg" :class="toneClass">
      <el-icon v-if="iconComponent" :size="25"><component :is="iconComponent" /></el-icon>
      <span v-else class="text-lg font-black">{{ icon }}</span>
    </div>
    <div class="min-w-0">
      <div class="truncate text-sm font-bold text-slate-500">{{ title }}</div>
      <div class="mt-1 flex min-w-0 items-end gap-1">
        <span class="truncate text-[28px] font-black leading-none tracking-tight text-slate-950">{{ value }}</span>
        <span v-if="unit" class="mb-1 shrink-0 text-sm font-bold text-slate-500">{{ unit }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  title: string
  value: string | number
  unit?: string
  icon?: string
  iconComponent?: unknown
  tone?: 'blue' | 'green' | 'purple' | 'orange'
}>()

const toneClass = computed(() => ({
  'bg-blue-50 text-blue-600': !props.tone || props.tone === 'blue',
  'bg-emerald-50 text-emerald-600': props.tone === 'green',
  'bg-violet-50 text-violet-600': props.tone === 'purple',
  'bg-orange-50 text-orange-600': props.tone === 'orange'
}))
</script>
