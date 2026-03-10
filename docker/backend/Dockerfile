# ── DocFlow Backend ──────────────────────────────────────────────────────────
FROM python:3.10-slim

# Dependências de sistema para WeasyPrint (HTML → PDF) e lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# --- Camada de dependências (invalidada apenas quando pyproject.toml mudar) ---
COPY pyproject.toml .
# Estrutura mínima do pacote para o hatchling resolver o projeto
RUN mkdir -p backend && touch backend/__init__.py
RUN uv sync --no-dev

# --- Código-fonte (invalidado em qualquer alteração do backend) ---
COPY backend/ ./backend/

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -sf http://localhost:8000/docs > /dev/null || exit 1

CMD ["uv", "run", "--no-sync", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
