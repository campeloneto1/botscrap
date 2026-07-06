from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, AppSettings
from app.schemas.settings import AppSettingsResponse, AppSettingsUpdate
from app.core.security import get_current_user

router = APIRouter()

# Scheduler instance (will be set from main.py)
_scheduler = None


def set_scheduler(scheduler):
    """Set the scheduler instance for dynamic reconfiguration."""
    global _scheduler
    _scheduler = scheduler


def mask_sensitive(value: str | None) -> str | None:
    """Mask sensitive values, showing only last 4 chars."""
    if not value or len(value) < 8:
        return "****" if value else None
    return "*" * (len(value) - 4) + value[-4:]


@router.get("", response_model=AppSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current application settings."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access settings",
        )

    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = AppSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    # Mask sensitive fields for response
    return AppSettingsResponse(
        id=settings.id,
        telegram_bot_token=mask_sensitive(settings.telegram_bot_token),
        instagram_username=settings.instagram_username,
        instagram_password=mask_sensitive(settings.instagram_password),
        scrape_interval_hours=settings.scrape_interval_hours,
        scrape_delay_seconds=settings.scrape_delay_seconds,
        use_proxies=settings.use_proxies,
        proxy_list=settings.proxy_list,
        groq_api_key=mask_sensitive(settings.groq_api_key),
        enable_ai_summary=settings.enable_ai_summary,
        updated_at=settings.updated_at,
    )


@router.put("", response_model=AppSettingsResponse)
async def update_settings(
    settings_data: AppSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update application settings."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can modify settings",
        )

    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings:
        settings = AppSettings()
        db.add(settings)

    # Update only provided fields (skip masked values)
    update_data = settings_data.model_dump(exclude_unset=True)
    old_interval = settings.scrape_interval_hours

    for field, value in update_data.items():
        # Skip if value contains mask pattern (user didn't change it)
        if isinstance(value, str) and value.startswith("*"):
            continue
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)

    # Reschedule if interval changed
    if _scheduler and settings.scrape_interval_hours != old_interval:
        _scheduler.reschedule(settings.scrape_interval_hours)

    # Return with masked sensitive fields
    return AppSettingsResponse(
        id=settings.id,
        telegram_bot_token=mask_sensitive(settings.telegram_bot_token),
        instagram_username=settings.instagram_username,
        instagram_password=mask_sensitive(settings.instagram_password),
        scrape_interval_hours=settings.scrape_interval_hours,
        scrape_delay_seconds=settings.scrape_delay_seconds,
        use_proxies=settings.use_proxies,
        proxy_list=settings.proxy_list,
        groq_api_key=mask_sensitive(settings.groq_api_key),
        enable_ai_summary=settings.enable_ai_summary,
        updated_at=settings.updated_at,
    )


@router.post("/test-telegram")
async def test_telegram_connection(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test Telegram bot connection."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can test connections",
        )

    result = await db.execute(select(AppSettings).limit(1))
    settings = result.scalar_one_or_none()

    if not settings or not settings.telegram_bot_token:
        return {"success": False, "error": "Telegram Bot Token não configurado"}

    try:
        from telegram import Bot
        bot = Bot(token=settings.telegram_bot_token)
        me = await bot.get_me()
        return {
            "success": True,
            "bot_name": me.first_name,
            "bot_username": me.username,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
