from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.security import decode_access_token
from app.services.auth_service import AuthService


# HTTP Bearer схема для Swagger UI
security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """
    Получение текущего аутентифицированного пользователя из JWT токена.
    
    Args:
        credentials: Bearer токен из заголовка Authorization
        db: Сессия базы данных
        
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
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Получение пользователя
    user = AuthService.get_user_by_id(db, int(token_data.user_id))
    return user


# Типизированная зависимость для удобства
CurrentUser = Annotated[User, Depends(get_current_user)]