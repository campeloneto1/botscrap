from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "BotScrap"
    debug: bool = False

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

    # Scraping
    scrape_interval_hours: int = 6
    scrape_delay_seconds: int = 3

    # Proxies
    use_proxies: bool = False
    proxy_list: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
