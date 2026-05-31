<script setup lang="ts">
import { ElDatePicker } from 'element-plus'

type DateRange = [Date, Date]

defineProps<{
  rangeSeparator?: string
  startPlaceholder?: string
  endPlaceholder?: string
}>()

const model = defineModel<DateRange>({ required: true })

const dateShortcuts = [
  {
    text: '今天',
    value: () => [startOfToday(), startOfToday()]
  },
  {
    text: '最近三天',
    value: () => [addDays(startOfToday(), -2), startOfToday()]
  },
  {
    text: '最近一周',
    value: () => [addDays(startOfToday(), -6), startOfToday()]
  },
  {
    text: '最近一月',
    value: () => [addDays(startOfToday(), -29), startOfToday()]
  },
  {
    text: '本月',
    value: () => {
      const today = startOfToday()
      return [new Date(today.getFullYear(), today.getMonth(), 1), today]
    }
  }
]

function startOfToday(): Date {
  const date = new Date()
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function addDays(date: Date, offset: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + offset)
  return next
}
</script>

<template>
  <ElDatePicker
    v-model="model"
    type="daterange"
    :range-separator="rangeSeparator ?? '至'"
    :start-placeholder="startPlaceholder ?? '开始时间'"
    :end-placeholder="endPlaceholder ?? '结束时间'"
    :shortcuts="dateShortcuts"
    :clearable="false"
  />
</template>
