"""
Testes unitários para DoclingService.

História de Usuário:
  Como pipeline de processamento,
  Quero converter PDFs para HTML via Docling Server,
  Para extrair o conteúdo estruturado do documento.
"""
from pathlib import Path

import httpx
import pytest
import respx

from backend.services.docling_service import DoclingConversionError, DoclingService

DOCLING_URL = "http://localhost:5001"
SAMPLE_HTML = "<html><body><h1>Test Document</h1><p>Content.</p></body></html>"
SAMPLE_RESPONSE = {"document": {"filename": "test.pdf", "html_content": SAMPLE_HTML}, "status": "success", "errors": [], "processing_time": 1.0}


@respx.mock
async def test_convert_pdf_calls_correct_endpoint(tmp_path: Path) -> None:
    """Deve realizar POST para /v1/convert/file com o arquivo PDF."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    route = respx.post(f"{DOCLING_URL}/v1/convert/file").mock(
        return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
    )

    service = DoclingService(base_url=DOCLING_URL)
    result = await service.convert_pdf_to_html(pdf_file)

    assert route.called
    assert result == SAMPLE_HTML.encode("utf-8")


@respx.mock
async def test_convert_pdf_returns_html_bytes(tmp_path: Path) -> None:
    """Deve retornar o conteúdo HTML como bytes."""
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    respx.post(f"{DOCLING_URL}/v1/convert/file").mock(
        return_value=httpx.Response(200, json=SAMPLE_RESPONSE)
    )

    service = DoclingService(base_url=DOCLING_URL)
    result = await service.convert_pdf_to_html(pdf_file)

    assert isinstance(result, bytes)
    assert b"<html" in result


@respx.mock
async def test_convert_pdf_raises_on_http_error(tmp_path: Path) -> None:
    """Deve lançar DoclingConversionError quando o servidor retornar erro HTTP."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    respx.post(f"{DOCLING_URL}/v1/convert/file").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    service = DoclingService(base_url=DOCLING_URL)
    with pytest.raises(DoclingConversionError, match="500"):
        await service.convert_pdf_to_html(pdf_file)


@respx.mock
async def test_convert_pdf_raises_on_connection_error(tmp_path: Path) -> None:
    """Deve lançar DoclingConversionError quando o servidor não estiver acessível."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    respx.post(f"{DOCLING_URL}/v1/convert/file").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    service = DoclingService(base_url=DOCLING_URL)
    with pytest.raises(DoclingConversionError):
        await service.convert_pdf_to_html(pdf_file)
