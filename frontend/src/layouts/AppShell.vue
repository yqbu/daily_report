<script setup lang="ts">
import { shallowRef } from 'vue'
import { RouterView } from 'vue-router'

import Sidebar from '../components/Sidebar.vue'
import TopBar from '../components/TopBar.vue'

const sidebarExpanded = shallowRef(false)

function toggleSidebar(): void {
  sidebarExpanded.value = !sidebarExpanded.value
}
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--expanded': sidebarExpanded }">
    <Sidebar :expanded="sidebarExpanded" @toggle="toggleSidebar" />

    <main class="app-main">
      <TopBar />

      <section class="app-workspace">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(246, 248, 252, 0.92)),
    #edf1f7;
  transition: grid-template-columns 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-shell--expanded {
  grid-template-columns: 248px minmax(0, 1fr);
}

.app-main {
  min-width: 0;
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  padding: 14px 16px 16px 16px;
}

.app-workspace {
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 820px) {
  .app-shell {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
  }

  .app-main {
    min-height: 0;
    grid-row: 1;
    padding: 12px;
  }

  .app-shell :deep(.sidebar) {
    grid-row: 2;
  }
}
</style>
