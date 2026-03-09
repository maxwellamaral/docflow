"""
Testes unitários para ConversionService.

História de Usuário:
  Como pipeline de processamento,
  Quero converter HTMLs traduzidos para .docx e .pdf,
  Para entregar os documentos em formatos amplamente utilizados.
"""
from pathlib import Path

import pytest
from docx import Document

from backend.services.conversion_service import ConversionService

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Documento de Teste</title></head>
<body>
<h1>Título do Documento</h1>
<h2>Introdução</h2>
<p>Este é um parágrafo com conteúdo relevante para o teste.</p>
<h3>Métodos</h3>
<p>Os procedimentos foram aplicados conforme o padrão estabelecido.</p>
<ul>
  <li>Item 1 da lista</li>
  <li>Item 2 da lista</li>
</ul>
</body></html>"""


def test_html_to_docx_creates_file(tmp_path: Path) -> None:
    """Deve criar o arquivo .docx no caminho especificado."""
    output = tmp_path / "output.docx"

    ConversionService().html_to_docx(SAMPLE_HTML, output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_html_to_docx_produces_valid_docx(tmp_path: Path) -> None:
    """O arquivo gerado deve ser um .docx válido e legível."""
    output = tmp_path / "output.docx"

    ConversionService().html_to_docx(SAMPLE_HTML, output)
    doc = Document(str(output))

    texts = [p.text for p in doc.paragraphs if p.text]
    assert len(texts) > 0
    assert any("Título" in t for t in texts)


def test_html_to_docx_includes_headings(tmp_path: Path) -> None:
    """Deve incluir os headings do HTML como parágrafos de heading no docx."""
    output = tmp_path / "output.docx"

    ConversionService().html_to_docx(SAMPLE_HTML, output)
    doc = Document(str(output))

    heading_texts = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
    assert len(heading_texts) > 0


def test_html_to_pdf_creates_file(tmp_path: Path) -> None:
    """Deve criar o arquivo .pdf no caminho especificado."""
    output = tmp_path / "output.pdf"

    ConversionService().html_to_pdf(SAMPLE_HTML, output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_html_to_pdf_starts_with_pdf_header(tmp_path: Path) -> None:
    """O arquivo PDF gerado deve começar com o header %PDF."""
    output = tmp_path / "output.pdf"

    ConversionService().html_to_pdf(SAMPLE_HTML, output)

    assert output.read_bytes()[:4] == b"%PDF"
