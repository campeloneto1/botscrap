import logging
import re
from typing import List, Optional, Dict, Any

from telegram import Bot
from telegram.constants import ParseMode

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TelegramBot:
    """Telegram bot for sending notifications."""

    def __init__(self):
        if not settings.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        self.bot = Bot(token=settings.telegram_bot_token)

    def _highlight_keywords(self, text: str, keywords: List[str]) -> str:
        """Highlight keywords in text with bold formatting."""
        if not keywords:
            return text

        for keyword in keywords:
            # Case-insensitive replacement with bold
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            text = pattern.sub(f"<b>⚡{keyword.upper()}⚡</b>", text)

        return text

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = ParseMode.HTML,
        disable_preview: bool = False,
    ) -> bool:
        """Send a text message to a chat."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            return False

    async def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: str,
        parse_mode: str = ParseMode.HTML,
    ) -> bool:
        """Send a photo with caption to a chat."""
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo_url,
                caption=caption,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send photo to {chat_id}: {e}")
            # Fallback to text message if photo fails
            return await self.send_message(chat_id, caption)

    async def send_post(
        self,
        chat_id: str,
        post: Dict[str, Any],
        profile_username: str,
        platform: str,
        matched_keywords: Optional[List[str]] = None,
    ) -> bool:
        """Send a formatted post to a chat."""
        # Build message
        lines = []

        # Header with platform and profile
        platform_emoji = {
            "instagram": "📸",
            "twitter": "🐦",
            "facebook": "📘",
        }.get(platform, "📱")

        lines.append(f"{platform_emoji} <b>@{profile_username}</b>")
        lines.append("")

        # Content with keyword highlighting
        content = post.get("content", "")
        if content:
            # Truncate if too long
            if len(content) > 800:
                content = content[:800] + "..."

            # Highlight keywords if any
            if matched_keywords:
                content = self._highlight_keywords(content, matched_keywords)

            lines.append(content)
            lines.append("")

        # Link
        if post.get("profile_url"):
            lines.append(f"🔗 <a href=\"{post['profile_url']}\">Ver post original</a>")

        # Keyword alert footer
        if matched_keywords:
            lines.append("")
            lines.append(f"🔔 <i>Palavras-chave: {', '.join(matched_keywords)}</i>")

        caption = "\n".join(lines)

        # Send with photo if available
        media_url = post.get("media_url")
        if media_url and not post.get("is_video"):
            return await self.send_photo(chat_id, media_url, caption)
        else:
            return await self.send_message(chat_id, caption)

    async def send_alert(
        self,
        chat_id: str,
        post: Dict[str, Any],
        profile_username: str,
        platform: str,
        matched_keywords: List[str],
        priority: int = 1,
    ) -> bool:
        """Send an urgent alert for posts with high-priority keywords."""
        # Priority headers
        priority_header = {
            1: "📢 Nova menção",
            2: "⚠️ ALERTA IMPORTANTE ⚠️",
            3: "🚨🚨🚨 ALERTA URGENTE 🚨🚨🚨",
        }.get(priority, "📢 Nova menção")

        lines = []
        lines.append(f"<b>{priority_header}</b>")
        lines.append("")
        lines.append(f"🎯 Palavras encontradas: <b>{', '.join(matched_keywords)}</b>")
        lines.append("")
        lines.append("━" * 20)
        lines.append("")

        platform_emoji = {
            "instagram": "📸",
            "twitter": "🐦",
            "facebook": "📘",
        }.get(platform, "📱")

        lines.append(f"{platform_emoji} <b>@{profile_username}</b>")
        lines.append("")

        # Content with highlighting
        content = post.get("content", "")
        if content:
            if len(content) > 800:
                content = content[:800] + "..."

            # Highlight keywords
            content = self._highlight_keywords(content, matched_keywords)
            lines.append(content)
            lines.append("")

        # Link
        if post.get("profile_url"):
            lines.append(f"🔗 <a href=\"{post['profile_url']}\">Ver post original</a>")

        caption = "\n".join(lines)

        # Send with photo if available
        media_url = post.get("media_url")
        if media_url and not post.get("is_video"):
            return await self.send_photo(chat_id, media_url, caption)
        else:
            return await self.send_message(chat_id, caption)
