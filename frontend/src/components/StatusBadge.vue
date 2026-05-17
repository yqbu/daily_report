<template>
  <el-tag :type="tagType" effect="light" round>
    {{ label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ label: string; tone?: 'blue' | 'green' | 'orange' | 'red' | 'gray' }>()
const tagType = computed(() => {
  if (props.tone === 'green') return 'success'
  if (props.tone === 'orange') return 'warning'
  if (props.tone === 'red') return 'danger'
  if (props.tone === 'gray') return 'info'
  return 'primary'
})
</script>
