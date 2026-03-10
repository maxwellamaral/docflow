# ── Build stage: compilar o frontend Vue.js ─────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Instalar dependências (camada cacheada)
COPY frontend/package*.json ./
RUN npm ci

# Copiar fonte e compilar
COPY frontend/ .
RUN npm run build

# ── Serve stage: nginx servindo os arquivos estáticos ────────────────────────
FROM nginx:1.27-alpine

# Arquivos estáticos do build
COPY --from=build /app/dist /usr/share/nginx/html

# Configuração do nginx com proxy reverso para o backend
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ > /dev/null || exit 1
