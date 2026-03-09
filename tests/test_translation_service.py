"""
Testes unitários para TranslationService.

História de Usuário:
  Como pipeline de processamento,
  Quero traduzir o conteúdo de HTMLs para Português (Brasil) via Ollama,
  Para gerar documentos acessíveis ao público-alvo.
"""
import json

import httpx
import pytest
import respx

from backend.services.translation_service import TranslationError, TranslationService

OLLAMA_URL = "http://localhost:11434"
SAMPLE_HTML = """<html><body>
<h1>Introduction</h1>
<p>This is a test paragraph with relevant content.</p>
<h2>Methods</h2>
<p>Standard procedures were applied.</p>
</body></html>"""


def _make_service() -> TranslationService:
    return TranslationService(
        base_url=OLLAMA_URL,
        model="translategemma:4b",
        target_language="Portuguese (Brazil)",
        timeout=30,
    )


@respx.mock
async def test_translate_html_calls_ollama_endpoint() -> None:
    """Deve realizar POST para /api/generate do Ollama."""
    route = respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "Introdução", "done": True})
    )

    await _make_service().translate_html(SAMPLE_HTML)

    assert route.called


@respx.mock
async def test_translate_html_uses_configured_model() -> None:
    """Deve enviar o request com o modelo translategemma:4b."""
    route = respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "texto traduzido", "done": True})
    )

    await _make_service().translate_html(SAMPLE_HTML)

    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "translategemma:4b"


@respx.mock
async def test_translate_html_returns_html_string() -> None:
    """Deve retornar uma string que ainda contém tags HTML."""
    respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "Texto traduzido", "done": True})
    )

    result = await _make_service().translate_html(SAMPLE_HTML)

    assert isinstance(result, str)
    assert "<html" in result
    assert "<body" in result


@respx.mock
async def test_translate_raises_on_ollama_http_error() -> None:
    """Deve lançar TranslationError quando Ollama retornar erro HTTP."""
    respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    with pytest.raises(TranslationError):
        await _make_service().translate_html(SAMPLE_HTML)


@respx.mock
async def test_translate_raises_on_connection_error() -> None:
    """Deve lançar TranslationError quando Ollama não estiver acessível."""
    respx.post(f"{OLLAMA_URL}/api/generate").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    with pytest.raises(TranslationError):
        await _make_service().translate_html(SAMPLE_HTML)


@respx.mock
async def test_translate_skips_empty_elements() -> None:
    """Não deve enviar requests para elementos sem texto."""
    html = "<html><body><p></p><p>   </p><p>Real content here.</p></body></html>"
    route = respx.post(f"{OLLAMA_URL}/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "Conteúdo real aqui.", "done": True})
    )

    await _make_service().translate_html(html)

    # Apenas 1 parágrafo tem texto real
    assert route.call_count == 1
