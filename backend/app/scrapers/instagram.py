import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

import instaloader
from instaloader import Profile, Post

from app.scrapers.base import BaseScraper
from app.config import get_settings, get_local_now_naive

logger = logging.getLogger(__name__)
settings = get_settings()


class InstagramScraper(BaseScraper):
    """Instagram scraper using Instaloader."""

    platform = "instagram"

    def __init__(self):
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
            max_connection_attempts=1,
        )
        # Disable rate limit wait - fail fast instead of waiting 30 minutes
        self.loader.context.request_timeout = 10
        self._logged_in = False

    async def _login(self) -> bool:
        """Login to Instagram if credentials are provided."""
        if self._logged_in:
            return True

        if settings.instagram_username and settings.instagram_password:
            try:
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.loader.login(
                        settings.instagram_username,
                        settings.instagram_password,
                    ),
                )
                self._logged_in = True
                logger.info("Successfully logged in to Instagram")
                return True
            except Exception as e:
                logger.error(f"Failed to login to Instagram: {e}")
                return False
        return False

    async def validate_profile(self, username: str) -> bool:
        """Check if a profile exists and is public."""
        try:
            loop = asyncio.get_event_loop()
            profile = await loop.run_in_executor(
                None,
                lambda: Profile.from_username(self.loader.context, username),
            )
            return not profile.is_private
        except Exception as e:
            logger.error(f"Failed to validate profile {username}: {e}")
            return False

    async def get_recent_posts(
        self,
        username: str,
        limit: int = 10,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent posts from an Instagram profile."""
        posts = []

        if since is None:
            since = get_local_now_naive() - timedelta(days=1)

        try:
            # Try to login for better rate limits
            await self._login()

            loop = asyncio.get_event_loop()

            # Get profile
            profile = await loop.run_in_executor(
                None,
                lambda: Profile.from_username(self.loader.context, username),
            )

            if profile.is_private:
                logger.warning(f"Profile {username} is private, skipping")
                return []

            # Get posts
            def fetch_posts():
                result = []
                for post in profile.get_posts():
                    if len(result) >= limit:
                        break
                    if post.date_utc < since:
                        break

                    post_data = {
                        "post_id": post.shortcode,
                        "content": post.caption or "",
                        "media_url": post.url,
                        "created_at": post.date_utc,
                        "likes": post.likes,
                        "comments": post.comments,
                        "is_video": post.is_video,
                        "profile_url": f"https://instagram.com/p/{post.shortcode}",
                    }
                    result.append(post_data)

                    # Random delay to avoid rate limiting
                    delay = random.uniform(1, settings.scrape_delay_seconds)
                    asyncio.get_event_loop().run_until_complete(asyncio.sleep(delay))

                return result

            posts = await loop.run_in_executor(None, fetch_posts)
            logger.info(f"Found {len(posts)} posts from {username}")

        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"Profile {username} does not exist")
            raise Exception(f"Perfil @{username} não existe no Instagram")
        except instaloader.exceptions.ConnectionException as e:
            error_str = str(e)
            logger.error(f"Connection error for {username}: {e}")
            if "429" in error_str or "Too Many Requests" in error_str:
                raise Exception("Rate limit do Instagram atingido. Aguarde alguns minutos e tente novamente.")
            raise Exception(f"Erro de conexão com Instagram: {error_str}")
        except instaloader.exceptions.TooManyRequestsException:
            logger.error(f"Rate limited while scraping {username}")
            raise Exception("Rate limit do Instagram atingido. Aguarde alguns minutos e tente novamente.")
        except Exception as e:
            logger.error(f"Error scraping {username}: {e}")
            raise

        return posts

    async def get_post_by_shortcode(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Get a specific post by its shortcode."""
        try:
            loop = asyncio.get_event_loop()
            post = await loop.run_in_executor(
                None,
                lambda: Post.from_shortcode(self.loader.context, shortcode),
            )

            return {
                "post_id": post.shortcode,
                "content": post.caption or "",
                "media_url": post.url,
                "created_at": post.date_utc,
                "likes": post.likes,
                "comments": post.comments,
                "is_video": post.is_video,
                "profile_url": f"https://instagram.com/p/{post.shortcode}",
            }
        except Exception as e:
            logger.error(f"Error getting post {shortcode}: {e}")
            return None
