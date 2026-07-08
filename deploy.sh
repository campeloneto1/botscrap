#!/bin/bash
# Script de deploy automático
# Executado quando recebe webhook do GitHub

set -e

DEPLOY_DIR="/home/campelo/campelo/botscrap"
LOG_FILE="/home/campelo/campelo/botscrap/deploy.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

cd "$DEPLOY_DIR"

log "=== Iniciando deploy ==="

# Pull das atualizações
log "Fazendo git pull..."
git pull origin main

# Para os containers
log "Parando containers..."
docker compose down

# Rebuild e inicia
log "Reconstruindo e iniciando containers..."
docker compose up -d --build

# Limpa imagens antigas não utilizadas
log "Limpando imagens antigas..."
docker image prune -f

log "=== Deploy concluído com sucesso ==="
