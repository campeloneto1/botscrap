# 🚀 Telegram Bot - Quick Start

## 1️⃣ Configure o Token

Edite o arquivo `.env` e adicione seu token do Telegram:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Como obter o token:**
1. Abra o Telegram
2. Busque por `@BotFather`
3. Envie `/newbot` e siga as instruções
4. Copie o token gerado

## 2️⃣ Inicie tudo com Docker

```bash
docker-compose up -d
```

Isso vai iniciar automaticamente:
- ✅ Banco de dados (PostgreSQL)
- ✅ Backend API (FastAPI)
- ✅ Scheduler (agendador de scraping)
- ✅ **Bot do Telegram** (novo!)
- ✅ Frontend (React)

## 3️⃣ Verifique os logs do bot

```bash
docker logs -f botscrap-telegram-bot
```

Você deve ver algo como:
```
🤖 Iniciando bot em modo polling...
Bot pronto para receber mensagens!
```

## 4️⃣ Use o bot no Telegram

Abra o Telegram e envie comandos para o bot:

### Comandos básicos:
```
/start                        # Ver menu
/help                         # Ajuda
```

### Consultas:
```
/profiles                     # Listar todos os perfis
/profile @nike                # Ver perfil específico
/stats                        # Estatísticas
```

### Ações:
```
/add instagram @nike          # Adicionar perfil
/run                          # Rodar scraping de todos
/run @nike                    # Rodar scraping de um perfil
```

## 🔧 Troubleshooting

### Bot não inicia
```bash
# Veja os logs
docker logs botscrap-telegram-bot

# Verifique se o token está correto no .env
cat .env | grep TELEGRAM_BOT_TOKEN
```

### Reiniciar apenas o bot
```bash
docker-compose restart telegram-bot
```

### Rodar bot localmente (sem Docker)
```bash
cd backend
python run_telegram_bot.py
```

## 📦 Comandos úteis

```bash
# Ver todos os containers rodando
docker-compose ps

# Parar tudo
docker-compose down

# Ver logs de todos os serviços
docker-compose logs -f

# Reconstruir e reiniciar
docker-compose up -d --build
```

## ✅ Está funcionando?

Se você ver nos logs:
```
Bot pronto para receber mensagens!
```

E conseguir enviar `/start` para o bot no Telegram e receber resposta, **está tudo certo!** 🎉
