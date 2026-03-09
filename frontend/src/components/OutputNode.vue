<script setup lang="ts">
import { type PropType } from 'vue'
import { viewOutputFileUrl, type OutputEntry } from '../api/client'

const props = defineProps({
  entry: { type: Object as PropType<OutputEntry>, required: true },
  expandedDirs: { type: Object as PropType<Set<string>>, required: true },
  depth: { type: Number, default: 0 },
})

const emit = defineEmits<{
  (e: 'toggle', path: string): void
  (e: 'delete', path: string, name: string): void
}>()

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const fileIconMap: Record<string, string> = {
  pdf: '📕',
  docx: '📘',
  html: '🌐',
}

function fileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  return fileIconMap[ext] ?? '📄'
}
</script>

<template>
  <li class="file-item" :style="{ paddingLeft: depth * 16 + 4 + 'px' }">
    <!-- Diretório -->
    <template v-if="entry.is_dir">
      <button class="dir-toggle" @click="emit('toggle', entry.path)">
        {{ expandedDirs.has(entry.path) ? '📂' : '📁' }}
      </button>
      <span class="file-name dir-name">{{ entry.name }}</span>
      <div class="file-actions">
        <button
          class="btn btn-sm btn-danger"
          title="Excluir pasta"
          @click="emit('delete', entry.path, entry.name)"
        >🗑</button>
      </div>
      <!-- Filhos recursivos -->
      <ul v-if="expandedDirs.has(entry.path)" class="file-list nested">
        <OutputNode
          v-for="child in entry.children"
          :key="child.path"
          :entry="child"
          :expanded-dirs="expandedDirs"
          :depth="depth + 1"
          @toggle="emit('toggle', $event)"
          @delete="(p, n) => emit('delete', p, n)"
        />
      </ul>
    </template>

    <!-- Arquivo -->
    <template v-else>
      <span class="file-icon">{{ fileIcon(entry.name) }}</span>
      <span class="file-name" :title="entry.name">{{ entry.name }}</span>
      <span class="file-size">{{ formatSize(entry.size) }}</span>
      <div class="file-actions">
        <a
          :href="viewOutputFileUrl(entry.path)"
          target="_blank"
          class="btn btn-sm btn-ghost"
          title="Visualizar / Baixar"
        >⬇</a>
        <button
          class="btn btn-sm btn-danger"
          title="Excluir"
          @click="emit('delete', entry.path, entry.name)"
        >🗑</button>
      </div>
    </template>
  </li>
</template>

<style scoped>
.file-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.5rem;
  border-radius: 7px;
  background: var(--color-surface, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
  flex-wrap: wrap;
  list-style: none;
}

.file-icon { font-size: 1rem; flex-shrink: 0; }

.file-name {
  flex: 1;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.dir-name {
  font-weight: 600;
  color: var(--color-accent, #2563eb);
}

.file-size {
  font-size: 0.78rem;
  color: var(--color-text-muted, #9ca3af);
  white-space: nowrap;
  flex-shrink: 0;
}

.file-actions { display: flex; gap: 0.3rem; flex-shrink: 0; }

.btn-sm {
  padding: 0.2rem 0.5rem;
  font-size: 0.8rem;
  border-radius: 5px;
}

.btn-ghost {
  background: transparent;
  border: 1px solid var(--color-border, #e5e7eb);
  color: var(--color-text, #374151);
  text-decoration: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.btn-ghost:hover { background: var(--color-surface-hover, #f3f4f6); }

.btn-danger {
  background: transparent;
  border: 1px solid #fca5a5;
  color: #dc2626;
  cursor: pointer;
}

.btn-danger:hover { background: #fee2e2; }

.dir-toggle {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0;
  flex-shrink: 0;
}

.file-list {
  list-style: none;
  margin: 0.4rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 100%;
}

.nested { margin-top: 0.4rem; width: 100%; }
</style>
