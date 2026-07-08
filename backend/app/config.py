from pydantic_settings import BaseSettings
from functools import lru_cache
from datetime import datetime
from zoneinfo import ZoneInfo


class Settings(BaseSettings):
    # App
    app_name: str = "BotScrap"
    debug: bool = False

    # Timezone
    timezone: str = "America/Fortaleza"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/botscrap"

    # Auth
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Default Admin User
    admin_email: str = "admin@botscrap.com"
    admin_password: str = "admin123"

    # Telegram
    telegram_bot_token: str = ""

    # Instagram
    instagram_username: str = ""
    instagram_password: str = ""

    # Twitter/X
    twitter_username: str = ""
    twitter_password: str = ""

    # Facebook
    facebook_email: str = ""
    facebook_password: str = ""

    # Scraping
    scrape_interval_hours: int = 6
    scrape_delay_seconds: int = 3

    # AI Summary (Groq - free tier)
    groq_api_key: str = ""
    enable_ai_summary: bool = True

    # Proxies
    use_proxies: bool = False
    proxy_list: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_local_now() -> datetime:
    """Retorna a data/hora atual no timezone configurado (America/Fortaleza)."""
    settings = get_settings()
    tz = ZoneInfo(settings.timezone)
    return datetime.now(tz)


def get_local_today_start() -> datetime:
    """Retorna o início do dia atual no timezone configurado."""
    now = get_local_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_local_now_naive() -> datetime:
    """
    Retorna a data/hora atual no timezone configurado sem info de timezone.
    Usado para compatibilidade com colunas DateTime do SQLAlchemy.
    """
    return get_local_now().replace(tzinfo=None)
