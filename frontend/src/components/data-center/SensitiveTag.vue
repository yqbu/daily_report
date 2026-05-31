<script setup lang="ts">
defineProps<{
  sensitive: boolean
}>()
</script>

<template>
  <el-tag :type="sensitive ? 'danger' : 'success'" effect="light" round>
    {{ sensitive ? '敏感' : '非敏感' }}
  </el-tag>
</template>
