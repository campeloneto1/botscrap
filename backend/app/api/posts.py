"""
Posts management endpoints - search, filters, retry, export.
"""
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import ProcessedPost, Profile
from app.api.auth import get_current_user, User
from app.config import get_local_now

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("/search")
async def search_posts(
    query: Optional[str] = None,
    platform: Optional[str] = None,
    profile_id: Optional[int] = None,
    status: Optional[str] = None,
    has_keyword: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search and filter posts.
    Supports text search, platform filter, date range, status, keywords.
    """

    # Base query
    stmt = (
        select(ProcessedPost)
        .options(selectinload(ProcessedPost.profile))
        .join(Profile)
    )

    # Filter by user (non-admin only sees their posts)
    if not current_user.is_admin:
        stmt = stmt.where(Profile.user_id == current_user.id)

    # Text search in content, OCR text, and matched keywords
    if query:
        search_filter = or_(
            ProcessedPost.content.ilike(f"%{query}%"),
            ProcessedPost.ocr_text.ilike(f"%{query}%"),
            func.cast(ProcessedPost.matched_keywords, func.Text()).ilike(f"%{query}%")
        )
        stmt = stmt.where(search_filter)

    # Platform filter
    if platform:
        stmt = stmt.where(Profile.platform == platform)

    # Profile filter
    if profile_id:
        stmt = stmt.where(ProcessedPost.profile_id == profile_id)

    # Status filter
    if status:
        stmt = stmt.where(ProcessedPost.status == status)

    # Keyword filter
    if has_keyword is not None:
        stmt = stmt.where(ProcessedPost.has_keyword == has_keyword)

    # Date range
    if date_from:
        date_from_dt = datetime.fromisoformat(date_from)
        stmt = stmt.where(ProcessedPost.processed_at >= date_from_dt)

    if date_to:
        date_to_dt = datetime.fromisoformat(date_to)
        stmt = stmt.where(ProcessedPost.processed_at <= date_to_dt)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Get posts
    stmt = stmt.order_by(ProcessedPost.processed_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    posts = result.scalars().all()

    return {
        "total": total,
        "posts": [
            {
                "id": post.id,
                "post_id": post.post_id,
                "profile": {
                    "id": post.profile.id,
                    "username": post.profile.username,
                    "platform": post.profile.platform,
                } if post.profile else None,
                "content": post.content,
                "summary": post.summary,
                "media_url": post.media_url,
                "ocr_text": post.ocr_text,
                "has_keyword": post.has_keyword,
                "matched_keywords": post.matched_keywords,
                "status": post.status,
                "sent_at": post.sent_at.isoformat() if post.sent_at else None,
                "processed_at": post.processed_at.isoformat() if post.processed_at else None,
            }
            for post in posts
        ]
    }


@router.get("/export")
async def export_posts(
    query: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    has_keyword: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export filtered posts to CSV."""

    # Reuse search logic
    stmt = (
        select(ProcessedPost)
        .options(selectinload(ProcessedPost.profile))
        .join(Profile)
    )

    if not current_user.is_admin:
        stmt = stmt.where(Profile.user_id == current_user.id)

    if query:
        search_filter = or_(
            ProcessedPost.content.ilike(f"%{query}%"),
            ProcessedPost.ocr_text.ilike(f"%{query}%"),
        )
        stmt = stmt.where(search_filter)

    if platform:
        stmt = stmt.where(Profile.platform == platform)

    if status:
        stmt = stmt.where(ProcessedPost.status == status)

    if has_keyword is not None:
        stmt = stmt.where(ProcessedPost.has_keyword == has_keyword)

    if date_from:
        stmt = stmt.where(ProcessedPost.processed_at >= datetime.fromisoformat(date_from))

    if date_to:
        stmt = stmt.where(ProcessedPost.processed_at <= datetime.fromisoformat(date_to))

    stmt = stmt.order_by(ProcessedPost.processed_at.desc()).limit(10000)  # Max 10k rows
    result = await db.execute(stmt)
    posts = result.scalars().all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID",
        "Post ID",
        "Platform",
        "Profile",
        "Content",
        "Summary",
        "Has Keyword",
        "Keywords",
        "Status",
        "Sent At",
        "Processed At",
    ])

    # Data
    for post in posts:
        writer.writerow([
            post.id,
            post.post_id,
            post.profile.platform if post.profile else "",
            post.profile.username if post.profile else "",
            post.content or "",
            post.summary or "",
            "Yes" if post.has_keyword else "No",
            ", ".join(post.matched_keywords) if post.matched_keywords else "",
            post.status,
            post.sent_at.isoformat() if post.sent_at else "",
            post.processed_at.isoformat() if post.processed_at else "",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=posts_{get_local_now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.post("/retry-failed")
async def retry_failed_posts(
    post_ids: Optional[List[int]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retry failed posts.
    If post_ids provided, retry specific posts.
    Otherwise, retry all failed posts.
    """

    # Build query
    stmt = select(ProcessedPost).where(ProcessedPost.status == "failed")

    if not current_user.is_admin:
        stmt = stmt.join(Profile).where(Profile.user_id == current_user.id)

    if post_ids:
        stmt = stmt.where(ProcessedPost.id.in_(post_ids))

    result = await db.execute(stmt)
    posts = result.scalars().all()

    if not posts:
        return {"success": False, "error": "No failed posts found"}

    # Reset status to pending for retry
    count = 0
    for post in posts:
        post.status = "pending"
        count += 1

    await db.commit()

    return {
        "success": True,
        "message": f"{count} posts marked for retry",
        "count": count
    }


@router.get("/failed")
async def get_failed_posts(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all failed posts with error details."""

    stmt = (
        select(ProcessedPost)
        .options(selectinload(ProcessedPost.profile))
        .where(ProcessedPost.status == "failed")
        .order_by(ProcessedPost.processed_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if not current_user.is_admin:
        stmt = stmt.join(Profile).where(Profile.user_id == current_user.id)

    # Count
    count_stmt = select(func.count(ProcessedPost.id)).where(ProcessedPost.status == "failed")
    if not current_user.is_admin:
        count_stmt = count_stmt.join(Profile).where(Profile.user_id == current_user.id)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    result = await db.execute(stmt)
    posts = result.scalars().all()

    return {
        "total": total,
        "posts": [
            {
                "id": post.id,
                "post_id": post.post_id,
                "profile": {
                    "username": post.profile.username,
                    "platform": post.profile.platform,
                } if post.profile else None,
                "content": post.content[:200] + "..." if post.content and len(post.content) > 200 else post.content,
                "processed_at": post.processed_at.isoformat() if post.processed_at else None,
            }
            for post in posts
        ]
    }
