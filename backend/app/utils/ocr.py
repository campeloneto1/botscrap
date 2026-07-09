"""
OCR utilities for extracting text from images.
Uses Tesseract OCR to detect text in post images.
Includes caching to avoid reprocessing the same images.
"""
import asyncio
import logging
import io
from typing import Optional, List, Tuple

import httpx
from PIL import Image
import pytesseract
from sqlalchemy import select

from app.config import get_local_now_naive
from app.db.database import async_session
from app.db.models import OCRCache
from app.utils.keywords import find_keywords

logger = logging.getLogger(__name__)

# Timeout for OCR processing
OCR_TIMEOUT = 30  # seconds


async def download_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """Download image from URL."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type:
                    return response.content
                logger.warning(f"URL is not an image: {content_type}")
            else:
                logger.warning(f"Failed to download image: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
    return None


def _extract_text_sync(image_bytes: bytes, lang: str = 'por+eng') -> str:
    """
    Extract text from image bytes using Tesseract OCR (synchronous).

    Args:
        image_bytes: Image data
        lang: Tesseract language codes (e.g., 'por+eng', 'eng', 'spa+eng')
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background

        # Use specified languages for OCR
        text = pytesseract.image_to_string(image, lang=lang)

        # Clean up the text
        text = text.strip()
        return text
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}")
        return ""


async def extract_text_from_image(image_bytes: bytes, lang: str = 'por+eng') -> str:
    """
    Extract text from image bytes using Tesseract OCR (async with timeout).

    Args:
        image_bytes: Image data
        lang: Tesseract language codes (e.g., 'por+eng', 'eng', 'spa+eng')
    """
    try:
        async with asyncio.timeout(OCR_TIMEOUT):
            return await asyncio.to_thread(_extract_text_sync, image_bytes, lang)
    except asyncio.TimeoutError:
        logger.error(f"OCR timeout ({OCR_TIMEOUT}s)")
        return ""
    except Exception as e:
        logger.error(f"Error in async OCR: {e}")
        return ""


async def extract_text_from_url(url: str, lang: str = 'por+eng', use_cache: bool = True) -> str:
    """
    Download image and extract text using OCR with caching.

    Args:
        url: Image URL
        lang: Tesseract language codes
        use_cache: Whether to use cache (default: True)
    """
    if not url:
        return ""

    # Check cache first
    if use_cache:
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(OCRCache).where(
                        OCRCache.image_url == url,
                        OCRCache.language == lang
                    )
                )
                cached = result.scalar_one_or_none()

                if cached:
                    logger.debug(f"OCR cache hit for {url[:100]}")
                    # Update last_used
                    cached.last_used = get_local_now_naive()
                    await db.commit()
                    return cached.ocr_text or ""

        except Exception as e:
            logger.warning(f"Failed to check OCR cache: {e}")

    # Cache miss or disabled - perform OCR
    logger.debug(f"Running OCR on image: {url[:100]}...")

    image_bytes = await download_image(url)
    if not image_bytes:
        return ""

    text = await extract_text_from_image(image_bytes, lang=lang)

    if text:
        logger.debug(f"OCR extracted {len(text)} characters")

    # Save to cache
    if use_cache:
        try:
            async with async_session() as db:
                cache_entry = OCRCache(
                    image_url=url,
                    ocr_text=text,
                    language=lang,
                )
                db.add(cache_entry)
                await db.commit()
                logger.debug(f"Saved OCR result to cache")
        except Exception as e:
            logger.warning(f"Failed to save OCR to cache: {e}")

    return text


async def process_image_for_keywords(
    image_url: str,
    keywords: List[dict]
) -> Tuple[bool, List[str], int, str]:
    """
    Process an image URL for keyword detection.
    Returns: (has_keyword, matched_keywords, priority, extracted_text)
    """
    if not image_url:
        return False, [], 0, ""

    # Extract text from image
    text = await extract_text_from_url(image_url)

    if not text:
        return False, [], 0, ""

    # Find keywords in the extracted text (uses shared function from keywords.py)
    has_keyword, matched, priority = find_keywords(text, keywords)

    if has_keyword:
        logger.info(f"OCR found keywords in image: {matched}")

    return has_keyword, matched, priority, text
