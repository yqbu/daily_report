<script setup lang="ts">
import { shallowRef } from 'vue'
import { RouterView } from 'vue-router'

import Sidebar from '../components/Sidebar.vue'

const sidebarExpanded = shallowRef(false)

function toggleSidebar(): void {
  sidebarExpanded.value = !sidebarExpanded.value
}
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--expanded': sidebarExpanded }">
    <Sidebar :expanded="sidebarExpanded" @toggle="toggleSidebar" />

    <main class="app-main">
      <section class="app-workspace">
        <RouterView />
      </section>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  min-height: 0;
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.78), rgba(246, 248, 252, 0.92)),
    #edf1f7;
  overflow: hidden;
  transition: grid-template-columns 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

.app-shell--expanded {
  grid-template-columns: 248px minmax(0, 1fr);
}

.app-main {
  position: relative;
  z-index: 0;
  min-width: 0;
  height: 100vh;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  padding: 14px 16px 16px 16px;
  overflow: hidden;
}

.app-workspace {
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: #fbfcfd;
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
