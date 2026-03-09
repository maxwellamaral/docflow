"""Configurações centralizadas da aplicação via pydantic-settings."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas do ambiente / arquivo .env.

    Attributes:
        docling_base_url: URL base do Docling Server (Docker).
        ollama_base_url: URL base do servidor Ollama local.
        ollama_model: Modelo de tradução a ser utilizado.
        ollama_timeout: Timeout em segundos para requests ao Ollama.
        target_language: Idioma de destino para tradução.
        input_dir: Pasta onde os PDFs de entrada são armazenados.
        output_dir: Pasta raiz onde os arquivos processados são salvos.
        backend_host: Host de bind do servidor uvicorn.
        backend_port: Porta do servidor uvicorn.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Docling Server
    docling_base_url: str = "http://localhost:5001"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "translategemma:4b"
    ollama_timeout: int = 600
    target_language: str = "Portuguese (Brazil)"

    # Pastas de trabalho
    input_dir: Path = Path("./input")
    output_dir: Path = Path("./output")

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000


settings = Settings()
