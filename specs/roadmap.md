# Roadmap de Implementação — DocFlow

> **Status atual:** Fase Green ✅ — Backend + Frontend implementados, 37 testes passando. Build de produção OK.

---

## Fase 0 — Inicialização (atual)

- [x] Levantar requisitos funcionais e não funcionais em `specs/requirements.md`
- [x] Definir arquitetura em `specs/architecture.md`
- [x] Criar este roadmap
- [ ] Configurar `pyproject.toml` com dependências mínimas via `uv`

---

## Fase 1 — Plano de Testes (`/plan`)

> Detalhar todos os casos de teste (unitários e E2E) antes de qualquer implementação.

- [ ] Definir testes unitários para `StorageService`
- [ ] Definir testes unitários para `DoclingService`
- [ ] Definir testes unitários para `TranslationService`
- [ ] Definir testes unitários para `ConversionService`
- [ ] Definir testes unitários para o orquestrador `Pipeline`
- [ ] Definir testes de integração para os routers FastAPI
- [ ] Definir testes E2E (Playwright) para o fluxo completo do frontend

---

## Fase 2 — Testes Red (`/test`)

> Criar arquivos de teste que **falham** (fase Red do TDD).

- [ ] `tests/test_storage_service.py`
- [ ] `tests/test_docling_service.py`
- [ ] `tests/test_translation_service.py`
- [ ] `tests/test_conversion_service.py`
- [ ] `tests/test_pipeline.py`
- [ ] `tests/test_api_upload.py`
- [ ] `tests/test_api_pipeline.py`
- [ ] `tests/test_api_download.py`
- [ ] `tests/e2e/test_frontend_flow.py` (Playwright)

---

## Fase 3 — Implementação Green

> Código mínimo para passar nos testes. Ordem sequencial abaixo:

### 3.1 — Core & Config
- [ ] `backend/core/config.py` — Settings com pydantic-settings + `.env`
- [ ] `backend/models/schemas.py` — Pydantic models (PipelineJob, FileInfo, PipelineStatus)

### 3.2 — Services (camada de domínio)
- [ ] `backend/services/storage_service.py`
  - Gerenciar `./input` e `./output/YYYY-MM-DD/{html,translated,docx,pdf}`
- [ ] `backend/services/docling_service.py`
  - POST para `http://localhost:5001/v1alpha/convert/file`
  - Parâmetros: `image_export_mode=placeholder`, `pipeline=standard`, `ocr_engine=auto`, `return_as_file=true`
- [ ] `backend/services/translation_service.py`
  - POST para `http://localhost:11434/api/generate`
  - Modelo: `translategemma:4b`, chunking de HTML para não estourar contexto
- [ ] `backend/services/conversion_service.py`
  - HTML → `.docx` via `python-docx` + `beautifulsoup4`
  - HTML → `.pdf` via `WeasyPrint`

### 3.3 — Pipeline Orchestrator
- [ ] `backend/core/pipeline.py`
  - Orquestração assíncrona das etapas 1→2→3a+3b
  - Emissão de eventos de progresso via WebSocket

### 3.4 — API Routers
- [ ] `backend/api/router_upload.py`
- [ ] `backend/api/router_pipeline.py` (inclui WebSocket `/ws/pipeline/{job_id}`)
- [ ] `backend/api/router_download.py`
- [ ] `backend/main.py` — montagem do app FastAPI

### 3.5 — Frontend Vue.js
- [ ] Scaffold com `npm create vite@latest frontend -- --template vue-ts`
- [ ] Instalar dependências: `pinia`, `axios`, `vue-router`
- [ ] `src/stores/pipeline.ts`
- [ ] `src/api/client.ts`
- [ ] `src/components/UploadPanel.vue`
- [ ] `src/components/PipelineMonitor.vue`
- [ ] `src/components/DownloadPanel.vue`
- [ ] `src/App.vue` — composição dos componentes

---

## Fase 4 — Refactor

- [ ] Revisar tratamento de erros em todos os services
- [ ] Garantir que o progresso da pipeline é granular e legível no frontend
- [ ] Adicionar validação de tipo de arquivo no upload (apenas PDF)
- [ ] Revisar performance do chunking de HTML na tradução
- [ ] Documentar todos os módulos com docstrings Google Style

---

## Dependências Python (previstas)

```toml
[project]
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "httpx>=0.28",          # cliente async para Docling e Ollama
    "python-multipart>=0.0.20",  # upload de arquivos
    "beautifulsoup4>=4.13",
    "python-docx>=1.1",
    "weasyprint>=63",
    "aiofiles>=24",
]

[tool.uv.dev-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "httpx",                # TestClient do FastAPI
    "pytest-playwright>=0.7",
    "respx>=0.22",          # mock de chamadas HTTP
]
```
