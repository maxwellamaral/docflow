"""Gerenciamento de arquivos de entrada e saída da pipeline."""
from datetime import date
from pathlib import Path

from backend.core.config import settings


class StorageService:
    """Gerencia os diretórios ./input e ./output.

    Args:
        input_dir: Caminho para a pasta de entrada (PDFs).
        output_dir: Caminho para a pasta de saída (resultados).
    """

    def __init__(
        self,
        input_dir: Path = settings.input_dir,
        output_dir: Path = settings.output_dir,
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_job_dirs(self, job_date: date | None = None) -> dict[str, Path]:
        """Cria as subpastas de saída organizadas por data.

        Args:
            job_date: Data do job (padrão: hoje).

        Returns:
            Dicionário com chaves 'html', 'translated', 'docx', 'pdf'
            mapeando para os respectivos caminhos criados.
        """
        today = job_date or date.today()
        base = self.output_dir / today.isoformat()
        dirs: dict[str, Path] = {
            "html": base / "html",
            "translated": base / "translated",
            "docx": base / "docx",
            "pdf": base / "pdf",
        }
        for path in dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        return dirs

    def save_uploaded_file(self, filename: str, content: bytes) -> Path:
        """Salva um arquivo enviado pelo usuário em ./input.

        Args:
            filename: Nome original do arquivo.
            content: Conteúdo binário do arquivo.

        Returns:
            Caminho do arquivo salvo.
        """
        dest = self.input_dir / filename
        dest.write_bytes(content)
        return dest

    def list_input_pdfs(self) -> list[Path]:
        """Retorna todos os arquivos .pdf encontrados em ./input.

        Returns:
            Lista de Paths ordenada alfabeticamente.
        """
        return sorted(self.input_dir.glob("*.pdf"))

    def get_output_path(
        self,
        job_dirs: dict[str, Path],
        kind: str,
        stem: str,
        ext: str,
    ) -> Path:
        """Monta o caminho de saída para um tipo específico de arquivo.

        Args:
            job_dirs: Dicionário retornado por create_job_dirs.
            kind: Tipo de arquivo ('html', 'translated', 'docx' ou 'pdf').
            stem: Nome base do arquivo sem extensão.
            ext: Extensão com ponto (ex: '.docx').

        Returns:
            Path completo para o arquivo de saída.
        """
        return job_dirs[kind] / f"{stem}{ext}"
