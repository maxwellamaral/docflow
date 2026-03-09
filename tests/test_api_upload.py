"""
Testes para o router de upload de PDFs.

História de Usuário:
  Como usuário,
  Quero enviar PDFs pela interface web,
  Para que eles sejam processados pela pipeline.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _mock_storage(tmp_path: Path):
    """Patch para isolar uploads em um diretório temporário."""
    from backend.services.storage_service import StorageService
    svc = StorageService(input_dir=tmp_path / "input", output_dir=tmp_path / "output")
    return patch("backend.api.router_upload._storage", svc)


def test_upload_pdf_returns_200_with_filename(tmp_path: Path) -> None:
    """Upload de um PDF válido deve retornar 200 com o nome do arquivo."""
    pdf_bytes = b"%PDF-1.4 minimal valid pdf"
    with _mock_storage(tmp_path):
        response = client.post(
            "/upload",
            files={"file": ("relatorio.pdf", pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "relatorio.pdf"
    assert "sucesso" in data["message"].lower()


def test_upload_non_pdf_returns_422() -> None:
    """Upload de arquivo não-PDF deve ser rejeitado com status 422."""
    response = client.post(
        "/upload",
        files={"file": ("notes.txt", b"some text content", "text/plain")},
    )

    assert response.status_code == 422


def test_upload_without_file_returns_422() -> None:
    """Request sem arquivo deve retornar 422."""
    response = client.post("/upload")

    assert response.status_code == 422


def test_upload_pdf_with_wrong_extension_returns_422() -> None:
    """Arquivo com extensão não-.pdf deve ser rejeitado."""
    response = client.post(
        "/upload",
        files={"file": ("document.docx", b"fake docx", "application/octet-stream")},
    )

    assert response.status_code == 422
