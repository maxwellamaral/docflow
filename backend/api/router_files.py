"""Router para gerenciamento de arquivos de entrada e saída."""
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.core.config import settings
from backend.services.storage_service import StorageService

router = APIRouter(prefix="/files", tags=["files"])

_storage = StorageService()


class FileInfo(BaseModel):
    """Metadados de um arquivo."""

    name: str
    path: str
    size: int


class InputFilesResponse(BaseModel):
    """Resposta com lista de arquivos de entrada."""

    files: list[FileInfo]


class OutputEntry(BaseModel):
    """Entrada de arquivo/pasta na árvore de saída."""

    name: str
    path: str
    is_dir: bool
    size: int
    children: list["OutputEntry"] = []


OutputEntry.model_rebuild()


class OutputFilesResponse(BaseModel):
    """Resposta com árvore de arquivos de saída."""

    entries: list[OutputEntry]


def _build_output_tree(base: Path, root: Path) -> list[OutputEntry]:
    """Monta a árvore de diretórios/arquivos de output recursivamente.

    Args:
        base: Pasta base de output (para calcular caminhos relativos).
        root: Pasta corrente sendo listada.

    Returns:
        Lista de OutputEntry ordenada (pastas primeiro, depois arquivos).
    """
    entries: list[OutputEntry] = []
    try:
        children = sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    except PermissionError:
        return entries

    for child in children:
        relative = str(child.relative_to(base))
        if child.is_dir():
            entries.append(
                OutputEntry(
                    name=child.name,
                    path=relative,
                    is_dir=True,
                    size=0,
                    children=_build_output_tree(base, child),
                )
            )
        else:
            entries.append(
                OutputEntry(
                    name=child.name,
                    path=relative,
                    is_dir=False,
                    size=child.stat().st_size,
                    children=[],
                )
            )
    return entries


# ── Input ──────────────────────────────────────────────────────────────────────

@router.get("/input", response_model=InputFilesResponse)
async def list_input_files() -> InputFilesResponse:
    """Lista todos os arquivos de entrada (PDFs enviados)."""
    files = [
        FileInfo(
            name=p.name,
            path=str(p.relative_to(_storage.input_dir)),
            size=p.stat().st_size,
        )
        for p in _storage.list_input_pdfs()
    ]
    return InputFilesResponse(files=files)


@router.get("/input/{filename}")
async def view_input_file(filename: str) -> FileResponse:
    """Faz download/visualização de um arquivo de entrada.

    Raises:
        HTTPException 400: Se o nome contiver separadores de caminho.
        HTTPException 404: Se o arquivo não existir.
    """
    # Proteção contra path traversal (OWASP A01)
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    input_resolved = _storage.input_dir.resolve()
    target = (_storage.input_dir / filename).resolve()
    try:
        target.relative_to(input_resolved)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(path=str(target), filename=target.name)


@router.delete("/input/{filename}", status_code=204)
async def delete_input_file(filename: str) -> None:
    """Remove um arquivo de entrada.

    Raises:
        HTTPException 400: Se o nome contiver separadores de caminho.
        HTTPException 404: Se o arquivo não existir.
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    input_resolved = _storage.input_dir.resolve()
    target = (_storage.input_dir / filename).resolve()
    try:
        target.relative_to(input_resolved)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    target.unlink()


# ── Output ─────────────────────────────────────────────────────────────────────

@router.get("/output", response_model=OutputFilesResponse)
async def list_output_files() -> OutputFilesResponse:
    """Lista a árvore de arquivos gerados na pasta output."""
    entries = _build_output_tree(_storage.output_dir, _storage.output_dir)
    return OutputFilesResponse(entries=entries)


@router.get("/output/{file_path:path}")
async def view_output_file(file_path: str) -> FileResponse:
    """Faz download/visualização de um arquivo de saída.

    Raises:
        HTTPException 403: Se o caminho apontar para fora de output_dir.
        HTTPException 404: Se o arquivo não existir ou for um diretório.
    """
    output_resolved = _storage.output_dir.resolve()
    target = (_storage.output_dir / file_path).resolve()
    try:
        target.relative_to(output_resolved)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    return FileResponse(path=str(target), filename=target.name)


@router.delete("/output/{file_path:path}", status_code=204)
async def delete_output_file(file_path: str) -> None:
    """Remove um arquivo ou pasta de saída.

    Raises:
        HTTPException 403: Se o caminho apontar para fora de output_dir.
        HTTPException 404: Se o arquivo/pasta não existir.
    """
    output_resolved = _storage.output_dir.resolve()
    target = (_storage.output_dir / file_path).resolve()
    try:
        target.relative_to(output_resolved)
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Arquivo ou pasta não encontrado.")

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
