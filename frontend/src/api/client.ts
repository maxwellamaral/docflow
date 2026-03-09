import axios from 'axios'

const api = axios.create({ baseURL: '/' })

export interface UploadResponse {
  filename: string
  message: string
}

export interface PipelineStartResponse {
  job_id: string
  message: string
}

export type PipelineStatus =
  | 'pending'
  | 'converting'
  | 'translating'
  | 'exporting'
  | 'completed'
  | 'failed'

export interface PipelineJob {
  job_id: string
  status: PipelineStatus
  created_at: string
  input_files: string[]
  outputs: string[]
  current_file: string | null
  progress: number
  error: string | null
}

export interface ProgressEvent {
  job_id: string
  status: PipelineStatus
  progress: number
  current_file: string | null
  message: string
}

export const uploadPdf = (file: File): Promise<UploadResponse> => {
  const form = new FormData()
  form.append('file', file)
  return api.post<UploadResponse>('/upload', form).then((r) => r.data)
}

export const startPipeline = (): Promise<PipelineStartResponse> =>
  api.post<PipelineStartResponse>('/pipeline/start').then((r) => r.data)

export const getJobStatus = (jobId: string): Promise<PipelineJob> =>
  api.get<PipelineJob>(`/pipeline/status/${jobId}`).then((r) => r.data)

export const connectProgressWebSocket = (
  jobId: string,
  onEvent: (event: ProgressEvent) => void,
  onClose?: () => void,
): WebSocket => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const wsHost = window.location.hostname
  const wsPort = import.meta.env.DEV ? '8000' : window.location.port
  const ws = new WebSocket(`${wsProtocol}://${wsHost}:${wsPort}/pipeline/ws/${jobId}`)

  ws.onmessage = (e) => {
    try {
      onEvent(JSON.parse(e.data) as ProgressEvent)
    } catch {
      // mensagem malformada — ignora
    }
  }
  ws.onclose = () => onClose?.()
  return ws
}

export const buildDownloadUrl = (relativePath: string): string =>
  `/download/${relativePath}`
