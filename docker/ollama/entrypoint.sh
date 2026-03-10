#!/bin/sh
# Entrypoint do container Ollama:
#   1. Inicia o servidor Ollama em background
#   2. Aguarda o servidor estar pronto
#   3. Baixa translategemma:4b (se ainda não estiver disponível)
#   4. Aguarda o processo principal (keep container alive)

set -e

echo "=== [Ollama] Iniciando servidor ==="
ollama serve &
OLLAMA_PID=$!

echo "=== [Ollama] Aguardando servidor ficar pronto ==="
MAX_WAIT=60
ELAPSED=0
until ollama list > /dev/null 2>&1; do
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        echo "=== [Ollama] ERRO: servidor não respondeu em ${MAX_WAIT}s ==="
        exit 1
    fi
    echo "  ... aguardando (${ELAPSED}s)"
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

echo "=== [Ollama] Servidor pronto ==="

echo "=== [Ollama] Verificando modelo translategemma:4b ==="
if ollama list | grep -q "translategemma"; then
    echo "=== [Ollama] Modelo translategemma:4b já disponível ==="
else
    echo "=== [Ollama] Baixando modelo translategemma:4b (pode demorar vários minutos) ==="
    ollama pull translategemma:4b
    echo "=== [Ollama] Modelo baixado com sucesso ==="
fi

echo "=== [Ollama] Stack pronta. Aguardando... ==="
wait "$OLLAMA_PID"
