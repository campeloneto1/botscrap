from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Profile, ProcessedPost, Keyword, TelegramGroup, ScrapingLog
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Import scheduler instance from main (will be set after app starts)
_scheduler = None
_manual_scrape_running = False
_manual_scrape_result = None
_manual_scrape_progress = None  # Track progress in real-time

def set_scheduler(scheduler):
    global _scheduler
    _scheduler = scheduler

def get_scheduler_status():
    status = {
        "is_running": False,
        "last_run": None,
        "next_run": None,
        "interval_hours": None,
    }
    if _scheduler:
        status = _scheduler.get_status()

    # Add manual scrape status
    status["manual_scrape_running"] = _manual_scrape_running
    return status


async def run_manual_scrape_background(hours: int = 3):
    """Run a manual scrape in background with progress tracking."""
    global _manual_scrape_running, _manual_scrape_result, _manual_scrape_progress
    _manual_scrape_running = True
    _manual_scrape_result = None
    _manual_scrape_progress = {
        "status": "starting",
        "profiles_total": 0,
        "profiles_completed": 0,
        "current_profiles": [],
    }

    try:
        if _scheduler:
            result = await _scheduler.run_manual_scrape(hours)
            _manual_scrape_result = result
            _manual_scrape_progress = {
                "status": "completed",
                "profiles_total": result.get("profiles_total", 0),
                "profiles_completed": result.get("profiles_scraped", 0),
                "current_profiles": [],
            }
            logger.info(f"Manual scrape completed: {result}")
    except Exception as e:
        logger.error(f"Manual scrape error: {e}")
        _manual_scrape_result = {"success": False, "error": str(e)}
        _manual_scrape_progress = {"status": "error", "error": str(e)}
    finally:
        _manual_scrape_running = False


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
        "scheduler": get_scheduler_status(),
    }


@router.post("/run-scrape")
async def trigger_manual_scrape(
    hours: int = Query(default=3, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger a manual scrape in background."""
    from fastapi import HTTPException, status

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can trigger manual scrapes",
        )

    if _manual_scrape_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A manual scrape is already running",
        )

    if not _scheduler:
        return {"success": False, "error": "Scheduler not available"}

    # Run in background - return immediately
    asyncio.create_task(run_manual_scrape_background(hours))

    return {
        "success": True,
        "message": "Scrape started in background",
        "hours": hours,
    }


@router.get("/scrape-status")
async def get_scrape_status(
    current_user: User = Depends(get_current_user),
):
    """Get the status of manual scrape."""
    return {
        "running": _manual_scrape_running,
        "result": _manual_scrape_result,
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
    offset: int = Query(default=0, ge=0),
    keyword_only: bool = Query(default=False),
    sent_only: bool = Query(default=False),
    profile_id: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload

    query = (
        select(ProcessedPost)
        .join(Profile)
        .options(selectinload(ProcessedPost.profile))
        .where(Profile.user_id == current_user.id)
    )

    if keyword_only:
        query = query.where(ProcessedPost.has_keyword == True)

    if sent_only:
        query = query.where(ProcessedPost.sent_at.isnot(None))

    if profile_id:
        query = query.where(ProcessedPost.profile_id == profile_id)

    if search:
        query = query.where(ProcessedPost.content.ilike(f"%{search}%"))

    # Count total for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ProcessedPost.processed_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    return {
        "total": total,
        "posts": [
            {
                "id": post.id,
                "profile_id": post.profile_id,
                "profile_username": post.profile.username if post.profile else None,
                "profile_platform": post.profile.platform if post.profile else None,
                "post_id": post.post_id,
                "content": post.content,
                "summary": post.summary,
                "media_url": post.media_url,
                "has_keyword": post.has_keyword,
                "matched_keywords": post.matched_keywords,
                "sent_at": post.sent_at,
                "processed_at": post.processed_at,
            }
            for post in posts
        ]
    }
