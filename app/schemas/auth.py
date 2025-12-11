"""
Pydantic схемы для аутентификации.
Валидация данных для регистрации, логина и токенов.
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime


class UserRegister(BaseModel):
    """
    Схема для регистрации нового пользователя.

    Attributes:
        login: Логин пользователя (email или username, 3-50 символов)
        password: Пароль (минимум 6 символов)
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
        min_length=6,
        max_length=100,
        description="Пароль (минимум 6 символов)",
        example="SecurePass123"
    )

    @validator("login")
    def validate_login(cls, v):
        """Валидация логина - приводим к нижнему регистру."""
        return v.lower().strip()


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
        example="SecurePass123"
    )


class UserData(BaseModel):
    """
    Схема данных пользователя для ответов API.

    Attributes:
        id: ID пользователя
        login: Логин пользователя
        createdAt: Дата создания (ISO 8601)
    """

    id: int
    login: str
    createdAt: str

    @classmethod
    def from_user(cls, user):
        """Создание из модели User."""
        login = user.email if user.email else user.username
        return cls(
            id=user.id,
            login=login,
            createdAt=user.created_at.isoformat() + "Z"
        )


class AuthResponse(BaseModel):
    """
    Схема ответа при регистрации/логине.

    Attributes:
        token: JWT токен доступа
        user: Данные пользователя
    """

    token: str = Field(
        ...,
        description="JWT токен доступа"
    )
    user: UserData = Field(
        ...,
        description="Данные пользователя"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": 1,
                    "login": "user123",
                    "createdAt": "2024-01-15T10:30:00Z"
                }
            }
        }
    }


class TokenVerifyResponse(BaseModel):
    """
    Схема ответа при проверке токена.

    Attributes:
        valid: Валидность токена
        user: Данные пользователя (если токен валиден)
    """

    valid: bool
    user: UserData | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "valid": True,
                "user": {
                    "id": 1,
                    "login": "user123"
                }
            }
        }
    }


class LogoutResponse(BaseModel):
    """
    Схема ответа при выходе из системы.

    Attributes:
        status: Статус операции
        message: Сообщение о результате
    """

    status: str = Field(
        ...,
        description="Статус операции"
    )
    message: str = Field(
        ...,
        description="Сообщение о результате"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Вы успешно вышли из системы"
            }
        }
    }


class ErrorResponse(BaseModel):
    """
    Стандартная схема ошибки.

    Attributes:
        error: Код ошибки
        message: Описание ошибки
    """

    error: str
    message: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Пароль должен содержать минимум 6 символов"
            }
        }
    }


# Старые схемы для обратной совместимости
class Token(BaseModel):
    """
    Схема JWT токена (deprecated, используйте AuthResponse).

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
    Схема ответа с данными пользователя (deprecated, используйте UserData).

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
