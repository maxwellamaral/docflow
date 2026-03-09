<template>
  <section class="panel">
    <h2>⬇️ Downloads</h2>

    <p v-if="!store.outputs.length" class="empty-msg">
      Nenhum arquivo disponível para download ainda.
    </p>

    <div v-else>
      <div
        v-for="group in groupedOutputs"
        :key="group.label"
        class="output-group"
      >
        <h3>{{ group.icon }} {{ group.label }}</h3>
        <ul class="file-list">
          <li v-for="item in group.items" :key="item.url">
            <span>{{ item.name }}</span>
            <a :href="item.url" :download="item.name" class="btn btn-secondary btn-sm">
              Baixar
            </a>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { usePipelineStore } from '../stores/pipeline'
import { buildDownloadUrl } from '../api/client'

const store = usePipelineStore()

interface OutputItem {
  name: string
  url: string
  type: string
}

const GROUPS = [
  { key: 'html', label: 'HTML Original', icon: '🌐' },
  { key: 'translated', label: 'HTML Traduzido', icon: '🌍' },
  { key: 'docx', label: 'Word (.docx)', icon: '📝' },
  { key: 'pdf', label: 'PDF', icon: '📕' },
]

const groupedOutputs = computed(() => {
  const items: OutputItem[] = store.outputs.map((fullPath) => {
    // fullPath é absoluto no servidor — extrai a parte relativa a ./output/
    const parts = fullPath.replace(/\\/g, '/').split('output/')
    const relative: string = parts.length > 1 && parts[1] != null
      ? parts[1]
      : fullPath.split('/').pop() ?? fullPath
    const name = fullPath.split('/').pop() ?? fullPath
    const type = relative.includes('/html/')
      ? 'html'
      : relative.includes('/translated/')
      ? 'translated'
      : relative.includes('/docx/')
      ? 'docx'
      : relative.includes('/pdf/')
      ? 'pdf'
      : 'other'

    return { name, url: buildDownloadUrl(relative), type }
  })

  return GROUPS.map((g) => ({
    ...g,
    items: items.filter((i) => i.type === g.key),
  })).filter((g) => g.items.length > 0)
})
</script>
