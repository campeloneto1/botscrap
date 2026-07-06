from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Keyword
from app.schemas.keyword import KeywordCreate, KeywordUpdate, KeywordResponse
from app.core.security import get_current_user

router = APIRouter()


@router.get("", response_model=List[KeywordResponse])
async def list_keywords(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Keyword).where(Keyword.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("", response_model=KeywordResponse)
async def create_keyword(
    keyword_data: KeywordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if keyword already exists
    result = await db.execute(
        select(Keyword).where(
            Keyword.user_id == current_user.id,
            Keyword.word == keyword_data.word.lower(),
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keyword already exists",
        )

    keyword = Keyword(
        user_id=current_user.id,
        word=keyword_data.word.lower(),
        priority=keyword_data.priority,
        active=keyword_data.active,
    )
    db.add(keyword)
    await db.commit()
    await db.refresh(keyword)

    return keyword


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    keyword_data: KeywordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Keyword).where(
            Keyword.id == keyword_id,
            Keyword.user_id == current_user.id,
        )
    )
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found",
        )

    update_data = keyword_data.model_dump(exclude_unset=True)
    if "word" in update_data:
        update_data["word"] = update_data["word"].lower()

    for field, value in update_data.items():
        setattr(keyword, field, value)

    await db.commit()
    await db.refresh(keyword)

    return keyword


@router.delete("/{keyword_id}")
async def delete_keyword(
    keyword_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Keyword).where(
            Keyword.id == keyword_id,
            Keyword.user_id == current_user.id,
        )
    )
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyword not found",
        )

    await db.delete(keyword)
    await db.commit()

    return {"message": "Keyword deleted"}
