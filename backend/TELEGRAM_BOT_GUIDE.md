# 🤖 Guia do Bot Telegram com Consulta à API Local

## Como Funciona

O bot usa **polling mode** para receber mensagens dos usuários do Telegram e consulta sua API FastAPI rodando em `localhost:8000`.

```
Usuário → Telegram → Bot (polling) → API localhost:8000
```

## ⚙️ Configuração

### 1. Configure o Token do Bot

No arquivo `.env`, adicione seu token:

```bash
TELEGRAM_BOT_TOKEN=seu_token_aqui
```

**Como obter o token:**
1. Abra o Telegram e busque por `@BotFather`
2. Envie `/newbot` e siga as instruções
3. Copie o token gerado

### 2. Certifique-se de que a API está rodando

O bot precisa que o FastAPI esteja rodando:

```bash
cd backend
uvicorn app.main:app --reload
# ou
docker-compose up
```

Verifique se está acessível: http://localhost:8000

## 🚀 Como Rodar o Bot

### Opção 1: Diretamente com Python

```bash
cd backend
python run_telegram_bot.py
```

### Opção 2: Dentro do container Docker

Adicione no `docker-compose.yml`:

```yaml
  telegram-bot:
    build:
      context: ./backend
    command: python run_telegram_bot.py
    env_file:
      - .env
    depends_on:
      - backend
    networks:
      - botscrap-network
```

## 📱 Comandos Disponíveis

### 📋 Consultas

- `/start` - Iniciar o bot e ver menu
- `/help` - Ver ajuda detalhada
- `/profiles` - Listar todos os perfis monitorados
- `/profile @username` - Ver informações de um perfil específico
- `/stats` - Ver estatísticas do sistema

### ⚡ Ações

- `/run` - Executar scraping de **todos** os perfis
- `/run @username` - Executar scraping de **um perfil específico**
- `/add <platform> @username` - Adicionar novo perfil para monitorar

### 💡 Exemplos Práticos

```
/profile @nike                    # Ver info do perfil Nike
/run @nike                        # Rodar scraping só da Nike
/add instagram @adidas            # Adicionar Adidas do Instagram
/add twitter @elonmusk            # Adicionar Elon Musk do Twitter
```

## 🔧 Personalizando

### Adicionar novos comandos

Edite `backend/app/telegram/handlers.py`:

```python
async def meu_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /meu_comando"""
    # Consulta sua API
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/seu-endpoint")
        data = response.json()

    await update.message.reply_text(f"Dados: {data}")

# Registrar o handler
application.add_handler(CommandHandler("meu_comando", meu_comando))
```

### Adicionar autenticação na API

Para consultas que precisam de autenticação, você pode:

1. **Salvar o token no banco** vinculado ao `chat_id` do usuário
2. **Usar headers de autenticação**:

```python
headers = {"Authorization": f"Bearer {token}"}
response = await client.get(url, headers=headers)
```

## 🆚 Polling vs Webhooks

### ✅ Polling (Implementado)
- **Vantagem**: Funciona perfeitamente com localhost
- **Vantagem**: Não precisa de túnel ou exposição pública
- **Desvantagem**: Usa mais recursos (polling constante)

### Webhooks (Alternativa)
- **Vantagem**: Mais eficiente (só recebe quando tem mensagem)
- **Desvantagem**: Precisa de URL pública
- **Solução para localhost**: Use ngrok ou localtunnel

#### Como usar webhooks com ngrok:

```bash
# Terminal 1: Rode sua API
uvicorn app.main:app --reload

# Terminal 2: Exponha com ngrok
ngrok http 8000

# Use a URL gerada (ex: https://abc123.ngrok.io) para configurar o webhook
```

## 🐛 Troubleshooting

### Bot não responde
- ✅ Verifique se o token está correto no `.env`
- ✅ Confirme que o bot está rodando (`python run_telegram_bot.py`)
- ✅ Veja os logs no terminal

### Erro ao consultar API
- ✅ Certifique-se de que o FastAPI está rodando
- ✅ Teste manualmente: `curl http://localhost:8000/api/profiles`
- ✅ Verifique se precisa de autenticação

### "Network error" ou timeout
- ✅ Verifique sua conexão com internet
- ✅ Telegram pode estar bloqueado em algumas redes (use VPN se necessário)

## 🎯 Exemplo Completo de Uso

Imagine que você quer monitorar a Nike no Instagram via Telegram:

```
1️⃣ Você: /add instagram @nike
   Bot: ✅ Perfil adicionado com sucesso!

2️⃣ Você: /run @nike
   Bot: 🔄 Executando scraping para @nike...
   Bot: ✅ Scraping concluído! 📝 Posts encontrados: 5

3️⃣ Você: /profile @nike
   Bot: 📸 @nike
        Plataforma: INSTAGRAM
        Status: ✅ Ativo

4️⃣ Você: /profiles
   Bot: 📋 Perfis monitorados:
        ✅ INSTAGRAM: @nike
        ✅ TWITTER: @elonmusk

5️⃣ Você: /stats
   Bot: 📊 Estatísticas:
        👥 Perfis: 2
        📝 Posts: 12
        🔔 Alertas enviados: 3
```

## 📚 Recursos

- [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
