"""
Telegram bot handlers para receber comandos dos usuários.
Este bot roda em polling mode (perfeito para localhost).
"""
import logging
import os
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# URL da sua API - detecta se está no Docker ou rodando localmente
# Se estiver no Docker, usa o nome do serviço "backend"
# Se estiver rodando localmente, usa localhost
API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000/api" if os.path.exists("/.dockerenv") else "http://localhost:8000/api")

# Credenciais para autenticação na API
BOT_API_USERNAME = os.getenv("BOT_API_USERNAME", "admin")
BOT_API_PASSWORD = os.getenv("BOT_API_PASSWORD", settings.admin_password)

# Cache do token JWT
_auth_token = None


async def get_auth_token(force_refresh: bool = False) -> str:
    """
    Obtém o token JWT para autenticação na API.
    Faz cache do token para evitar múltiplas chamadas de login.

    Args:
        force_refresh: Se True, força novo login mesmo se houver token em cache
    """
    global _auth_token

    # Se já temos um token e não é refresh forçado, retorna
    if _auth_token and not force_refresh:
        return _auth_token

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/auth/login",
                data={
                    "username": BOT_API_USERNAME,
                    "password": BOT_API_PASSWORD,
                }
            )

            if response.status_code == 200:
                data = response.json()
                _auth_token = data["access_token"]
                logger.info("Bot autenticado com sucesso na API")
                return _auth_token
            else:
                logger.error(f"Erro ao autenticar bot: HTTP {response.status_code} - {response.text}")
                raise Exception(f"Erro de autenticação: HTTP {response.status_code}")

    except httpx.TimeoutException:
        logger.error("Timeout ao tentar autenticar na API")
        raise Exception("Timeout ao conectar com a API")
    except httpx.ConnectError as e:
        logger.error(f"Erro de conexão com a API: {e}")
        raise Exception("Não foi possível conectar com a API")
    except Exception as e:
        logger.error(f"Erro ao obter token: {type(e).__name__}: {e}", exc_info=True)
        raise


async def get_authenticated_headers() -> dict:
    """
    Retorna headers com token de autenticação.
    Tenta renovar o token automaticamente se houver erro de autenticação.
    """
    token = await get_auth_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def invalidate_auth_token():
    """Invalida o token em cache, forçando novo login na próxima requisição."""
    global _auth_token
    _auth_token = None
    logger.info("Token de autenticação invalidado")


async def make_authenticated_request(client: httpx.AsyncClient, method: str, url: str, **kwargs):
    """
    Faz uma requisição autenticada, renovando o token automaticamente se expirado.

    Args:
        client: Cliente HTTP
        method: Método HTTP (GET, POST, etc)
        url: URL da requisição
        **kwargs: Outros parâmetros para a requisição
    """
    headers = await get_authenticated_headers()
    if "headers" in kwargs:
        kwargs["headers"].update(headers)
    else:
        kwargs["headers"] = headers

    # Primeira tentativa
    response = await client.request(method, url, **kwargs)

    # Se receber 401, tenta renovar o token e fazer novamente
    if response.status_code == 401:
        logger.warning("Token expirado, renovando...")
        invalidate_auth_token()
        headers = await get_authenticated_headers()
        kwargs["headers"] = headers
        response = await client.request(method, url, **kwargs)

    return response


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /start"""
    await update.message.reply_text(
        "👋 Olá! Eu sou o BotScrap.\n\n"
        "<b>📋 Consultas:</b>\n"
        "/profiles - Listar todos os perfis\n"
        "/profile @user - Ver perfil específico\n"
        "/stats - Ver estatísticas\n"
        "/status - Status do scraping\n\n"
        "<b>⚡ Ações:</b>\n"
        "/run - Executar scraping de TODOS\n"
        "/add <platform> @user - Adicionar perfil\n"
        "/search <palavras> - Buscar posts no Instagram\n\n"
        "/help - Ver ajuda detalhada",
        parse_mode="HTML"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /help"""
    await update.message.reply_text(
        "📚 <b>Guia de Comandos - BotScrap</b>\n\n"
        "<b>📋 CONSULTAS</b>\n"
        "/profiles - Lista todos os perfis monitorados\n"
        "/profile @user - Informações de um perfil específico\n"
        "/stats - Estatísticas do sistema\n"
        "/status - Status do scraping em andamento\n\n"
        "<b>⚡ AÇÕES</b>\n"
        "/run - Scraping de TODOS (padrão)\n"
        "/run 6 - Scraping de TODOS (6h)\n"
        "/run @nike - Scraping de UM (padrão)\n"
        "/run @nike 12 - Scraping de UM (12h)\n"
        "/add instagram @nike - Adiciona novo perfil\n"
        "/search greve ceara - Busca posts no Instagram\n\n"
        "<b>💡 EXEMPLOS</b>\n"
        "• <code>/profile @nike</code>\n"
        "• <code>/run</code> ou <code>/run 12</code>\n"
        "• <code>/run @nike</code> ou <code>/run @nike 24</code>\n"
        "• <code>/search black friday</code>\n"
        "• <code>/status</code>\n"
        "• <code>/add instagram @adidas</code>\n\n"
        "Use /commands para ver lista completa.",
        parse_mode="HTML"
    )


async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /commands - lista todos os comandos"""
    await update.message.reply_text(
        "📋 <b>Todos os Comandos Disponíveis:</b>\n\n"
        "/start - Menu inicial\n"
        "/help - Ajuda detalhada\n"
        "/commands - Esta lista\n\n"
        "<b>📊 Consultas:</b>\n"
        "/profiles - Listar perfis\n"
        "/profile @user - Detalhes de perfil\n"
        "/stats - Estatísticas gerais\n"
        "/status - Status do scraping\n\n"
        "<b>⚡ Ações de Scraping:</b>\n"
        "/run - Todos os perfis (usa config)\n"
        "/run 6 - Todos os perfis (6h)\n"
        "/run @user - Um perfil (usa config)\n"
        "/run @user 12 - Um perfil (12h)\n\n"
        "<b>🔍 Busca em Redes Sociais:</b>\n"
        "/search <palavras> - Busca posts no Instagram\n"
        "Exemplo: /search greve ceara\n"
        "Retorna posts com TODAS as palavras.\n\n"
        "<b>➕ Gerenciamento:</b>\n"
        "/add instagram @user - Adicionar perfil\n\n"
        "<b>ℹ️ Sobre o período padrão:</b>\n"
        "Quando não informar horas, usa a configuração\n"
        "da tabela app_settings do banco de dados.\n"
        "Você pode personalizar em Configurações.\n\n"
        "<b>🌐 Plataformas:</b>\n"
        "instagram, twitter, facebook",
        parse_mode="HTML"
    )


async def profiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca perfis da API local e retorna para o usuário"""
    try:
        # Consulta sua API local
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await make_authenticated_request(
                client, "GET", f"{API_BASE_URL}/profiles"
            )

            if response.status_code == 200:
                profiles = response.json()

                if not profiles:
                    await update.message.reply_text("📭 Nenhum perfil monitorado ainda.")
                    return

                # Formata a resposta
                message_lines = ["📋 <b>Perfis monitorados:</b>\n"]
                for profile in profiles:
                    platform = profile.get("platform", "unknown")
                    username = profile.get("username", "unknown")
                    is_active = "✅" if profile.get("is_active") else "❌"
                    message_lines.append(f"{is_active} {platform.upper()}: @{username}")

                await update.message.reply_text(
                    "\n".join(message_lines),
                    parse_mode="HTML"
                )
            else:
                await update.message.reply_text(
                    f"❌ Erro ao buscar perfis: {response.status_code}"
                )

    except Exception as e:
        logger.error(f"Erro ao buscar perfis: {e}")
        await update.message.reply_text(
            "❌ Erro ao consultar API. Verifique se o backend está rodando."
        )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca estatísticas da API local"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await make_authenticated_request(
                client, "GET", f"{API_BASE_URL}/stats/overview"
            )

            if response.status_code == 200:
                stats = response.json()

                # Extrai dados da resposta
                status_counts = stats.get('status_counts', {})
                total_posts = stats.get('total_posts', 0)
                keywords_last_7_days = stats.get('keywords_last_7_days', 0)
                ocr_processed = stats.get('ocr_processed', 0)

                message = (
                    "📊 <b>Estatísticas:</b>\n\n"
                    f"📝 Total de posts: {total_posts}\n"
                    f"🔔 Alertas (7 dias): {keywords_last_7_days}\n"
                    f"🖼️ Posts com OCR: {ocr_processed}\n\n"
                    f"<b>Status:</b>\n"
                    f"✅ Completados: {status_counts.get('completed', 0)}\n"
                    f"⏳ Pendentes: {status_counts.get('pending', 0)}\n"
                    f"🔄 Processando: {status_counts.get('processing', 0)}\n"
                    f"❌ Falhas: {status_counts.get('failed', 0)}"
                )

                await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text(
                    f"❌ Erro ao buscar estatísticas: {response.status_code}"
                )

    except Exception as e:
        logger.error(f"Erro ao buscar stats: {e}")
        await update.message.reply_text(
            "❌ Erro ao consultar API. Verifique se o backend está rodando."
        )


async def run_single_profile_scraping(update: Update, username: str, hours: int = None):
    """
    Executa scraping de um perfil específico e envia para Telegram.

    Args:
        username: Username do perfil (sem @)
        hours: Número de horas para buscar posts (None = usa config padrão)
    """
    try:
        await update.message.reply_text(
            f"🔍 Buscando perfil @{username}..."
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Busca o perfil
            response = await make_authenticated_request(
                client, "GET", f"{API_BASE_URL}/profiles"
            )

            if response.status_code != 200:
                await update.message.reply_text(
                    f"❌ Erro ao buscar perfil: {response.status_code}"
                )
                return

            profiles = response.json()
            profile = next(
                (p for p in profiles if p.get("username", "").lower() == username.lower()),
                None
            )

            if not profile:
                await update.message.reply_text(
                    f"❌ Perfil @{username} não encontrado.\n\n"
                    f"💡 <b>Deseja adicionar este perfil?</b>\n"
                    f"Use: <code>/add instagram @{username}</code>\n"
                    f"Ou: <code>/add twitter @{username}</code>\n\n"
                    f"📋 Ver perfis cadastrados: /profiles",
                    parse_mode="HTML"
                )
                return

            profile_id = profile["id"]
            platform = profile.get("platform", "").upper()

            hours_text = f"últimas {hours}h" if hours else "período padrão"
            await update.message.reply_text(
                f"🔄 Executando scraping de @{username} ({platform})...\n\n"
                f"📅 Buscando posts do {hours_text}\n"
                f"⏳ Enviando para o Telegram..."
            )

            # Monta URL com parâmetro de horas se informado
            url = f"{API_BASE_URL}/profiles/{profile_id}/test-telegram"
            if hours is not None:
                url += f"?hours={hours}"

            # Executa scraping e envia para Telegram
            scrape_response = await make_authenticated_request(
                client, "POST", url
            )

            if scrape_response.status_code == 200:
                result = scrape_response.json()

                if result.get("success"):
                    hours_used = result.get('hours', '?')
                    posts_found = result.get('posts_found', 0)
                    posts_sent = result.get('posts_sent', 0)
                    posts_skipped = result.get('posts_skipped', 0)

                    message = (
                        f"✅ Scraping de @{username} concluído!\n\n"
                        f"📅 Período: últimas {hours_used}h\n"
                        f"📝 Posts encontrados: {posts_found}\n"
                        f"📤 Posts enviados: {posts_sent}\n"
                    )

                    if posts_skipped > 0:
                        message += f"⏭️ Posts já processados: {posts_skipped}\n"

                    message += f"📬 Grupo: {result.get('telegram_group', 'N/A')}"

                    if result.get("keywords_matched"):
                        keywords = ", ".join(result["keywords_matched"])
                        message += f"\n🔔 Keywords: {keywords}"

                    await update.message.reply_text(message)
                else:
                    error = result.get("error", "Erro desconhecido")
                    await update.message.reply_text(
                        f"❌ Erro ao fazer scraping de @{username}:\n\n{error}"
                    )
            elif scrape_response.status_code == 400:
                error_detail = scrape_response.json().get("detail", "")
                if "grupo Telegram" in error_detail.lower():
                    await update.message.reply_text(
                        f"❌ @{username} não tem grupo Telegram associado.\n\n"
                        f"Configure um grupo para este perfil primeiro."
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Erro: {error_detail}"
                    )
            else:
                await update.message.reply_text(
                    f"❌ Erro ao fazer scraping: {scrape_response.status_code}"
                )

    except Exception as e:
        logger.error(f"Erro ao fazer scraping de perfil específico: {e}")
        await update.message.reply_text(
            f"❌ Erro ao fazer scraping: {str(e)}"
        )


async def run_scraping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Executa scraping manualmente.
    Uso:
      /run - Todos os perfis (config padrão)
      /run 6 - Todos os perfis (últimas 6 horas)
      /run @username - Apenas um perfil específico (config padrão)
      /run @username 12 - Apenas um perfil (últimas 12 horas)
    """
    try:
        # Verifica se é um perfil específico
        if context.args and context.args[0].startswith("@"):
            username = context.args[0].replace("@", "")

            # Verifica se foi informado horas como segundo parâmetro
            hours = None
            if len(context.args) > 1:
                try:
                    hours = int(context.args[1])
                    if hours < 1 or hours > 168:  # max 7 dias
                        await update.message.reply_text(
                            "⚠️ O número de horas deve estar entre 1 e 168 (7 dias).\n"
                            "Usando configuração padrão."
                        )
                        hours = None
                except ValueError:
                    await update.message.reply_text(
                        "⚠️ Número de horas inválido.\n"
                        "Usando configuração padrão."
                    )
                    hours = None

            await run_single_profile_scraping(update, username, hours)
            return

        # Caso contrário, executa para todos os perfis
        hours = 3
        if context.args:
            try:
                hours = int(context.args[0])
                if hours < 1 or hours > 24:
                    await update.message.reply_text(
                        "⚠️ O número de horas deve estar entre 1 e 24.\n"
                        "Usando padrão: 3 horas"
                    )
                    hours = 3
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Número de horas inválido.\n"
                    "Usando padrão: 3 horas"
                )

        await update.message.reply_text(
            f"🔄 Executando scraping de todos os perfis...\n"
            f"📅 Posts das últimas {hours} hora(s)\n\n"
            f"⏳ Isso pode demorar alguns minutos."
        )

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await make_authenticated_request(
                client, "POST", f"{API_BASE_URL}/dashboard/run-scrape?hours={hours}"
            )

            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    await update.message.reply_text(
                        f"✅ Scraping iniciado com sucesso!\n\n"
                        f"O processo está rodando em background.\n"
                        f"Use /status para verificar o andamento."
                    )
                else:
                    error_msg = result.get("error", "Erro desconhecido")
                    await update.message.reply_text(
                        f"❌ Erro ao iniciar scraping: {error_msg}"
                    )
            elif response.status_code == 409:
                await update.message.reply_text(
                    "⚠️ Já existe um scraping em andamento.\n"
                    "Aguarde a conclusão ou use /status para verificar."
                )
            elif response.status_code == 403:
                await update.message.reply_text(
                    "❌ Você não tem permissão para executar scraping.\n"
                    "Apenas administradores podem usar este comando."
                )
            else:
                await update.message.reply_text(
                    f"❌ Erro: {response.status_code}"
                )

    except Exception as e:
        logger.error(f"Erro ao executar scraping: {e}")
        await update.message.reply_text(
            f"❌ Erro ao executar scraping: {str(e)}"
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Verifica o status do scraping em andamento.
    Uso: /status
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await make_authenticated_request(
                client, "GET", f"{API_BASE_URL}/dashboard/scrape-status"
            )

            if response.status_code == 200:
                status_data = response.json()
                is_running = status_data.get("running", False)
                result = status_data.get("result")

                if is_running:
                    await update.message.reply_text(
                        "🔄 <b>Scraping em andamento...</b>\n\n"
                        "⏳ O processo está sendo executado.\n"
                        "Use /status novamente para verificar.",
                        parse_mode="HTML"
                    )
                elif result:
                    # Scraping finalizado, mostra resultado
                    if result.get("success", False):
                        message = (
                            "✅ <b>Último scraping concluído!</b>\n\n"
                            f"📊 Perfis: {result.get('profiles_scraped', 0)}/{result.get('profiles_total', 0)}\n"
                            f"📝 Posts encontrados: {result.get('posts_found', 0)}\n"
                            f"🔔 Posts enviados: {result.get('posts_sent', 0)}"
                        )
                    else:
                        error = result.get("error", "Erro desconhecido")
                        message = f"❌ <b>Último scraping falhou</b>\n\nErro: {error}"

                    await update.message.reply_text(message, parse_mode="HTML")
                else:
                    await update.message.reply_text(
                        "ℹ️ Nenhum scraping foi executado ainda.\n\n"
                        "Use /run para iniciar um scraping."
                    )
            else:
                await update.message.reply_text(
                    f"❌ Erro ao verificar status: {response.status_code}"
                )

    except Exception as e:
        logger.error(f"Erro ao verificar status: {e}")
        await update.message.reply_text(
            f"❌ Erro ao verificar status: {str(e)}"
        )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Consulta um perfil específico.
    Uso: /profile @username
    """
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Uso: /profile @username\n\n"
            "Exemplo: /profile @nike"
        )
        return

    username = context.args[0].replace("@", "")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Busca o perfil
            response = await make_authenticated_request(
                client, "GET", f"{API_BASE_URL}/profiles"
            )

            if response.status_code == 200:
                profiles = response.json()

                # Procura o perfil específico
                profile = next(
                    (p for p in profiles if p.get("username", "").lower() == username.lower()),
                    None
                )

                if profile:
                    platform_emoji = {
                        "instagram": "📸",
                        "twitter": "🐦",
                        "facebook": "📘",
                    }.get(profile.get("platform", ""), "📱")

                    message = (
                        f"{platform_emoji} <b>@{profile['username']}</b>\n\n"
                        f"Plataforma: {profile['platform'].upper()}\n"
                        f"Status: {'✅ Ativo' if profile.get('is_active') else '❌ Inativo'}\n"
                        f"ID: {profile.get('id')}\n"
                    )

                    await update.message.reply_text(message, parse_mode="HTML")
                else:
                    await update.message.reply_text(
                        f"❌ Perfil @{username} não encontrado.\n\n"
                        "Use /profiles para ver todos os perfis monitorados."
                    )
            else:
                await update.message.reply_text(
                    f"❌ Erro ao buscar perfil: {response.status_code}"
                )

    except Exception as e:
        logger.error(f"Erro ao buscar perfil: {e}")
        await update.message.reply_text(f"❌ Erro: {str(e)}")


async def add_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Adiciona um novo perfil para monitorar.
    Os alertas serão enviados para este chat/grupo.
    Uso: /add instagram @username
    """
    if len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ <b>Como adicionar um perfil:</b>\n\n"
            "Uso: /add <platform> @username\n\n"
            "<b>Exemplos:</b>\n"
            "/add instagram @nike\n"
            "/add twitter @elonmusk\n\n"
            "<b>Plataformas disponíveis:</b>\n"
            "• instagram\n"
            "• twitter\n"
            "• facebook\n\n"
            "💡 Os alertas serão enviados para este chat!",
            parse_mode="HTML"
        )
        return

    platform = context.args[0].lower()
    username = context.args[1].replace("@", "")

    if platform not in ["instagram", "twitter", "facebook"]:
        await update.message.reply_text(
            "❌ Plataforma inválida.\n\n"
            "Plataformas disponíveis: instagram, twitter, facebook"
        )
        return

    try:
        await update.message.reply_text(f"⏳ Adicionando @{username} ({platform})...")

        # Pega o chat_id onde o comando foi enviado
        chat_id = str(update.effective_chat.id)
        chat_title = update.effective_chat.title or update.effective_user.first_name or "Chat"

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Primeiro, verifica/cria o grupo do Telegram
            groups_response = await make_authenticated_request(
                client, "GET", f"{API_BASE_URL}/telegram/groups"
            )

            telegram_group_id = None

            if groups_response.status_code == 200:
                groups = groups_response.json()
                # Procura se já existe um grupo com este chat_id
                existing_group = next(
                    (g for g in groups if g.get("chat_id") == chat_id),
                    None
                )

                if existing_group:
                    telegram_group_id = existing_group["id"]
                    logger.info(f"Usando grupo existente: {telegram_group_id}")
                else:
                    # Cria novo grupo
                    group_payload = {
                        "chat_id": chat_id,
                        "name": chat_title,
                        "active": True
                    }
                    create_group_response = await make_authenticated_request(
                        client, "POST", f"{API_BASE_URL}/telegram/groups",
                        json=group_payload
                    )

                    if create_group_response.status_code in [200, 201]:
                        new_group = create_group_response.json()
                        telegram_group_id = new_group["id"]
                        logger.info(f"Grupo criado: {telegram_group_id}")

            # 2. Agora cria o perfil com o telegram_group_id
            if not telegram_group_id:
                await update.message.reply_text(
                    "❌ Erro ao configurar grupo do Telegram."
                )
                return

            profile_payload = {
                "username": username,
                "platform": platform,
                "active": True,
                "telegram_group_id": telegram_group_id
            }

            response = await make_authenticated_request(
                client, "POST", f"{API_BASE_URL}/profiles",
                json=profile_payload
            )

            if response.status_code == 200 or response.status_code == 201:
                await update.message.reply_text(
                    f"✅ Perfil adicionado com sucesso!\n\n"
                    f"📱 Plataforma: {platform.upper()}\n"
                    f"👤 Username: @{username}\n"
                    f"📬 Alertas: Este chat\n\n"
                    f"Use /run para fazer scraping."
                )
            elif response.status_code == 400:
                error_detail = response.json().get("detail", "")
                if "already exists" in error_detail.lower():
                    await update.message.reply_text(
                        f"⚠️ O perfil @{username} já está sendo monitorado."
                    )
                else:
                    await update.message.reply_text(
                        f"❌ Erro ao adicionar perfil: {error_detail}"
                    )
            else:
                error_detail = response.json().get("detail", "Erro desconhecido")
                await update.message.reply_text(
                    f"❌ Erro ao adicionar perfil: {error_detail}"
                )

    except Exception as e:
        logger.error(f"Erro ao adicionar perfil: {e}")
        await update.message.reply_text(
            f"❌ Erro ao adicionar perfil: {str(e)}\n\n"
            "Verifique se a API está rodando."
        )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Busca posts nas redes sociais por palavras-chave.
    Uso: /search <palavra1> <palavra2> ...
    Exemplo: /search greve ceara
    """
    if not context.args:
        await update.message.reply_text(
            "ℹ️ <b>Como buscar posts:</b>\n\n"
            "Uso: /search <palavra1> <palavra2> ...\n\n"
            "<b>Exemplos:</b>\n"
            "/search greve\n"
            "/search greve ceara\n"
            "/search black friday\n\n"
            "💡 A busca retornará posts que contenham\n"
            "<b>TODAS</b> as palavras informadas.\n\n"
            "⚠️ Por padrão, busca no Instagram.\n"
            "Outras plataformas em breve.",
            parse_mode="HTML"
        )
        return

    keywords = " ".join(context.args)

    try:
        await update.message.reply_text(
            f"🔍 Buscando posts com: <b>{keywords}</b>\n\n"
            "⏳ Isso pode levar alguns segundos...",
            parse_mode="HTML"
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await make_authenticated_request(
                client, "GET",
                f"{API_BASE_URL}/search?keywords={keywords}&limit=10"
            )

            if response.status_code == 200:
                result = response.json()

                if not result.get("success"):
                    await update.message.reply_text(
                        f"❌ Erro na busca: {result.get('error', 'Erro desconhecido')}"
                    )
                    return

                posts = result.get("posts", [])
                posts_found = result.get("posts_found", 0)
                keyword_list = result.get("keywords", [])

                if posts_found == 0:
                    await update.message.reply_text(
                        f"📭 Nenhum post encontrado com as palavras:\n"
                        f"<b>{', '.join(keyword_list)}</b>\n\n"
                        "💡 Tente palavras-chave diferentes.",
                        parse_mode="HTML"
                    )
                    return

                # Format results
                message_lines = [
                    f"✅ Encontrados <b>{posts_found}</b> posts!\n",
                    f"🔑 Palavras-chave: <b>{', '.join(keyword_list)}</b>\n"
                ]

                for i, post in enumerate(posts, 1):
                    post_url = post.get("profile_url", "")
                    content = post.get("content", "")

                    # Truncate content if too long
                    if len(content) > 100:
                        content = content[:100] + "..."

                    message_lines.append(
                        f"\n<b>{i}.</b> {post_url}\n"
                        f"📝 {content}"
                    )

                # Split into multiple messages if too long
                full_message = "\n".join(message_lines)

                if len(full_message) > 4000:
                    # Send in chunks
                    await update.message.reply_text(
                        "\n".join(message_lines[:3]),
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )

                    for i in range(0, len(posts), 5):
                        chunk = posts[i:i+5]
                        chunk_lines = []
                        for j, post in enumerate(chunk, i+1):
                            post_url = post.get("profile_url", "")
                            content = post.get("content", "")
                            if len(content) > 100:
                                content = content[:100] + "..."
                            chunk_lines.append(
                                f"<b>{j}.</b> {post_url}\n"
                                f"📝 {content}\n"
                            )
                        await update.message.reply_text(
                            "\n".join(chunk_lines),
                            parse_mode="HTML",
                            disable_web_page_preview=True
                        )
                else:
                    await update.message.reply_text(
                        full_message,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )

            elif response.status_code == 408:
                await update.message.reply_text(
                    "⏱️ Timeout: Instagram demorou muito para responder.\n"
                    "Tente novamente em alguns minutos."
                )
            else:
                error_data = response.json()
                error_msg = error_data.get("detail", "Erro desconhecido")
                await update.message.reply_text(
                    f"❌ Erro na busca: {error_msg}"
                )

    except httpx.TimeoutException:
        await update.message.reply_text(
            "⏱️ Timeout ao buscar posts.\n"
            "A busca demorou muito. Tente novamente."
        )
    except Exception as e:
        logger.error(f"Erro ao buscar posts: {e}")
        await update.message.reply_text(
            f"❌ Erro ao buscar posts: {str(e)}\n\n"
            "Verifique se a API está rodando."
        )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para mensagens de texto (não comandos)"""
    text = update.message.text

    await update.message.reply_text(
        f"📩 Você disse: {text}\n\n"
        "Use /help para ver os comandos disponíveis."
    )


def create_bot_application():
    """
    Cria e configura a aplicação do bot.
    Retorna a aplicação configurada para uso com polling.
    """
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN não configurado no .env")

    # Cria a aplicação
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Adiciona handlers de comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("commands", commands_command))

    # Consultas
    application.add_handler(CommandHandler("profiles", profiles_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("status", status_command))

    # Ações
    application.add_handler(CommandHandler("run", run_scraping_command))
    application.add_handler(CommandHandler("add", add_profile_command))
    application.add_handler(CommandHandler("search", search_command))

    # Handler para mensagens de texto (não comandos)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot handlers configurados")

    return application


def run_polling():
    """
    Inicia o bot em modo polling (ideal para localhost).
    O bot fica rodando e consultando o Telegram por novas mensagens.
    """
    application = create_bot_application()

    logger.info("🤖 Iniciando bot em modo polling...")
    logger.info("Bot pronto para receber mensagens!")

    # Inicia polling - o bot ficará rodando
    # run_polling() é síncrono e gerencia seu próprio event loop
    application.run_polling()
