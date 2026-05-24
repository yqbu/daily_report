<script setup lang="ts">
/**
 * 表格组件骨架。
 *
 * 作用：
 * - 保留表格所需的 rows/columns/loading/pagination 前置契约
 * - 保留 row-click 与 selection-change 事件
 * - 具体表格 UI 由后续实现补充
 */

type Row = Record<string, unknown>

export interface AppTableColumn {
  key: string
  label: string
  width?: number | string
  minWidth?: number | string
  fixed?: boolean | 'left' | 'right'
  type?: 'selection' | 'index' | 'expand'
  align?: 'left' | 'center' | 'right'
  formatter?: (row: Row) => string | number
  slotName?: string
}

withDefaults(defineProps<{
  rows: Row[]
  columns: AppTableColumn[]
  loading?: boolean
  rowKey?: string | ((row: Row) => string | number)
  height?: string | number
  selectable?: boolean
  emptyText?: string
}>(), {
  loading: false,
  rowKey: 'id',
  height: '100%',
  selectable: false,
  emptyText: '暂无数据'
})

defineEmits<{
  'row-click': [row: Row]
  'selection-change': [selection: Row[]]
}>()
</script>

<template>
  <div class="app-data-table" v-loading="loading">
    <!--
      待实现：
      - 根据 columns 渲染表头和单元格
      - 根据 rows 渲染数据行
      - selectable=true 时提供选择列
      - 行点击时 emit('row-click', row)
      - 选择变化时 emit('selection-change', selection)
    -->
    <slot />
  </div>
</template>

<style scoped>
.app-data-table {
  min-width: 0;
  min-height: 0;
}
</style>
