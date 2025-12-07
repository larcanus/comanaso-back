"""
FastAPI dependencies для аутентификации и авторизации.
Кастомный HTTPBearer с правильным форматом ошибок и get_current_user.

Содержит:
- CustomHTTPBearer: Кастомная схема аутентификации с правильным форматом ошибок
- get_current_user: Зависимость для получения текущего пользователя из JWT токена
- CurrentUser: Типизированная зависимость для удобства использования в роутах
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.jwt import decode_access_token
from app.services.auth_service import AuthService


class CustomHTTPBearer(HTTPBearer):
    """Кастомный HTTPBearer с правильным форматом ошибок."""

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            return await super().__call__(request)
        except HTTPException:
            # Перехватываем исключение от базового HTTPBearer и выбрасываем своё
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "UNAUTHORIZED",
                    "message": "Требуется авторизация"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )


# HTTP Bearer схема для Swagger UI
security = CustomHTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Получение текущего аутентифицированного пользователя из JWT токена.

    Args:
        credentials: Bearer токен из заголовка Authorization
        db: Асинхронная сессия базы данных

    Returns:
        User: Текущий пользователь

    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    # Извлечение токена
    token = credentials.credentials

    # Декодирование токена
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_TOKEN",
                "message": "Токен недействителен или истек"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Получение пользователя
    user = await AuthService.get_user_by_id(db, int(token_data.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "USER_NOT_FOUND",
                "message": "Пользователь не найден"
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# Типизированная зависимость для удобства
CurrentUser = Annotated[User, Depends(get_current_user)]