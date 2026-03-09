<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import OutputNode from './OutputNode.vue'
import { usePipelineStore } from '../stores/pipeline'
import {
  listInputFiles,
  listOutputFiles,
  deleteInputFile,
  deleteOutputFile,
  viewInputFileUrl,
  uploadPdf,
  type FileInfo,
  type OutputEntry,
} from '../api/client'

type Tab = 'input' | 'output'
const activeTab = ref<Tab>('input')

const inputFiles = ref<FileInfo[]>([])
const outputEntries = ref<OutputEntry[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)
const successMsg = ref<string | null>(null)

const fileInputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const expandedDirs = ref<Set<string>>(new Set())

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function flash(msg: string) {
  successMsg.value = msg
  setTimeout(() => (successMsg.value = null), 3000)
}

async function loadInput() {
  loading.value = true
  errorMsg.value = null
  try {
    inputFiles.value = (await listInputFiles()).files
  } catch {
    errorMsg.value = 'Erro ao listar arquivos de entrada.'
  } finally {
    loading.value = false
  }
}

async function loadOutput() {
  loading.value = true
  errorMsg.value = null
  try {
    outputEntries.value = (await listOutputFiles()).entries
  } catch {
    errorMsg.value = 'Erro ao listar arquivos de saída.'
  } finally {
    loading.value = false
  }
}

async function switchTab(tab: Tab) {
  activeTab.value = tab
  if (tab === 'input') await loadInput()
  else await loadOutput()
}

switchTab('input')

async function handleUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  uploading.value = true
  errorMsg.value = null
  try {
    for (const file of Array.from(target.files)) {
      await uploadPdf(file)
    }
    flash(`${target.files.length} arquivo(s) enviado(s).`)
    await loadInput()
  } catch {
    errorMsg.value = 'Erro ao enviar arquivo(s).'
  } finally {
    uploading.value = false
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

async function removeInput(filename: string) {
  if (!confirm(`Excluir "${filename}"?`)) return
  try {
    await deleteInputFile(filename)
    flash(`"${filename}" excluído.`)
    await loadInput()
  } catch {
    errorMsg.value = `Erro ao excluir "${filename}".`
  }
}

async function removeOutput(path: string, name: string) {
  if (!confirm(`Excluir "${name}"?`)) return
  try {
    await deleteOutputFile(path)
    flash(`"${name}" excluído.`)
    await loadOutput()
  } catch {
    errorMsg.value = `Erro ao excluir "${name}".`
  }
}

function toggleDir(path: string) {
  const next = new Set(expandedDirs.value)
  if (next.has(path)) next.delete(path)
  else next.add(path)
  expandedDirs.value = next
}

const hasInput = computed(() => inputFiles.value.length > 0)
const hasOutput = computed(() => outputEntries.value.length > 0)

// Sincroniza com uploads feitos pelo painel "Envio de PDFs"
const pipelineStore = usePipelineStore()
watch(() => pipelineStore.uploadSuccessCount, () => {
  if (activeTab.value === 'input') loadInput()
})
</script>

<template>
  <div class="panel files-panel">
    <h2 class="panel-title">🗂 Gerenciar Arquivos</h2>

    <div class="tabs">
      <button class="tab-btn" :class="{ active: activeTab === 'input' }" @click="switchTab('input')">
        📥 Entrada
        <span v-if="inputFiles.length" class="badge">{{ inputFiles.length }}</span>
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'output' }" @click="switchTab('output')">
        📤 Saída
      </button>
    </div>

    <div v-if="errorMsg" class="alert alert--error">{{ errorMsg }}</div>
    <div v-if="successMsg" class="alert alert--success">{{ successMsg }}</div>

    <div v-if="loading" class="loading-row">
      <span class="spinner" /><span>Carregando…</span>
    </div>

    <template v-if="!loading && activeTab === 'input'">
      <div class="toolbar">
        <label class="btn btn-primary upload-label">
          <span v-if="!uploading">+ Adicionar PDFs</span>
          <span v-else>⏳ Enviando…</span>
          <input ref="fileInputRef" type="file" accept=".pdf" multiple hidden :disabled="uploading" @change="handleUpload" />
        </label>
        <button class="btn btn-secondary" @click="loadInput">↺ Atualizar</button>
      </div>
      <p v-if="!hasInput" class="empty-msg">Nenhum arquivo de entrada encontrado.</p>
      <ul v-else class="file-list">
        <li v-for="file in inputFiles" :key="file.name" class="file-item">
          <span class="file-icon">📄</span>
          <span class="file-name" :title="file.name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
          <div class="file-actions">
            <a :href="viewInputFileUrl(file.name)" target="_blank" class="btn btn-sm btn-ghost" title="Baixar">⬇</a>
            <button class="btn btn-sm btn-danger" title="Excluir" @click="removeInput(file.name)">🗑</button>
          </div>
        </li>
      </ul>
    </template>

    <template v-if="!loading && activeTab === 'output'">
      <div class="toolbar">
        <button class="btn btn-secondary" @click="loadOutput">↺ Atualizar</button>
      </div>
      <p v-if="!hasOutput" class="empty-msg">Nenhum arquivo de saída encontrado.</p>
      <ul v-else class="file-list">
        <OutputNode
          v-for="entry in outputEntries"
          :key="entry.path"
          :entry="entry"
          :expanded-dirs="expandedDirs"
          :depth="0"
          @toggle="toggleDir"
          @delete="removeOutput"
        />
      </ul>
    </template>
  </div>
</template>

<style scoped>
.files-panel { display: flex; flex-direction: column; gap: 0.75rem; }

.tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid rgba(255,255,255,0.1);
  padding-bottom: 0.5rem;
}

.tab-btn {
  background: none; border: none;
  padding: 0.4rem 1rem; border-radius: 6px 6px 0 0;
  cursor: pointer; font-size: 0.9rem;
  color: rgba(255,255,255,0.45);
  display: flex; align-items: center; gap: 0.4rem;
  transition: background 0.15s, color 0.15s;
}
.tab-btn:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.75); }
.tab-btn.active {
  background: rgba(124,140,248,0.15);
  color: #7c8cf8;
  font-weight: 600;
}

.badge {
  background: var(--color-accent, #2563eb); color: #fff;
  border-radius: 999px; font-size: 0.7rem;
  padding: 0.05rem 0.45rem; font-weight: 700;
}

.toolbar { display: flex; align-items: center; gap: 0.5rem; }
.upload-label { cursor: pointer; display: inline-flex; align-items: center; }

.btn-secondary {
  background: #0f3460;
  border: 1px solid #1a4a8a;
  color: rgba(255,255,255,0.85);
  padding: 0.4rem 0.9rem; border-radius: 7px;
  cursor: pointer; font-size: 0.875rem;
}
.btn-secondary:hover { filter: brightness(1.2); }

.file-list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-direction: column; gap: 0.35rem;
  max-height: 420px; overflow-y: auto;
}

.file-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.4rem 0.6rem; border-radius: 7px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
}

.file-icon { font-size: 1rem; flex-shrink: 0; }
.file-name {
  flex: 1; font-size: 0.875rem;
  color: rgba(255,255,255,0.87);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
}
.file-size {
  font-size: 0.78rem; color: rgba(255,255,255,0.45);
  white-space: nowrap; flex-shrink: 0;
}
.file-actions { display: flex; gap: 0.3rem; flex-shrink: 0; }

.btn-sm { padding: 0.2rem 0.5rem; font-size: 0.8rem; border-radius: 5px; }
.btn-ghost {
  background: transparent; border: 1px solid rgba(255,255,255,0.2);
  color: rgba(255,255,255,0.75); text-decoration: none;
  cursor: pointer; display: inline-flex; align-items: center;
}
.btn-ghost:hover { background: rgba(255,255,255,0.08); }
.btn-danger {
  background: transparent; border: 1px solid rgba(233,69,96,0.5);
  color: #e94560; cursor: pointer;
}
.btn-danger:hover { background: rgba(233,69,96,0.12); }

.empty-msg {
  color: rgba(255,255,255,0.4); font-size: 0.875rem;
  text-align: center; padding: 1.5rem 0;
}

.loading-row {
  display: flex; align-items: center; gap: 0.5rem;
  color: rgba(255,255,255,0.4); font-size: 0.875rem;
}

.spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.15);
  border-top-color: #7c8cf8;
  border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.alert { padding: 0.6rem 0.9rem; border-radius: 7px; font-size: 0.875rem; }
.alert--error { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
.alert--success { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
</style>
