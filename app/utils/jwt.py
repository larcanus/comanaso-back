"""Утилиты для работы с JWT токенами."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import settings
from app.schemas.auth import TokenData


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает JWT access token.

    Args:
        data: Данные для включения в токен (обычно {"sub": user_id})
        expires_delta: Время жизни токена (по умолчанию из настроек)

    Returns:
        Закодированный JWT токен
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,  # Используем secret_key вместо JWT_SECRET
        algorithm=settings.algorithm  # Используем algorithm вместо JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Декодирует и валидирует JWT токен.

    Args:
        token: JWT токен

    Returns:
        TokenData с user_id и username или None если токен невалиден
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,  # Используем secret_key вместо JWT_SECRET
            algorithms=[settings.algorithm]  # Используем algorithm вместо JWT_ALGORITHM
        )
        user_id: str = payload.get("sub")
        username: str = payload.get("username")

        if user_id is None:
            return None

        return TokenData(user_id=int(user_id), username=username)

    except JWTError:
        return None
    except ValueError:
        return None