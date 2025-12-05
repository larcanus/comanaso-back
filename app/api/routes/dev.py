"""
Development/Testing endpoints.
Используются только в dev окружении для тестирования.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models.user import User
from app.config import settings

router = APIRouter(tags=["Development"])


@router.delete(
    "/cleanup/test-users",
    summary="Удаление тестовых пользователей",
    description="Удаляет всех пользователей с email/username содержащим 'test'. Только для dev окружения."
)
async def cleanup_test_users(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Удаляет всех тестовых пользователей из базы данных.
    Работает только в development окружении.
    """
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development environment"
        )

    # Удаляем пользователей с test в email или username
    stmt = delete(User).where(
        (User.email.ilike('%test%')) | (User.username.ilike('%test%'))
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    deleted_count = result.rowcount
    
    return {
        "message": f"Deleted {deleted_count} test user(s)",
        "deleted_count": deleted_count
    }


@router.delete(
    "/cleanup/user/{user_id}",
    summary="Удаление пользователя по ID",
    description="Удаляет конкретного пользователя. Только для dev окружения."
)
async def delete_user_by_id(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Удаляет пользователя по ID.
    Работает только в development окружении.
    """
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development environment"
        )

    # Проверяем существование пользователя
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Удаляем пользователя
    await db.delete(user)
    await db.commit()
    
    return {
        "message": f"User {user_id} deleted successfully",
        "user_id": user_id,
        "username": user.username
    }


@router.get(
    "/users/list",
    summary="Список всех пользователей",
    description="Возвращает список всех пользователей. Только для dev окружения."
)
async def list_all_users(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Возвращает список всех пользователей в системе.
    Работает только в development окружении.
    """
    if settings.environment != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in development environment"
        )

    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return {
        "total": len(users),
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat()
            }
            for user in users
        ]
    }