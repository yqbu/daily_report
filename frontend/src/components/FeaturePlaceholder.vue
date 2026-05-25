<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  icon: Component
  title: string
  description: string
  sections: Array<{
    title: string
    description: string
  }>
}>()
</script>

<template>
  <section class="feature-placeholder">
    <div class="feature-hero">
      <div class="feature-icon">
        <component :is="icon" />
      </div>

      <div class="feature-copy">
        <p class="feature-state">界面占位</p>
        <h3 class="feature-title">{{ title }}</h3>
        <p class="feature-description">{{ description }}</p>
      </div>

      <span class="feature-badge">待实现</span>
    </div>

    <div class="section-grid">
      <article v-for="(section, index) in sections" :key="section.title" class="section-card">
        <span class="section-index">{{ String(index + 1).padStart(2, '0') }}</span>
        <h4 class="section-title">{{ section.title }}</h4>
        <p class="section-description">{{ section.description }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.feature-placeholder {
  display: grid;
  gap: 18px;
}

.feature-hero {
  min-height: 178px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 20px;
  padding: 24px;
  border: 1px solid #dde6f2;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(234, 241, 255, 0.82), rgba(248, 250, 252, 0.72)),
    #ffffff;
}

.feature-icon {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: #2563eb;
  background: #ffffff;
  border: 1px solid #c9dcff;
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.1);
}

.feature-icon :deep(svg) {
  width: 34px;
  height: 34px;
}

.feature-copy {
  min-width: 0;
}

.feature-state {
  margin: 0 0 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.feature-title {
  margin: 0;
  color: #172033;
  font-size: 24px;
  font-weight: 740;
  line-height: 1.2;
  letter-spacing: 0;
}

.feature-description {
  max-width: 760px;
  margin: 10px 0 0;
  color: #5f6f86;
  font-size: 14px;
  line-height: 1.7;
}

.feature-badge {
  align-self: start;
  padding: 7px 10px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  color: #9a3412;
  background: #fff7ed;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.section-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.section-card {
  min-height: 150px;
  padding: 18px;
  border: 1px solid #e0e7f1;
  border-radius: 8px;
  background: #ffffff;
}

.section-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 24px;
  margin-bottom: 18px;
  border-radius: 6px;
  color: #2563eb;
  background: #eff6ff;
  font-size: 12px;
  font-weight: 800;
}

.section-title {
  margin: 0;
  color: #172033;
  font-size: 15px;
  font-weight: 720;
  line-height: 1.35;
}

.section-description {
  margin: 8px 0 0;
  color: #667085;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 1100px) {
  .section-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .feature-hero {
    grid-template-columns: minmax(0, 1fr);
  }

  .feature-badge {
    justify-self: start;
  }

  .section-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
