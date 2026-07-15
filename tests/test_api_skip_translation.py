"""
Testes para a funcionalidade de pular tradução e refinar OCR na pipeline.

História de Usuário:
  Como operador de processamento de documentos em português,
  Quero poder indicar que a tradução pelo Ollama deve ser ignorada,
  Para economizar recursos de GPU e tempo de processamento quando o PDF já está em português.
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock, ANY
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core import pipeline as pipeline_core
from backend.models.schemas import PipelineStatus

client = TestClient(app)


def test_get_pipeline_config_returns_languages() -> None:
    """GET /pipeline/config deve retornar as configurações de idioma do backend."""
    response = client.get("/pipeline/config")
    assert response.status_code == 200
    data = response.json()
    assert "source_language" in data
    assert "target_language" in data


@pytest.mark.asyncio
async def test_run_pipeline_refines_ocr_instead_of_translating(tmp_path: Path) -> None:
    """Quando translate=False e refine_ocr=True, a tradução é pulada e o refinamento é chamado."""
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
            return_value=b"<html><body>Original Content</body></html>"
        )
        MockTranslation.return_value.translate_html = AsyncMock(
            return_value="<html><body>Refined Content</body></html>"
        )

        # Executa a pipeline passando translate=False e refine_ocr=True
        await pipeline_core.run_pipeline(
            job.job_id,
            on_progress=capture,
            translate=False,
            refine_ocr=True
        )

    # O status final do job deve ser COMPLETED e o TranslationService deve ter sido chamado com mode="refine"
    assert job.status == PipelineStatus.COMPLETED
    MockTranslation.return_value.translate_html.assert_called_once_with(
        "<html><body>Original Content</body></html>",
        mode="refine",
        on_block_progress=ANY
    )

    # As exportações (html_to_docx e html_to_pdf) devem ter sido chamadas com o conteúdo refinado
    MockConversion.return_value.html_to_docx.assert_called_once()
    args, _ = MockConversion.return_value.html_to_docx.call_args
    assert "Refined Content" in args[0]


def test_html_to_docx_embeds_base64_images(tmp_path: Path) -> None:
    """O ConversionService deve embutir imagens base64 encontradas no HTML no arquivo .docx."""
    from backend.services.conversion_service import ConversionService

    html = '<html><body><h1>Titulo</h1><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="></body></html>'
    docx_path = tmp_path / "output.docx"

    service = ConversionService()

    with patch("backend.services.conversion_service.Document") as MockDoc:
        mock_doc_instance = MockDoc.return_value
        service.html_to_docx(html, docx_path)

        # add_picture deve ter sido chamada com os bytes decodificados da imagem base64
        mock_doc_instance.add_picture.assert_called_once()
