from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class AppSettingsBase(BaseModel):
    telegram_bot_token: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None
    twitter_username: Optional[str] = None
    twitter_password: Optional[str] = None
    facebook_email: Optional[str] = None
    facebook_password: Optional[str] = None
    scrape_interval_hours: int = 6
    scrape_delay_seconds: int = 3
    use_proxies: bool = False
    proxy_list: Optional[str] = None
    groq_api_key: Optional[str] = None
    enable_ai_summary: bool = True
    # Notificações
    notify_no_posts: bool = True
    show_profiles_in_no_posts: bool = True
    send_only_with_keywords: bool = False


class AppSettingsUpdate(BaseModel):
    telegram_bot_token: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None
    twitter_username: Optional[str] = None
    twitter_password: Optional[str] = None
    facebook_email: Optional[str] = None
    facebook_password: Optional[str] = None
    scrape_interval_hours: Optional[int] = None
    scrape_delay_seconds: Optional[int] = None
    use_proxies: Optional[bool] = None
    proxy_list: Optional[str] = None
    groq_api_key: Optional[str] = None
    enable_ai_summary: Optional[bool] = None
    # Notificações
    notify_no_posts: Optional[bool] = None
    show_profiles_in_no_posts: Optional[bool] = None
    send_only_with_keywords: Optional[bool] = None


class AppSettingsResponse(AppSettingsBase):
    id: int
    updated_at: Optional[datetime] = None

    # Mask sensitive fields
    telegram_bot_token: Optional[str] = None
    instagram_password: Optional[str] = None
    twitter_password: Optional[str] = None
    facebook_password: Optional[str] = None
    groq_api_key: Optional[str] = None

    class Config:
        from_attributes = True
