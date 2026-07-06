from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class AppSettingsBase(BaseModel):
    telegram_bot_token: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None
    scrape_interval_hours: int = 6
    scrape_delay_seconds: int = 3
    use_proxies: bool = False
    proxy_list: Optional[str] = None
    groq_api_key: Optional[str] = None
    enable_ai_summary: bool = True


class AppSettingsUpdate(BaseModel):
    telegram_bot_token: Optional[str] = None
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None
    scrape_interval_hours: Optional[int] = None
    scrape_delay_seconds: Optional[int] = None
    use_proxies: Optional[bool] = None
    proxy_list: Optional[str] = None
    groq_api_key: Optional[str] = None
    enable_ai_summary: Optional[bool] = None


class AppSettingsResponse(AppSettingsBase):
    id: int
    updated_at: Optional[datetime] = None

    # Mask sensitive fields
    telegram_bot_token: Optional[str] = None
    instagram_password: Optional[str] = None
    groq_api_key: Optional[str] = None

    class Config:
        from_attributes = True
