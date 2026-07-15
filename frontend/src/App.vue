<script setup lang="ts">
import { ref, onMounted } from 'vue'
import UploadPanel from './components/UploadPanel.vue'
import PipelineMonitor from './components/PipelineMonitor.vue'
import DownloadPanel from './components/DownloadPanel.vue'
import FilesPanel from './components/FilesPanel.vue'
import LogsPanel from './components/LogsPanel.vue'

const isDark = ref(true)

function toggleTheme() {
  isDark.value = !isDark.value
  const theme = isDark.value ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('docflow-theme', theme)
}

onMounted(() => {
  const saved = localStorage.getItem('docflow-theme')
  if (saved) {
    isDark.value = saved === 'dark'
    document.documentElement.setAttribute('data-theme', saved)
  } else {
    const prefersLight = window.matchMedia('(prefers-color-scheme: light)').matches
    isDark.value = !prefersLight
    document.documentElement.setAttribute('data-theme', prefersLight ? 'light' : 'dark')
  }
})
</script>

<template>
  <div id="app-layout">
    <header class="app-header">
      <div class="header-title-row">
        <h1>📄 DocFlow</h1>
        <button
          class="theme-toggle-btn"
          @click="toggleTheme"
          :title="isDark ? 'Ativar Modo Claro' : 'Ativar Modo Escuro'"
        >
          {{ isDark ? '☀️ Claro' : '🌙 Escuro' }}
        </button>
      </div>
      <p class="subtitle">Conversão, tradução e exportação de documentos PDF</p>
    </header>

    <main class="app-main">
      <UploadPanel />
      <PipelineMonitor />
      <DownloadPanel />
      <FilesPanel />
      <LogsPanel class="logs-panel-span" />
    </main>
  </div>
</template>

<style scoped>
.app-header {
  text-align: center;
  padding: 2rem 1rem 1rem;
}

.header-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1.2rem;
  margin-bottom: 0.3rem;
}

.app-header h1 {
  font-size: 2.2rem;
  margin: 0;
}

.theme-toggle-btn {
  background: var(--btn-secondary-bg);
  border: 1px solid var(--btn-secondary-border);
  color: var(--btn-secondary-text);
  padding: 0.35rem 0.85rem;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.theme-toggle-btn:hover {
  filter: brightness(1.1);
}

.subtitle {
  color: #888;
  margin: 0;
  font-size: 0.95rem;
}

.app-main {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.logs-panel-span {
  grid-column: 1 / -1;
}
</style>

