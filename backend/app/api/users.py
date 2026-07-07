from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.database import get_db
from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.core.security import get_password_hash, get_current_active_admin

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Lista todos os usuários (apenas admin)."""
    query = select(User)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            (User.username.ilike(search_term)) | (User.email.ilike(search_term))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.execute(count_query)
    total_count = total.scalar()

    # Get users
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(users=list(users), total=total_count)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Retorna um usuário específico (apenas admin)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Cria um novo usuário (apenas admin)."""
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já está em uso",
        )

    # Check if email exists (if provided)
    if user_data.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já está cadastrado",
            )

    user = User(
        username=user_data.username.lower(),
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        is_active=user_data.is_active,
        is_admin=user_data.is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Atualiza um usuário (apenas admin)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    # Check username uniqueness if changing
    if user_data.username and user_data.username.lower() != user.username:
        result = await db.execute(
            select(User).where(User.username == user_data.username.lower())
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username já está em uso",
            )
        user.username = user_data.username.lower()

    # Check email uniqueness if changing
    if user_data.email is not None and user_data.email != user.email:
        if user_data.email:
            result = await db.execute(select(User).where(User.email == user_data.email))
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email já está cadastrado",
                )
        user.email = user_data.email

    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    if user_data.is_admin is not None:
        # Prevent removing admin status from yourself
        if user.id == current_user.id and not user_data.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode remover seu próprio status de admin",
            )
        user.is_admin = user_data.is_admin

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """Remove um usuário (apenas admin)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode deletar seu próprio usuário",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    await db.delete(user)
    await db.commit()
