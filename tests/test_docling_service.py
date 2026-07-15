"""
Testes unitários para DoclingService integrado localmente via SDK.

História de Usuário:
  Como sistema de processamento de documentos,
  Quero converter arquivos PDF em HTML usando a biblioteca do Docling localmente no backend e obter o progresso de cada página convertida,
  Para que o usuário possa ver em tempo real o avanço página por página do documento na interface gráfica.

Critérios de Aceitação:
  - O serviço deve carregar e usar o `DocumentConverter` local da biblioteca `docling`.
  - O serviço deve processar o documento dividindo-o em páginas individuais para monitoramento fino.
  - O serviço deve aceitar um callback de progresso (`on_page_progress`) e chamá-lo para cada página processada.
  - O serviço deve retornar o HTML unificado com o conteúdo de todas as páginas convertidas.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.services.docling_service import DoclingConversionError, DoclingService


async def test_convert_pdf_returns_html_bytes_local(tmp_path: Path) -> None:
    """Deve converter o PDF localmente e retornar o HTML consolidado como bytes."""
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    # Mock das dependências locais da biblioteca docling e pypdf
    with (
        patch("backend.services.docling_service.PdfReader") as MockPdfReader,
        patch("backend.services.docling_service.PdfWriter") as MockPdfWriter,
        patch("backend.services.docling_service.DocumentConverter") as MockConverter,
        patch("backend.services.docling_service.BeautifulSoup") as MockBS,
    ):
        # Configura o leitor de PDF mockado para simular 2 páginas
        mock_reader = MockPdfReader.return_value
        mock_reader.pages = [MagicMock(), MagicMock()]

        # Configura o conversor mockado para retornar um HTML fake
        mock_converter = MockConverter.return_value
        mock_result = MagicMock()
        mock_result.document.export_to_html.return_value = "<html><body><p>Conteudo da pagina</p></body></html>"
        mock_converter.convert.return_value = mock_result

        # Configura o BeautifulSoup para retornar a div interna da página
        mock_soup = MockBS.return_value
        mock_soup.find.return_value = MagicMock(decode_contents=lambda: "<div>Conteudo</div>")

        service = DoclingService()
        result = await service.convert_pdf_to_html(pdf_file)

        assert isinstance(result, bytes)
        assert b"<div>Conteudo</div>" in result


async def test_convert_pdf_calls_progress_callback(tmp_path: Path) -> None:
    """Deve chamar o callback de progresso para cada página convertida."""
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    progress_calls = []
    def callback(current: int, total: int):
        progress_calls.append((current, total))

    with (
        patch("backend.services.docling_service.PdfReader") as MockPdfReader,
        patch("backend.services.docling_service.PdfWriter") as MockPdfWriter,
        patch("backend.services.docling_service.DocumentConverter") as MockConverter,
        patch("backend.services.docling_service.BeautifulSoup") as MockBS,
    ):
        mock_reader = MockPdfReader.return_value
        mock_reader.pages = [MagicMock(), MagicMock(), MagicMock()] # 3 páginas

        mock_converter = MockConverter.return_value
        mock_result = MagicMock()
        mock_result.document.export_to_html.return_value = "<html><body><p>Pagina</p></body></html>"
        mock_converter.convert.return_value = mock_result

        mock_soup = MockBS.return_value
        mock_soup.find.return_value = MagicMock(decode_contents=lambda: "<div>Pagina</div>")

        service = DoclingService()
        await service.convert_pdf_to_html(pdf_file, on_page_progress=callback)

        # Deve chamar o callback 3 vezes (páginas 1, 2 e 3)
        assert len(progress_calls) == 3
        assert progress_calls == [(1, 3), (2, 3), (3, 3)]
