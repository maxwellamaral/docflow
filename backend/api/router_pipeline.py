"""Router para controle e monitoramento em tempo real da pipeline."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect

from backend.core import pipeline as pipeline_core
from backend.models.schemas import PipelineJob, PipelineStartResponse, ProgressEvent
from backend.services.storage_service import StorageService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Mapa de conexões WebSocket ativas por job_id
_ws_connections: dict[str, list[WebSocket]] = {}


async def _broadcast_progress(event: ProgressEvent) -> None:
    """Envia evento de progresso para todos os clientes WebSocket do job.

    Args:
        event: Evento de progresso a ser transmitido.
    """
    connections = _ws_connections.get(event.job_id, [])
    dead: list[WebSocket] = []

    for ws in connections:
        try:
            await ws.send_text(event.model_dump_json())
        except Exception:
            dead.append(ws)

    for ws in dead:
        connections.remove(ws)


@router.post("/start", response_model=PipelineStartResponse)
async def start_pipeline(background_tasks: BackgroundTasks) -> PipelineStartResponse:
    """Inicia a pipeline de processamento em background.

    Returns:
        Resposta com o job_id criado e mensagem de confirmação.

    Raises:
        HTTPException 422: Se não houver PDFs em ./input para processar.
    """
    storage = StorageService()
    if not storage.list_input_pdfs():
        raise HTTPException(
            status_code=422,
            detail="Nenhum PDF encontrado em ./input. Envie ao menos um arquivo antes de iniciar a pipeline.",
        )
    job = pipeline_core.create_job()
    background_tasks.add_task(pipeline_core.run_pipeline, job.job_id, _broadcast_progress)
    return PipelineStartResponse(
        job_id=job.job_id,
        message="Pipeline iniciada com sucesso.",
    )


@router.get("/status/{job_id}", response_model=PipelineJob)
async def get_status(job_id: str) -> PipelineJob:
    """Retorna o estado atual de um job de pipeline.

    Args:
        job_id: Identificador único do job.

    Returns:
        Objeto PipelineJob com o estado atual.

    Raises:
        HTTPException 404: Se o job não for encontrado.
    """
    job = pipeline_core.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return job


@router.websocket("/ws/{job_id}")
async def websocket_pipeline(websocket: WebSocket, job_id: str) -> None:
    """WebSocket para receber eventos de progresso em tempo real.

    Ao conectar, emite imediatamente o estado atual do job (se existir).
    Mantém a conexão aberta até o cliente desconectar.

    Args:
        websocket: Conexão WebSocket.
        job_id: Identificador do job a monitorar.
    """
    await websocket.accept()
    _ws_connections.setdefault(job_id, []).append(websocket)

    # Envia estado atual imediatamente após a conexão
    job = pipeline_core.get_job(job_id)
    if job:
        current = ProgressEvent(
            job_id=job_id,
            status=job.status,
            progress=job.progress,
            current_file=job.current_file,
            message="Conectado. Estado atual do job.",
        )
        await websocket.send_text(current.model_dump_json())

    try:
        while True:
            # Mantém a conexão viva aguardando mensagens do cliente (heartbeat)
            await websocket.receive_text()
    except WebSocketDisconnect:
        conns = _ws_connections.get(job_id, [])
        if websocket in conns:
            conns.remove(websocket)
