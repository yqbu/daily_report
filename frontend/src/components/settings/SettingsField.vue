<script setup lang="ts">
defineProps<{
  label: string
  description?: string
  compact?: boolean
  wide?: boolean
}>()
</script>

<template>
  <div class="settings-field" :class="{ 'settings-field--compact': compact, 'settings-field--wide': wide }">
    <div class="settings-field-copy">
      <label class="settings-field-label">{{ label }}</label>
      <p v-if="description" class="settings-field-description">{{ description }}</p>
      <slot name="meta" />
    </div>

    <div class="settings-field-control">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.settings-field {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 320px);
  gap: 18px;
  align-items: center;
  padding: 17px 20px;
  border-bottom: 1px solid #edf1f7;
}

.settings-field:last-child {
  border-bottom: 0;
}

.settings-field--compact {
  grid-template-columns: minmax(0, 1fr) auto;
}

.settings-field--wide {
  grid-template-columns: minmax(0, 0.9fr) minmax(320px, 1.1fr);
}

.settings-field-copy {
  min-width: 0;
}

.settings-field-label {
  display: block;
  color: #344054;
  font-size: 13px;
  font-weight: 760;
  line-height: 1.35;
}

.settings-field-description {
  margin: 5px 0 0;
  color: #667085;
  font-size: 13px;
  line-height: 1.55;
}

.settings-field-control {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.settings-field-control :deep(.el-input),
.settings-field-control :deep(.el-input-number),
.settings-field-control :deep(.el-select),
.settings-field-control :deep(.el-textarea),
.settings-field-control :deep(.el-slider) {
  width: 100%;
}

@media (max-width: 820px) {
  .settings-field,
  .settings-field--compact {
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
    align-items: stretch;
  }

  .settings-field-control {
    justify-content: flex-start;
  }
}
</style>
