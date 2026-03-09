"""Router para download seguro de arquivos processados."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.core.config import settings

router = APIRouter(prefix="/download", tags=["download"])


@router.get("/{file_path:path}")
async def download_file(file_path: str) -> FileResponse:
    """Faz o download de um arquivo da pasta ./output.

    Inclui proteção contra path traversal: qualquer tentativa de acessar
    arquivos fora de output_dir resulta em 403.

    Args:
        file_path: Caminho relativo ao output_dir (ex: '2026-03-09/html/doc.html').

    Returns:
        FileResponse com o conteúdo do arquivo.

    Raises:
        HTTPException 403: Se o caminho apontar para fora de output_dir.
        HTTPException 404: Se o arquivo não existir.
    """
    output_resolved = settings.output_dir.resolve()
    target = (settings.output_dir / file_path).resolve()

    # Proteção contra path traversal (OWASP A01)
    try:
        target.relative_to(output_resolved)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(path=str(target), filename=target.name)
