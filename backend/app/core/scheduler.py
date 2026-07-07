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
from app.db.models import Profile, ProcessedPost, ScrapingLog, AppSettings
from app.scrapers.instagram_playwright import InstagramPlaywrightScraper
from app.core.app_settings import get_app_settings, get_scrape_delay, get_scrape_interval

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
        """Start the scheduler with scraping and processing jobs."""
        # Job 1: Scraping - runs every X hours (configurable)
        self.scheduler.add_job(
            self.run_scraping_job,
            trigger=IntervalTrigger(hours=self._current_interval_hours),
            id="scraping_job",
            name="Scraping Job",
            replace_existing=True,
        )

        # Job 2: Post Processing - runs every minute to process pending posts
        self.scheduler.add_job(
            self.run_post_processing_job,
            trigger=IntervalTrigger(minutes=1),
            id="processing_job",
            name="Post Processing Job",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True
        logger.info(f"Scheduler started. Scraping every {self._current_interval_hours}h, processing every 1min")

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

    async def run_post_processing_job(self):
        """Process pending posts - runs every minute."""
        from app.core.post_processor import post_processor

        if post_processor.is_processing:
            logger.debug("Post processing already running, skipping...")
            return

        logger.debug("Checking for pending posts...")
        result = await post_processor.process_pending_posts()

        if result.get("posts_processed", 0) > 0:
            logger.info(f"Processed {result['posts_processed']} posts, sent {result.get('posts_sent', 0)} to Telegram")

    async def run_manual_scrape(self, hours: int = 3) -> dict:
        """Run a manual scrape - sequential with timeout per profile."""
        logger.info(f"Starting manual scrape for last {hours} hours...")

        results = {
            "success": True,
            "hours": hours,
            "profiles_scraped": 0,
            "profiles_total": 0,
            "posts_found": 0,
            "posts_sent": 0,
            "errors": [],
        }

        # Get settings and profiles first
        async with async_session() as db:
            app_settings = await get_app_settings(db)

            # Get all active profiles with their relationships loaded
            from sqlalchemy.orm import selectinload
            result = await db.execute(
                select(Profile)
                .options(selectinload(Profile.telegram_group))
                .where(Profile.active == True)
            )
            profiles = result.scalars().all()
            profile_list = [(p.id, p.username, p.platform, p.user_id,
                            p.telegram_group_id,
                            p.telegram_group.chat_id if p.telegram_group else None)
                           for p in profiles]

        results["profiles_total"] = len(profile_list)
        logger.info(f"Found {len(profile_list)} profiles to scrape sequentially")

        # Process each profile sequentially with individual timeout
        PROFILE_TIMEOUT = 120  # 2 minutes max per profile

        for i, profile_data in enumerate(profile_list):
            profile_id, username, platform, user_id, tg_group_id, chat_id = profile_data
            logger.info(f"[{i+1}/{len(profile_list)}] Processing @{username}...")

            try:
                # Wrap in timeout to prevent single profile from blocking
                async with asyncio.timeout(PROFILE_TIMEOUT):
                    async with async_session() as db:
                        stats = await self._scrape_profile_by_id(
                            db, profile_id, username, platform, user_id,
                            tg_group_id, chat_id, app_settings, hours
                        )

                results["profiles_scraped"] += 1
                results["posts_found"] += stats.get("posts_found", 0)
                results["posts_sent"] += stats.get("posts_sent", 0)
                logger.info(f"[{i+1}/{len(profile_list)}] Done @{username}: {stats.get('posts_found', 0)} posts")

            except asyncio.TimeoutError:
                results["errors"].append(f"{username}: timeout")
                logger.warning(f"[{i+1}/{len(profile_list)}] Timeout @{username}, skipping...")

            except Exception as e:
                results["errors"].append(f"{username}: {str(e)}")
                logger.error(f"[{i+1}/{len(profile_list)}] Error @{username}: {e}")

            # Small delay between profiles
            await asyncio.sleep(1)

        logger.info(f"Manual scrape completed: {results['profiles_scraped']}/{results['profiles_total']} profiles")
        return results

    async def _scrape_profile_by_id(
        self, db: AsyncSession, profile_id: int, username: str, platform: str,
        user_id: int, telegram_group_id: int, chat_id: str,
        app_settings: AppSettings, hours: int
    ) -> dict:
        """Scrape a single profile - only collect and save posts as pending."""
        logger.info(f"Collecting posts from {platform}/@{username} (last {hours}h)")

        scraper = self.scrapers.get(platform)
        if not scraper:
            raise Exception(f"No scraper for platform {platform}")

        stats = {"posts_found": 0, "posts_new": 0}

        # Use custom hours period
        since = datetime.utcnow() - timedelta(hours=hours)

        # Get posts from Instagram
        posts = await scraper.get_recent_posts(
            username,
            limit=20,
            since=since,
        )

        stats["posts_found"] = len(posts)

        # Save posts as pending (processing happens later)
        for post in posts:
            # Check if already exists
            existing = await db.execute(
                select(ProcessedPost).where(
                    ProcessedPost.profile_id == profile_id,
                    ProcessedPost.post_id == post["post_id"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Save post with status='pending' - will be processed later
            processed_post = ProcessedPost(
                profile_id=profile_id,
                post_id=post["post_id"],
                content=post.get("content", ""),
                media_url=post.get("media_url"),
                status="pending",  # Will be processed by PostProcessor
            )
            db.add(processed_post)
            stats["posts_new"] += 1

        # Update last scraped
        profile_obj = (await db.execute(
            select(Profile).where(Profile.id == profile_id)
        )).scalar_one()
        profile_obj.last_scraped = datetime.utcnow()

        # Log
        log = ScrapingLog(
            profile_id=profile_id,
            status="success",
            message=f"Collected {stats['posts_new']} new posts from {username}",
            posts_found=stats["posts_found"],
            posts_sent=0,  # Will be updated by processor
        )
        db.add(log)

        await db.commit()
        logger.info(f"Collected {stats['posts_new']} new posts from @{username}")
        return stats

    async def run_scraping_job(self):
        """Main scraping job that runs periodically."""
        logger.info("Starting scraping job...")
        self.last_run = datetime.utcnow()

        # Track profiles with no posts for grouped notifications
        profiles_without_posts = {}  # {user_id: [(username, platform), ...]}

        # Get settings and profile IDs first
        async with async_session() as db:
            app_settings = await get_app_settings(db)
            scrape_delay = get_scrape_delay(app_settings)
            interval_hours = get_scrape_interval(app_settings)

            # Get all active profiles with relationships loaded
            from sqlalchemy.orm import selectinload
            result = await db.execute(
                select(Profile)
                .options(selectinload(Profile.telegram_group))
                .where(Profile.active == True)
            )
            profiles = result.scalars().all()

            # Extract profile data to avoid lazy loading issues
            profile_ids = [(p.id, p.username, p.platform, p.user_id,
                           p.telegram_group_id,
                           p.telegram_group.chat_id if p.telegram_group else None)
                          for p in profiles]

        logger.info(f"Found {len(profile_ids)} active profiles to scrape")

        # Process each profile with its own session
        for profile_data in profile_ids:
            profile_id, username, platform, user_id, tg_group_id, chat_id = profile_data
            try:
                async with async_session() as db:
                    stats = await self._scrape_profile_by_data_with_stats(
                        db, profile_id, username, platform, user_id,
                        tg_group_id, chat_id, app_settings
                    )

                # Track profiles with no posts
                if stats.get("posts_found", 0) == 0 and tg_group_id and chat_id:
                    if user_id not in profiles_without_posts:
                        profiles_without_posts[user_id] = {
                            "profiles": [],
                            "chat_id": chat_id,
                        }
                    profiles_without_posts[user_id]["profiles"].append((username, platform))

            except Exception as e:
                logger.error(f"Error scraping {username}: {e}")

            # Delay aleatório entre perfis (mais natural, evita rate limit)
            delay = random.uniform(scrape_delay, scrape_delay * 2)
            logger.info(f"Waiting {delay:.1f}s before next profile...")
            await asyncio.sleep(delay)

        # Send grouped "no posts" notifications
        if profiles_without_posts:
            from app.core.app_settings import get_telegram_token
            from app.telegram.bot import TelegramBot

            async with async_session() as db:
                app_settings = await get_app_settings(db)
                telegram_token = get_telegram_token(app_settings)

                if telegram_token:
                    bot = TelegramBot(token=telegram_token)

                    for user_id, data in profiles_without_posts.items():
                        try:
                            profiles_list = data["profiles"]
                            chat_id = data["chat_id"]

                            if len(profiles_list) == 1:
                                username, platform = profiles_list[0]
                                await bot.send_no_posts_found(
                                    chat_id=chat_id,
                                    profile_username=username,
                                    platform=platform,
                                    hours=interval_hours,
                                )
                            else:
                                # Send grouped message
                                profiles_text = "\n".join([f"• @{u} ({p})" for u, p in profiles_list])
                                message = (
                                    f"🔍 *Nenhum post encontrado*\n\n"
                                    f"Nos seguintes perfis (últimas {interval_hours}h):\n\n"
                                    f"{profiles_text}"
                                )

                                import httpx
                                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                                async with httpx.AsyncClient() as client:
                                    await client.post(url, json={
                                        "chat_id": chat_id,
                                        "text": message,
                                        "parse_mode": "Markdown"
                                    })

                                logger.info(f"Sent grouped no-posts notification: {len(profiles_list)} profiles")

                        except Exception as e:
                            logger.error(f"Failed to send no-posts notification: {e}")

        logger.info("Scraping job completed")

    async def _scrape_profile_by_data_with_stats(
        self, db: AsyncSession, profile_id: int, username: str, platform: str,
        user_id: int, telegram_group_id: int, chat_id: str,
        app_settings: AppSettings
    ) -> dict:
        """Scrape a single profile - only collect and save posts as pending. Returns stats."""
        logger.info(f"Collecting posts from {platform}/@{username}")

        scraper = self.scrapers.get(platform)
        if not scraper:
            logger.warning(f"No scraper for platform {platform}")
            return {"posts_found": 0, "posts_new": 0}

        # Get posts from last interval
        interval_hours = get_scrape_interval(app_settings)
        since = datetime.utcnow() - timedelta(hours=interval_hours)

        posts = await scraper.get_recent_posts(
            username,
            limit=20,
            since=since,
        )

        posts_found = len(posts)
        posts_new = 0

        # Save posts as pending (processing happens by PostProcessor)
        for post in posts:
            # Check if already exists
            existing = await db.execute(
                select(ProcessedPost).where(
                    ProcessedPost.profile_id == profile_id,
                    ProcessedPost.post_id == post["post_id"],
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Save post with status='pending'
            processed_post = ProcessedPost(
                profile_id=profile_id,
                post_id=post["post_id"],
                content=post.get("content", ""),
                media_url=post.get("media_url"),
                status="pending",
            )
            db.add(processed_post)
            posts_new += 1

        # Update last scraped
        profile_obj = (await db.execute(
            select(Profile).where(Profile.id == profile_id)
        )).scalar_one()
        profile_obj.last_scraped = datetime.utcnow()

        # Log
        log = ScrapingLog(
            profile_id=profile_id,
            status="success",
            message=f"Collected {posts_new} new posts from {username}",
            posts_found=posts_found,
            posts_sent=0,
        )
        db.add(log)

        await db.commit()
        logger.info(f"Collected {posts_new} new posts from @{username}")

        return {"posts_found": posts_found, "posts_new": posts_new}

    async def scrape_profile(self, db: AsyncSession, profile: Profile, app_settings: AppSettings = None):
        """Scrape a single profile - only collect and save posts as pending."""
        logger.info(f"Collecting posts from {profile.platform}/@{profile.username}")

        scraper = self.scrapers.get(profile.platform)
        if not scraper:
            logger.warning(f"No scraper for platform {profile.platform}")
            return

        try:
            # Get posts from last interval
            interval_hours = get_scrape_interval(app_settings) if app_settings else settings.scrape_interval_hours
            since = datetime.utcnow() - timedelta(hours=interval_hours)

            posts = await scraper.get_recent_posts(
                profile.username,
                limit=20,
                since=since,
            )

            posts_found = len(posts)
            posts_new = 0

            # Save posts as pending
            for post in posts:
                existing = await db.execute(
                    select(ProcessedPost).where(
                        ProcessedPost.profile_id == profile.id,
                        ProcessedPost.post_id == post["post_id"],
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                processed_post = ProcessedPost(
                    profile_id=profile.id,
                    post_id=post["post_id"],
                    content=post.get("content", ""),
                    media_url=post.get("media_url"),
                    status="pending",
                )
                db.add(processed_post)
                posts_new += 1

            # Update last scraped
            profile.last_scraped = datetime.utcnow()

            # Log
            log = ScrapingLog(
                profile_id=profile.id,
                status="success",
                message=f"Collected {posts_new} new posts from {profile.username}",
                posts_found=posts_found,
                posts_sent=0,
            )
            db.add(log)

            await db.commit()
            logger.info(f"Collected {posts_new} new posts from @{profile.username}")

        except Exception as e:
            logger.error(f"Error scraping {profile.username}: {e}")
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
