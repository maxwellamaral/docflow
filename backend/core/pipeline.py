"""Orquestrador assíncrono da pipeline de processamento de documentos."""
import uuid
from collections.abc import Awaitable, Callable
from datetime import date, datetime

from backend.core.config import settings
from backend.models.schemas import PipelineJob, PipelineStatus, ProgressEvent
from backend.services.conversion_service import ConversionService
from backend.services.docling_service import DoclingService
from backend.services.storage_service import StorageService
from backend.services.translation_service import TranslationService

# Registro em memória dos jobs ativos
_jobs: dict[str, PipelineJob] = {}

ProgressCallback = Callable[[ProgressEvent], Awaitable[None]]


def create_job() -> PipelineJob:
    """Cria e registra um novo job de pipeline.

    Returns:
        Job criado com status PENDING.
    """
    job_id = str(uuid.uuid4())
    job = PipelineJob(
        job_id=job_id,
        status=PipelineStatus.PENDING,
        created_at=datetime.utcnow(),
    )
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> PipelineJob | None:
    """Retorna o job pelo ID, ou None se não existir.

    Args:
        job_id: Identificador único do job.

    Returns:
        PipelineJob correspondente ou None.
    """
    return _jobs.get(job_id)


def list_jobs() -> list[PipelineJob]:
    """Retorna todos os jobs registrados.

    Returns:
        Lista de todos os jobs.
    """
    return list(_jobs.values())


async def run_pipeline(
    job_id: str,
    on_progress: ProgressCallback | None = None,
) -> PipelineJob:
    """Executa a pipeline completa para todos os PDFs em ./input.

    Etapas por arquivo:
      1. PDF → HTML via Docling Server
      2. HTML → HTML traduzido via Ollama
      3. HTML traduzido → .docx e .pdf

    Args:
        job_id: ID do job a executar.
        on_progress: Callback assíncrono chamado a cada evento de progresso.

    Returns:
        Job atualizado com status final.

    Raises:
        Exception: Qualquer erro durante o processamento reraise após marcar o job.
    """
    storage = StorageService()
    docling = DoclingService()
    translation = TranslationService()
    conversion = ConversionService()

    job = _jobs[job_id]
    job_dirs = storage.create_job_dirs(date.today())

    async def emit(
        status: PipelineStatus,
        progress: int,
        current_file: str | None = None,
        message: str = "",
    ) -> None:
        job.status = status
        job.progress = progress
        job.current_file = current_file
        event = ProgressEvent(
            job_id=job_id,
            status=status,
            progress=progress,
            current_file=current_file,
            message=message,
        )
        if on_progress:
            await on_progress(event)

    try:
        pdf_files = storage.list_input_pdfs()
        job.input_files = [str(p) for p in pdf_files]
        total = len(pdf_files)

        if total == 0:
            await emit(PipelineStatus.COMPLETED, 100, message="Nenhum PDF encontrado em ./input")
            return job

        for idx, pdf_path in enumerate(pdf_files):
            stem = pdf_path.stem
            file_base_progress = int((idx / total) * 100)
            step_size = 100 // total

            # Etapa 1: PDF → HTML
            await emit(
                PipelineStatus.CONVERTING,
                file_base_progress,
                str(pdf_path),
                f"Convertendo {pdf_path.name} para HTML…",
            )
            html_bytes = await docling.convert_pdf_to_html(pdf_path)
            html_path = storage.get_output_path(job_dirs, "html", stem, ".html")
            html_path.write_bytes(html_bytes)

            # Etapa 2: Tradução do HTML
            await emit(
                PipelineStatus.TRANSLATING,
                file_base_progress + step_size // 3,
                str(pdf_path),
                f"Traduzindo {pdf_path.name}…",
            )
            html_content = html_bytes.decode("utf-8", errors="replace")
            translated_html = await translation.translate_html(html_content)
            translated_path = storage.get_output_path(job_dirs, "translated", stem, ".html")
            translated_path.write_text(translated_html, encoding="utf-8")

            # Etapa 3: Exportação para .docx e .pdf
            await emit(
                PipelineStatus.EXPORTING,
                file_base_progress + (step_size * 2) // 3,
                str(pdf_path),
                f"Exportando {pdf_path.name} para .docx e .pdf…",
            )
            docx_path = storage.get_output_path(job_dirs, "docx", stem, ".docx")
            conversion.html_to_docx(translated_html, docx_path)

            pdf_out_path = storage.get_output_path(job_dirs, "pdf", stem, ".pdf")
            conversion.html_to_pdf(translated_html, pdf_out_path)

            job.outputs.extend(
                [
                    str(html_path),
                    str(translated_path),
                    str(docx_path),
                    str(pdf_out_path),
                ]
            )

        await emit(PipelineStatus.COMPLETED, 100, message="Pipeline concluída com sucesso!")

    except Exception as exc:
        job.status = PipelineStatus.FAILED
        job.error = str(exc)
        await emit(PipelineStatus.FAILED, job.progress, message=f"Erro: {exc}")
        raise

    return job
