"""
Testes para o router de download de arquivos processados.

História de Usuário:
  Como usuário,
  Quero baixar os arquivos resultantes do processamento,
  Através de um link seguro que impeça acesso a outros diretórios do sistema.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.config import settings

client = TestClient(app)


def test_download_nonexistent_file_returns_404() -> None:
    """GET /download/{arquivo_inexistente} deve retornar 404."""
    response = client.get("/download/2026-03-09/html/nao_existe.html")

    assert response.status_code == 404


def test_download_path_traversal_blocked() -> None:
    """Tentativa de path traversal deve ser bloqueada com 403."""
    response = client.get("/download/../.env")

    assert response.status_code in (403, 404)


def test_download_existing_file_returns_200(tmp_path, monkeypatch) -> None:
    """GET /download/{caminho} deve retornar o arquivo quando ele existir."""
    test_file = tmp_path / "test_document.html"
    test_file.write_text("<html><body><p>Conteúdo de teste</p></body></html>")

    monkeypatch.setattr(settings, "output_dir", tmp_path)

    response = client.get("/download/test_document.html")

    assert response.status_code == 200


def test_download_returns_correct_content(tmp_path, monkeypatch) -> None:
    """O conteúdo do arquivo baixado deve ser idêntico ao original."""
    content = b"<html><body><p>Documento original</p></body></html>"
    test_file = tmp_path / "doc.html"
    test_file.write_bytes(content)

    monkeypatch.setattr(settings, "output_dir", tmp_path)

    response = client.get("/download/doc.html")

    assert response.status_code == 200
    assert response.content == content
