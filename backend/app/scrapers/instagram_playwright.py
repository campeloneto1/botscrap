import asyncio
import random
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from app.scrapers.base import BaseScraper
from app.config import get_settings, get_local_now_naive

logger = logging.getLogger(__name__)
settings = get_settings()


class InstagramPlaywrightScraper(BaseScraper):
    """Instagram scraper using Playwright (headless browser)."""

    platform = "instagram"

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
        Login to Instagram if credentials are configured.

        Args:
            username: Instagram username (optional, uses .env if not provided)
            password: Instagram password (optional, uses .env if not provided)

        Returns:
            True if login successful or already logged in, False otherwise
        """
        if self._logged_in:
            return True

        # Use provided credentials or fall back to .env
        insta_username = username or settings.instagram_username
        insta_password = password or settings.instagram_password

        if not insta_username or not insta_password:
            logger.warning("Instagram credentials not configured, skipping login")
            return False

        try:
            logger.info("Attempting Instagram login...")

            # Go to login page
            await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Fill username
            username_input = await page.query_selector('input[name="username"]')
            if username_input:
                await username_input.fill(insta_username)
                await asyncio.sleep(1)
            else:
                logger.error("Could not find username input")
                return False

            # Fill password
            password_input = await page.query_selector('input[name="password"]')
            if password_input:
                await password_input.fill(insta_password)
                await asyncio.sleep(1)
            else:
                logger.error("Could not find password input")
                return False

            # Click login button
            login_button = await page.query_selector('button[type="submit"]')
            if login_button:
                await login_button.click()
                await asyncio.sleep(5)
            else:
                logger.error("Could not find login button")
                return False

            # Check if login was successful
            content = await page.content()

            # Check for common login errors
            if "incorrect" in content.lower() or "senha" in content.lower():
                logger.error("Instagram login failed: incorrect credentials")
                return False

            # Check for "Save Your Login Info?" prompt and skip it
            try:
                not_now_button = await page.query_selector('button:has-text("Not Now")')
                if not_now_button:
                    await not_now_button.click()
                    await asyncio.sleep(2)
            except:
                pass

            # Check for "Turn on Notifications?" prompt and skip it
            try:
                not_now_button = await page.query_selector('button:has-text("Not Now")')
                if not_now_button:
                    await not_now_button.click()
                    await asyncio.sleep(2)
            except:
                pass

            self._logged_in = True
            logger.info("Instagram login successful")
            return True

        except Exception as e:
            logger.error(f"Error during Instagram login: {e}")
            return False

    async def validate_profile(self, username: str) -> bool:
        """Check if a profile exists and is public."""
        try:
            browser = await self._get_browser()
            page = await browser.new_page()

            await page.goto(f"https://www.instagram.com/{username}/", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Check if profile exists
            content = await page.content()
            if "Sorry, this page isn't available" in content:
                await page.close()
                return False

            # Check if private
            if "This account is private" in content or "Esta conta é privada" in content:
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
        """Get recent posts from an Instagram profile using Playwright."""
        posts = []

        if since is None:
            since = get_local_now_naive() - timedelta(days=1)

        browser = None
        page = None

        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Navigate to profile
            url = f"https://www.instagram.com/{username}/"
            logger.info(f"Navigating to {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to load
            await asyncio.sleep(3)

            # Check for errors
            content = await page.content()

            if "Sorry, this page isn't available" in content:
                raise Exception(f"Perfil @{username} não existe no Instagram")

            if "This account is private" in content or "Esta conta é privada" in content:
                raise Exception(f"Perfil @{username} é privado")

            if "Login" in content and "Sign up" in content and username not in content:
                raise Exception("Instagram solicitou login. Tente novamente mais tarde.")

            # Try to extract posts from the page
            # Instagram loads posts dynamically, so we need to look for the data in the HTML/scripts

            # Method 1: Look for post links in the HTML
            post_links = await page.query_selector_all('a[href*="/p/"]')

            seen_shortcodes = set()

            for link in post_links[:limit * 2]:  # Get more than needed to filter
                try:
                    href = await link.get_attribute("href")
                    if href and "/p/" in href:
                        # Extract shortcode from URL
                        match = re.search(r'/p/([A-Za-z0-9_-]+)', href)
                        if match:
                            shortcode = match.group(1)
                            if shortcode not in seen_shortcodes:
                                seen_shortcodes.add(shortcode)

                                # Get post details by visiting the post page
                                post_data = await self._get_post_details(browser, shortcode, since)
                                if post_data:
                                    posts.append(post_data)

                                    if len(posts) >= limit:
                                        break

                                    # Delay between posts
                                    delay = random.uniform(1, 2)
                                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.warning(f"Error processing post link: {e}")
                    continue

            logger.info(f"Found {len(posts)} posts from {username}")

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

    async def _get_post_details(
        self,
        browser: Browser,
        shortcode: str,
        since: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get details of a specific post."""
        page = None
        try:
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            url = f"https://www.instagram.com/p/{shortcode}/"
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)

            content = await page.content()

            # Extract caption
            caption = ""
            # Try to find caption in meta tags
            meta_desc = await page.query_selector('meta[property="og:description"]')
            if meta_desc:
                caption = await meta_desc.get_attribute("content") or ""

            # Try to find caption in the page content
            if not caption:
                caption_elem = await page.query_selector('div[class*="Caption"] span')
                if caption_elem:
                    caption = await caption_elem.text_content() or ""

            # Extract image URL
            media_url = ""
            og_image = await page.query_selector('meta[property="og:image"]')
            if og_image:
                media_url = await og_image.get_attribute("content") or ""

            # Check if it's a video
            video_elem = await page.query_selector('video')
            is_video = video_elem is not None

            # Try to extract date from the page
            time_elem = await page.query_selector('time[datetime]')
            created_at = get_local_now_naive()
            if time_elem:
                datetime_str = await time_elem.get_attribute("datetime")
                if datetime_str:
                    try:
                        created_at = datetime.fromisoformat(datetime_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    except:
                        pass

            # Skip if post is older than since
            if created_at < since:
                return None

            return {
                "post_id": shortcode,
                "content": caption or "",
                "media_url": media_url,
                "created_at": created_at,
                "likes": 0,  # Can't easily get without login
                "comments": 0,  # Can't easily get without login
                "is_video": is_video,
                "profile_url": f"https://instagram.com/p/{shortcode}",
            }

        except Exception as e:
            logger.warning(f"Error getting post {shortcode}: {e}")
            return None
        finally:
            if page:
                await page.close()

    async def get_post_by_shortcode(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Get a specific post by its shortcode."""
        try:
            browser = await self._get_browser()
            return await self._get_post_details(browser, shortcode, datetime.min)
        except Exception as e:
            logger.error(f"Error getting post {shortcode}: {e}")
            return None

    async def search_by_keywords(
        self,
        keywords: List[str],
        limit: int = 10,
        instagram_username: str = None,
        instagram_password: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Instagram by keywords and return recent posts.

        Args:
            keywords: List of keywords to search for (e.g., ["greve", "ceara"])
            limit: Maximum number of posts to return
            instagram_username: Instagram username for login (optional)
            instagram_password: Instagram password for login (optional)

        Returns:
            List of posts containing ALL the specified keywords
        """
        posts = []

        if not keywords:
            return posts

        # Use the first keyword as the main hashtag to search
        main_keyword = keywords[0].lower().replace("#", "")

        browser = None
        page = None

        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Try to login first if credentials are available
            login_success = await self._login(page, instagram_username, instagram_password)

            # Navigate to hashtag page
            url = f"https://www.instagram.com/explore/tags/{main_keyword}/"
            logger.info(f"Searching hashtag: {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Check for errors
            content = await page.content()

            if "Sorry, this page isn't available" in content:
                raise Exception(f"Hashtag #{main_keyword} não encontrada")

            if "Login" in content and "Sign up" in content and not login_success:
                raise Exception(
                    "Instagram solicitou login. Configure as credenciais do Instagram "
                    "na tabela app_settings (instagram_username e instagram_password) para usar a busca."
                )

            # Get post links from hashtag page
            post_links = await page.query_selector_all('a[href*="/p/"]')

            seen_shortcodes = set()
            checked_count = 0
            max_checks = limit * 3  # Check more posts to find enough matching ones

            for link in post_links[:max_checks]:
                try:
                    href = await link.get_attribute("href")
                    if href and "/p/" in href:
                        # Extract shortcode from URL
                        match = re.search(r'/p/([A-Za-z0-9_-]+)', href)
                        if match:
                            shortcode = match.group(1)
                            if shortcode not in seen_shortcodes:
                                seen_shortcodes.add(shortcode)
                                checked_count += 1

                                # Get post details
                                post_data = await self._get_post_details(
                                    browser,
                                    shortcode,
                                    get_local_now_naive() - timedelta(days=30)  # Last 30 days
                                )

                                if post_data:
                                    # Check if ALL keywords are in the post content
                                    content_lower = post_data.get("content", "").lower()

                                    if all(keyword.lower() in content_lower for keyword in keywords):
                                        posts.append(post_data)
                                        logger.info(f"Found matching post: {shortcode}")

                                        if len(posts) >= limit:
                                            break

                                # Delay between posts
                                delay = random.uniform(1, 2)
                                await asyncio.sleep(delay)

                except Exception as e:
                    logger.warning(f"Error processing post link: {e}")
                    continue

            logger.info(f"Found {len(posts)} posts matching keywords: {keywords}")

        except PlaywrightTimeout:
            logger.error(f"Timeout searching for {main_keyword}")
            raise Exception(f"Timeout ao buscar #{main_keyword}")
        except Exception as e:
            logger.error(f"Error searching keywords {keywords}: {e}")
            raise
        finally:
            if page:
                await page.close()

        return posts
