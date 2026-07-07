from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    is_active: bool = True
    is_admin: bool = False

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


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username deve conter apenas letras, números, _ ou -')
        if len(v) < 3:
            raise ValueError('Username deve ter pelo menos 3 caracteres')
        if len(v) > 50:
            raise ValueError('Username deve ter no máximo 50 caracteres')
        return v.lower()


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
