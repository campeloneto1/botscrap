import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from app.scrapers.base import BaseScraper
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TwitterPlaywrightScraper(BaseScraper):
    """Twitter/X scraper using Playwright (headless browser)."""

    platform = "twitter"

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._playwright = None
        self._logged_in = False

    async def _get_browser(self) -> Browser:
        """Get or create browser instance."""
        if self._browser is None or not self._browser.is_connected():
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                ]
            )
        return self._browser

    async def _close_browser(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._logged_in = False

    async def _login(self, page: Page, username: str = None, password: str = None) -> bool:
        """
        Login to Twitter/X if credentials are configured.

        Note: Twitter now requires login to view most content.
        """
        if self._logged_in:
            return True

        # Get credentials from settings or AppSettings
        twitter_username = username
        twitter_password = password

        if not twitter_username or not twitter_password:
            logger.warning("Twitter credentials not configured, login required")
            return False

        try:
            logger.info("Attempting Twitter login...")

            # Go to login page
            await page.goto("https://twitter.com/i/flow/login", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Fill username/email
            username_input = await page.wait_for_selector('input[autocomplete="username"]', timeout=10000)
            if username_input:
                await username_input.fill(twitter_username)
                await asyncio.sleep(1)

                # Click next button
                next_button = await page.query_selector('button:has-text("Next")')
                if next_button:
                    await next_button.click()
                    await asyncio.sleep(2)
            else:
                logger.error("Could not find username input")
                return False

            # Fill password
            password_input = await page.wait_for_selector('input[name="password"]', timeout=10000)
            if password_input:
                await password_input.fill(twitter_password)
                await asyncio.sleep(1)

                # Click login button
                login_button = await page.query_selector('button[data-testid="LoginForm_Login_Button"]')
                if login_button:
                    await login_button.click()
                    await asyncio.sleep(5)
                else:
                    logger.error("Could not find login button")
                    return False
            else:
                logger.error("Could not find password input")
                return False

            # Check if login was successful
            content = await page.content()

            if "Wrong" in content or "incorrect" in content.lower():
                logger.error("Twitter login failed: incorrect credentials")
                return False

            self._logged_in = True
            logger.info("Twitter login successful")
            return True

        except Exception as e:
            logger.error(f"Error during Twitter login: {e}")
            return False

    async def validate_profile(self, username: str) -> bool:
        """Check if a Twitter profile exists."""
        try:
            browser = await self._get_browser()
            page = await browser.new_page()

            # Remove @ if present
            clean_username = username.lstrip('@')

            await page.goto(f"https://twitter.com/{clean_username}", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            content = await page.content()

            # Check if profile exists
            if "This account doesn't exist" in content or "Essa conta não existe" in content:
                await page.close()
                return False

            await page.close()
            return True
        except Exception as e:
            logger.error(f"Failed to validate profile {username}: {e}")
            return False

    async def get_recent_posts(
        self,
        username: str,
        limit: int = 10,
        since: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent tweets from a Twitter profile using Playwright."""
        posts = []

        if since is None:
            since = datetime.utcnow() - timedelta(days=1)

        browser = None
        page = None

        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Remove @ if present
            clean_username = username.lstrip('@')

            # Navigate to profile
            url = f"https://twitter.com/{clean_username}"
            logger.info(f"Navigating to {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Check for errors
            content = await page.content()

            if "This account doesn't exist" in content or "Essa conta não existe" in content:
                raise Exception(f"Perfil @{username} não existe no Twitter")

            if "Account suspended" in content or "Conta suspensa" in content:
                raise Exception(f"Perfil @{username} está suspenso")

            # Twitter now requires login for most content
            if "Log in" in content and "Sign up" in content:
                # Try to login if we haven't already
                # Note: You'll need to implement login with credentials from AppSettings
                logger.warning("Twitter is requesting login. Limited data may be available.")

            # Scroll to load tweets
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1)

            # Extract tweets
            # Twitter uses article elements with data-testid="tweet"
            tweets = await page.query_selector_all('article[data-testid="tweet"]')

            logger.info(f"Found {len(tweets)} tweet elements")

            for tweet in tweets[:limit]:
                try:
                    post_data = await self._extract_tweet_data(tweet, since)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Error extracting tweet: {e}")
                    continue

            logger.info(f"Extracted {len(posts)} posts from @{username}")

        except PlaywrightTimeout:
            logger.error(f"Timeout loading profile {username}")
            raise Exception(f"Timeout ao carregar perfil @{username}")
        except Exception as e:
            logger.error(f"Error scraping {username}: {e}")
            raise
        finally:
            if page:
                await page.close()

        return posts

    async def _extract_tweet_data(self, tweet_element, since: datetime) -> Optional[Dict[str, Any]]:
        """Extract data from a tweet element."""
        try:
            # Extract tweet text
            text_elem = await tweet_element.query_selector('div[data-testid="tweetText"]')
            content = ""
            if text_elem:
                content = await text_elem.text_content() or ""

            # Extract time/date
            time_elem = await tweet_element.query_selector('time')
            created_at = datetime.utcnow()
            if time_elem:
                datetime_str = await time_elem.get_attribute("datetime")
                if datetime_str:
                    try:
                        created_at = datetime.fromisoformat(datetime_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    except:
                        pass

            # Skip if tweet is older than since
            if created_at < since:
                return None

            # Extract tweet ID from link
            link_elem = await tweet_element.query_selector('a[href*="/status/"]')
            post_id = ""
            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    match = re.search(r'/status/(\d+)', href)
                    if match:
                        post_id = match.group(1)

            # Extract media (if any)
            media_url = ""
            img_elem = await tweet_element.query_selector('img[src*="media"]')
            if img_elem:
                media_url = await img_elem.get_attribute("src") or ""

            # Check for video
            video_elem = await tweet_element.query_selector('video')
            is_video = video_elem is not None

            if not post_id:
                # Generate a unique ID from content hash if no ID found
                import hashlib
                post_id = hashlib.md5(f"{content}{created_at}".encode()).hexdigest()[:16]

            return {
                "post_id": post_id,
                "content": content or "",
                "media_url": media_url,
                "created_at": created_at,
                "likes": 0,
                "comments": 0,
                "is_video": is_video,
                "profile_url": f"https://twitter.com/i/web/status/{post_id}" if post_id.isdigit() else "",
            }

        except Exception as e:
            logger.warning(f"Error extracting tweet data: {e}")
            return None

    async def _close_browser(self):
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._logged_in = False
