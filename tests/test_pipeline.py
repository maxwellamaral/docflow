"""
Testes unitários para o orquestrador Pipeline.

História de Usuário:
  Como usuário,
  Quero iniciar uma pipeline e receber atualizações de progresso,
  Para saber em qual etapa meu documento está sendo processado.
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core import pipeline as pipeline_core
from backend.models.schemas import PipelineStatus


def test_create_job_returns_pending_job() -> None:
    """Deve criar e registrar um job com status PENDING."""
    job = pipeline_core.create_job()

    assert job.status == PipelineStatus.PENDING
    assert job.job_id != ""
    assert pipeline_core.get_job(job.job_id) is job


async def test_pipeline_completes_immediately_with_no_pdfs(tmp_path: Path) -> None:
    """Pipeline deve completar com status COMPLETED se não há PDFs em ./input."""
    job = pipeline_core.create_job()
    events = []

    async def capture(event):
        events.append(event)

    with (
        patch("backend.core.pipeline.StorageService") as MockStorage,
        patch("backend.core.pipeline.DoclingService"),
        patch("backend.core.pipeline.TranslationService"),
        patch("backend.core.pipeline.ConversionService"),
    ):
        mock_storage = MockStorage.return_value
        mock_storage.list_input_pdfs.return_value = []
        mock_storage.create_job_dirs.return_value = {}

        await pipeline_core.run_pipeline(job.job_id, on_progress=capture)

    assert job.status == PipelineStatus.COMPLETED
    assert any(e.status == PipelineStatus.COMPLETED for e in events)


async def test_pipeline_emits_progress_events_for_each_stage(tmp_path: Path) -> None:
    """Deve emitir eventos CONVERTING, TRANSLATING e EXPORTING para cada PDF."""
    job = pipeline_core.create_job()
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF test")

    events = []

    async def capture(event):
        events.append(event)

    job_dirs = {
        "html": tmp_path / "html",
        "translated": tmp_path / "translated",
        "docx": tmp_path / "docx",
        "pdf": tmp_path / "pdf",
    }
    for d in job_dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    with (
        patch("backend.core.pipeline.StorageService") as MockStorage,
        patch("backend.core.pipeline.DoclingService") as MockDocling,
        patch("backend.core.pipeline.TranslationService") as MockTranslation,
        patch("backend.core.pipeline.ConversionService") as MockConversion,
    ):
        mock_storage = MockStorage.return_value
        mock_storage.list_input_pdfs.return_value = [pdf_path]
        mock_storage.create_job_dirs.return_value = job_dirs
        mock_storage.get_output_path.side_effect = (
            lambda dirs, kind, stem, ext: dirs[kind] / f"{stem}{ext}"
        )

        MockDocling.return_value.convert_pdf_to_html = AsyncMock(
            return_value=b"<html><body><p>Test</p></body></html>"
        )
        MockTranslation.return_value.translate_html = AsyncMock(
            return_value="<html><body><p>Teste</p></body></html>"
        )
        MockConversion.return_value.html_to_docx = MagicMock()
        MockConversion.return_value.html_to_pdf = MagicMock()

        await pipeline_core.run_pipeline(job.job_id, on_progress=capture)

    statuses = [e.status for e in events]
    assert PipelineStatus.CONVERTING in statuses
    assert PipelineStatus.TRANSLATING in statuses
    assert PipelineStatus.EXPORTING in statuses
    assert PipelineStatus.COMPLETED in statuses


async def test_pipeline_marks_job_failed_on_error(tmp_path: Path) -> None:
    """Deve marcar o job como FAILED quando um serviço lançar exceção."""
    job = pipeline_core.create_job()
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF test")

    job_dirs = {k: tmp_path / k for k in ("html", "translated", "docx", "pdf")}
    for d in job_dirs.values():
        d.mkdir()

    with (
        patch("backend.core.pipeline.StorageService") as MockStorage,
        patch("backend.core.pipeline.DoclingService") as MockDocling,
        patch("backend.core.pipeline.TranslationService"),
        patch("backend.core.pipeline.ConversionService"),
    ):
        mock_storage = MockStorage.return_value
        mock_storage.list_input_pdfs.return_value = [pdf_path]
        mock_storage.create_job_dirs.return_value = job_dirs
        mock_storage.get_output_path.side_effect = (
            lambda dirs, kind, stem, ext: dirs[kind] / f"{stem}{ext}"
        )
        MockDocling.return_value.convert_pdf_to_html = AsyncMock(
            side_effect=Exception("Docling unavailable")
        )

        with pytest.raises(Exception, match="Docling unavailable"):
            await pipeline_core.run_pipeline(job.job_id)

    assert job.status == PipelineStatus.FAILED
    assert job.error is not None
