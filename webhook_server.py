#!/usr/bin/env python3
"""
Servidor de webhook para deploy automático.
Recebe webhooks do GitHub e executa o deploy.

Uso:
    python webhook_server.py

Configuração no GitHub:
    1. Vá em Settings > Webhooks > Add webhook
    2. Payload URL: http://SEU_IP:9000/webhook
    3. Content type: application/json
    4. Secret: (o mesmo definido em WEBHOOK_SECRET)
    5. Events: Just the push event
"""

import hashlib
import hmac
import subprocess
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Configurações
PORT = 9000
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "seu_secret_aqui")  # Defina um secret forte!
DEPLOY_SCRIPT = "/home/campelo/campelo/botscrap/deploy.sh"
ALLOWED_BRANCH = "refs/heads/main"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/campelo/campelo/botscrap/webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verifica a assinatura do webhook do GitHub."""
    if not signature:
        return False

    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/webhook':
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get('Content-Length', 0))
        payload = self.rfile.read(content_length)

        # Verifica assinatura
        signature = self.headers.get('X-Hub-Signature-256', '')
        if WEBHOOK_SECRET != "seu_secret_aqui" and not verify_signature(payload, signature):
            logger.warning("Assinatura inválida!")
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Invalid signature')
            return

        # Verifica se é push event
        event = self.headers.get('X-GitHub-Event', '')
        if event != 'push':
            logger.info(f"Evento ignorado: {event}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Event ignored')
            return

        # Parse do payload
        try:
            data = json.loads(payload)
            ref = data.get('ref', '')
            pusher = data.get('pusher', {}).get('name', 'unknown')
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        # Verifica branch
        if ref != ALLOWED_BRANCH:
            logger.info(f"Branch ignorada: {ref}")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Branch ignored')
            return

        logger.info(f"Push na main detectado por {pusher}! Iniciando deploy...")

        # Executa deploy em background
        try:
            subprocess.Popen(
                ['bash', DEPLOY_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            logger.info("Deploy iniciado com sucesso!")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Deploy started')
        except Exception as e:
            logger.error(f"Erro ao iniciar deploy: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self):
        """Health check endpoint."""
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Sobrescreve para usar nosso logger."""
        logger.info(f"{self.address_string()} - {format % args}")


def main():
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    logger.info(f"Servidor webhook iniciado na porta {PORT}")
    logger.info(f"Endpoint: http://0.0.0.0:{PORT}/webhook")
    logger.info(f"Health check: http://0.0.0.0:{PORT}/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Servidor parado")
        server.shutdown()


if __name__ == '__main__':
    main()
