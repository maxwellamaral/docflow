"""
Testes unitários e de integração para a funcionalidade de cancelamento de pipeline.

História de Usuário:
  Como operador de processamento de documentos,
  Quero poder parar o pipeline de um job ativo,
  Para interromper a conversão de novos arquivos caso eu note algum erro ou queira desistir do processamento.
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core import pipeline as pipeline_core
from backend.models.schemas import PipelineStatus

client = TestClient(app)


def test_cancel_nonexistent_job_returns_404() -> None:
    """POST /pipeline/cancel/{id_inexistente} deve retornar 404."""
    response = client.post("/pipeline/cancel/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_cancel_active_job_updates_status() -> None:
    """cancel_job deve marcar um job ativo como CANCELLED e retornar True."""
    job = pipeline_core.create_job()
    job.status = PipelineStatus.CONVERTING

    success = pipeline_core.cancel_job(job.job_id)
    assert success is True
    assert job.status == PipelineStatus.CANCELLED


def test_cancel_completed_job_returns_false() -> None:
    """cancel_job deve retornar False se o job já estiver finalizado."""
    job = pipeline_core.create_job()
    job.status = PipelineStatus.COMPLETED

    success = pipeline_core.cancel_job(job.job_id)
    assert success is False
    assert job.status == PipelineStatus.COMPLETED


@pytest.mark.asyncio
async def test_pipeline_stops_cooperatively_on_cancelled_status(tmp_path: Path) -> None:
    """O loop run_pipeline deve parar imediatamente ao detectar status CANCELLED."""
    job = pipeline_core.create_job()
    pdf_1 = tmp_path / "doc1.pdf"
    pdf_2 = tmp_path / "doc2.pdf"
    pdf_1.write_bytes(b"%PDF-1.4 test")
    pdf_2.write_bytes(b"%PDF-1.4 test")

    events = []
    async def capture(event):
        events.append(event)

    job_dirs = {k: tmp_path / k for k in ("html", "translated", "docx", "pdf", "markdown")}
    for d in job_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    with (
        patch("backend.core.pipeline.StorageService") as MockStorage,
        patch("backend.core.pipeline.DoclingService") as MockDocling,
        patch("backend.core.pipeline.TranslationService"),
        patch("backend.core.pipeline.ConversionService"),
    ):
        mock_storage = MockStorage.return_value
        mock_storage.list_input_pdfs.return_value = [pdf_1, pdf_2]
        mock_storage.create_job_dirs.return_value = job_dirs
        mock_storage.get_output_path.side_effect = (
            lambda dirs, kind, stem, ext: dirs[kind] / f"{stem}{ext}"
        )

        # Simula conversão e cancela o job cooperativamente assim que a primeira página terminar
        async def mock_convert(path, on_page_progress=None):
            # Cancela o job no meio do loop do primeiro arquivo
            job.status = PipelineStatus.CANCELLED
            return b"<html><body>Ok</body></html>"

        MockDocling.return_value.convert_pdf_to_html.side_effect = mock_convert

        await pipeline_core.run_pipeline(job.job_id, on_progress=capture)

    # O pipeline deve terminar com status CANCELLED
    assert job.status == PipelineStatus.CANCELLED
    statuses = [e.status for e in events]
    assert PipelineStatus.CANCELLED in statuses
    # O segundo arquivo (pdf_2) não deve ser processado, ou seja, converter só foi chamado 1 vez
    assert MockDocling.return_value.convert_pdf_to_html.call_count == 1


@pytest.mark.asyncio
async def test_pipeline_raises_pipeline_cancelled_error_and_stops_immediately(tmp_path: Path) -> None:
    """O callback de progresso deve lançar PipelineCancelledError e parar o loop do Docling imediatamente."""
    from backend.services.docling_service import PipelineCancelledError

    job = pipeline_core.create_job()
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    events = []
    async def capture(event):
        events.append(event)

    job_dirs = {k: tmp_path / k for k in ("html", "translated", "docx", "pdf", "markdown")}
    for d in job_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    with (
        patch("backend.core.pipeline.StorageService") as MockStorage,
        patch("backend.core.pipeline.DoclingService") as MockDocling,
        patch("backend.core.pipeline.TranslationService"),
        patch("backend.core.pipeline.ConversionService"),
    ):
        mock_storage = MockStorage.return_value
        mock_storage.list_input_pdfs.return_value = [pdf_path]
        mock_storage.create_job_dirs.return_value = job_dirs

        # Simula cancelamento do job durante o callback
        job.status = PipelineStatus.CANCELLED

        # A chamada de convert_pdf_to_html deve propagar PipelineCancelledError
        MockDocling.return_value.convert_pdf_to_html.side_effect = PipelineCancelledError("Cancelado")

        await pipeline_core.run_pipeline(job.job_id, on_progress=capture)

    # O status final do job deve ser CANCELLED e o evento com status CANCELLED emitido
    assert job.status == PipelineStatus.CANCELLED
    statuses = [e.status for e in events]
    assert PipelineStatus.CANCELLED in statuses
