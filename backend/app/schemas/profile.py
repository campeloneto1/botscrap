from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProfileCreate(BaseModel):
    platform: str
    username: str
    telegram_group_id: Optional[int] = None
    active: bool = True


class ProfileUpdate(BaseModel):
    platform: Optional[str] = None
    username: Optional[str] = None
    telegram_group_id: Optional[int] = None
    active: Optional[bool] = None


class ProfileResponse(BaseModel):
    id: int
    platform: str
    username: str
    telegram_group_id: Optional[int]
    active: bool
    last_scraped: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
