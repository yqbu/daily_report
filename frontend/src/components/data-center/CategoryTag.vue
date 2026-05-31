<script setup lang="ts">
defineProps<{
  category?: string | null
}>()
</script>

<template>
  <el-tag effect="plain" round>
    {{ category || '其他' }}
  </el-tag>
</template>
