"""
Post Processor - Processes pending posts in background.
Handles OCR, keyword detection, AI summary, and Telegram notifications.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import async_session
from app.db.models import ProcessedPost, Profile, Keyword, AppSettings
from app.utils.keywords import find_keywords
from app.utils.ocr import process_image_for_keywords
from app.utils.ai_summary import generate_summary
from app.telegram.bot import TelegramBot
from app.core.app_settings import (
    get_app_settings,
    is_ai_summary_enabled,
    get_telegram_token,
)

logger = logging.getLogger(__name__)


class PostProcessor:
    """Processes pending posts - OCR, keywords, AI summary, Telegram."""

    def __init__(self):
        self.is_processing = False
        self.posts_processed = 0
        self.posts_total = 0

    def get_status(self) -> dict:
        """Get processor status."""
        return {
            "is_processing": self.is_processing,
            "posts_processed": self.posts_processed,
            "posts_total": self.posts_total,
        }

    async def process_pending_posts(self, user_id: Optional[int] = None) -> dict:
        """
        Process all pending posts.
        If user_id is provided, only process posts for that user.
        """
        if self.is_processing:
            return {"success": False, "error": "Already processing"}

        self.is_processing = True
        self.posts_processed = 0
        results = {
            "success": True,
            "posts_processed": 0,
            "posts_sent": 0,
            "keywords_found": 0,
            "ocr_performed": 0,
            "errors": [],
        }

        try:
            async with async_session() as db:
                app_settings = await get_app_settings(db)

                # Get pending posts with profile info
                query = (
                    select(ProcessedPost)
                    .options(selectinload(ProcessedPost.profile).selectinload(Profile.telegram_group))
                    .where(ProcessedPost.status == "pending")
                    .order_by(ProcessedPost.processed_at.asc())
                )

                if user_id:
                    query = query.join(Profile).where(Profile.user_id == user_id)

                result = await db.execute(query)
                pending_posts = result.scalars().all()

                self.posts_total = len(pending_posts)
                logger.info(f"Processing {self.posts_total} pending posts...")

                for post in pending_posts:
                    try:
                        await self._process_single_post(db, post, app_settings)
                        results["posts_processed"] += 1

                        if post.has_keyword:
                            results["keywords_found"] += 1
                        if post.ocr_text:
                            results["ocr_performed"] += 1
                        if post.sent_at:
                            results["posts_sent"] += 1

                        self.posts_processed += 1

                    except Exception as e:
                        logger.error(f"Error processing post {post.id}: {e}")
                        results["errors"].append(f"Post {post.id}: {str(e)}")
                        post.status = "failed"
                        await db.commit()

                await db.commit()

        except Exception as e:
            logger.error(f"Error in post processor: {e}")
            results["success"] = False
            results["error"] = str(e)

        finally:
            self.is_processing = False

        logger.info(f"Post processing completed: {results}")
        return results

    async def _process_single_post(
        self,
        db: AsyncSession,
        post: ProcessedPost,
        app_settings: AppSettings
    ):
        """Process a single post - OCR, keywords, AI, Telegram."""
        post.status = "processing"
        await db.commit()

        profile = post.profile
        if not profile:
            post.status = "failed"
            return

        # Get user's keywords
        keywords_result = await db.execute(
            select(Keyword).where(
                Keyword.user_id == profile.user_id,
                Keyword.active == True,
            )
        )
        keywords = [
            {"word": k.word, "priority": k.priority}
            for k in keywords_result.scalars().all()
        ]

        # Check keywords in text content
        content = post.content or ""
        has_keyword, matched, priority = find_keywords(content, keywords)

        # OCR on image if available
        if post.media_url and keywords:
            try:
                ocr_has_kw, ocr_matched, ocr_priority, ocr_text = await process_image_for_keywords(
                    post.media_url, keywords
                )
                post.ocr_text = ocr_text if ocr_text else None

                if ocr_has_kw:
                    if not has_keyword:
                        has_keyword = True
                        matched = ocr_matched
                        priority = ocr_priority
                    else:
                        for kw in ocr_matched:
                            if kw not in matched:
                                matched.append(kw)
                        priority = max(priority, ocr_priority)

                    logger.info(f"OCR found keywords in post {post.id}: {ocr_matched}")

            except Exception as e:
                logger.warning(f"OCR failed for post {post.id}: {e}")

        # Update keyword info
        post.has_keyword = has_keyword
        post.matched_keywords = matched if matched else None

        # Generate AI summary if enabled and content is long
        if is_ai_summary_enabled(app_settings) and content and len(content) > 300:
            try:
                summary = await generate_summary(content, app_settings)
                post.summary = summary
            except Exception as e:
                logger.warning(f"AI summary failed for post {post.id}: {e}")

        # Send to Telegram
        if profile.telegram_group_id and profile.telegram_group:
            try:
                telegram_token = get_telegram_token(app_settings)
                bot = TelegramBot(token=telegram_token)
                chat_id = profile.telegram_group.chat_id

                # Build post dict for telegram
                post_data = {
                    "post_id": post.post_id,
                    "content": post.content,
                    "media_url": post.media_url,
                    "summary": post.summary,
                }

                if has_keyword and priority >= 2:
                    await bot.send_alert(
                        chat_id=chat_id,
                        post=post_data,
                        profile_username=profile.username,
                        platform=profile.platform,
                        matched_keywords=matched,
                        priority=priority,
                    )
                else:
                    await bot.send_post(
                        chat_id=chat_id,
                        post=post_data,
                        profile_username=profile.username,
                        platform=profile.platform,
                        matched_keywords=matched if has_keyword else None,
                    )

                post.sent_at = datetime.utcnow()
                logger.info(f"Post {post.id} sent to Telegram")

            except Exception as e:
                logger.error(f"Failed to send post {post.id} to Telegram: {e}")

        post.status = "completed"
        await db.commit()


# Global processor instance
post_processor = PostProcessor()


async def process_pending_posts_background():
    """Run post processing in background."""
    return await post_processor.process_pending_posts()
