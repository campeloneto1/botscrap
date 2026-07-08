#!/usr/bin/env python3
"""
Script para rodar o bot Telegram em modo polling.

USO:
    python run_telegram_bot.py

O bot ficará rodando e consultando o Telegram por novas mensagens.
Ideal para desenvolvimento local (localhost).

IMPORTANTE: Certifique-se de que:
1. O backend FastAPI está rodando (localhost:8000 ou backend:8000 no Docker)
2. O TELEGRAM_BOT_TOKEN está configurado no .env
"""
import logging

from app.telegram.handlers import run_polling

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        logger.info("=" * 50)
        logger.info("🚀 Iniciando Telegram Bot")
        logger.info("=" * 50)
        logger.info("Modo: POLLING (ideal para localhost)")
        logger.info("Pressione Ctrl+C para parar")
        logger.info("=" * 50)

        # Roda o bot (já gerencia seu próprio event loop)
        run_polling()

    except KeyboardInterrupt:
        logger.info("\n👋 Bot encerrado pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar bot: {e}")
        raise
