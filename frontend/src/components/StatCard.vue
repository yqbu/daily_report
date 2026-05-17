<template>
  <section class="card flex items-center gap-4 p-5">
    <div class="grid h-14 w-14 place-items-center rounded-2xl" :class="toneClass">
      <span class="text-xl font-black">{{ icon }}</span>
    </div>
    <div>
      <div class="text-sm font-semibold text-slate-500">{{ title }}</div>
      <div class="mt-1 flex items-end gap-1">
        <span class="text-3xl font-black tracking-tight text-slate-950">{{ value }}</span>
        <span v-if="unit" class="mb-1 text-sm font-semibold text-slate-500">{{ unit }}</span>
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
  tone?: 'blue' | 'green' | 'purple' | 'orange'
}>()

const toneClass = computed(() => ({
  'bg-blue-50 text-blue-600': !props.tone || props.tone === 'blue',
  'bg-emerald-50 text-emerald-600': props.tone === 'green',
  'bg-violet-50 text-violet-600': props.tone === 'purple',
  'bg-orange-50 text-orange-600': props.tone === 'orange'
}))
</script>
