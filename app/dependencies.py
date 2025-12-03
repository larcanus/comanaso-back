"""FastAPI dependencies для аутентификации и авторизации."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.jwt import decode_access_token

# Схема безопасности для Bearer токена
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    Получает текущего аутентифицированного пользователя из JWT токена.
    
    Args:
        credentials: Bearer токен из заголовка Authorization
        db: Сессия базы данных
        
    Returns:
        Объект пользователя
        
    Raises:
        HTTPException: Если токен невалиден или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Декодируем токен
    token_data = decode_access_token(credentials.credentials)
    
    if token_data is None:
        raise credentials_exception
    
    # Получаем пользователя из БД
    user = await db.get(User, token_data.user_id)
    
    if user is None:
        raise credentials_exception
    
    return user


# Типизированная зависимость для использования в роутерах
CurrentUser = Annotated[User, Depends(get_current_user)]