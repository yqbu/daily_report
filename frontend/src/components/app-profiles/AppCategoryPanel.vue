<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { Close, Delete, Plus } from '@element-plus/icons-vue'

import type { AppCategoryConfig } from '../../api/types'

const props = defineProps<{
  categories: AppCategoryConfig[]
  selectedCategory: string
  loading: boolean
  saving: boolean
}>()

const emit = defineEmits<{
  create: [payload: { name: string; color: string }]
  delete: [name: string]
  select: [name: string]
  clear: []
}>()

const categoryName = shallowRef('')
const categoryColor = shallowRef('#2563EB')

const sortedCategories = computed(() => {
  return [...props.categories].sort((a, b) => {
    return a.sort_order - b.sort_order || a.name.localeCompare(b.name, 'zh-CN')
  })
})

const canCreate = computed(() => categoryName.value.trim().length > 0 && !props.saving)

function submitCategory(): void {
  if (!canCreate.value) return

  emit('create', {
    name: categoryName.value.trim(),
    color: categoryColor.value
  })
  categoryName.value = ''
}

function deleteCategory(category: AppCategoryConfig): void {
  if (category.is_builtin || props.saving) return

  emit('delete', category.name)
}
</script>

<template>
  <section class="category-panel">
    <header class="category-header">
      <div class="category-heading">
        <p class="category-kicker">分类颜色</p>
        <h2 class="category-title">应用分类</h2>
      </div>

      <button
        v-if="selectedCategory"
        class="clear-button"
        type="button"
        title="清除分类筛选"
        :disabled="loading || saving"
        @click="emit('clear')"
      >
        <Close class="button-icon" />
      </button>
    </header>

    <form class="category-form" @submit.prevent="submitCategory">
      <input v-model="categoryColor" class="color-input" type="color" title="分类颜色" />
      <input
        v-model="categoryName"
        class="category-input"
        type="text"
        placeholder="新增分类"
        maxlength="24"
        autocomplete="off"
      />
      <button class="add-button" type="submit" title="新增分类" :disabled="!canCreate">
        <Plus class="button-icon" />
      </button>
    </form>

    <div class="category-list" v-loading="loading">
      <div
        v-for="category in sortedCategories"
        :key="category.name"
        class="category-row"
        :class="{ 'category-row--active': selectedCategory === category.name }"
      >
        <span class="category-swatch" :style="{ backgroundColor: category.color }"></span>
        <button class="category-name-button" type="button" @click="emit('select', category.name)">
          <span class="category-name">{{ category.name }}</span>
        </button>
        <span class="category-count">{{ category.profile_count }}</span>
        <button
          v-if="!category.is_builtin"
          class="delete-button"
          type="button"
          title="删除分类"
          :disabled="saving"
          @click.stop="deleteCategory(category)"
        >
          <Delete class="button-icon" />
        </button>
      </div>

      <p v-if="sortedCategories.length === 0" class="category-empty">暂无分类，可先新增一个应用分类。</p>
    </div>
  </section>
</template>

<style scoped>
.category-panel {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 13px;
  padding: 18px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}

.category-header {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.category-heading {
  min-width: 0;
}

.category-kicker,
.category-title,
.category-empty {
  margin: 0;
}

.category-kicker {
  color: #0891b2;
  font-size: 12px;
  font-weight: 780;
  line-height: 1.2;
}

.category-title {
  margin-top: 4px;
  color: #172033;
  font-size: 19px;
  font-weight: 820;
  line-height: 1.2;
}

.clear-button,
.add-button,
.delete-button {
  display: grid;
  place-items: center;
  border-radius: 8px;
  cursor: pointer;
}

.clear-button {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border: 1px solid #dce3ee;
  color: #526179;
  background: #f8fafc;
}

.clear-button:hover {
  color: #2563eb;
  border-color: #c9dcff;
  background: #eff6ff;
}

.category-form {
  height: 38px;
  min-width: 0;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 34px;
  align-items: center;
  gap: 8px;
}

.color-input {
  width: 34px;
  height: 34px;
  padding: 2px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  background: #ffffff;
  cursor: pointer;
}

.category-input {
  min-width: 0;
  width: 100%;
  height: 36px;
  padding: 0 10px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  outline: 0;
  color: #172033;
  background: #f8fafc;
  font-size: 13px;
}

.category-input:focus {
  border-color: #93c5fd;
  background: #ffffff;
}

.add-button {
  width: 34px;
  height: 34px;
  border: 1px solid #c9dcff;
  color: #1d4ed8;
  background: #eff6ff;
}

.add-button:hover {
  border-color: #93c5fd;
  background: #dbeafe;
}

.add-button:disabled,
.clear-button:disabled,
.delete-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.button-icon {
  width: 15px;
  height: 15px;
}

.category-list {
  min-height: 0;
  display: grid;
  align-content: start;
  gap: 8px;
  overflow: auto;
  padding-right: 2px;
}

.category-row {
  min-width: 0;
  min-height: 36px;
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border: 1px solid #e6ebf3;
  border-radius: 8px;
  color: #344054;
  background: #fbfdff;
}

.category-row:hover,
.category-row--active {
  border-color: #c9dcff;
  background: #eff6ff;
}

.category-swatch {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.12);
}

.category-name-button {
  min-width: 0;
  padding: 0;
  border: 0;
  color: inherit;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.category-name {
  display: block;
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 720;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-count {
  min-width: 24px;
  padding: 2px 6px;
  border-radius: 999px;
  color: #667085;
  background: #eef2f7;
  font-size: 12px;
  font-weight: 720;
  text-align: center;
}

.delete-button {
  width: 26px;
  height: 26px;
  border: 0;
  color: #98a2b3;
  background: transparent;
}

.delete-button:hover {
  color: #b42318;
  background: #fee4e2;
}

.category-empty {
  padding: 18px 6px;
  color: #98a2b3;
  font-size: 13px;
}
</style>
