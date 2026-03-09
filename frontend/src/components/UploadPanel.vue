<template>
  <section class="panel">
    <h2>📤 Envio de PDFs</h2>

    <div
      class="drop-zone"
      :class="{ 'drop-zone--active': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <p v-if="!isDragging">Arraste PDFs aqui ou</p>
      <p v-else>Solte aqui!</p>
      <label class="btn btn-secondary">
        Selecionar arquivos
        <input type="file" multiple accept=".pdf" hidden @change="onFileInput" />
      </label>
    </div>

    <p v-if="store.uploadError" class="error-msg">{{ store.uploadError }}</p>

    <ul v-if="store.pendingFiles.length" class="file-list">
      <li v-for="(file, i) in store.pendingFiles" :key="file.name">
        <span>📄 {{ file.name }}</span>
        <button class="btn-icon" title="Remover" @click="store.removeFile(i)">✕</button>
      </li>
    </ul>

    <div class="actions">
      <button
        class="btn btn-primary"
        :disabled="!store.pendingFiles.length || store.isUploading"
        @click="store.uploadAll()"
      >
        <span v-if="store.isUploading">Enviando…</span>
        <span v-else>Enviar ({{ store.pendingFiles.length }}) PDFs</span>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePipelineStore } from '../stores/pipeline'

const store = usePipelineStore()
const isDragging = ref(false)

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) store.addFiles(e.dataTransfer.files)
}

function onFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) store.addFiles(input.files)
  input.value = ''
}
</script>
