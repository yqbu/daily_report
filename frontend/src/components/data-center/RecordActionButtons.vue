<script setup lang="ts">
import { Delete, Hide, View } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  sensitive: boolean
  showDetail?: boolean
}>(), {
  showDetail: true
})

defineEmits<{
  detail: []
  toggleSensitive: []
  delete: []
}>()
</script>

<template>
  <div class="record-actions" @click.stop>
    <el-tooltip v-if="showDetail" content="查看详情" placement="top" :show-after="120">
      <el-button :icon="View" circle size="small" @click="$emit('detail')" />
    </el-tooltip>
    <el-tooltip :content="sensitive ? '取消敏感' : '标记敏感'" placement="top" :show-after="120">
      <el-button :icon="Hide" circle size="small" @click="$emit('toggleSensitive')" />
    </el-tooltip>
    <el-tooltip content="删除记录" placement="top" :show-after="120">
      <el-button :icon="Delete" circle size="small" type="danger" @click="$emit('delete')" />
    </el-tooltip>
  </div>
</template>

<style scoped>
.record-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
