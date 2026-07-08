import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Callable, Any, TypeVar

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, get_local_now_naive
from app.db.database import async_session
from app.db.models import Profile, ProcessedPost, ScrapingLog, AppSettings
from app.scrapers.instagram_playwright import InstagramPlaywrightScraper
from app.scrapers.twitter_playwright import TwitterPlaywrightScraper
from app.scrapers.facebook_playwright import FacebookPlaywrightScraper
from app.core.app_settings import get_app_settings, get_scrape_delay, get_scrape_interval

logger = logging.getLogger(__name__)
settings = get_settings()  # Fallback for startup

# ============================================================
# CONFIGURAÇÕES DE PARALELISMO E RETRY
# ============================================================
MAX_CONCURRENT_SCRAPES = 3  # Número máximo de profiles em paralelo
MAX_RETRIES = 3  # Número máximo de tentativas por profile
RETRY_BASE_DELAY = 2  # Delay base em segundos (exponencial: 2, 4, 8)
PROFILE_TIMEOUT = 120  # Timeout máximo por profile em segundos

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[..., Any],
    *args,
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
    **kwargs
) -> Any:
    """
    Executa uma função com retry exponencial.

    Args:
        func: Função assíncrona a ser executada
        max_retries: Número máximo de tentativas
        base_delay: Delay base em segundos (será multiplicado exponencialmente)

    Returns:
        Resultado da função ou None se todas as tentativas falharem
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except asyncio.TimeoutError:
            # Timeout não faz retry
            raise
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponencial: 2, 4, 8...
                logger.warning(
                    f"Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                    f"Retry em {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Todas as {max_retries} tentativas falharam: {e}")

    raise last_exception if last_exception else Exception("Retry failed")


class ScrapingScheduler:
    """Scheduler for periodic scraping jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scrapers = {
            "instagram": InstagramPlaywrightScraper(),
            "twitter": TwitterPlaywrightScraper(),
            "facebook": FacebookPlaywrightScraper(),
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
        """Run a manual scrape - parallel with retry and timeout per profile."""
        logger.info(f"Starting manual scrape for last {hours} hours (parallel: {MAX_CONCURRENT_SCRAPES})...")

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
        logger.info(f"Found {len(profile_list)} profiles to scrape in parallel (max {MAX_CONCURRENT_SCRAPES} concurrent)")

        # Semaphore to limit concurrent scrapes
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

        async def scrape_with_semaphore(profile_data, index):
            """Scrape a profile with semaphore, timeout and retry."""
            profile_id, username, platform, user_id, tg_group_id, chat_id = profile_data

            async with semaphore:
                logger.info(f"[{index+1}/{len(profile_list)}] Starting @{username}...")

                try:
                    # Wrap in timeout
                    async with asyncio.timeout(PROFILE_TIMEOUT):
                        # Use retry with exponential backoff
                        async def do_scrape():
                            async with async_session() as db:
                                return await self._scrape_profile_by_id(
                                    db, profile_id, username, platform, user_id,
                                    tg_group_id, chat_id, app_settings, hours
                                )

                        stats = await retry_with_backoff(do_scrape)

                    logger.info(f"[{index+1}/{len(profile_list)}] Done @{username}: {stats.get('posts_found', 0)} posts")
                    return {"success": True, "username": username, "stats": stats}

                except asyncio.TimeoutError:
                    logger.warning(f"[{index+1}/{len(profile_list)}] Timeout @{username}")
                    return {"success": False, "username": username, "error": "timeout"}

                except Exception as e:
                    logger.error(f"[{index+1}/{len(profile_list)}] Error @{username}: {e}")
                    return {"success": False, "username": username, "error": str(e)}

        # Run all scrapes in parallel (limited by semaphore)
        tasks = [scrape_with_semaphore(profile_data, i) for i, profile_data in enumerate(profile_list)]
        scrape_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        for result in scrape_results:
            if isinstance(result, Exception):
                results["errors"].append(str(result))
            elif result.get("success"):
                results["profiles_scraped"] += 1
                results["posts_found"] += result.get("stats", {}).get("posts_found", 0)
                results["posts_sent"] += result.get("stats", {}).get("posts_sent", 0)
            else:
                results["errors"].append(f"{result.get('username', '?')}: {result.get('error', 'unknown')}")

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
        since = get_local_now_naive() - timedelta(hours=hours)

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
                post_url=post.get("profile_url", ""),
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
        profile_obj.last_scraped = get_local_now_naive()

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
        """Main scraping job that runs periodically - with parallelism and retry."""
        logger.info(f"Starting scraping job (parallel: {MAX_CONCURRENT_SCRAPES}, retry: {MAX_RETRIES})...")
        self.last_run = get_local_now_naive()

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

        logger.info(f"Found {len(profile_ids)} active profiles to scrape in parallel")

        # Semaphore to limit concurrent scrapes
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

        async def scrape_with_semaphore(profile_data, index):
            """Scrape a profile with semaphore, timeout and retry."""
            profile_id, username, platform, user_id, tg_group_id, chat_id = profile_data

            async with semaphore:
                # Add random delay to stagger requests (avoid burst)
                stagger_delay = random.uniform(0, scrape_delay)
                await asyncio.sleep(stagger_delay)

                logger.info(f"[{index+1}/{len(profile_ids)}] Starting @{username}...")

                try:
                    async with asyncio.timeout(PROFILE_TIMEOUT):
                        # Use retry with exponential backoff
                        async def do_scrape():
                            async with async_session() as db:
                                return await self._scrape_profile_by_data_with_stats(
                                    db, profile_id, username, platform, user_id,
                                    tg_group_id, chat_id, app_settings
                                )

                        stats = await retry_with_backoff(do_scrape)

                    logger.info(f"[{index+1}/{len(profile_ids)}] Done @{username}: {stats.get('posts_found', 0)} posts")
                    return {
                        "success": True,
                        "username": username,
                        "platform": platform,
                        "user_id": user_id,
                        "tg_group_id": tg_group_id,
                        "chat_id": chat_id,
                        "stats": stats
                    }

                except asyncio.TimeoutError:
                    logger.warning(f"[{index+1}/{len(profile_ids)}] Timeout @{username}")
                    return {"success": False, "username": username, "error": "timeout"}

                except Exception as e:
                    logger.error(f"[{index+1}/{len(profile_ids)}] Error @{username}: {e}")
                    return {"success": False, "username": username, "error": str(e)}

        # Run all scrapes in parallel (limited by semaphore)
        tasks = [scrape_with_semaphore(profile_data, i) for i, profile_data in enumerate(profile_ids)]
        scrape_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and track profiles without posts
        for result in scrape_results:
            if isinstance(result, Exception):
                logger.error(f"Unexpected error: {result}")
                continue

            if result.get("success"):
                stats = result.get("stats", {})
                # Track profiles with no posts
                if stats.get("posts_found", 0) == 0:
                    tg_group_id = result.get("tg_group_id")
                    chat_id = result.get("chat_id")
                    if tg_group_id and chat_id:
                        user_id = result.get("user_id")
                        if user_id not in profiles_without_posts:
                            profiles_without_posts[user_id] = {
                                "profiles": [],
                                "chat_id": chat_id,
                            }
                        profiles_without_posts[user_id]["profiles"].append(
                            (result.get("username"), result.get("platform"))
                        )

        # Send grouped "no posts" notifications (if enabled)
        if profiles_without_posts:
            from app.core.app_settings import get_telegram_token
            from app.telegram.bot import TelegramBot

            async with async_session() as db:
                app_settings = await get_app_settings(db)

                # Check if notifications are enabled
                notify_no_posts = getattr(app_settings, 'notify_no_posts', True)
                show_profiles = getattr(app_settings, 'show_profiles_in_no_posts', True)

                if not notify_no_posts:
                    logger.info("No-posts notifications disabled, skipping")
                else:
                    telegram_token = get_telegram_token(app_settings)

                    if telegram_token:
                        bot = TelegramBot(token=telegram_token)

                        for user_id, data in profiles_without_posts.items():
                            try:
                                profiles_list = data["profiles"]
                                chat_id = data["chat_id"]

                                if len(profiles_list) == 1:
                                    username, platform = profiles_list[0]
                                    if show_profiles:
                                        await bot.send_no_posts_found(
                                            chat_id=chat_id,
                                            profile_username=username,
                                            platform=platform,
                                            hours=interval_hours,
                                        )
                                    else:
                                        # Simple message without profile details
                                        message = f"ℹ️ Nenhum post encontrado nas últimas {interval_hours}h."
                                        await bot.send_message(chat_id=chat_id, text=message)
                                else:
                                    # Send grouped message
                                    if show_profiles:
                                        profiles_text = "\n".join([f"• @{u} ({p})" for u, p in profiles_list])
                                        message = (
                                            f"🔍 *Nenhum post encontrado*\n\n"
                                            f"Nos seguintes perfis (últimas {interval_hours}h):\n\n"
                                            f"{profiles_text}"
                                        )
                                    else:
                                        message = (
                                            f"🔍 *Nenhum post encontrado*\n\n"
                                            f"Nenhum novo post nas últimas {interval_hours}h "
                                            f"({len(profiles_list)} perfis verificados)."
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
        since = get_local_now_naive() - timedelta(hours=interval_hours)

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
                post_url=post.get("profile_url", ""),
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
        profile_obj.last_scraped = get_local_now_naive()

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
            since = get_local_now_naive() - timedelta(hours=interval_hours)

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
                    post_url=post.get("profile_url", ""),
                    content=post.get("content", ""),
                    media_url=post.get("media_url"),
                    status="pending",
                )
                db.add(processed_post)
                posts_new += 1

            # Update last scraped
            profile.last_scraped = get_local_now_naive()

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
