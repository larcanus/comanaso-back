"""
FastAPI dependencies для аутентификации и авторизации.
Кастомный HTTPBearer с правильным форматом ошибок и get_current_user.

Содержит:
- CustomHTTPBearer: Кастомная схема аутентификации с правильным форматом ошибок
- get_current_user: Зависимость для получения текущего пользователя из JWT токена
- CurrentUser: Типизированная зависимость для удобства использования в роутах
"""
from typing import Annotated, Any
from fastapi import Depends, HTTPException, status, Request, Path
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.http import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.account import Account
from app.models.user import User
from app.services import TelegramService
from app.utils.jwt import decode_access_token
from app.services.auth_service import AuthService
from app.utils.telethon_client import TelethonManager


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
                "error": "UNAUTHORIZED",
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

async def get_account(
    account_id: int = Path(..., description="ID аккаунта"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> Account:
    """
    Dependency: возвращает Account по account_id из path и проверяет, что он принадлежит current_user.
    Возвращает 404 если не найден, 403 если нет прав.
    """
    result = await db.execute(select(Account).filter(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Проверяем типичные поля владельца: user_id, owner_id или связанный объект user
    if getattr(account, "user_id", None) is not None:
        if account.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif getattr(account, "owner_id", None) is not None:
        if account.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    else:
        user_obj = getattr(account, "user", None)
        if user_obj is not None and getattr(user_obj, "id", None) != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return account


def get_telethon_manager(request: Request) -> TelethonManager:
    """
    Dependency: возвращает TelethonManager из app.state, создаёт один экземпляр при первом вызове.
    """
    tm = getattr(request.app.state, "telethon_manager", None)
    if tm is None:
        tm = TelethonManager()
        request.app.state.telethon_manager = tm
    return tm

def get_telegram_service(db: AsyncSession = Depends(get_db)) -> TelegramService:
    """Dependency для получения TelegramService"""
    tm = TelethonManager()
    return TelegramService(tm)

# Типизированная зависимость для удобства
CurrentUser = Annotated[User, Depends(get_current_user)]