"""
Testes para validação do progresso em tempo real por blocos no Ollama (TranslationService).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.translation_service import TranslationService


@pytest.mark.asyncio
async def test_translate_html_calls_on_block_progress() -> None:
    """O método translate_html deve invocar o callback on_block_progress para cada bloco traduzido."""
    html = "<html><body><p>Bloco 1</p><h2>Bloco 2</h2><p>Bloco 3</p></body></html>"
    service = TranslationService()

    # Mock do processador de texto para retornar texto limpo sem erros
    service._process_text = AsyncMock(side_effect=lambda text, client, mode: f"Cleaned: {text}")

    progress_calls = []
    async def on_progress(current: int, total: int) -> None:
        progress_calls.append((current, total))

    # Executa com 3 blocos válidos (<p>, <h2>, <p>)
    result = await service.translate_html(html, mode="refine", on_block_progress=on_progress)

    # Devem ocorrer exatamente 3 chamadas ao callback de progresso
    assert len(progress_calls) == 3
    assert progress_calls == [(1, 3), (2, 3), (3, 3)]
    assert "Cleaned: Bloco 1" in result
    assert "Cleaned: Bloco 2" in result
    assert "Cleaned: Bloco 3" in result
