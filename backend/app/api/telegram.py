from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, TelegramGroup
from app.schemas.telegram import (
    TelegramGroupCreate,
    TelegramGroupUpdate,
    TelegramGroupResponse,
    TelegramTestMessage,
)
from app.core.security import get_current_user
from app.telegram.bot import TelegramBot

router = APIRouter()


@router.get("/groups", response_model=List[TelegramGroupResponse])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TelegramGroup).where(TelegramGroup.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/groups", response_model=TelegramGroupResponse)
async def create_group(
    group_data: TelegramGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if group already exists
    result = await db.execute(
        select(TelegramGroup).where(
            TelegramGroup.user_id == current_user.id,
            TelegramGroup.chat_id == group_data.chat_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group already exists",
        )

    group = TelegramGroup(
        user_id=current_user.id,
        chat_id=group_data.chat_id,
        name=group_data.name,
        active=group_data.active,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)

    return group


@router.put("/groups/{group_id}", response_model=TelegramGroupResponse)
async def update_group(
    group_id: int,
    group_data: TelegramGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TelegramGroup).where(
            TelegramGroup.id == group_id,
            TelegramGroup.user_id == current_user.id,
        )
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    update_data = group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)

    await db.commit()
    await db.refresh(group)

    return group


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TelegramGroup).where(
            TelegramGroup.id == group_id,
            TelegramGroup.user_id == current_user.id,
        )
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await db.delete(group)
    await db.commit()

    return {"message": "Group deleted"}


@router.post("/test")
async def test_telegram(
    message_data: TelegramTestMessage,
    current_user: User = Depends(get_current_user),
):
    try:
        bot = TelegramBot()
        await bot.send_message(
            chat_id=message_data.chat_id,
            text=message_data.message,
        )
        return {"success": True, "message": "Message sent successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}
