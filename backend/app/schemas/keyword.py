from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class KeywordCreate(BaseModel):
    word: str
    priority: int = 1  # 1=normal, 2=importante, 3=urgente
    active: bool = True


class KeywordUpdate(BaseModel):
    word: Optional[str] = None
    priority: Optional[int] = None
    active: Optional[bool] = None


class KeywordResponse(BaseModel):
    id: int
    word: str
    priority: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True
