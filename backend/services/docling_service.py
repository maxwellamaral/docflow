"""Integração com o Docling Server para conversão de PDF para HTML.

Fluxo async:
  1. POST /v1/convert/file/async  → { task_id, task_status }
  2. GET  /v1/status/poll/{task_id} → poll até task_status == "success"
  3. GET  /v1/result/{task_id}      → { document: { html_content } }
"""
import asyncio
from pathlib import Path

import httpx

from backend.core.config import settings

# Status terminais retornados pelo Docling Server
_TERMINAL_STATUS = {"success", "partial_success", "failure", "skipped"}
_POLL_INTERVAL = 3.0   # segundos entre cada poll
_MAX_POLLS = 200       # 200 × 3 s = 10 min de timeout máximo


class DoclingConversionError(Exception):
    """Erro durante a conversão via Docling Server."""


class DoclingService:
    """Cliente HTTP para o Docling Server (fluxo assíncrono).

    Args:
        base_url: URL base do Docling Server.
    """

    def __init__(self, base_url: str = settings.docling_base_url) -> None:
        self.base_url = base_url.rstrip("/")
        self._submit_url = f"{self.base_url}/v1/convert/file/async"
        self._poll_url = f"{self.base_url}/v1/status/poll"
        self._result_url = f"{self.base_url}/v1/result"

    async def convert_pdf_to_html(self, pdf_path: Path) -> bytes:
        """Converte um arquivo PDF para HTML via Docling Server.

        Submete a tarefa de forma assíncrona, aguarda a conclusão via polling
        e retorna o conteúdo HTML gerado.

        Args:
            pdf_path: Caminho para o arquivo PDF de entrada.

        Returns:
            Conteúdo HTML como bytes.

        Raises:
            DoclingConversionError: Se o servidor retornar erro ou for inacessível.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            task_id = await self._submit(client, pdf_path)
            await self._wait_for_completion(client, task_id)
            return await self._fetch_result(client, task_id)

    # ── Passos internos ────────────────────────────────────────────────────────

    async def _submit(self, client: httpx.AsyncClient, pdf_path: Path) -> str:
        """Envia o PDF para conversão e retorna o task_id."""
        with pdf_path.open("rb") as f:
            try:
                response = await client.post(
                    self._submit_url,
                    files={"files": (pdf_path.name, f, "application/pdf")},
                    data={
                        "to_formats": "html",
                        "image_export_mode": "embedded",
                        "do_ocr": "true",
                        "ocr_engine": "easyocr",
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise DoclingConversionError(
                    f"Docling retornou status {exc.response.status_code} ao submeter: "
                    f"{exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise DoclingConversionError(
                    f"Erro ao conectar ao Docling Server: {exc}"
                ) from exc

        data = response.json()
        task_id: str | None = data.get("task_id")
        if not task_id:
            raise DoclingConversionError(
                f"Docling não retornou task_id. Resposta: {data}"
            )
        return task_id

    async def _wait_for_completion(
        self, client: httpx.AsyncClient, task_id: str
    ) -> None:
        """Aguarda o Docling Server concluir a tarefa via polling."""
        for _ in range(_MAX_POLLS):
            await asyncio.sleep(_POLL_INTERVAL)
            try:
                resp = await client.get(f"{self._poll_url}/{task_id}")
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise DoclingConversionError(
                    f"Erro ao consultar status da tarefa {task_id}: "
                    f"HTTP {exc.response.status_code}"
                ) from exc
            except httpx.RequestError as exc:
                raise DoclingConversionError(
                    f"Erro de rede ao consultar status: {exc}"
                ) from exc

            status = resp.json().get("task_status", "")
            if status in _TERMINAL_STATUS:
                if status == "failure":
                    # Tenta buscar detalhes do resultado para mensagem mais útil
                    details = ""
                    try:
                        r = await client.get(f"{self._result_url}/{task_id}")
                        if r.is_success:
                            body = r.json()
                            errors = body.get("errors") or []
                            details = "; ".join(
                                e.get("error_message", str(e)) for e in errors
                            ) if errors else str(body)
                    except Exception:
                        pass
                    raise DoclingConversionError(
                        f"Docling reportou falha na tarefa {task_id}"
                        + (f": {details}" if details else ".")
                    )
                return  # success ou partial_success

        raise DoclingConversionError(
            f"Timeout: tarefa {task_id} não concluiu em {_MAX_POLLS * _POLL_INTERVAL:.0f}s."
        )

    async def _fetch_result(
        self, client: httpx.AsyncClient, task_id: str
    ) -> bytes:
        """Recupera o resultado HTML da tarefa concluída."""
        try:
            resp = await client.get(f"{self._result_url}/{task_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DoclingConversionError(
                f"Erro ao buscar resultado da tarefa {task_id}: "
                f"HTTP {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise DoclingConversionError(
                f"Erro de rede ao buscar resultado: {exc}"
            ) from exc

        result = resp.json()
        html_content: str | None = result.get("document", {}).get("html_content")
        if not html_content:
            raise DoclingConversionError(
                "Docling não retornou html_content no resultado. "
                f"Status: {result.get('status')}, Erros: {result.get('errors', [])}"
            )
        return html_content.encode("utf-8")
