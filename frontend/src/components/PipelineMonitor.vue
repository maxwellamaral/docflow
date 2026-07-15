<template>
  <section class="panel">
    <h2>⚙️ Pipeline</h2>

    <div class="skip-translation-checkbox" style="margin: 0 0 1rem 0; display: flex; flex-direction: column; gap: 0.5rem;">
      <label style="display: inline-flex; align-items: center; cursor: pointer; color: #f8fafc; font-size: 0.9rem;">
        <input
          type="checkbox"
          v-model="store.translate"
          :disabled="store.isRunning"
          style="margin-right: 0.5rem; width: 16px; height: 16px; cursor: pointer;"
        />
        Traduzir Documentos
      </label>
      <label style="display: inline-flex; align-items: center; cursor: pointer; color: #f8fafc; font-size: 0.9rem;">
        <input
          type="checkbox"
          v-model="store.refineOcr"
          :disabled="store.isRunning"
          style="margin-right: 0.5rem; width: 16px; height: 16px; cursor: pointer;"
        />
        Refinar OCR com IA (Correção Gramatical)
      </label>
    </div>

    <button
      class="btn btn-primary"
      :disabled="store.isRunning"
      @click="store.runPipeline()"
    >
      <span v-if="store.isRunning">Processando…</span>
      <span v-else>▶ Iniciar Pipeline</span>
    </button>

    <button
      v-if="store.isRunning"
      class="btn btn-danger"
      @click="store.cancelPipeline()"
      style="margin-left: 0.5rem;"
    >
      ⏹️ Parar Pipeline
    </button>

    <div v-if="store.currentJob" class="job-info">
      <div class="status-badge" :class="`status--${store.status}`">
        {{ statusLabel }}
      </div>

      <div class="progress-bar-wrap">
        <div class="progress-bar" :style="{ width: store.progress + '%' }" />
        <span class="progress-label">{{ store.progress }}%</span>
      </div>

      <p v-if="store.progressMessage" class="progress-msg">
        {{ store.progressMessage }}
      </p>

      <p v-if="store.currentJob.current_file" class="current-file">
        📄 {{ basename(store.currentJob.current_file) }}
      </p>
    </div>

    <p v-if="store.pipelineError" class="error-msg">{{ store.pipelineError }}</p>

    <button
      v-if="store.isDone"
      class="btn btn-secondary"
      @click="store.reset()"
    >
      🔄 Nova Pipeline
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { usePipelineStore } from '../stores/pipeline'

const store = usePipelineStore()

onMounted(() => {
  store.loadConfig()
})

const STATUS_LABELS: Record<string, string> = {
  pending: 'Aguardando',
  converting: 'Convertendo para HTML',
  translating: 'Traduzindo',
  exporting: 'Exportando .docx / .pdf',
  completed: 'Concluído ✅',
  failed: 'Falhou ❌',
  cancelled: 'Cancelado 🛑',
}

const statusLabel = computed(() =>
  store.status ? STATUS_LABELS[store.status] ?? store.status : '',
)

function basename(path: string): string {
  return path.split('/').pop() ?? path
}
</script>
