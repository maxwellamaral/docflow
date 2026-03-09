"""Router para recebimento de arquivos PDF via upload."""
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.models.schemas import UploadResponse
from backend.services.storage_service import StorageService

router = APIRouter(prefix="/upload", tags=["upload"])

_storage = StorageService()


@router.post("", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    """Recebe um arquivo PDF e o salva em ./input para processamento.

    Args:
        file: Arquivo enviado via multipart/form-data.

    Returns:
        Resposta com o nome do arquivo e mensagem de confirmação.

    Raises:
        HTTPException 422: Se o arquivo não for um PDF.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=422,
            detail="Apenas arquivos PDF são aceitos. Envie um arquivo com extensão .pdf.",
        )

    content = await file.read()
    _storage.save_uploaded_file(filename, content)

    return UploadResponse(
        filename=filename,
        message=f"Arquivo '{filename}' enviado com sucesso.",
    )
