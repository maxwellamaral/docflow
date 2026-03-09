import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  uploadPdf,
  startPipeline,
  connectProgressWebSocket,
  getJobStatus,
  type PipelineJob,
  type PipelineStatus,
  type ProgressEvent,
} from '../api/client'

export const usePipelineStore = defineStore('pipeline', () => {
  // ── State ─────────────────────────────────────────────────────────────────
  const pendingFiles = ref<File[]>([])
  const currentJob = ref<PipelineJob | null>(null)
  const progressMessage = ref('')
  const uploadError = ref<string | null>(null)
  const pipelineError = ref<string | null>(null)
  const isUploading = ref(false)
  const isRunning = ref(false)
  const uploadSuccessCount = ref(0)
  let ws: WebSocket | null = null

  // ── Getters ───────────────────────────────────────────────────────────────
  const status = computed<PipelineStatus | null>(() => currentJob.value?.status ?? null)
  const progress = computed(() => currentJob.value?.progress ?? 0)
  const outputs = computed(() => currentJob.value?.outputs ?? [])
  const isDone = computed(() =>
    status.value === 'completed' || status.value === 'failed',
  )

  // ── Actions ───────────────────────────────────────────────────────────────
  function addFiles(files: FileList | File[]) {
    uploadError.value = null
    for (const f of Array.from(files)) {
      if (!f.name.toLowerCase().endsWith('.pdf')) {
        uploadError.value = `"${f.name}" não é um PDF e foi ignorado.`
        continue
      }
      if (!pendingFiles.value.find((p) => p.name === f.name)) {
        pendingFiles.value.push(f)
      }
    }
  }

  function removeFile(index: number) {
    pendingFiles.value.splice(index, 1)
  }

  async function uploadAll(): Promise<void> {
    if (!pendingFiles.value.length) return
    uploadError.value = null
    isUploading.value = true
    try {
      for (const file of pendingFiles.value) {
        await uploadPdf(file)
      }
      pendingFiles.value = []
      uploadSuccessCount.value++
    } catch (err: unknown) {
      uploadError.value = `Erro no upload: ${(err as Error).message}`
    } finally {
      isUploading.value = false
    }
  }

  async function runPipeline(): Promise<void> {
    pipelineError.value = null
    isRunning.value = true
    progressMessage.value = 'Iniciando pipeline…'
    currentJob.value = null

    try {
      const { job_id } = await startPipeline()
      currentJob.value = await getJobStatus(job_id)
      _listenWebSocket(job_id)
    } catch (err: unknown) {
      pipelineError.value = `Erro ao iniciar pipeline: ${(err as Error).message}`
      isRunning.value = false
    }
  }

  function _listenWebSocket(jobId: string) {
    ws?.close()
    ws = connectProgressWebSocket(
      jobId,
      (event: ProgressEvent) => {
        if (!currentJob.value) return
        currentJob.value.status = event.status
        currentJob.value.progress = event.progress
        currentJob.value.current_file = event.current_file
        progressMessage.value = event.message

        if (event.status === 'completed') {
          // Busca a lista final de outputs
          getJobStatus(jobId).then((job) => {
            currentJob.value = job
            isRunning.value = false
          })
        } else if (event.status === 'failed') {
          pipelineError.value = event.message
          isRunning.value = false
        }
      },
      () => {
        isRunning.value = false
      },
    )
  }

  function reset() {
    ws?.close()
    ws = null
    currentJob.value = null
    progressMessage.value = ''
    uploadError.value = null
    pipelineError.value = null
    isRunning.value = false
    isUploading.value = false
    pendingFiles.value = []
  }

  return {
    pendingFiles,
    currentJob,
    progressMessage,
    uploadError,
    pipelineError,
    isUploading,
    isRunning,
    uploadSuccessCount,
    status,
    progress,
    outputs,
    isDone,
    addFiles,
    removeFile,
    uploadAll,
    runPipeline,
    reset,
  }
})
