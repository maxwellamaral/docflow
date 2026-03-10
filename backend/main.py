"""Entrypoint principal do backend DocFlow."""
import atexit
import subprocess
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router_download import router as download_router
from backend.api.router_files import router as files_router
from backend.api.router_pipeline import router as pipeline_router
from backend.api.router_upload import router as upload_router
from backend.core.config import settings

app = FastAPI(
    title="DocFlow API",
    description="Pipeline de conversão, tradução e exportação de documentos PDF.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:5174",   # Vite dev server (porta alternativa)
        "http://localhost:3000",   # alternativo dev
        "http://localhost:8090",   # Docker — nginx frontend (produção)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(pipeline_router)
app.include_router(download_router)
app.include_router(files_router)


def run() -> None:
    """Inicia o frontend (npm run dev) e o servidor uvicorn simultaneamente."""
    frontend_dir = Path(__file__).parent.parent / "frontend"
    fe_proc = subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir)

    def _cleanup() -> None:
        fe_proc.terminate()
        try:
            fe_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            fe_proc.kill()

    atexit.register(_cleanup)

    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
