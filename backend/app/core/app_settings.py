"""
Dynamic application settings that can be configured via the UI.
Falls back to .env values if not configured in the database.
"""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import async_session
from app.db.models import AppSettings

logger = logging.getLogger(__name__)
_env_settings = get_settings()

# Cache for settings
_cached_settings: Optional[AppSettings] = None


async def get_app_settings(db: Optional[AsyncSession] = None) -> AppSettings:
    """
    Get application settings from database, with fallback to .env values.
    Creates default settings if none exist.
    """
    global _cached_settings

    if db is None:
        async with async_session() as db:
            return await _get_or_create_settings(db)
    else:
        return await _get_or_create_settings(db)


async def _get_or_create_settings(db: AsyncSession) -> AppSettings:
    """Get settings from DB or create with defaults from .env."""
    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings:
        # Create with defaults from .env
        settings = AppSettings(
            telegram_bot_token=_env_settings.telegram_bot_token or None,
            instagram_username=_env_settings.instagram_username or None,
            instagram_password=_env_settings.instagram_password or None,
            twitter_username=_env_settings.twitter_username or None,
            twitter_password=_env_settings.twitter_password or None,
            facebook_email=_env_settings.facebook_email or None,
            facebook_password=_env_settings.facebook_password or None,
            scrape_interval_hours=_env_settings.scrape_interval_hours,
            scrape_delay_seconds=_env_settings.scrape_delay_seconds,
            use_proxies=_env_settings.use_proxies,
            proxy_list=_env_settings.proxy_list or None,
            groq_api_key=_env_settings.groq_api_key or None,
            enable_ai_summary=_env_settings.enable_ai_summary,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info("Created default app settings from .env")

    return settings


def get_telegram_token(settings: AppSettings) -> Optional[str]:
    """Get Telegram bot token, with fallback to .env."""
    return settings.telegram_bot_token or _env_settings.telegram_bot_token or None


def get_instagram_credentials(settings: AppSettings) -> tuple[Optional[str], Optional[str]]:
    """Get Instagram credentials, with fallback to .env."""
    username = settings.instagram_username or _env_settings.instagram_username or None
    password = settings.instagram_password or _env_settings.instagram_password or None
    return username, password


def get_twitter_credentials(settings: AppSettings) -> tuple[Optional[str], Optional[str]]:
    """Get Twitter credentials, with fallback to .env."""
    username = settings.twitter_username or _env_settings.twitter_username or None
    password = settings.twitter_password or _env_settings.twitter_password or None
    return username, password


def get_facebook_credentials(settings: AppSettings) -> tuple[Optional[str], Optional[str]]:
    """Get Facebook credentials, with fallback to .env."""
    email = settings.facebook_email or _env_settings.facebook_email or None
    password = settings.facebook_password or _env_settings.facebook_password or None
    return email, password


def get_scrape_interval(settings: AppSettings) -> int:
    """Get scrape interval in hours."""
    return settings.scrape_interval_hours or _env_settings.scrape_interval_hours


def get_scrape_delay(settings: AppSettings) -> int:
    """Get scrape delay in seconds."""
    return settings.scrape_delay_seconds or _env_settings.scrape_delay_seconds


def get_groq_api_key(settings: AppSettings) -> Optional[str]:
    """Get Groq API key, with fallback to .env."""
    return settings.groq_api_key or _env_settings.groq_api_key or None


def is_ai_summary_enabled(settings: AppSettings) -> bool:
    """Check if AI summary is enabled."""
    return settings.enable_ai_summary


def get_proxy_list(settings: AppSettings) -> list[str]:
    """Get list of proxies if enabled."""
    if not settings.use_proxies:
        return []

    proxy_list = settings.proxy_list or _env_settings.proxy_list
    if not proxy_list:
        return []

    return [p.strip() for p in proxy_list.split('\n') if p.strip()]
