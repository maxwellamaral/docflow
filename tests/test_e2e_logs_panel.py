"""
Testes E2E de UI com Playwright para o painel grande de logs e controle do pipeline.

História de Usuário:
  Como operador de processamento de documentos,
  Quero visualizar um painel detalhado de logs da pipeline e ter a opção de parar o processamento,
  Para acompanhar visualmente o andamento e a duração de cada etapa ou interromper o pipeline caso queira.
"""
import subprocess
import time
import socket
from pathlib import Path
import pytest
from playwright.sync_api import Page, expect

def is_port_open(port: int) -> bool:
    """Verifica se uma porta está aberta na máquina local."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

@pytest.fixture(scope="module", autouse=True)
def app_server():
    """Fixture que garante que o backend e o frontend (Vite) estão rodando durante o teste."""
    # Se já estiverem rodando (ex: pelo usuário no terminal), apenas usa
    if is_port_open(5173) and is_port_open(8000):
        yield
        return

    # Caso contrário, inicia o pipeline completo
    proc = subprocess.Popen(
        ["uv", "run", "docflow"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Aguarda inicialização (até 15s)
    start = time.time()
    while time.time() - start < 15:
        if is_port_open(5173) and is_port_open(8000):
            break
        time.sleep(0.5)

    yield

    # Encerra processos ao finalizar
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_logs_panel_is_visible_and_shows_details(page: Page) -> None:
    """Deve verificar se o novo painel grande de logs está renderizado na página principal.

    Verifica se o painel possui as seções avançadas de visualização de etapas,
    barra de progresso por etapa, e terminal de logs históricos após injetar um estado.
    """
    # Abre a URL do frontend local (Vite)
    page.goto("http://localhost:5173")

    # 1. Verifica se o contêiner geral do painel de logs está visível e integrado no layout
    logs_panel = page.locator(".logs-panel-full")
    expect(logs_panel).to_be_visible()

    # 2. Verifica se o cabeçalho possui o título de Logs da Pipeline
    expect(logs_panel.locator("h2")).to_contain_text("📋 Logs da Pipeline")

    # 3. Verifica que no estado inicial, a mensagem de estado vazio está visível
    expect(page.locator(".pipeline-empty-state")).to_be_visible()

    # 4. Injeta um estado de processamento simulado no Pinia Store para validar o comportamento dinâmico
    page.evaluate("""() => {
        if (window.pipelineStore) {
            window.pipelineStore.fileTasks = [{
                fileName: 'documento_teste.pdf',
                filePath: 'input/documento_teste.pdf',
                status: 'converting',
                stages: {
                    converting: { name: 'Conversão HTML', status: 'running', progress: 40, startTime: Date.now() },
                    translating: { name: 'Tradução (Ollama)', status: 'pending', progress: 0 },
                    exporting: { name: 'Exportação (.docx/.pdf)', status: 'pending', progress: 0 }
                }
            }];
            window.pipelineStore.logs = [{
                timestamp: '14:20:00',
                status: 'converting',
                message: 'Iniciando conversão de documento_teste.pdf...'
            }];
        }
    }""")

    # 5. Verifica se o container de etapas ficou visível após a injeção
    pipeline_stages = page.locator(".pipeline-stages-container")
    expect(pipeline_stages).to_be_visible()

    # 6. Verifica se o console/terminal de logs brutos contém a linha de log injetada
    terminal_console = page.locator(".terminal-logs-section")
    expect(terminal_console).to_be_visible()
    expect(terminal_console).to_contain_text("Iniciando conversão de documento_teste.pdf...")


def test_pipeline_can_be_cancelled_via_button(page: Page) -> None:
    """Deve verificar se o botão de parar pipeline aparece durante a execução e permite cancelar."""
    page.goto("http://localhost:5173")

    # Intercepta a chamada de cancelamento para retornar sucesso sem bater de verdade no backend
    page.route("**/pipeline/cancel/job-cancel-test", lambda route: route.fulfill(
        status=200,
        json={"message": "Pipeline cancelada com sucesso."}
    ))

    # Injeta um estado ativo de processamento na store Pinia
    page.evaluate("""() => {
        if (window.pipelineStore) {
            window.pipelineStore.isRunning = true;
            window.pipelineStore.currentJob = {
                job_id: 'job-cancel-test',
                status: 'converting',
                created_at: new Date().toISOString(),
                input_files: ['documento_teste.pdf'],
                outputs: [],
                current_file: 'input/documento_teste.pdf',
                progress: 30,
                error: null
            };
            window.pipelineStore.fileTasks = [{
                fileName: 'documento_teste.pdf',
                filePath: 'input/documento_teste.pdf',
                status: 'converting',
                stages: {
                    converting: { name: 'Conversão HTML', status: 'running', progress: 40, startTime: Date.now() },
                    translating: { name: 'Tradução (Ollama)', status: 'pending', progress: 0 },
                    exporting: { name: 'Exportação (.docx/.pdf)', status: 'pending', progress: 0 }
                }
            }];
        }
    }""")

    # 1. Verifica se o botão de parar/cancelar pipeline está visível na tela
    cancel_button = page.locator("button:has-text('Parar Pipeline')")
    expect(cancel_button).to_be_visible()

    # 2. Clica no botão de cancelar
    cancel_button.click()

    # 3. Simulamos a recepção do evento de status 'cancelled'
    page.evaluate("""() => {
        if (window.pipelineStore) {
            window.pipelineStore.isRunning = false;
            if (window.pipelineStore.currentJob) {
                window.pipelineStore.currentJob.status = 'cancelled';
            }
            window.pipelineStore.fileTasks[0].status = 'cancelled';
            window.pipelineStore.fileTasks[0].stages.converting.status = 'failed';
        }
    }""")

    # 4. Verifica se o badge de status reflete "Cancelado" ou similar
    status_badge = page.locator(".status-badge")
    expect(status_badge).to_contain_text("Cancelado")


def test_pipeline_skip_translation_checkbox(page: Page) -> None:
    """Deve verificar o comportamento dos checkboxes de traduzir e refinar OCR com base nos idiomas."""
    # 1. Configura mock das chamadas de API antes de navegar
    # Intercepta GET /pipeline/config para retornar idiomas idênticos (deve iniciar com translate=False!)
    page.route("**/pipeline/config", lambda route: route.fulfill(
        status=200,
        json={"source_language": "Portuguese", "target_language": "Portuguese"}
    ))

    # Intercepta POST /pipeline/start e captura o payload enviado pelo frontend
    start_payloads = []
    def handle_start(route):
        start_payloads.append(route.request.post_data_json)
        route.fulfill(
            status=200,
            json={"job_id": "job-skip-test", "message": "Pipeline iniciada com sucesso."}
        )
    page.route("**/pipeline/start", handle_start)

    page.goto("http://localhost:5173")

    # 2. Ambos os checkboxes devem estar visíveis
    checkbox_translate = page.locator("label:has-text('Traduzir Documentos') input[type='checkbox']")
    checkbox_refine = page.locator("label:has-text('Refinar OCR com IA') input[type='checkbox']")

    expect(checkbox_translate).to_be_visible()
    expect(checkbox_refine).to_be_visible()

    # 3. Como os idiomas retornados no config mock são iguais, 'Traduzir' deve estar desmarcado e 'Refinar' marcado
    expect(checkbox_translate).not_to_be_checked()
    expect(checkbox_refine).to_be_checked()

    # 4. Inicia o pipeline
    start_button = page.locator("button:has-text('Iniciar Pipeline')")
    expect(start_button).to_be_visible()
    start_button.click()

    # 5. Verifica se o body do POST continha translate=False e refine_ocr=True
    page.wait_for_timeout(500)  # Pequena folga para a chamada assíncrona resolver
    assert len(start_payloads) > 0
    assert start_payloads[0].get("translate") is False
    assert start_payloads[0].get("refine_ocr") is True


def test_delete_input_file_via_ui(page: Page) -> None:
    """Deve verificar a exclusão de um arquivo de entrada a partir do painel de arquivos."""
    # 1. Configura mock para retornar um arquivo de entrada
    page.route("**/files/input", lambda route: route.fulfill(
        status=200,
        json={"files": [{"name": "teste_excluir.pdf", "path": "teste_excluir.pdf", "size": 1024}]}
    ))

    # 2. Intercepta a chamada de exclusão do arquivo
    delete_called = []
    def handle_delete(route):
        delete_called.append(True)
        route.fulfill(status=204)
    page.route("**/files/input/teste_excluir.pdf", handle_delete)

    page.goto("http://localhost:5173")

    # 3. O item do arquivo deve estar visível na interface
    expect(page.locator("text=teste_excluir.pdf")).to_be_visible()

    # 4. Clica no botão de excluir pela primeira vez (entra em modo de confirmação)
    trash_button = page.locator("li:has-text('teste_excluir.pdf') button")
    expect(trash_button).to_be_visible()
    trash_button.click()

    # 5. O botão deve mudar de texto para incluir "Confirmar"
    expect(page.locator("text=Confirmar?")).to_be_visible()

    # 6. Clica pela segunda vez para disparar a chamada real de exclusão
    trash_button.click()

    # 7. Verifica se o frontend de fato disparou o DELETE correspondente
    page.wait_for_timeout(500)
    assert len(delete_called) == 1

