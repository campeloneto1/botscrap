from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TelegramGroupCreate(BaseModel):
    chat_id: str
    name: str
    active: bool = True


class TelegramGroupUpdate(BaseModel):
    chat_id: Optional[str] = None
    name: Optional[str] = None
    active: Optional[bool] = None


class TelegramGroupResponse(BaseModel):
    id: int
    chat_id: str
    name: str
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TelegramTestMessage(BaseModel):
    chat_id: str
    message: str = "Mensagem de teste do BotScrap!"
