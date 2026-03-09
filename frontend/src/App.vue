<script setup lang="ts">
import UploadPanel from './components/UploadPanel.vue'
import PipelineMonitor from './components/PipelineMonitor.vue'
import DownloadPanel from './components/DownloadPanel.vue'
import FilesPanel from './components/FilesPanel.vue'
</script>

<template>
  <div id="app-layout">
    <header class="app-header">
      <h1>📄 DocFlow</h1>
      <p class="subtitle">Conversão, tradução e exportação de documentos PDF</p>
    </header>

    <main class="app-main">
      <UploadPanel />
      <PipelineMonitor />
      <DownloadPanel />
      <FilesPanel />
    </main>
  </div>
</template>

<style scoped>
.app-header {
  text-align: center;
  padding: 2rem 1rem 1rem;
}

.app-header h1 {
  font-size: 2.2rem;
  margin: 0 0 0.3rem;
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
</style>
