<template>
  <el-empty :description="title" class="h-full min-h-44">
    <template v-if="description" #default>
      <p class="mx-auto max-w-md text-sm leading-6 text-slate-500">{{ description }}</p>
    </template>
  </el-empty>
</template>

<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>
