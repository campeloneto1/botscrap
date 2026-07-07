#!/bin/bash
set -e

echo "=== BotScrap Backend Startup ==="

# Aguardar o banco de dados estar pronto
echo "Aguardando banco de dados..."
while ! pg_isready -h db -p 5432 -U postgres > /dev/null 2>&1; do
    sleep 1
done
echo "Banco de dados está pronto!"

# Rodar migrations
echo "Executando migrações..."
python migrate.py

# Iniciar o servidor
echo "Iniciando servidor..."
exec "$@"
