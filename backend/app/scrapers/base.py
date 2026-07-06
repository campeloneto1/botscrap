from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class BaseScraper(ABC):
    """Base class for all social media scrapers."""

    platform: str = "unknown"

    @abstractmethod
    async def get_recent_posts(
        self,
        username: str,
        limit: int = 10,
        since: datetime = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent posts from a profile.

        Args:
            username: The username/handle to scrape
            limit: Maximum number of posts to retrieve
            since: Only get posts after this datetime

        Returns:
            List of post dictionaries with at least:
            - post_id: unique identifier
            - content: text content
            - media_url: URL to media (if any)
            - created_at: post creation time
        """
        pass

    @abstractmethod
    async def validate_profile(self, username: str) -> bool:
        """Check if a profile exists and is accessible."""
        pass
