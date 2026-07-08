import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from app.core.security import get_current_user

router = APIRouter()


@router.get("", response_model=List[ProfileResponse])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("", response_model=ProfileResponse)
async def create_profile(
    profile_data: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Normalize username (remove @)
    username = profile_data.username.lstrip("@")

    # Check if profile already exists
    result = await db.execute(
        select(Profile).where(
            Profile.user_id == current_user.id,
            Profile.platform == profile_data.platform,
            Profile.username == username,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists",
        )

    profile = Profile(
        user_id=current_user.id,
        platform=profile_data.platform,
        username=username,
        telegram_group_id=profile_data.telegram_group_id,
        active=profile_data.active,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return profile


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    profile_data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    update_data = profile_data.model_dump(exclude_unset=True)
    if "username" in update_data:
        update_data["username"] = update_data["username"].lstrip("@")

    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return profile


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    await db.delete(profile)
    await db.commit()

    return {"message": "Profile deleted"}


@router.patch("/{profile_id}/toggle", response_model=ProfileResponse)
async def toggle_profile_active(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle profile active status (pause/resume monitoring)."""
    result = await db.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    profile.active = not profile.active
    await db.commit()
    await db.refresh(profile)

    return profile


@router.post("/{profile_id}/test")
async def test_scrape_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(
            Profile.id == profile_id,
            Profile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Import scraper and test - usando Playwright (navegador headless)
    from app.scrapers.instagram_playwright import InstagramPlaywrightScraper

    if profile.platform != "instagram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scraper for {profile.platform} not implemented yet",
        )

    from datetime import datetime, timedelta

    try:
        scraper = InstagramPlaywrightScraper()
        # Para teste, busca posts dos últimos 30 dias (não apenas 24h)
        since = datetime.utcnow() - timedelta(days=30)
        # Timeout de 60 segundos (navegador é mais lento)
        posts = await asyncio.wait_for(
            scraper.get_recent_posts(profile.username, limit=3, since=since),
            timeout=60.0
        )
        return {
            "success": True,
            "profile": profile.username,
            "posts_found": len(posts),
            "posts": posts,
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "profile": profile.username,
            "error": "Timeout: Instagram demorou muito para responder. Tente novamente mais tarde.",
        }
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            error_msg = "Rate limit do Instagram atingido. Aguarde alguns minutos e tente novamente."
        return {
            "success": False,
            "profile": profile.username,
            "error": error_msg,
        }


@router.post("/{profile_id}/test-telegram")
async def test_scrape_and_send_telegram(
    profile_id: int,
    hours: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scrape profile and send posts to Telegram."""
    from datetime import datetime, timedelta
    from sqlalchemy.orm import selectinload
    from app.db.models import AppSettings

    # Se não informar horas, busca da config do banco
    if hours is None:
        settings_result = await db.execute(select(AppSettings))
        app_settings = settings_result.scalar_one_or_none()

        if app_settings:
            hours = app_settings.scrape_interval_hours
        else:
            # Fallback se não existir config no banco
            hours = 6

    result = await db.execute(
        select(Profile)
        .options(selectinload(Profile.telegram_group))
        .where(
            Profile.id == profile_id,
            Profile.user_id == current_user.id,
        )
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    if not profile.telegram_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Perfil não tem grupo Telegram associado",
        )

    # Import dependencies
    from app.scrapers.instagram_playwright import InstagramPlaywrightScraper
    from app.telegram.bot import TelegramBot
    from app.utils.keywords import find_keywords
    from app.db.models import Keyword, ProcessedPost

    if profile.platform != "instagram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scraper for {profile.platform} not implemented yet",
        )

    try:
        # Get keywords
        keywords_result = await db.execute(
            select(Keyword).where(
                Keyword.user_id == current_user.id,
                Keyword.active == True,
            )
        )
        keywords = [
            {"word": k.word, "priority": k.priority}
            for k in keywords_result.scalars().all()
        ]

        # Scrape posts
        scraper = InstagramPlaywrightScraper()
        since = datetime.utcnow() - timedelta(hours=hours)
        posts = await asyncio.wait_for(
            scraper.get_recent_posts(profile.username, limit=3, since=since),
            timeout=60.0
        )

        if not posts:
            return {
                "success": False,
                "profile": profile.username,
                "error": f"Nenhum post encontrado nas últimas {hours} horas",
            }

        # Send to Telegram
        bot = TelegramBot()
        chat_id = profile.telegram_group.chat_id
        sent_count = 0
        skipped_count = 0

        for post in posts:  # Envia todos os posts encontrados
            post_id = post.get("id", "")

            # Verifica se o post já foi processado
            existing_post = await db.execute(
                select(ProcessedPost).where(
                    ProcessedPost.profile_id == profile.id,
                    ProcessedPost.post_id == post_id,
                )
            )
            existing = existing_post.scalar_one_or_none()

            if existing:
                # Post já foi processado, pula
                skipped_count += 1
                continue

            has_keyword, matched, priority = find_keywords(
                post.get("content", ""),
                keywords,
            )

            if has_keyword and priority >= 2:
                success = await bot.send_alert(
                    chat_id=chat_id,
                    post=post,
                    profile_username=profile.username,
                    platform=profile.platform,
                    matched_keywords=matched,
                    priority=priority,
                )
            else:
                success = await bot.send_post(
                    chat_id=chat_id,
                    post=post,
                    profile_username=profile.username,
                    platform=profile.platform,
                    matched_keywords=matched if has_keyword else None,
                )

            if success:
                sent_count += 1

                # Salva o post no banco de dados
                processed_post = ProcessedPost(
                    profile_id=profile.id,
                    post_id=post_id,
                    content=post.get("content", ""),
                    summary=post.get("summary"),
                    media_url=post.get("media_url"),
                    ocr_text=post.get("ocr_text"),
                    has_keyword=has_keyword,
                    matched_keywords=matched if has_keyword else None,
                    status="completed",
                    sent_at=datetime.utcnow(),
                    processed_at=datetime.utcnow(),
                )
                db.add(processed_post)

        # Atualiza o last_scraped do perfil
        profile.last_scraped = datetime.utcnow()
        await db.commit()

        return {
            "success": True,
            "profile": profile.username,
            "posts_found": len(posts),
            "posts_sent": sent_count,
            "posts_skipped": skipped_count,
            "telegram_group": profile.telegram_group.name,
            "keywords_matched": matched if has_keyword else [],
            "hours": hours,
        }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "profile": profile.username,
            "error": "Timeout ao buscar posts",
        }
    except Exception as e:
        return {
            "success": False,
            "profile": profile.username,
            "error": str(e),
        }
