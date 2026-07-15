import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  uploadPdf,
  startPipeline,
  connectProgressWebSocket,
  getJobStatus,
  cancelPipelineJob,
  getPipelineConfig,
  type PipelineJob,
  type PipelineStatus,
  type ProgressEvent,
} from '../api/client'

export interface PipelineStage {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  startTime?: number
  duration?: number // em segundos
}

export interface FileTask {
  fileName: string
  filePath: string
  status: PipelineStatus
  stages: {
    converting: PipelineStage
    translating: PipelineStage
    exporting: PipelineStage
  }
}

export interface LogEntry {
  timestamp: string
  status: string
  message: string
  file?: string
}

export const usePipelineStore = defineStore('pipeline', () => {
  // ── State ─────────────────────────────────────────────────────────────────
  const pendingFiles = ref<File[]>([])
  const currentJob = ref<PipelineJob | null>(null)
  const progressMessage = ref('')
  const uploadError = ref<string | null>(null)
  const pipelineError = ref<string | null>(null)
  const isUploading = ref(false)
  const isRunning = ref(false)
  const translate = ref(true)
  const refineOcr = ref(true)
  const uploadSuccessCount = ref(0)
  const logs = ref<LogEntry[]>([])
  const fileTasks = ref<FileTask[]>([])
  let ws: WebSocket | null = null

  // ── Getters ───────────────────────────────────────────────────────────────
  const status = computed<PipelineStatus | null>(() => currentJob.value?.status ?? null)
  const progress = computed(() => currentJob.value?.progress ?? 0)
  const outputs = computed(() => currentJob.value?.outputs ?? [])
  const isDone = computed(() =>
    status.value === 'completed' || status.value === 'failed',
  )

  // ── Auxiliares ────────────────────────────────────────────────────────────
  function getBasename(path: string): string {
    return path.split('/').pop() ?? path
  }

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
    logs.value = []
    fileTasks.value = []

    try {
      const { job_id } = await startPipeline({
        translate: translate.value,
        refine_ocr: refineOcr.value,
      })
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

        // Adiciona ao console de logs
        const now = new Date()
        const timestamp = now.toTimeString().split(' ')[0] || ''
        logs.value.push({
          timestamp,
          status: event.status,
          message: event.message,
          file: event.current_file || ''
        })

        // Rastreamento das etapas por arquivo
        if (event.current_file) {
          const filePath = event.current_file
          const fileName = getBasename(filePath)

          let task = fileTasks.value.find((t) => t.filePath === filePath)
          if (!task) {
            task = {
              fileName,
              filePath,
              status: 'pending',
              stages: {
                converting: { name: 'Conversão HTML', status: 'pending', progress: 0 },
                translating: { name: 'Tradução (Ollama)', status: 'pending', progress: 0 },
                exporting: { name: 'Exportação (.docx/.pdf)', status: 'pending', progress: 0 }
              }
            }
            fileTasks.value.push(task)
          }

          task.status = event.status

          // Gerenciar status e tempo de duração das etapas
          if (event.status === 'converting') {
            task.stages.converting.status = 'running'
            if (!task.stages.converting.startTime) {
              task.stages.converting.startTime = Date.now()
            }
            task.stages.converting.progress = 40
          } else if (event.status === 'translating') {
            // Concluir etapa anterior
            if (task.stages.converting.status === 'running') {
              task.stages.converting.status = 'completed'
              task.stages.converting.progress = 100
              if (task.stages.converting.startTime) {
                task.stages.converting.duration = (Date.now() - task.stages.converting.startTime) / 1000
              }
            }
            // Iniciar etapa atual
            task.stages.translating.status = 'running'
            if (!task.stages.translating.startTime) {
              task.stages.translating.startTime = Date.now()
            }
            task.stages.translating.progress = 60
          } else if (event.status === 'exporting') {
            // Concluir etapas anteriores
            if (task.stages.converting.status !== 'completed') {
              task.stages.converting.status = 'completed'
              task.stages.converting.progress = 100
            }
            if (task.stages.translating.status === 'running') {
              task.stages.translating.status = 'completed'
              task.stages.translating.progress = 100
              if (task.stages.translating.startTime) {
                task.stages.translating.duration = (Date.now() - task.stages.translating.startTime) / 1000
              }
            }
            // Iniciar etapa atual
            task.stages.exporting.status = 'running'
            if (!task.stages.exporting.startTime) {
              task.stages.exporting.startTime = Date.now()
            }
            task.stages.exporting.progress = 80
          }
        }

        if (event.status === 'completed') {
          // Finalizar todas as etapas pendentes de todos os arquivos
          fileTasks.value.forEach((task) => {
            Object.values(task.stages).forEach((stage) => {
              if (stage.status === 'running') {
                stage.status = 'completed'
                stage.progress = 100
                if (stage.startTime) {
                  stage.duration = (Date.now() - stage.startTime) / 1000
                }
              } else if (stage.status === 'pending') {
                stage.status = 'completed'
                stage.progress = 100
              }
            })
            task.status = 'completed'
          })

          getJobStatus(jobId).then((job) => {
            currentJob.value = job
            isRunning.value = false
          })
        } else if (event.status === 'failed') {
          // Marcar etapa ativa como falha
          fileTasks.value.forEach((task) => {
            Object.values(task.stages).forEach((stage) => {
              if (stage.status === 'running') {
                stage.status = 'failed'
                if (stage.startTime) {
                  stage.duration = (Date.now() - stage.startTime) / 1000
                }
              }
            })
            if (task.status === 'converting' || task.status === 'translating' || task.status === 'exporting') {
              task.status = 'failed'
            }
          })
          pipelineError.value = event.message
          isRunning.value = false
        } else if (event.status === 'cancelled') {
          // Marcar etapa ativa como falha/cancelada e parar
          fileTasks.value.forEach((task) => {
            Object.values(task.stages).forEach((stage) => {
              if (stage.status === 'running') {
                stage.status = 'failed'
                if (stage.startTime) {
                  stage.duration = (Date.now() - stage.startTime) / 1000
                }
              }
            })
            if (task.status === 'converting' || task.status === 'translating' || task.status === 'exporting' || task.status === 'pending') {
              task.status = 'cancelled'
            }
          })
          progressMessage.value = 'Pipeline cancelada pelo usuário.'
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
    logs.value = []
    fileTasks.value = []
  }

  async function cancelPipeline(): Promise<void> {
    if (!currentJob.value || !isRunning.value) return
    try {
      await cancelPipelineJob(currentJob.value.job_id)
      progressMessage.value = 'Cancelando pipeline…'
    } catch (err: unknown) {
      pipelineError.value = `Erro ao cancelar pipeline: ${(err as Error).message}`
    }
  }

  async function loadConfig(): Promise<void> {
    try {
      const config = await getPipelineConfig()
      if (
        config.source_language &&
        config.target_language &&
        config.source_language.toLowerCase().trim() === config.target_language.toLowerCase().trim()
      ) {
        translate.value = false
        refineOcr.value = true
      } else {
        translate.value = true
        refineOcr.value = true
      }
    } catch (err) {
      console.error('Erro ao carregar as configurações de idioma:', err)
    }
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
    logs,
    fileTasks,
    addFiles,
    removeFile,
    uploadAll,
    runPipeline,
    cancelPipeline,
    translate,
    refineOcr,
    loadConfig,
    reset,
  }
})

