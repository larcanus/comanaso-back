"""
Pydantic схемы для аутентификации.
Валидация данных для регистрации, логина и токенов.
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


class UserRegister(BaseModel):
    """
    Схема для регистрации нового пользователя.

    Attributes:
        login: Логин пользователя (email или username, 3-50 символов)
        password: Пароль (минимум 8 символов)
    """

    login: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Логин пользователя (email или username)",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Пароль (минимум 8 символов)",
        example="SecurePass123!"
    )

    @validator("login")
    def validate_login(cls, v):
        """Валидация логина - приводим к нижнему регистру."""
        return v.lower().strip()

    @validator("password")
    def validate_password(cls, v):
        """Валидация пароля."""
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        return v


class UserLogin(BaseModel):
    """
    Схема для входа пользователя.

    Attributes:
        login: Логин пользователя (email или username)
        password: Пароль
    """

    login: str = Field(
        ...,
        description="Логин пользователя (email или username)",
        example="user@example.com"
    )
    password: str = Field(
        ...,
        description="Пароль",
        example="SecurePass123!"
    )


class Token(BaseModel):
    """
    Схема JWT токена.

    Attributes:
        access_token: JWT токен доступа
        token_type: Тип токена (всегда "bearer")
    """

    access_token: str = Field(
        ...,
        description="JWT токен доступа"
    )
    token_type: str = Field(
        default="bearer",
        description="Тип токена"
    )


class TokenData(BaseModel):
    """
    Схема данных из JWT токена.

    Attributes:
        user_id: ID пользователя
        username: Имя пользователя
    """

    user_id: int | None = None
    username: str | None = None


class UserResponse(BaseModel):
    """
    Схема ответа с данными пользователя.

    Attributes:
        id: ID пользователя
        email: Email (может быть None)
        username: Имя пользователя
        is_active: Активен ли пользователь
        created_at: Дата создания
    """

    id: int
    email: str | None = None
    username: str
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "username": "john_doe",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00"
            }
        }
    }
