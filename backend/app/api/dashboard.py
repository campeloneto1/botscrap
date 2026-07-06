from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Profile, ProcessedPost, Keyword, TelegramGroup, ScrapingLog
from app.core.security import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Total profiles
    profiles_result = await db.execute(
        select(func.count(Profile.id)).where(Profile.user_id == current_user.id)
    )
    total_profiles = profiles_result.scalar() or 0

    # Active profiles
    active_profiles_result = await db.execute(
        select(func.count(Profile.id)).where(
            Profile.user_id == current_user.id,
            Profile.active == True,
        )
    )
    active_profiles = active_profiles_result.scalar() or 0

    # Total keywords
    keywords_result = await db.execute(
        select(func.count(Keyword.id)).where(Keyword.user_id == current_user.id)
    )
    total_keywords = keywords_result.scalar() or 0

    # Total telegram groups
    groups_result = await db.execute(
        select(func.count(TelegramGroup.id)).where(TelegramGroup.user_id == current_user.id)
    )
    total_groups = groups_result.scalar() or 0

    # Posts today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    posts_today_result = await db.execute(
        select(func.count(ProcessedPost.id))
        .join(Profile)
        .where(
            Profile.user_id == current_user.id,
            ProcessedPost.processed_at >= today_start,
        )
    )
    posts_today = posts_today_result.scalar() or 0

    # Posts with keywords today
    keyword_posts_result = await db.execute(
        select(func.count(ProcessedPost.id))
        .join(Profile)
        .where(
            Profile.user_id == current_user.id,
            ProcessedPost.processed_at >= today_start,
            ProcessedPost.has_keyword == True,
        )
    )
    keyword_posts_today = keyword_posts_result.scalar() or 0

    return {
        "total_profiles": total_profiles,
        "active_profiles": active_profiles,
        "total_keywords": total_keywords,
        "total_telegram_groups": total_groups,
        "posts_today": posts_today,
        "keyword_alerts_today": keyword_posts_today,
    }


@router.get("/logs")
async def get_logs(
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScrapingLog)
        .join(Profile, isouter=True)
        .where(Profile.user_id == current_user.id)
        .order_by(ScrapingLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "profile_id": log.profile_id,
            "status": log.status,
            "message": log.message,
            "posts_found": log.posts_found,
            "posts_sent": log.posts_sent,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.get("/posts")
async def get_recent_posts(
    limit: int = Query(default=20, le=100),
    keyword_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(ProcessedPost)
        .join(Profile)
        .where(Profile.user_id == current_user.id)
    )

    if keyword_only:
        query = query.where(ProcessedPost.has_keyword == True)

    query = query.order_by(ProcessedPost.processed_at.desc()).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    return [
        {
            "id": post.id,
            "profile_id": post.profile_id,
            "post_id": post.post_id,
            "content": post.content[:200] if post.content else None,
            "media_url": post.media_url,
            "has_keyword": post.has_keyword,
            "matched_keywords": post.matched_keywords,
            "sent_at": post.sent_at,
            "processed_at": post.processed_at,
        }
        for post in posts
    ]
