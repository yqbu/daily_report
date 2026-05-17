<template>
  <div class="app-data-table flex min-h-0 min-w-0 flex-1 overflow-hidden">
    <el-table
      v-loading="loading"
      :data="rows"
      :height="height"
      :row-key="resolvedRowKey"
      highlight-current-row
      scrollbar-always-on
      class="min-h-0 min-w-0 flex-1"
      @row-click="(row: Row) => emit('row-click', row)"
      @selection-change="(selection: Row[]) => emit('selection-change', selection)"
    >
      <el-table-column v-if="selectable" type="selection" width="46" fixed="left" />
      <template v-for="column in columns" :key="column.key">
        <el-table-column
          :prop="column.key"
          :label="column.label"
          :width="column.width"
          :min-width="column.minWidth || 120"
          :fixed="column.fixed"
          :type="column.type"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <slot v-if="column.slotName" :name="column.slotName" :row="row" :column="column">
              {{ formatCell(row, column) }}
            </slot>
            <span v-else class="safe-text">{{ formatCell(row, column) }}</span>
          </template>
        </el-table-column>
      </template>
      <template #empty>
        <div class="py-10 text-slate-400">{{ emptyText }}</div>
      </template>
    </el-table>
  </div>
</template>

<script setup lang="ts">
type Row = Record<string, unknown>

export interface AppTableColumn {
  key: string
  label: string
  width?: number | string
  minWidth?: number | string
  fixed?: boolean | 'left' | 'right'
  type?: string
  formatter?: (row: Row) => string
  slotName?: string
}

const props = withDefaults(defineProps<{
  rows: Row[]
  columns: AppTableColumn[]
  loading?: boolean
  rowKey?: string | ((row: Row) => string)
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

const emit = defineEmits<{
  'row-click': [row: Row]
  'selection-change': [selection: Row[]]
}>()

const resolvedRowKey = props.rowKey

function formatCell(row: Row, column: AppTableColumn) {
  if (column.formatter) return column.formatter(row)
  const value = row[column.key]
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}
</script>
