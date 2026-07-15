"""Integração local com o SDK do Docling para conversão de PDF para HTML.

Este serviço utiliza o processamento local via GPU (se disponível) e realiza
a conversão página a página do PDF para fornecer progresso em tempo real.
"""
import asyncio
from collections.abc import Awaitable
from pathlib import Path
import tempfile
from typing import Callable

from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

from backend.core.config import settings


class DoclingConversionError(Exception):
    """Erro durante a conversão usando a biblioteca local do Docling."""


class PipelineCancelledError(Exception):
    """Exceção levantada quando o processamento da pipeline é voluntariamente cancelado."""


class DoclingService:
    """Cliente para conversão local de PDFs usando a biblioteca Docling.

    A conversão é feita localmente tirando proveito da GPU/CPU.
    """

    def __init__(self) -> None:
        # Configura as opções do pipeline do Docling
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    async def convert_pdf_to_html(
        self,
        pdf_path: Path,
        on_page_progress: Callable[[int, int], None] | Callable[[int, int], Awaitable[None]] | None = None
    ) -> bytes:
        """Converte um arquivo PDF para HTML dividindo-o por páginas.

        Permite monitorar o progresso em tempo real página a página.

        Args:
            pdf_path: Caminho para o arquivo PDF.
            on_page_progress: Callback opcional (síncrono ou assíncrono) chamado a cada página processada.

        Returns:
            Bytes do HTML final consolidado com todas as páginas unificadas.

        Raises:
            DoclingConversionError: Se ocorrer qualquer erro na conversão.
        """
        if not pdf_path.exists():
            raise DoclingConversionError(f"Arquivo PDF não encontrado: {pdf_path}")

        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
        except Exception as e:
            raise DoclingConversionError(f"Erro ao abrir e ler o PDF: {e}") from e

        if total_pages == 0:
            raise DoclingConversionError("O arquivo PDF fornecido está vazio e não possui páginas.")

        html_blocks = []
        first_page_head = ""

        for idx in range(total_pages):
            current_page_number = idx + 1
            # Notifica progresso no início de cada página
            if on_page_progress:
                try:
                    if asyncio.iscoroutinefunction(on_page_progress):
                        await on_page_progress(current_page_number, total_pages)
                    else:
                        on_page_progress(current_page_number, total_pages)
                except PipelineCancelledError as e:
                    raise e
                except Exception:
                    pass  # Impede que erros comuns no callback quebrem o pipeline principal

            # Cria um PDF temporário contendo apenas a página atual
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)

            try:
                writer = PdfWriter()
                writer.add_page(reader.pages[idx])
                with open(tmp_path, "wb") as f:
                    writer.write(f)

                # Roda a conversão em thread separada para não travar o loop de eventos
                result = await asyncio.to_thread(self.converter.convert, tmp_path)
                page_html = result.document.export_to_html()

                # Extrai o conteúdo do body e opcionalmente o head da primeira página
                soup = BeautifulSoup(page_html, "html.parser")
                
                # Se for a primeira página, armazena o head com os estilos CSS gerados pelo Docling
                if idx == 0:
                    head_el = soup.find("head")
                    first_page_head = head_el.decode_contents() if head_el else ""

                body_el = soup.find("body")
                if body_el:
                    content = body_el.decode_contents()
                    html_blocks.append(f'<div class="docling-page" data-page="{current_page_number}">{content}</div>')
                else:
                    html_blocks.append(f'<div class="docling-page" data-page="{current_page_number}">{page_html}</div>')

            except Exception as e:
                raise DoclingConversionError(f"Erro ao converter página {current_page_number}/{total_pages}: {e}") from e
            finally:
                # Garante que o PDF temporário seja apagado
                if tmp_path.exists():
                    tmp_path.unlink()

        # Reconstrói um documento HTML consolidado
        unified_content = "\n".join(html_blocks)
        final_html = (
            f"<!DOCTYPE html>\n"
            f"<html>\n"
            f"<head>\n"
            f"<meta charset=\"utf-8\">\n"
            f"{first_page_head}\n"
            f"</head>\n"
            f"<body>\n"
            f"<div class=\"docling-document\">\n"
            f"{unified_content}\n"
            f"</div>\n"
            f"</body>\n"
            f"</html>"
        )

        return final_html.encode("utf-8")
