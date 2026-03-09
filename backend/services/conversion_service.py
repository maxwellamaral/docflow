"""Conversão de HTML para os formatos Word (.docx) e PDF."""
from pathlib import Path

import weasyprint
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn


class ConversionService:
    """Serviço de conversão de HTML para .docx e .pdf."""

    def html_to_docx(self, html_content: str, output_path: Path) -> Path:
        """Converte um HTML para formato Word (.docx).

        Extrai headings, parágrafos e itens de lista do HTML e os mapeia
        para os estilos correspondentes do python-docx.

        Args:
            html_content: Conteúdo HTML de entrada.
            output_path: Caminho de destino para o arquivo .docx.

        Returns:
            Caminho do arquivo .docx gerado.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        doc = Document()

        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
            text = element.get_text(strip=True)
            if not text:
                continue

            tag = element.name
            if tag == "h1":
                doc.add_heading(text, level=1)
            elif tag == "h2":
                doc.add_heading(text, level=2)
            elif tag in ("h3", "h4"):
                doc.add_heading(text, level=3)
            elif tag in ("h5", "h6"):
                doc.add_heading(text, level=4)
            elif tag == "li":
                try:
                    doc.add_paragraph(text, style="List Bullet")
                except KeyError:
                    doc.add_paragraph(f"• {text}")
            else:
                doc.add_paragraph(text)

        doc.save(output_path)
        return output_path

    def html_to_pdf(self, html_content: str, output_path: Path) -> Path:
        """Converte um HTML para PDF usando WeasyPrint.

        Args:
            html_content: Conteúdo HTML de entrada.
            output_path: Caminho de destino para o arquivo .pdf.

        Returns:
            Caminho do arquivo .pdf gerado.
        """
        weasyprint.HTML(string=html_content).write_pdf(str(output_path))
        return output_path
