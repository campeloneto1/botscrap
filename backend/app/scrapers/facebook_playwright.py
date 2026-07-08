import asyncio
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from app.scrapers.base import BaseScraper
from app.config import get_settings, get_local_now_naive

logger = logging.getLogger(__name__)
settings = get_settings()


class FacebookPlaywrightScraper(BaseScraper):
    """Facebook scraper using Playwright (headless browser)."""

    platform = "facebook"

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

    async def _login(self, page: Page, email: str = None, password: str = None) -> bool:
        """
        Login to Facebook if credentials are configured.

        Note: Facebook has strong anti-bot measures. Use with caution.
        """
        if self._logged_in:
            return True

        facebook_email = email
        facebook_password = password

        if not facebook_email or not facebook_password:
            logger.warning("Facebook credentials not configured")
            return False

        try:
            logger.info("Attempting Facebook login...")

            # Go to login page
            await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Accept cookies if prompted
            try:
                cookie_button = await page.query_selector('button[data-cookiebanner="accept_button"]')
                if cookie_button:
                    await cookie_button.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Fill email
            email_input = await page.query_selector('input[name="email"]')
            if email_input:
                await email_input.fill(facebook_email)
                await asyncio.sleep(1)
            else:
                logger.error("Could not find email input")
                return False

            # Fill password
            password_input = await page.query_selector('input[name="pass"]')
            if password_input:
                await password_input.fill(facebook_password)
                await asyncio.sleep(1)
            else:
                logger.error("Could not find password input")
                return False

            # Click login button
            login_button = await page.query_selector('button[name="login"]')
            if login_button:
                await login_button.click()
                await asyncio.sleep(5)
            else:
                logger.error("Could not find login button")
                return False

            # Check if login was successful
            content = await page.content()

            if "incorrect" in content.lower() or "senha" in content.lower():
                logger.error("Facebook login failed: incorrect credentials")
                return False

            # Handle "Save login info?" prompt
            try:
                not_now = await page.query_selector('div[aria-label="Not now"], div[aria-label="Agora não"]')
                if not_now:
                    await not_now.click()
                    await asyncio.sleep(2)
            except:
                pass

            self._logged_in = True
            logger.info("Facebook login successful")
            return True

        except Exception as e:
            logger.error(f"Error during Facebook login: {e}")
            return False

    async def validate_profile(self, username: str) -> bool:
        """Check if a Facebook profile/page exists."""
        try:
            browser = await self._get_browser()
            page = await browser.new_page()

            await page.goto(f"https://www.facebook.com/{username}", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            content = await page.content()

            # Check if page exists
            if "This page isn't available" in content or "Esta página não está disponível" in content:
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
        """Get recent posts from a Facebook profile/page using Playwright."""
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

            # Navigate to profile/page
            url = f"https://www.facebook.com/{username}"
            logger.info(f"Navigating to {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Accept cookies if prompted
            try:
                cookie_button = await page.query_selector('button[data-cookiebanner="accept_button"]')
                if cookie_button:
                    await cookie_button.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Check for errors
            content = await page.content()

            if "This page isn't available" in content or "Esta página não está disponível" in content:
                raise Exception(f"Perfil/Página @{username} não existe no Facebook")

            if "Log In" in content and "Sign Up" in content:
                logger.warning("Facebook may require login for full access")

            # Scroll to load posts
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(2)

            # Facebook posts are in divs with specific attributes
            # This is a generic approach as Facebook's DOM changes frequently
            post_elements = await page.query_selector_all('div[data-ad-preview="message"]')

            if not post_elements:
                # Try alternative selectors
                post_elements = await page.query_selector_all('div[data-ad-comet-preview="message"]')

            if not post_elements:
                # Try finding posts by role
                post_elements = await page.query_selector_all('[role="article"]')

            logger.info(f"Found {len(post_elements)} post elements")

            for i, post_elem in enumerate(post_elements[:limit]):
                try:
                    post_data = await self._extract_post_data(post_elem, username, i, since)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Error extracting post: {e}")
                    continue

            logger.info(f"Extracted {len(posts)} posts from {username}")

        except PlaywrightTimeout:
            logger.error(f"Timeout loading profile {username}")
            raise Exception(f"Timeout ao carregar perfil {username}")
        except Exception as e:
            logger.error(f"Error scraping {username}: {e}")
            raise
        finally:
            if page:
                await page.close()

        return posts

    async def _extract_post_data(self, post_element, username: str, index: int, since: datetime) -> Optional[Dict[str, Any]]:
        """Extract data from a Facebook post element."""
        try:
            # Extract post text - Facebook has multiple possible structures
            content = ""

            # Try different selectors for post text
            text_selectors = [
                'div[data-ad-preview="message"]',
                'div[data-ad-comet-preview="message"]',
                'div[dir="auto"]',
            ]

            for selector in text_selectors:
                text_elem = await post_element.query_selector(selector)
                if text_elem:
                    text = await text_elem.text_content()
                    if text and len(text) > len(content):
                        content = text
                        break

            # If still no content, get all text from the post
            if not content:
                content = await post_element.text_content() or ""
                # Clean up excessive whitespace
                content = " ".join(content.split())

            # Extract time/date (Facebook uses relative time like "2h", "3d")
            created_at = get_local_now_naive()
            time_elem = await post_element.query_selector('abbr')
            if time_elem:
                time_text = await time_elem.text_content()
                created_at = self._parse_relative_time(time_text)

            # Skip if post is older than since
            if created_at < since:
                return None

            # Extract post link to get ID
            link_elem = await post_element.query_selector('a[href*="/posts/"], a[href*="/permalink/"]')
            post_id = ""
            profile_url = ""

            if link_elem:
                href = await link_elem.get_attribute("href")
                if href:
                    profile_url = f"https://www.facebook.com{href}" if href.startswith('/') else href
                    # Extract ID from URL
                    match = re.search(r'/posts/(\d+)', href)
                    if not match:
                        match = re.search(r'/permalink/(\d+)', href)
                    if match:
                        post_id = match.group(1)

            # If no ID found, generate one
            if not post_id:
                import hashlib
                post_id = hashlib.md5(f"{username}{index}{content[:50]}".encode()).hexdigest()[:16]

            # Extract media
            media_url = ""
            img_elem = await post_element.query_selector('img[src*="fbcdn"]')
            if img_elem:
                media_url = await img_elem.get_attribute("src") or ""

            # Check for video
            video_elem = await post_element.query_selector('video')
            is_video = video_elem is not None

            return {
                "post_id": post_id,
                "content": content.strip()[:5000] or "",  # Limit content length
                "media_url": media_url,
                "created_at": created_at,
                "likes": 0,
                "comments": 0,
                "is_video": is_video,
                "profile_url": profile_url or f"https://facebook.com/{username}",
            }

        except Exception as e:
            logger.warning(f"Error extracting post data: {e}")
            return None

    def _parse_relative_time(self, time_text: str) -> datetime:
        """Parse Facebook's relative time format (e.g., '2h', '3d', '1w')."""
        try:
            time_text = time_text.lower().strip()

            # Handle "just now"
            if "just now" in time_text or "agora" in time_text:
                return get_local_now_naive()

            # Extract number and unit
            match = re.search(r'(\d+)\s*([smhdwy])', time_text)
            if match:
                amount = int(match.group(1))
                unit = match.group(2)

                if unit == 's':  # seconds
                    return get_local_now_naive() - timedelta(seconds=amount)
                elif unit == 'm':  # minutes
                    return get_local_now_naive() - timedelta(minutes=amount)
                elif unit == 'h':  # hours
                    return get_local_now_naive() - timedelta(hours=amount)
                elif unit == 'd':  # days
                    return get_local_now_naive() - timedelta(days=amount)
                elif unit == 'w':  # weeks
                    return get_local_now_naive() - timedelta(weeks=amount)
                elif unit == 'y':  # years
                    return get_local_now_naive() - timedelta(days=amount * 365)

            # If parsing fails, assume recent
            return get_local_now_naive()

        except Exception as e:
            logger.warning(f"Error parsing time '{time_text}': {e}")
            return get_local_now_naive()
