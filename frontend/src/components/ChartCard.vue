<template>
  <section class="app-card flex min-h-0 min-w-0 flex-col p-4">
    <div class="mb-3 flex shrink-0 items-center justify-between gap-3">
      <div class="min-w-0">
        <h2 class="section-title truncate">{{ title }}</h2>
        <p v-if="subtitle" class="mt-1 truncate text-sm text-slate-500">{{ subtitle }}</p>
      </div>
      <slot name="actions" />
    </div>
    <div class="min-h-0 min-w-0 flex-1 overflow-hidden">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>
