"""
Statistics endpoints for dashboard.
"""
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ProcessedPost, Profile, ScrapingLog
from app.api.auth import get_current_user, User
from app.config import get_local_now

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
async def get_stats_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overview statistics for dashboard."""

    # Posts by status
    status_query = select(
        ProcessedPost.status,
        func.count(ProcessedPost.id).label("count")
    )

    if not current_user.is_admin:
        # Filter by user's profiles
        status_query = status_query.join(Profile).where(Profile.user_id == current_user.id)

    status_query = status_query.group_by(ProcessedPost.status)

    result = await db.execute(status_query)
    status_counts = {row[0]: row[1] for row in result.fetchall()}

    # Recent posts with keywords (last 7 days) - usando timezone America/Fortaleza
    seven_days_ago = get_local_now() - timedelta(days=7)
    keywords_query = select(func.count(ProcessedPost.id)).where(
        and_(
            ProcessedPost.has_keyword == True,
            ProcessedPost.processed_at >= seven_days_ago
        )
    )

    if not current_user.is_admin:
        keywords_query = keywords_query.join(Profile).where(Profile.user_id == current_user.id)

    keywords_result = await db.execute(keywords_query)
    keywords_count = keywords_result.scalar() or 0

    # Total posts
    total_query = select(func.count(ProcessedPost.id))
    if not current_user.is_admin:
        total_query = total_query.join(Profile).where(Profile.user_id == current_user.id)

    total_result = await db.execute(total_query)
    total_posts = total_result.scalar() or 0

    # OCR usage
    ocr_query = select(func.count(ProcessedPost.id)).where(
        ProcessedPost.ocr_text.isnot(None)
    )
    if not current_user.is_admin:
        ocr_query = ocr_query.join(Profile).where(Profile.user_id == current_user.id)

    ocr_result = await db.execute(ocr_query)
    ocr_count = ocr_result.scalar() or 0

    return {
        "status_counts": {
            "pending": status_counts.get("pending", 0),
            "processing": status_counts.get("processing", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
        },
        "keywords_last_7_days": keywords_count,
        "total_posts": total_posts,
        "ocr_processed": ocr_count,
    }


@router.get("/timeline")
async def get_posts_timeline(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get posts count per day for the last N days."""

    start_date = get_local_now() - timedelta(days=days)

    from sqlalchemy import case

    query = select(
        func.date(ProcessedPost.processed_at).label("date"),
        func.count(ProcessedPost.id).label("count"),
        func.sum(
            case((ProcessedPost.has_keyword == True, 1), else_=0)
        ).label("with_keywords")
    ).where(
        ProcessedPost.processed_at >= start_date
    ).group_by(
        func.date(ProcessedPost.processed_at)
    ).order_by(
        func.date(ProcessedPost.processed_at)
    )

    if not current_user.is_admin:
        query = query.join(Profile).where(Profile.user_id == current_user.id)

    result = await db.execute(query)
    rows = result.fetchall()

    return {
        "timeline": [
            {
                "date": row[0].isoformat() if row[0] else None,
                "total": row[1],
                "with_keywords": row[2] or 0
            }
            for row in rows
        ]
    }


@router.get("/recent-posts")
async def get_recent_posts(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent processed posts with keywords."""

    from sqlalchemy.orm import selectinload

    query = (
        select(ProcessedPost)
        .options(selectinload(ProcessedPost.profile))
        .where(ProcessedPost.status == "completed")
        .order_by(ProcessedPost.processed_at.desc())
        .limit(limit)
    )

    if not current_user.is_admin:
        query = query.join(Profile).where(Profile.user_id == current_user.id)

    result = await db.execute(query)
    posts = result.scalars().all()

    return {
        "posts": [
            {
                "id": post.id,
                "post_id": post.post_id,
                "profile": {
                    "username": post.profile.username if post.profile else None,
                    "platform": post.profile.platform if post.profile else None,
                },
                "content": post.content[:200] + "..." if post.content and len(post.content) > 200 else post.content,
                "has_keyword": post.has_keyword,
                "matched_keywords": post.matched_keywords,
                "sent_at": post.sent_at.isoformat() if post.sent_at else None,
                "processed_at": post.processed_at.isoformat() if post.processed_at else None,
            }
            for post in posts
        ]
    }


@router.get("/scraping-logs")
async def get_recent_scraping_logs(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent scraping logs."""

    from sqlalchemy.orm import selectinload

    query = (
        select(ScrapingLog)
        .options(selectinload(ScrapingLog.profile))
        .order_by(ScrapingLog.created_at.desc())
        .limit(limit)
    )

    if not current_user.is_admin:
        query = query.join(Profile).where(Profile.user_id == current_user.id)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": log.id,
                "profile": {
                    "username": log.profile.username if log.profile else None,
                    "platform": log.profile.platform if log.profile else None,
                },
                "status": log.status,
                "message": log.message,
                "posts_found": log.posts_found,
                "posts_sent": log.posts_sent,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    }
