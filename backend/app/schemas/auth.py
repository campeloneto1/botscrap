from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username deve conter apenas letras, números, _ ou -')
        if len(v) < 3:
            raise ValueError('Username deve ter pelo menos 3 caracteres')
        if len(v) > 50:
            raise ValueError('Username deve ter no máximo 50 caracteres')
        return v.lower()


class UserLogin(BaseModel):
    username: str  # Pode ser username ou email
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
