<template>
  <section class="card p-5">
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="section-title">{{ title }}</h2>
        <p v-if="subtitle" class="mt-1 text-sm text-slate-500">{{ subtitle }}</p>
      </div>
      <slot name="actions" />
    </div>
    <slot />
  </section>
</template>

<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>
