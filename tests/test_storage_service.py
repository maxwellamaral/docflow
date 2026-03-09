"""
Testes unitários para StorageService.

História de Usuário:
  Como pipeline de processamento,
  Quero que os arquivos sejam organizados em pastas por data e tipo,
  Para localizar resultados facilmente.
"""
from datetime import date
from pathlib import Path

import pytest

from backend.services.storage_service import StorageService


def test_create_job_dirs_creates_expected_structure(tmp_path: Path) -> None:
    """Deve criar as 4 subpastas (html, translated, docx, pdf) dentro de output/YYYY-MM-DD/."""
    service = StorageService(input_dir=tmp_path / "input", output_dir=tmp_path / "output")
    today = date(2026, 3, 9)

    dirs = service.create_job_dirs(today)

    assert set(dirs.keys()) == {"html", "translated", "docx", "pdf"}
    for subdir in dirs.values():
        assert subdir.exists()
        assert subdir.is_dir()
        assert "2026-03-09" in str(subdir)


def test_save_uploaded_file_persists_content(tmp_path: Path) -> None:
    """Deve salvar o conteúdo do arquivo em ./input com o nome correto."""
    service = StorageService(input_dir=tmp_path / "input", output_dir=tmp_path / "output")
    content = b"%PDF-1.4 test content"

    path = service.save_uploaded_file("relatorio.pdf", content)

    assert path.exists()
    assert path.read_bytes() == content
    assert path.parent == service.input_dir
    assert path.name == "relatorio.pdf"


def test_list_input_pdfs_returns_only_pdf_files(tmp_path: Path) -> None:
    """Deve retornar apenas arquivos .pdf presentes em ./input."""
    service = StorageService(input_dir=tmp_path / "input", output_dir=tmp_path / "output")
    (service.input_dir / "doc_a.pdf").write_bytes(b"pdf")
    (service.input_dir / "doc_b.pdf").write_bytes(b"pdf")
    (service.input_dir / "notes.txt").write_text("text")
    (service.input_dir / "image.png").write_bytes(b"png")

    pdfs = service.list_input_pdfs()

    assert len(pdfs) == 2
    assert all(p.suffix == ".pdf" for p in pdfs)


def test_list_input_pdfs_returns_empty_when_no_pdfs(tmp_path: Path) -> None:
    """Deve retornar lista vazia se não há PDFs."""
    service = StorageService(input_dir=tmp_path / "input", output_dir=tmp_path / "output")

    assert service.list_input_pdfs() == []


def test_get_output_path_returns_correct_path(tmp_path: Path) -> None:
    """Deve montar o caminho de saída com stem e extensão corretos."""
    service = StorageService(input_dir=tmp_path / "input", output_dir=tmp_path / "output")
    job_dirs = service.create_job_dirs(date(2026, 3, 9))

    path = service.get_output_path(job_dirs, "docx", "my_document", ".docx")

    assert path.name == "my_document.docx"
    assert path.parent == job_dirs["docx"]


def test_storage_service_creates_dirs_on_init(tmp_path: Path) -> None:
    """Deve criar input_dir e output_dir ao ser instanciado."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"

    StorageService(input_dir=input_dir, output_dir=output_dir)

    assert input_dir.exists()
    assert output_dir.exists()
