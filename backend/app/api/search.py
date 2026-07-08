import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, AppSettings
from app.core.security import get_current_user

router = APIRouter()


@router.get("")
async def search_posts(
    keywords: str = Query(..., description="Keywords to search (space-separated, e.g., 'greve ceara')"),
    platform: str = Query(default="instagram", description="Platform to search"),
    limit: int = Query(default=10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search social media posts by keywords.

    Args:
        keywords: Space-separated keywords (e.g., "greve ceara")
        platform: Platform to search (currently only "instagram")
        limit: Maximum number of results (1-20)

    Returns:
        List of posts matching ALL the specified keywords
    """
    # Split keywords by space
    keyword_list = [k.strip() for k in keywords.split() if k.strip()]

    if not keyword_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forneça pelo menos uma palavra-chave para buscar",
        )

    if platform != "instagram":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Busca para {platform} ainda não implementada. Use 'instagram'.",
        )

    # Get Instagram credentials from database
    settings_result = await db.execute(select(AppSettings))
    app_settings = settings_result.scalar_one_or_none()

    instagram_username = None
    instagram_password = None

    if app_settings:
        instagram_username = app_settings.instagram_username
        instagram_password = app_settings.instagram_password

    # Import scraper
    from app.scrapers.instagram_playwright import InstagramPlaywrightScraper

    try:
        scraper = InstagramPlaywrightScraper()

        # Search with timeout
        posts = await asyncio.wait_for(
            scraper.search_by_keywords(
                keyword_list,
                limit=limit,
                instagram_username=instagram_username,
                instagram_password=instagram_password
            ),
            timeout=90.0  # 90 seconds timeout
        )

        return {
            "success": True,
            "keywords": keyword_list,
            "platform": platform,
            "posts_found": len(posts),
            "posts": posts,
        }

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Timeout: Instagram demorou muito para responder. Tente novamente.",
        )
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            error_msg = "Rate limit do Instagram atingido. Aguarde alguns minutos."

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )
