import logging
import re
import unicodedata
from typing import List, Optional, Dict, Any

from telegram import Bot
from telegram.constants import ParseMode

from app.config import get_settings

logger = logging.getLogger(__name__)
env_settings = get_settings()


class TelegramBot:
    """Telegram bot for sending notifications."""

    def __init__(self, token: Optional[str] = None):
        # Use provided token, or fallback to .env
        bot_token = token or env_settings.telegram_bot_token
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured")
        self.bot = Bot(token=bot_token)

    def _normalize_text(self, text: str) -> str:
        """Remove accents and convert to lowercase."""
        if not text:
            return ""
        normalized = unicodedata.normalize('NFD', text)
        without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return without_accents.lower()

    def _highlight_keywords(self, text: str, keywords: List[str]) -> str:
        """Highlight keywords in text with bold formatting. Handles accents."""
        if not keywords or not text:
            return text

        result = text
        text_normalized = self._normalize_text(text)

        for keyword in keywords:
            keyword_normalized = self._normalize_text(keyword)
            if not keyword_normalized:
                continue

            # Find matches in normalized text
            pattern = re.compile(r'\b' + re.escape(keyword_normalized) + r'\b')
            matches = list(pattern.finditer(text_normalized))

            # Replace from end to start to preserve positions
            for match in reversed(matches):
                start, end = match.start(), match.end()
                original_word = result[start:end]
                result = result[:start] + f"<b>⚡{original_word.upper()}⚡</b>" + result[end:]

        return result

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

        # Content - use summary if available, otherwise send full content
        content = post.get("content", "")
        summary = post.get("summary")

        if summary:
            # Show AI summary
            lines.append(f"📝 <b>Resumo:</b> {summary}")
            lines.append("")
            if len(content) > 200:
                lines.append(f"<i>(Post completo: {len(content)} caracteres)</i>")
                lines.append("")
        elif content:
            # Send full content (no truncation when summary not available)
            display_content = content

            # Highlight keywords if any
            if matched_keywords:
                display_content = self._highlight_keywords(display_content, matched_keywords)

            lines.append(display_content)
            lines.append("")

        # Video transcript if available
        video_transcript = post.get("video_transcript")
        if video_transcript:
            lines.append("🎬 <b>Transcrição do vídeo:</b>")
            # Truncate if too long
            if len(video_transcript) > 500:
                transcript_display = video_transcript[:500] + "..."
            else:
                transcript_display = video_transcript
            if matched_keywords:
                transcript_display = self._highlight_keywords(transcript_display, matched_keywords)
            lines.append(f"<i>{transcript_display}</i>")
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

        # Content - use summary if available, otherwise send full content
        content = post.get("content", "")
        summary = post.get("summary")

        if summary:
            # Show AI summary with highlighted keywords
            summary_highlighted = self._highlight_keywords(summary, matched_keywords)
            lines.append(f"📝 <b>Resumo:</b> {summary_highlighted}")
            lines.append("")
            if len(content) > 200:
                lines.append(f"<i>(Post completo: {len(content)} caracteres)</i>")
                lines.append("")
        elif content:
            # Send full content with highlighted keywords
            display_content = self._highlight_keywords(content, matched_keywords)
            lines.append(display_content)
            lines.append("")

        # Video transcript if available
        video_transcript = post.get("video_transcript")
        if video_transcript:
            lines.append("🎬 <b>Transcrição do vídeo:</b>")
            # Truncate if too long
            if len(video_transcript) > 500:
                transcript_display = video_transcript[:500] + "..."
            else:
                transcript_display = video_transcript
            transcript_display = self._highlight_keywords(transcript_display, matched_keywords)
            lines.append(f"<i>{transcript_display}</i>")
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

    async def send_no_posts_found(
        self,
        chat_id: str,
        profile_username: str,
        platform: str,
        hours: int,
    ) -> bool:
        """Send notification when no posts are found for a profile."""
        platform_emoji = {
            "instagram": "📸",
            "twitter": "🐦",
            "facebook": "📘",
        }.get(platform, "📱")

        message = (
            f"ℹ️ <b>Nenhum post encontrado</b>\n"
            f"\n"
            f"{platform_emoji} <b>@{profile_username}</b>\n"
            f"\n"
            f"Nenhum post encontrado nas últimas <b>{hours}</b> hora(s)."
        )

        return await self.send_message(chat_id, message)
