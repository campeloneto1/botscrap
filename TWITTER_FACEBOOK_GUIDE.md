# Guia de Configuração - Twitter/X e Facebook

Este guia explica como configurar e usar o BotScrap para monitorar perfis do Twitter/X e Facebook.

## 🚀 Novidades

O BotScrap agora suporta scraping de **Twitter/X** e **Facebook** usando Playwright (navegador headless), assim como já faz com Instagram.

## ⚠️ Requisitos Importantes

### Twitter/X
- **Credenciais obrigatórias**: O Twitter agora exige login para visualizar a maioria do conteúdo
- Você precisa de uma conta válida do Twitter/X
- Recomenda-se usar uma conta secundária (não sua conta principal)

### Facebook
- **Credenciais obrigatórias**: O Facebook tem fortes proteções anti-bot
- Você precisa de uma conta válida do Facebook
- Recomenda-se usar uma conta secundária (não sua conta principal)
- Use o **email** da conta (não o username)

## 📝 Configuração

### Opção 1: Através da Interface Web

1. Acesse o painel de **Configurações** (Settings)
2. Role até as seções **Twitter/X** e **Facebook**
3. Preencha as credenciais:
   - **Twitter**: Username ou email + senha
   - **Facebook**: Email + senha
4. Clique em **Salvar Configurações**

### Opção 2: Variáveis de Ambiente (.env)

Edite o arquivo `.env` e adicione:

```bash
# Twitter/X
TWITTER_USERNAME=seu_usuario_ou_email
TWITTER_PASSWORD=sua_senha

# Facebook
FACEBOOK_EMAIL=seu_email@exemplo.com
FACEBOOK_PASSWORD=sua_senha
```

Reinicie o container:
```bash
docker-compose restart
```

## 📊 Adicionando Perfis para Monitorar

Após configurar as credenciais, você pode adicionar perfis do Twitter e Facebook:

1. Acesse **Perfis** (Profiles)
2. Clique em **Adicionar Perfil**
3. Selecione a plataforma:
   - `twitter` para Twitter/X
   - `facebook` para Facebook
4. Insira o username/nome da página
5. Selecione o grupo do Telegram (opcional)
6. Clique em **Salvar**

### Exemplos de Usernames

**Twitter:**
```
elonmusk          (sem @)
BBCBreaking
CNNBrasil
```

**Facebook:**
```
zuck              (username/slug da página)
BBCNews
GloboNews
```

## 🔧 Como Funciona

### Twitter/X
1. O scraper faz login com suas credenciais
2. Navega até o perfil especificado
3. Extrai os tweets recentes (últimas X horas)
4. Salva os posts no banco de dados
5. O sistema processa os posts (OCR, keywords, resumo IA)
6. Envia notificações via Telegram

### Facebook
1. O scraper faz login com suas credenciais
2. Navega até a página/perfil especificado
3. Extrai os posts recentes
4. Processa e envia notificações

## ⚙️ Configurações de Scraping

As mesmas configurações do Instagram se aplicam:

- **Intervalo de verificação**: A cada quantas horas verificar novos posts
- **Delay entre perfis**: Tempo de espera entre cada perfil (evita bloqueio)

Ajuste em **Configurações > Scraping**

## 🚨 Avisos Importantes

### Segurança
- ⚠️ Use contas secundárias para scraping
- ⚠️ Não use sua conta pessoal principal
- ⚠️ As senhas são armazenadas de forma mascarada no banco

### Rate Limits
- Twitter e Facebook têm proteções anti-bot rigorosas
- Evite scraping muito frequente (recomendado: 6+ horas)
- Use delays maiores entre perfis (3-10 segundos)

### Privacidade
- Apenas perfis/páginas **públicos** podem ser monitorados
- Perfis privados retornarão erro

### Estabilidade
- A estrutura do DOM do Twitter e Facebook muda frequentemente
- Se o scraping parar de funcionar, pode ser necessário atualizar os seletores
- Instagram continua funcionando normalmente

## 🧪 Testando

### Via Interface
1. Adicione um perfil de teste
2. Clique no botão **Testar** ao lado do perfil
3. Verifique se consegue extrair posts

### Via Scraping Manual
1. Vá em **Dashboard**
2. Clique em **Executar Scraping Manual**
3. Escolha o período (últimas 3, 6, 12, 24 horas)
4. Acompanhe os logs

## 🐛 Problemas Comuns

### "Twitter login failed"
- Verifique se as credenciais estão corretas
- Certifique-se de que a conta não tem autenticação de dois fatores (2FA)
- Tente usar o email ao invés do username

### "Facebook login failed"
- Use o **email** (não o username)
- Verifique se a senha está correta
- Desative 2FA temporariamente

### "This account doesn't exist"
- Verifique se o username está correto
- Não use @ no início
- Para Facebook, use o slug da URL (facebook.com/SLUG)

### Posts não são encontrados
- Verifique se o perfil é público
- Aumente o intervalo de verificação
- Verifique os logs em Dashboard > Logs

## 📖 Estrutura do Banco de Dados

Os posts do Twitter e Facebook são salvos na mesma tabela `processed_posts`, com:

```python
platform: "twitter" ou "facebook"
post_id: ID único do post
content: Texto do post
media_url: URL de imagem/vídeo (se houver)
created_at: Data de criação
```

## 🔄 Atualizações

As credenciais podem ser atualizadas a qualquer momento:

1. Vá em **Configurações**
2. Edite Twitter ou Facebook
3. Salve
4. O sistema usará as novas credenciais no próximo scraping

## 💡 Dicas

1. **Comece devagar**: Teste com 1-2 perfis antes de adicionar muitos
2. **Use delays maiores**: 5-10 segundos é mais seguro que 3 segundos
3. **Monitore os logs**: Fique de olho em erros de rate limit
4. **Contas separadas**: Use contas exclusivas para scraping
5. **Backup de credenciais**: Anote suas credenciais em local seguro

## 📚 Referências

- Scrapers implementados em: `backend/app/scrapers/`
  - `twitter_playwright.py`
  - `facebook_playwright.py`
- Scheduler: `backend/app/core/scheduler.py`
- Configurações: Tabela `app_settings` no banco de dados

## 🆘 Suporte

Se encontrar problemas:

1. Verifique os logs no Dashboard
2. Teste manualmente o perfil
3. Verifique se as credenciais estão corretas
4. Reporte issues em: https://github.com/seu-repo/issues
