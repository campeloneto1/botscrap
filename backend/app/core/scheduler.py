import asyncio
import logging
import random
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import async_session
from app.db.models import Profile, Keyword, ProcessedPost, ScrapingLog
from app.scrapers.instagram_playwright import InstagramPlaywrightScraper
from app.telegram.bot import TelegramBot
from app.utils.keywords import find_keywords

logger = logging.getLogger(__name__)
settings = get_settings()


class ScrapingScheduler:
    """Scheduler for periodic scraping jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scrapers = {
            "instagram": InstagramPlaywrightScraper(),
        }

    def start(self):
        """Start the scheduler."""
        self.scheduler.add_job(
            self.run_scraping_job,
            trigger=IntervalTrigger(hours=settings.scrape_interval_hours),
            id="scraping_job",
            name="Scraping Job",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(f"Scheduler started. Running every {settings.scrape_interval_hours} hours")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    async def run_scraping_job(self):
        """Main scraping job that runs periodically."""
        logger.info("Starting scraping job...")

        async with async_session() as db:
            # Get all active profiles
            result = await db.execute(
                select(Profile).where(Profile.active == True)
            )
            profiles = result.scalars().all()

            logger.info(f"Found {len(profiles)} active profiles to scrape")

            for profile in profiles:
                await self.scrape_profile(db, profile)
                # Delay aleatório entre perfis (mais natural, evita rate limit)
                delay = random.uniform(
                    settings.scrape_delay_seconds,
                    settings.scrape_delay_seconds * 2
                )
                logger.info(f"Waiting {delay:.1f}s before next profile...")
                await asyncio.sleep(delay)

        logger.info("Scraping job completed")

    async def scrape_profile(self, db: AsyncSession, profile: Profile):
        """Scrape a single profile."""
        logger.info(f"Scraping {profile.platform}/@{profile.username}")

        scraper = self.scrapers.get(profile.platform)
        if not scraper:
            logger.warning(f"No scraper for platform {profile.platform}")
            return

        try:
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

            # Sempre busca posts das últimas X horas (baseado no intervalo de scraping)
            since = datetime.utcnow() - timedelta(hours=settings.scrape_interval_hours)

            # Get posts
            posts = await scraper.get_recent_posts(
                profile.username,
                limit=20,
                since=since,
            )

            posts_found = len(posts)
            posts_sent = 0

            # Process posts
            for post in posts:
                # Check if already processed
                existing = await db.execute(
                    select(ProcessedPost).where(
                        ProcessedPost.profile_id == profile.id,
                        ProcessedPost.post_id == post["post_id"],
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Check for keywords
                has_keyword, matched, priority = find_keywords(
                    post.get("content", ""),
                    keywords,
                )

                # Save to database
                processed_post = ProcessedPost(
                    profile_id=profile.id,
                    post_id=post["post_id"],
                    content=post.get("content"),
                    media_url=post.get("media_url"),
                    has_keyword=has_keyword,
                    matched_keywords=matched if matched else None,
                )
                db.add(processed_post)

                # Send to Telegram
                if profile.telegram_group_id and profile.telegram_group:
                    try:
                        bot = TelegramBot()
                        chat_id = profile.telegram_group.chat_id

                        if has_keyword and priority >= 2:
                            await bot.send_alert(
                                chat_id=chat_id,
                                post=post,
                                profile_username=profile.username,
                                platform=profile.platform,
                                matched_keywords=matched,
                                priority=priority,
                            )
                        else:
                            await bot.send_post(
                                chat_id=chat_id,
                                post=post,
                                profile_username=profile.username,
                                platform=profile.platform,
                                matched_keywords=matched if has_keyword else None,
                            )

                        processed_post.sent_at = datetime.utcnow()
                        posts_sent += 1
                    except Exception as e:
                        logger.error(f"Failed to send to Telegram: {e}")

            # Update last scraped
            profile.last_scraped = datetime.utcnow()

            # Log
            log = ScrapingLog(
                profile_id=profile.id,
                status="success",
                message=f"Scraped {profile.username}",
                posts_found=posts_found,
                posts_sent=posts_sent,
            )
            db.add(log)

            await db.commit()
            logger.info(f"Processed {posts_found} posts, sent {posts_sent} to Telegram")

        except Exception as e:
            logger.error(f"Error scraping {profile.username}: {e}")

            # Log error
            log = ScrapingLog(
                profile_id=profile.id,
                status="error",
                message=str(e),
            )
            db.add(log)
            await db.commit()


# Entry point for running scheduler standalone
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    scheduler = ScrapingScheduler()
    scheduler.start()

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        sys.exit(0)
