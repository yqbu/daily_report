<template>
  <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold" :class="toneClass">
    <span class="mr-1.5 h-1.5 w-1.5 rounded-full bg-current"></span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ label: string; tone?: 'blue' | 'green' | 'orange' | 'red' | 'gray' }>()
const toneClass = computed(() => ({
  'bg-blue-50 text-blue-600': !props.tone || props.tone === 'blue',
  'bg-emerald-50 text-emerald-600': props.tone === 'green',
  'bg-orange-50 text-orange-600': props.tone === 'orange',
  'bg-red-50 text-red-600': props.tone === 'red',
  'bg-slate-100 text-slate-600': props.tone === 'gray'
}))
</script>
