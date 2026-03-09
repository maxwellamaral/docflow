"""
Testes unitários para DoclingService.

História de Usuário:
  Como pipeline de processamento,
  Quero converter PDFs para HTML via Docling Server,
  Para extrair o conteúdo estruturado do documento.
"""
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import respx

from backend.services.docling_service import DoclingConversionError, DoclingService

DOCLING_URL = "http://localhost:5001"
TASK_ID = "abc-123"
SAMPLE_HTML = "<html><body><h1>Test Document</h1><p>Content.</p></body></html>"

SUBMIT_RESPONSE = {"task_id": TASK_ID, "task_status": "pending", "task_type": "convert"}
POLL_RESPONSE_DONE = {"task_id": TASK_ID, "task_status": "success", "task_type": "convert"}
RESULT_RESPONSE = {
    "document": {"filename": "test.pdf", "html_content": SAMPLE_HTML},
    "status": "success",
    "errors": [],
    "processing_time": 1.0,
}


def _no_sleep():
    """Patch asyncio.sleep para não esperar nos testes."""
    return patch("backend.services.docling_service.asyncio.sleep", return_value=None)


@respx.mock
async def test_convert_pdf_calls_correct_endpoint(tmp_path: Path) -> None:
    """Deve realizar POST para /v1/convert/file/async com o arquivo PDF."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    submit = respx.post(f"{DOCLING_URL}/v1/convert/file/async").mock(
        return_value=httpx.Response(200, json=SUBMIT_RESPONSE)
    )
    respx.get(f"{DOCLING_URL}/v1/status/poll/{TASK_ID}").mock(
        return_value=httpx.Response(200, json=POLL_RESPONSE_DONE)
    )
    respx.get(f"{DOCLING_URL}/v1/result/{TASK_ID}").mock(
        return_value=httpx.Response(200, json=RESULT_RESPONSE)
    )

    with _no_sleep():
        service = DoclingService(base_url=DOCLING_URL)
        result = await service.convert_pdf_to_html(pdf_file)

    assert submit.called
    assert result == SAMPLE_HTML.encode("utf-8")


@respx.mock
async def test_convert_pdf_returns_html_bytes(tmp_path: Path) -> None:
    """Deve retornar o conteúdo HTML como bytes."""
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    respx.post(f"{DOCLING_URL}/v1/convert/file/async").mock(
        return_value=httpx.Response(200, json=SUBMIT_RESPONSE)
    )
    respx.get(f"{DOCLING_URL}/v1/status/poll/{TASK_ID}").mock(
        return_value=httpx.Response(200, json=POLL_RESPONSE_DONE)
    )
    respx.get(f"{DOCLING_URL}/v1/result/{TASK_ID}").mock(
        return_value=httpx.Response(200, json=RESULT_RESPONSE)
    )

    with _no_sleep():
        service = DoclingService(base_url=DOCLING_URL)
        result = await service.convert_pdf_to_html(pdf_file)

    assert isinstance(result, bytes)
    assert b"<html" in result


@respx.mock
async def test_convert_pdf_polls_until_success(tmp_path: Path) -> None:
    """Deve continuar polling enquanto task_status for 'pending' ou 'started'."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    respx.post(f"{DOCLING_URL}/v1/convert/file/async").mock(
        return_value=httpx.Response(200, json=SUBMIT_RESPONSE)
    )
    poll_route = respx.get(f"{DOCLING_URL}/v1/status/poll/{TASK_ID}").mock(
        side_effect=[
            httpx.Response(200, json={"task_id": TASK_ID, "task_status": "pending"}),
            httpx.Response(200, json={"task_id": TASK_ID, "task_status": "started"}),
            httpx.Response(200, json=POLL_RESPONSE_DONE),
        ]
    )
    respx.get(f"{DOCLING_URL}/v1/result/{TASK_ID}").mock(
        return_value=httpx.Response(200, json=RESULT_RESPONSE)
    )

    with _no_sleep():
        service = DoclingService(base_url=DOCLING_URL)
        result = await service.convert_pdf_to_html(pdf_file)

    assert poll_route.call_count == 3
    assert result == SAMPLE_HTML.encode("utf-8")


@respx.mock
async def test_convert_pdf_raises_on_http_error(tmp_path: Path) -> None:
    """Deve lançar DoclingConversionError quando o submit retornar erro HTTP."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    respx.post(f"{DOCLING_URL}/v1/convert/file/async").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    with _no_sleep():
        service = DoclingService(base_url=DOCLING_URL)
        with pytest.raises(DoclingConversionError, match="500"):
            await service.convert_pdf_to_html(pdf_file)


@respx.mock
async def test_convert_pdf_raises_on_connection_error(tmp_path: Path) -> None:
    """Deve lançar DoclingConversionError quando o servidor não estiver acessível."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    respx.post(f"{DOCLING_URL}/v1/convert/file/async").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    with _no_sleep():
        service = DoclingService(base_url=DOCLING_URL)
        with pytest.raises(DoclingConversionError):
            await service.convert_pdf_to_html(pdf_file)
