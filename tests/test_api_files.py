"""
Testes para o router de gerenciamento de arquivos (input/output).

Histórias de Usuário:
  - Como usuário, quero listar os PDFs enviados para ver o que está na fila.
  - Como usuário, quero excluir um PDF de entrada para remover arquivos desnecessários.
  - Como usuário, quero listar os arquivos gerados para encontrar os resultados.
  - Como usuário, quero excluir arquivos/pastas de saída para liberar espaço.
  - Como sistema, não devo permitir acesso a arquivos fora das pastas permitidas.
"""
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.storage_service import StorageService

client = TestClient(app)


def _mock_storage(tmp_path: Path):
    """Cria e injeta um StorageService isolado em diretório temporário."""
    svc = StorageService(
        input_dir=tmp_path / "input",
        output_dir=tmp_path / "output",
    )
    return svc, patch("backend.api.router_files._storage", svc)


# ── Input ──────────────────────────────────────────────────────────────────────

def test_list_input_files_returns_only_pdfs(tmp_path: Path) -> None:
    """GET /files/input deve retornar apenas os PDFs presentes em input."""
    svc, mock = _mock_storage(tmp_path)
    with mock:
        (svc.input_dir / "doc1.pdf").write_bytes(b"%PDF-1.4")
        (svc.input_dir / "doc2.pdf").write_bytes(b"%PDF-1.4")
        (svc.input_dir / "notes.txt").write_text("texto")

        response = client.get("/files/input")

    assert response.status_code == 200
    files = response.json()["files"]
    names = [f["name"] for f in files]
    assert "doc1.pdf" in names
    assert "doc2.pdf" in names
    assert "notes.txt" not in names


def test_list_input_files_empty(tmp_path: Path) -> None:
    """GET /files/input retorna lista vazia quando não há PDFs."""
    _, mock = _mock_storage(tmp_path)
    with mock:
        response = client.get("/files/input")

    assert response.status_code == 200
    assert response.json()["files"] == []


def test_delete_input_file_removes_file(tmp_path: Path) -> None:
    """DELETE /files/input/{filename} deve remover o arquivo e retornar 204."""
    svc, mock = _mock_storage(tmp_path)
    target = svc.input_dir / "remover.pdf"
    target.write_bytes(b"%PDF-1.4")
    with mock:
        response = client.delete("/files/input/remover.pdf")

    assert response.status_code == 204
    assert not target.exists()


def test_delete_input_file_not_found_returns_404(tmp_path: Path) -> None:
    """DELETE /files/input/{filename} deve retornar 404 para arquivo inexistente."""
    _, mock = _mock_storage(tmp_path)
    with mock:
        response = client.delete("/files/input/fantasma.pdf")

    assert response.status_code == 404


def test_delete_input_file_path_traversal_blocked(tmp_path: Path) -> None:
    """DELETE com path traversal deve ser bloqueado com 400."""
    _, mock = _mock_storage(tmp_path)
    with mock:
        response = client.delete("/files/input/../etc/passwd")

    assert response.status_code in (400, 404)


# ── Output ─────────────────────────────────────────────────────────────────────

def test_list_output_files_returns_tree(tmp_path: Path) -> None:
    """GET /files/output deve retornar a árvore de arquivos de saída."""
    svc, mock = _mock_storage(tmp_path)
    date_dir = svc.output_dir / "2026-03-09" / "html"
    date_dir.mkdir(parents=True)
    (date_dir / "result.html").write_text("<html/>")
    with mock:
        response = client.get("/files/output")

    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) >= 1
    names = [e["name"] for e in entries]
    assert "2026-03-09" in names


def test_delete_output_file_removes_it(tmp_path: Path) -> None:
    """DELETE /files/output/{path} deve remover o arquivo e retornar 204."""
    svc, mock = _mock_storage(tmp_path)
    f = svc.output_dir / "result.html"
    f.write_text("<html/>")
    with mock:
        response = client.delete("/files/output/result.html")

    assert response.status_code == 204
    assert not f.exists()


def test_delete_output_folder_removes_tree(tmp_path: Path) -> None:
    """DELETE /files/output/{path} deve remover uma pasta inteira."""
    svc, mock = _mock_storage(tmp_path)
    folder = svc.output_dir / "2026-03-09"
    (folder / "html").mkdir(parents=True)
    (folder / "html" / "result.html").write_text("<html/>")
    with mock:
        response = client.delete("/files/output/2026-03-09")

    assert response.status_code == 204
    assert not folder.exists()


def test_delete_output_path_traversal_blocked(tmp_path: Path) -> None:
    """DELETE com path traversal em output deve ser bloqueado com 403 ou 404."""
    _, mock = _mock_storage(tmp_path)
    with mock:
        response = client.delete("/files/output/../../etc/passwd")

    assert response.status_code in (403, 404)
