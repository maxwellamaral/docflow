<template>
  <section class="panel logs-panel-full">
    <div class="logs-top-bar">
      <div class="logs-header-title">
        <h2>📋 Logs da Pipeline</h2>
        <p class="logs-subtitle">Status das etapas e tempos de processamento em tempo real</p>
      </div>
      <div class="logs-top-actions">
        <span class="logs-count-badge" v-if="store.fileTasks.length">
          {{ store.fileTasks.length }} {{ store.fileTasks.length === 1 ? 'arquivo' : 'arquivos' }}
        </span>
        <button class="btn btn-sm btn-secondary" @click="store.reset()">Limpar Tudo</button>
      </div>
    </div>

    <!-- Lista de Arquivos e suas Etapas de Pipeline -->
    <div v-if="!store.fileTasks.length" class="pipeline-empty-state">
      <div class="empty-icon">⏳</div>
      <p class="empty-text">Nenhum pipeline iniciado. Envie arquivos PDF e clique em "Iniciar Pipeline".</p>
    </div>

    <div v-else class="pipeline-files-list">
      <div
        v-for="task in store.fileTasks"
        :key="task.filePath"
        class="file-pipeline-card"
        :class="`card--${task.status}`"
      >
        <div class="file-card-header">
          <div class="file-info-group">
            <span class="file-icon">📄</span>
            <span class="file-name" :title="task.filePath">{{ task.fileName }}</span>
          </div>
          <span class="file-status-badge" :class="`badge--${task.status}`">
            {{ formatStatus(task.status) }}
          </span>
        </div>

        <!-- Barra de Progresso do Arquivo -->
        <div class="file-progress-container">
          <div class="progress-bar-track">
            <div
              class="progress-bar-fill"
              :class="`fill--${task.status}`"
              :style="{ width: getTaskProgressPercent(task) + '%' }"
            />
          </div>
          <span class="progress-percentage">{{ getTaskProgressPercent(task) }}%</span>
        </div>

        <!-- Etapas Individuais -->
        <div class="pipeline-stages-container">
          <!-- Etapa 1: Conversão -->
          <div class="stage-item" :class="`stage--${task.stages.converting.status}`">
            <div class="stage-meta">
              <span class="stage-name">🔍 Conversão HTML</span>
              <span class="stage-time">{{ getStageDuration(task.filePath, 'converting', task.stages.converting) }}</span>
            </div>
            <div class="stage-progress-track">
              <div
                class="stage-progress-fill fill--converting"
                :style="{ width: task.stages.converting.progress + '%' }"
              />
            </div>
          </div>

          <!-- Etapa 2: Tradução -->
          <div class="stage-item" :class="`stage--${task.stages.translating.status}`">
            <div class="stage-meta">
              <span class="stage-name">🔤 Tradução (Ollama)</span>
              <span class="stage-time">{{ getStageDuration(task.filePath, 'translating', task.stages.translating) }}</span>
            </div>
            <div class="stage-progress-track">
              <div
                class="stage-progress-fill fill--translating"
                :style="{ width: task.stages.translating.progress + '%' }"
              />
            </div>
          </div>

          <!-- Etapa 3: Exportação -->
          <div class="stage-item" :class="`stage--${task.stages.exporting.status}`">
            <div class="stage-meta">
              <span class="stage-name">💾 Exportação (Docx/PDF)</span>
              <span class="stage-time">{{ getStageDuration(task.filePath, 'exporting', task.stages.exporting) }}</span>
            </div>
            <div class="stage-progress-track">
              <div
                class="stage-progress-fill fill--exporting"
                :style="{ width: task.stages.exporting.progress + '%' }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Terminal de Logs Brutos -->
    <div class="terminal-logs-section">
      <div class="terminal-header" @click="isConsoleExpanded = !isConsoleExpanded">
        <span class="terminal-title">🖥️ Console de Eventos</span>
        <div class="terminal-header-actions">
          <span class="logs-badge" v-if="store.logs.length">{{ store.logs.length }} logs</span>
          <span class="toggle-icon">{{ isConsoleExpanded ? '▼' : '▲' }}</span>
        </div>
      </div>

      <div v-show="isConsoleExpanded" ref="logsListEl" class="terminal-body">
        <div v-if="!store.logs.length" class="terminal-empty">
          Nenhum evento registrado no console.
        </div>
        <div
          v-else
          v-for="(log, i) in store.logs"
          :key="i"
          class="terminal-line"
          :class="`line--${log.status}`"
        >
          <span class="line-time">[{{ log.timestamp }}]</span>
          <span class="line-status">[{{ log.status.toUpperCase() }}]</span>
          <span class="line-message">{{ log.message }}</span>
          <span class="line-file" v-if="log.file">({{ basename(log.file) }})</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { usePipelineStore } from '../stores/pipeline'

const store = usePipelineStore()
if (typeof window !== 'undefined') {
  ;(window as any).pipelineStore = store
}
const logsListEl = ref<HTMLElement | null>(null)
const isConsoleExpanded = ref(true)

// Estado local para manter as durações decorridas ativas das etapas que estão rodando
const activeDurations = ref<Record<string, number>>({})
let timerInterval: number | null = null

onMounted(() => {
  timerInterval = window.setInterval(() => {
    store.fileTasks.forEach((task) => {
      Object.entries(task.stages).forEach(([stageKey, stage]) => {
        if (stage.status === 'running' && stage.startTime) {
          const elapsed = (Date.now() - stage.startTime) / 1000
          activeDurations.value[`${task.filePath}-${stageKey}`] = elapsed
        }
      })
    })
  }, 100)
})

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval)
  }
})

// Rolar o console de logs para a base a cada nova linha
watch(
  () => store.logs.length,
  async () => {
    await nextTick()
    if (logsListEl.value) {
      logsListEl.value.scrollTop = logsListEl.value.scrollHeight
    }
  },
)

function formatStatus(status: string): string {
  const map: Record<string, string> = {
    pending: 'Pendente',
    converting: 'Convertendo',
    translating: 'Traduzindo',
    exporting: 'Exportando',
    completed: 'Concluído',
    failed: 'Falhou',
    cancelled: 'Cancelado',
  }
  return map[status] ?? status
}

function getTaskProgressPercent(task: any): number {
  if (task.status === 'completed') return 100
  if (task.status === 'failed' || task.status === 'cancelled') {
    return task.stages.exporting.status === 'failed' ? 80 : (task.stages.translating.status === 'failed' ? 50 : 20)
  }

  let completedStages = 0
  if (task.stages.converting.status === 'completed') completedStages++
  if (task.stages.translating.status === 'completed') completedStages++
  if (task.stages.exporting.status === 'completed') completedStages++

  if (completedStages === 0) {
    return task.stages.converting.status === 'running' ? 15 : 0
  } else if (completedStages === 1) {
    return task.stages.translating.status === 'running' ? 45 : 33
  } else if (completedStages === 2) {
    return task.stages.exporting.status === 'running' ? 80 : 66
  }
  return 100
}

function getStageDuration(taskFilePath: string, stageKey: string, stage: any): string {
  if (stage.status === 'completed' || stage.status === 'failed') {
    return stage.duration !== undefined ? `${stage.duration.toFixed(1)}s` : '-'
  }
  if (stage.status === 'running') {
    const elapsed = activeDurations.value[`${taskFilePath}-${stageKey}`]
    return elapsed !== undefined ? `${elapsed.toFixed(1)}s` : '0.0s'
  }
  return '-'
}

function basename(path: string): string {
  return path.split('/').pop() ?? path
}
</script>

<style scoped>
.logs-panel-full {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  backdrop-filter: blur(12px);
  padding: 1.25rem;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
}

.logs-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 0.75rem;
}

.logs-header-title h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #f8fafc;
}

.logs-subtitle {
  margin: 0.15rem 0 0 0;
  font-size: 0.8rem;
  color: #94a3b8;
}

.logs-top-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logs-count-badge {
  font-size: 0.75rem;
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  border: 1px solid rgba(99, 102, 241, 0.3);
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
}

/* Empty State */
.pipeline-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px dashed rgba(255, 255, 255, 0.05);
}

.empty-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
  animation: pulse-light 2s infinite ease-in-out;
}

@keyframes pulse-light {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.empty-text {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0;
}

/* Files Pipeline cards */
.pipeline-files-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 450px;
  overflow-y: auto;
}

.file-pipeline-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  transition: all 0.25s ease;
}

.file-pipeline-card:hover {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(30, 41, 59, 0.55);
}

.card--failed {
  border-color: rgba(239, 68, 68, 0.25);
  background: rgba(239, 68, 68, 0.03);
}

.card--cancelled {
  border-color: rgba(249, 115, 22, 0.25);
  background: rgba(249, 115, 22, 0.03);
}

.card--completed {
  border-color: rgba(16, 185, 129, 0.2);
}

.file-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.file-info-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  overflow: hidden;
}

.file-icon {
  flex-shrink: 0;
}

.file-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-status-badge {
  font-size: 0.7rem;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge--pending { background: #334155; color: #94a3b8; }
.badge--converting { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
.badge--translating { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
.badge--exporting { background: rgba(6, 182, 212, 0.2); color: #22d3ee; }
.badge--completed { background: rgba(16, 185, 129, 0.2); color: #34d399; }
.badge--failed { background: rgba(239, 68, 68, 0.2); color: #f87171; }
.badge--cancelled { background: rgba(249, 115, 22, 0.2); color: #fb923c; }

/* File progress bar */
.file-progress-container {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.progress-bar-track {
  height: 6px;
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 10px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fill--converting { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.fill--translating { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.fill--exporting { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
.fill--completed { background: linear-gradient(90deg, #10b981, #34d399); }
.fill--failed { background: #ef4444; }
.fill--cancelled { background: #f97316; }
.fill--pending { background: #475569; }

.progress-percentage {
  font-size: 0.72rem;
  color: #94a3b8;
  width: 28px;
  text-align: right;
  font-family: monospace;
}

/* Pipeline Stages Container */
.pipeline-stages-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-top: 0.35rem;
  background: rgba(0, 0, 0, 0.15);
  padding: 0.65rem;
  border-radius: 6px;
}

.stage-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  opacity: 0.4;
  transition: opacity 0.3s;
}

.stage--running {
  opacity: 1;
}

.stage--completed {
  opacity: 0.95;
}

.stage--failed {
  opacity: 1;
}

.stage-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.78rem;
}

.stage-name {
  color: #cbd5e1;
  font-weight: 500;
}

.stage-time {
  font-family: monospace;
  color: #94a3b8;
}

.stage--running .stage-time {
  color: #3b82f6;
  font-weight: 600;
}

.stage-progress-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  overflow: hidden;
}

.stage-progress-fill {
  height: 100%;
  width: 0;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.stage--completed .stage-progress-fill {
  background: #10b981;
  width: 100% !important;
}

.stage--failed .stage-progress-fill {
  background: #ef4444;
  width: 100% !important;
}

.stage--running .stage-progress-fill {
  animation: progress-pulse 1.5s infinite ease-in-out;
}

.fill--converting { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.fill--translating { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.fill--exporting { background: linear-gradient(90deg, #06b6d4, #22d3ee); }

@keyframes progress-pulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

/* Terminal Logs Section */
.terminal-logs-section {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.terminal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  user-select: none;
  background: rgba(255, 255, 255, 0.02);
  transition: background 0.2s;
}

.terminal-header:hover {
  background: rgba(255, 255, 255, 0.05);
}

.terminal-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: #94a3b8;
}

.terminal-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logs-badge {
  font-size: 0.65rem;
  background: rgba(255, 255, 255, 0.05);
  color: #64748b;
  padding: 0.08rem 0.4rem;
  border-radius: 10px;
}

.toggle-icon {
  font-size: 0.7rem;
  color: #64748b;
}

.terminal-body {
  height: 140px;
  overflow-y: auto;
  background: #020617;
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 0.6rem;
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
  font-size: 0.72rem;
  line-height: 1.4;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
}

.terminal-empty {
  color: #475569;
  text-align: center;
  padding: 2.5rem 0;
}

.terminal-line {
  display: flex;
  gap: 0.5rem;
  padding: 0.1rem 0;
  border-left: 2px solid transparent;
  padding-left: 0.3rem;
}

.line-time {
  color: #475569;
  flex-shrink: 0;
}

.line-status {
  font-weight: 600;
  flex-shrink: 0;
}

.line-message {
  color: #cbd5e1;
  word-break: break-all;
}

.line-file {
  color: #64748b;
  font-style: italic;
  white-space: nowrap;
}

.line--converting .line-status { color: #3b82f6; }
.line--translating .line-status { color: #8b5cf6; }
.line--exporting .line-status { color: #06b6d4; }
.line--completed .line-status { color: #10b981; }
.line--failed .line-status { color: #ef4444; }
.line--cancelled .line-status { color: #f97316; }
.line--pending .line-status { color: #64748b; }
.line--failed { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.05); }
.line--cancelled { border-left-color: #f97316; background: rgba(249, 115, 22, 0.05); }

/* Custom Scrollbar for Webkit */
.terminal-body::-webkit-scrollbar,
.pipeline-files-list::-webkit-scrollbar {
  width: 5px;
}
.terminal-body::-webkit-scrollbar-track,
.pipeline-files-list::-webkit-scrollbar-track {
  background: transparent;
}
.terminal-body::-webkit-scrollbar-thumb,
.pipeline-files-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}
.terminal-body::-webkit-scrollbar-thumb:hover,
.pipeline-files-list::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
