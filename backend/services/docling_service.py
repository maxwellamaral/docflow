"""Integração com o Docling Server para conversão de PDF para HTML."""
from pathlib import Path

import httpx

from backend.core.config import settings


class DoclingConversionError(Exception):
    """Erro durante a conversão via Docling Server."""


class DoclingService:
    """Cliente HTTP para o Docling Server.

    Args:
        base_url: URL base do Docling Server.
    """

    def __init__(self, base_url: str = settings.docling_base_url) -> None:
        self.base_url = base_url.rstrip("/")
        self._endpoint = f"{self.base_url}/v1/convert/file"

    async def convert_pdf_to_html(self, pdf_path: Path) -> bytes:
        """Converte um arquivo PDF para HTML via Docling Server.

        Args:
            pdf_path: Caminho para o arquivo PDF de entrada.

        Returns:
            Conteúdo HTML como bytes.

        Raises:
            DoclingConversionError: Se o servidor retornar erro ou for inacessível.
        """
        async with httpx.AsyncClient(timeout=600) as client:
            with pdf_path.open("rb") as f:
                try:
                    response = await client.post(
                        self._endpoint,
                        files={"files": (pdf_path.name, f, "application/pdf")},
                        data={
                            "to_formats": "html",
                            "image_export_mode": "placeholder",
                            "do_ocr": "true",
                            "ocr_engine": "easyocr",
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise DoclingConversionError(
                        f"Docling retornou status {exc.response.status_code}: "
                        f"{exc.response.text}"
                    ) from exc
                except httpx.RequestError as exc:
                    raise DoclingConversionError(
                        f"Erro ao conectar ao Docling Server: {exc}"
                    ) from exc

        result = response.json()
        html_content: str | None = result.get("document", {}).get("html_content")
        if not html_content:
            raise DoclingConversionError(
                "Docling não retornou html_content na resposta. "
                f"Status: {result.get('status')}, Erros: {result.get('errors', [])}"
            )
        return html_content.encode("utf-8")
