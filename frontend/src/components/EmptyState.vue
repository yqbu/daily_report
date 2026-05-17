<template>
  <div class="grid min-h-48 place-items-center p-8 text-center">
    <div>
      <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-slate-100 text-2xl text-slate-400">∅</div>
      <h3 class="mt-4 font-bold text-slate-800">{{ title }}</h3>
      <p v-if="description" class="mt-1 text-sm text-slate-500">{{ description }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>
