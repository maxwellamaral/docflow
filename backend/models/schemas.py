"""Modelos Pydantic para validação e serialização de dados da API."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class PipelineStatus(str, Enum):
    """Estados possíveis de um job de pipeline."""

    PENDING = "pending"
    CONVERTING = "converting"
    TRANSLATING = "translating"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineJob(BaseModel):
    """Representa o estado completo de um job de processamento.

    Attributes:
        job_id: Identificador único do job (UUID).
        status: Estado atual do job.
        created_at: Momento de criação do job.
        input_files: Lista de caminhos dos PDFs a processar.
        outputs: Lista de caminhos dos arquivos gerados.
        current_file: Arquivo sendo processado no momento.
        progress: Percentual de conclusão (0–100).
        error: Mensagem de erro, se o job falhou.
    """

    job_id: str
    status: PipelineStatus = PipelineStatus.PENDING
    created_at: datetime
    input_files: list[str] = []
    outputs: list[str] = []
    current_file: str | None = None
    progress: int = 0
    error: str | None = None


class PipelineStartResponse(BaseModel):
    """Resposta ao iniciar uma pipeline."""

    job_id: str
    message: str


class UploadResponse(BaseModel):
    """Resposta ao enviar um arquivo."""

    filename: str
    message: str


class ProgressEvent(BaseModel):
    """Evento de progresso emitido via WebSocket.

    Attributes:
        job_id: Identificador do job relacionado.
        status: Status atual.
        progress: Percentual de conclusão.
        current_file: Arquivo em processamento.
        message: Mensagem descritiva da etapa.
    """

    job_id: str
    status: PipelineStatus
    progress: int
    current_file: str | None = None
    message: str = ""
