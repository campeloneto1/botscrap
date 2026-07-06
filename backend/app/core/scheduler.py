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
from app.db.models import Profile, Keyword, ProcessedPost, ScrapingLog, AppSettings
from app.scrapers.instagram_playwright import InstagramPlaywrightScraper
from app.telegram.bot import TelegramBot
from app.utils.keywords import find_keywords
from app.utils.ai_summary import generate_summary
from app.core.app_settings import get_app_settings, get_scrape_delay, get_scrape_interval, is_ai_summary_enabled, get_telegram_token

logger = logging.getLogger(__name__)
settings = get_settings()  # Fallback for startup


class ScrapingScheduler:
    """Scheduler for periodic scraping jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scrapers = {
            "instagram": InstagramPlaywrightScraper(),
        }
        self.last_run: datetime = None
        self.is_running: bool = False
        self._current_interval_hours: int = settings.scrape_interval_hours

    def start(self):
        """Start the scheduler with default interval (will be updated by init_from_db)."""
        self.scheduler.add_job(
            self.run_scraping_job,
            trigger=IntervalTrigger(hours=self._current_interval_hours),
            id="scraping_job",
            name="Scraping Job",
            replace_existing=True,
        )
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Scheduler started. Running every {self._current_interval_hours} hours")

    async def init_from_db(self):
        """Initialize scheduler interval from database settings."""
        try:
            async with async_session() as db:
                app_settings = await get_app_settings(db)
                new_interval = get_scrape_interval(app_settings)
                if new_interval != self._current_interval_hours:
                    self.reschedule(new_interval)
                    logger.info(f"Scheduler interval updated from database: {new_interval} hours")
        except Exception as e:
            logger.warning(f"Failed to load scheduler interval from database: {e}")

    def reschedule(self, new_interval_hours: int):
        """Reschedule the job with a new interval."""
        if new_interval_hours < 1:
            logger.warning(f"Invalid interval {new_interval_hours}, using 1 hour minimum")
            new_interval_hours = 1

        job = self.scheduler.get_job("scraping_job")
        if job:
            self.scheduler.reschedule_job(
                "scraping_job",
                trigger=IntervalTrigger(hours=new_interval_hours),
            )
            self._current_interval_hours = new_interval_hours
            logger.info(f"Scheduler rescheduled to run every {new_interval_hours} hours")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Scheduler stopped")

    def get_status(self) -> dict:
        """Get scheduler status information."""
        job = self.scheduler.get_job("scraping_job")
        next_run = None
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()

        return {
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": next_run,
            "interval_hours": self._current_interval_hours,
        }

    async def run_manual_scrape(self, hours: int = 3) -> dict:
        """Run a manual scrape with custom hours period."""
        logger.info(f"Starting manual scrape for last {hours} hours...")
        results = {
            "success": True,
            "hours": hours,
            "profiles_scraped": 0,
            "posts_found": 0,
            "posts_sent": 0,
            "errors": [],
        }

        # Get settings and profiles first
        async with async_session() as db:
            app_settings = await get_app_settings(db)
            scrape_delay = get_scrape_delay(app_settings)

            # Get all active profiles with their relationships loaded
            from sqlalchemy.orm import selectinload
            result = await db.execute(
                select(Profile)
                .options(selectinload(Profile.telegram_group))
                .where(Profile.active == True)
            )
            profiles = result.scalars().all()
            profile_ids = [(p.id, p.username, p.platform, p.user_id,
                           p.telegram_group_id,
                           p.telegram_group.chat_id if p.telegram_group else None)
                          for p in profiles]

        # Process each profile with its own session
        for profile_data in profile_ids:
            profile_id, username, platform, user_id, tg_group_id, chat_id = profile_data
            try:
                async with async_session() as db:
                    stats = await self._scrape_profile_by_id(
                        db, profile_id, username, platform, user_id,
                        tg_group_id, chat_id, app_settings, hours
                    )
                    results["profiles_scraped"] += 1
                    results["posts_found"] += stats.get("posts_found", 0)
                    results["posts_sent"] += stats.get("posts_sent", 0)

                # Small delay between profiles
                await asyncio.sleep(scrape_delay)
            except Exception as e:
                results["errors"].append(f"{username}: {str(e)}")
                logger.error(f"Error scraping {username}: {e}")

        logger.info(f"Manual scrape completed: {results}")
        return results

    async def _scrape_profile_by_id(
        self, db: AsyncSession, profile_id: int, username: str, platform: str,
        user_id: int, telegram_group_id: int, chat_id: str,
        app_settings: AppSettings, hours: int
    ) -> dict:
        """Scrape a single profile by ID with custom hours period."""
        logger.info(f"Manual scraping {platform}/@{username} for last {hours} hours")

        scraper = self.scrapers.get(platform)
        if not scraper:
            raise Exception(f"No scraper for platform {platform}")

        stats = {"posts_found": 0, "posts_sent": 0}

        # Get user's keywords
        keywords_result = await db.execute(
            select(Keyword).where(
                Keyword.user_id == user_id,
                Keyword.active == True,
            )
        )
        keywords = [
            {"word": k.word, "priority": k.priority}
            for k in keywords_result.scalars().all()
        ]

        # Use custom hours period
        since = datetime.utcnow() - timedelta(hours=hours)

        # Get posts
        posts = await scraper.get_recent_posts(
            username,
            limit=20,
            since=since,
        )

        stats["posts_found"] = len(posts)

        # Process posts
        for post in posts:
            # Check if already processed
            existing = await db.execute(
                select(ProcessedPost).where(
                    ProcessedPost.profile_id == profile_id,
                    ProcessedPost.post_id == post["post_id"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Check for keywords
            content = post.get("content", "")
            has_keyword, matched, priority = find_keywords(content, keywords)

            # Generate AI summary for long posts (if enabled)
            summary = None
            ai_enabled = is_ai_summary_enabled(app_settings)
            if ai_enabled and content and len(content) > 300:
                try:
                    summary = await generate_summary(content, app_settings)
                except Exception as e:
                    logger.warning(f"Failed to generate summary: {e}")

            # Save to database
            processed_post = ProcessedPost(
                profile_id=profile_id,
                post_id=post["post_id"],
                content=content,
                summary=summary,
                media_url=post.get("media_url"),
                has_keyword=has_keyword,
                matched_keywords=matched if matched else None,
            )
            db.add(processed_post)

            # Add summary to post dict for telegram
            if summary:
                post["summary"] = summary

            # Send to Telegram
            if telegram_group_id and chat_id:
                try:
                    telegram_token = get_telegram_token(app_settings)
                    bot = TelegramBot(token=telegram_token)

                    if has_keyword and priority >= 2:
                        await bot.send_alert(
                            chat_id=chat_id,
                            post=post,
                            profile_username=username,
                            platform=platform,
                            matched_keywords=matched,
                            priority=priority,
                        )
                    else:
                        await bot.send_post(
                            chat_id=chat_id,
                            post=post,
                            profile_username=username,
                            platform=platform,
                            matched_keywords=matched if has_keyword else None,
                        )

                    processed_post.sent_at = datetime.utcnow()
                    stats["posts_sent"] += 1
                except Exception as e:
                    logger.error(f"Failed to send to Telegram: {e}")

        # Update last scraped
        await db.execute(
            select(Profile).where(Profile.id == profile_id).with_for_update()
        )
        profile_obj = (await db.execute(
            select(Profile).where(Profile.id == profile_id)
        )).scalar_one()
        profile_obj.last_scraped = datetime.utcnow()

        # Log
        log = ScrapingLog(
            profile_id=profile_id,
            status="success",
            message=f"Manual scrape: {username} ({hours}h)",
            posts_found=stats["posts_found"],
            posts_sent=stats["posts_sent"],
        )
        db.add(log)

        await db.commit()
        return stats

    async def run_scraping_job(self):
        """Main scraping job that runs periodically."""
        logger.info("Starting scraping job...")
        self.last_run = datetime.utcnow()

        async with async_session() as db:
            # Get app settings from database
            app_settings = await get_app_settings(db)
            scrape_delay = get_scrape_delay(app_settings)

            # Get all active profiles
            result = await db.execute(
                select(Profile).where(Profile.active == True)
            )
            profiles = result.scalars().all()

            logger.info(f"Found {len(profiles)} active profiles to scrape")

            for profile in profiles:
                await self.scrape_profile(db, profile, app_settings)
                # Delay aleatório entre perfis (mais natural, evita rate limit)
                delay = random.uniform(scrape_delay, scrape_delay * 2)
                logger.info(f"Waiting {delay:.1f}s before next profile...")
                await asyncio.sleep(delay)

        logger.info("Scraping job completed")

    async def scrape_profile(self, db: AsyncSession, profile: Profile, app_settings: AppSettings = None):
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
            interval_hours = get_scrape_interval(app_settings) if app_settings else settings.scrape_interval_hours
            since = datetime.utcnow() - timedelta(hours=interval_hours)

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
                content = post.get("content", "")
                has_keyword, matched, priority = find_keywords(
                    content,
                    keywords,
                )

                # Generate AI summary for long posts (if enabled)
                summary = None
                ai_enabled = is_ai_summary_enabled(app_settings) if app_settings else True
                if ai_enabled and content and len(content) > 300:
                    try:
                        summary = await generate_summary(content, app_settings)
                    except Exception as e:
                        logger.warning(f"Failed to generate summary: {e}")

                # Save to database
                processed_post = ProcessedPost(
                    profile_id=profile.id,
                    post_id=post["post_id"],
                    content=content,
                    summary=summary,
                    media_url=post.get("media_url"),
                    has_keyword=has_keyword,
                    matched_keywords=matched if matched else None,
                )
                db.add(processed_post)

                # Add summary to post dict for telegram
                if summary:
                    post["summary"] = summary

                # Send to Telegram
                if profile.telegram_group_id and profile.telegram_group:
                    try:
                        telegram_token = get_telegram_token(app_settings) if app_settings else None
                        bot = TelegramBot(token=telegram_token)
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

            # Notify if no posts found
            if posts_found == 0 and profile.telegram_group_id and profile.telegram_group:
                try:
                    telegram_token = get_telegram_token(app_settings) if app_settings else None
                    bot = TelegramBot(token=telegram_token)
                    chat_id = profile.telegram_group.chat_id
                    await bot.send_no_posts_found(
                        chat_id=chat_id,
                        profile_username=profile.username,
                        platform=profile.platform,
                        hours=interval_hours,
                    )
                except Exception as e:
                    logger.error(f"Failed to send no-posts notification: {e}")

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
