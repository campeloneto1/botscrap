"""
Health check and monitoring endpoints.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ProcessedPost, ScrapingLog
from app.config import get_local_now, get_local_now_naive

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    Verifies database, scheduler, and processor status.
    """
    health = {
        "status": "healthy",
        "timestamp": get_local_now().isoformat(),
        "components": {}
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health["components"]["database"] = {
            "status": "healthy",
            "message": "Database connection OK"
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["components"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {str(e)}"
        }

    # Check scheduler (last scrape should be within interval + grace period)
    try:
        last_log = await db.execute(
            select(ScrapingLog)
            .order_by(ScrapingLog.created_at.desc())
            .limit(1)
        )
        last_log_obj = last_log.scalar_one_or_none()

        if last_log_obj:
            time_since_last = get_local_now().replace(tzinfo=None) - last_log_obj.created_at
            # Grace period: 2 hours beyond expected interval
            if time_since_last > timedelta(hours=26):  # 24h interval + 2h grace
                health["components"]["scheduler"] = {
                    "status": "warning",
                    "message": f"Last scrape was {time_since_last.total_seconds() / 3600:.1f} hours ago",
                    "last_run": last_log_obj.created_at.isoformat()
                }
            else:
                health["components"]["scheduler"] = {
                    "status": "healthy",
                    "message": "Scheduler is running",
                    "last_run": last_log_obj.created_at.isoformat()
                }
        else:
            health["components"]["scheduler"] = {
                "status": "warning",
                "message": "No scraping logs found"
            }
    except Exception as e:
        health["components"]["scheduler"] = {
            "status": "unknown",
            "message": f"Error checking scheduler: {str(e)}"
        }

    # Check processor (pending posts queue)
    try:
        pending_count = await db.execute(
            select(func.count(ProcessedPost.id))
            .where(ProcessedPost.status == "pending")
        )
        pending = pending_count.scalar() or 0

        processing_count = await db.execute(
            select(func.count(ProcessedPost.id))
            .where(ProcessedPost.status == "processing")
        )
        processing = processing_count.scalar() or 0

        failed_count = await db.execute(
            select(func.count(ProcessedPost.id))
            .where(ProcessedPost.status == "failed")
        )
        failed = failed_count.scalar() or 0

        # Warning if too many pending or stuck in processing
        if pending > 100:
            processor_status = "warning"
            processor_msg = f"High queue: {pending} pending posts"
        elif processing > 10:
            processor_status = "warning"
            processor_msg = f"Posts stuck processing: {processing}"
        elif failed > 50:
            processor_status = "warning"
            processor_msg = f"Many failed posts: {failed}"
        else:
            processor_status = "healthy"
            processor_msg = "Processor queue normal"

        health["components"]["processor"] = {
            "status": processor_status,
            "message": processor_msg,
            "queue": {
                "pending": pending,
                "processing": processing,
                "failed": failed
            }
        }
    except Exception as e:
        health["components"]["processor"] = {
            "status": "unknown",
            "message": f"Error checking processor: {str(e)}"
        }

    # Overall status
    component_statuses = [c["status"] for c in health["components"].values()]
    if "unhealthy" in component_statuses:
        health["status"] = "unhealthy"
    elif "warning" in component_statuses:
        health["status"] = "degraded"

    return health


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Get system metrics for monitoring."""

    from sqlalchemy import func

    # Processing times (last 24h) - usando timezone America/Fortaleza
    yesterday = get_local_now_naive() - timedelta(days=1)

    # Average processing performance
    completed_24h = await db.execute(
        select(func.count(ProcessedPost.id))
        .where(
            ProcessedPost.status == "completed",
            ProcessedPost.processed_at >= yesterday
        )
    )
    completed = completed_24h.scalar() or 0

    failed_24h = await db.execute(
        select(func.count(ProcessedPost.id))
        .where(
            ProcessedPost.status == "failed",
            ProcessedPost.processed_at >= yesterday
        )
    )
    failed = failed_24h.scalar() or 0

    success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0

    return {
        "last_24h": {
            "posts_completed": completed,
            "posts_failed": failed,
            "success_rate": round(success_rate, 2)
        }
    }
