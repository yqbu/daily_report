<template>
  <div class="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white p-2">
    <input :value="modelValue" type="date" class="h-9 rounded-xl border border-transparent px-3 text-sm outline-none hover:border-slate-200 focus:border-blue-500" @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)" />
    <button class="h-9 rounded-xl bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700" @click="emit('refresh')">刷新</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; refresh: [] }>()
</script>
