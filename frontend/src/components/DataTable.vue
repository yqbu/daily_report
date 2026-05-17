<template>
  <div class="overflow-hidden rounded-2xl border border-slate-200 bg-white">
    <LoadingState v-if="loading" />
    <EmptyState v-else-if="!rows.length" :title="emptyText || '暂无数据'" />
    <table v-else class="w-full table-fixed text-left text-sm">
      <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
        <tr>
          <th v-for="column in columns" :key="column.key" class="px-4 py-3 font-bold">{{ column.label }}</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-for="(row, rowIndex) in rows" :key="rowKey(row, rowIndex)" class="hover:bg-blue-50/40">
          <td v-for="column in columns" :key="column.key" class="truncate px-4 py-3 text-slate-700">
            <slot :name="column.key" :row="row">
              {{ formatValue(row[column.key]) }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import EmptyState from './EmptyState.vue'
import LoadingState from './LoadingState.vue'

type Row = Record<string, unknown>

defineProps<{
  columns: Array<{ key: string; label: string }>
  rows: Row[]
  loading?: boolean
  emptyText?: string
}>()

function rowKey(row: Row, index: number) {
  return String(row.id ?? row.key ?? index)
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}
</script>
