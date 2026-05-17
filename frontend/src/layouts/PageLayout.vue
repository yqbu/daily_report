<template>
  <section class="page-layout flex h-full min-h-0 min-w-0 flex-col overflow-hidden">
    <header class="page-header flex shrink-0 items-start justify-between gap-4">
      <div class="min-w-0">
        <h1 class="truncate text-[28px] font-black tracking-tight text-slate-950">{{ title }}</h1>
        <p v-if="subtitle" class="mt-1.5 truncate text-sm text-slate-500">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
      </div>
    </header>
    <div class="page-content min-h-0 min-w-0 flex-1 overflow-hidden">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<style scoped>
.page-layout {
  gap: 14px;
}

.page-header {
  min-height: 50px;
}
</style>
