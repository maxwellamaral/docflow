"""
Testes para o router de controle da pipeline.

História de Usuário:
  Como usuário,
  Quero iniciar a pipeline e acompanhar o progresso em tempo real,
  Para saber quando meu documento estará pronto.
"""
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _patch_pipeline():
    """Contexto que impede a pipeline de executar chamadas externas nos testes."""
    return patch("backend.core.pipeline.run_pipeline", new_callable=lambda: lambda: AsyncMock())


def _patch_start():
    """Patches necessários para POST /pipeline/start funcionar sem fs/IO reais."""
    patch_run = patch("backend.api.router_pipeline.pipeline_core.run_pipeline", new=AsyncMock())
    patch_storage = patch(
        "backend.api.router_pipeline.StorageService.list_input_pdfs",
        return_value=[Path("dummy.pdf")],
    )
    return patch_run, patch_storage


def test_start_pipeline_returns_job_id() -> None:
    """POST /pipeline/start deve retornar um job_id válido."""
    patch_run, patch_storage = _patch_start()
    with patch_run, patch_storage:
        response = client.post("/pipeline/start")

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert len(data["job_id"]) > 0
    assert "message" in data


def test_get_status_returns_job_info() -> None:
    """GET /pipeline/status/{job_id} deve retornar as informações do job."""
    patch_run, patch_storage = _patch_start()
    with patch_run, patch_storage:
        start = client.post("/pipeline/start")
    job_id = start.json()["job_id"]

    response = client.get(f"/pipeline/status/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert "status" in data
    assert "progress" in data


def test_get_status_unknown_job_returns_404() -> None:
    """GET /pipeline/status/{id_inexistente} deve retornar 404."""
    response = client.get("/pipeline/status/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_start_pipeline_creates_distinct_jobs() -> None:
    """Cada chamada a /pipeline/start deve criar um job com ID único."""
    patch_run, patch_storage = _patch_start()
    with patch_run, patch_storage:
        r1 = client.post("/pipeline/start")
        r2 = client.post("/pipeline/start")

    assert r1.json()["job_id"] != r2.json()["job_id"]


def test_start_pipeline_with_empty_input_returns_422() -> None:
    """POST /pipeline/start deve retornar 422 quando ./input não tiver PDFs."""
    with patch(
        "backend.api.router_pipeline.StorageService.list_input_pdfs",
        return_value=[],
    ):
        response = client.post("/pipeline/start")

    assert response.status_code == 422
    assert "Nenhum PDF" in response.json()["detail"]
