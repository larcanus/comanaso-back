"""
Pydantic схемы для аутентификации.
Валидация данных для регистрации, логина и токенов.
"""
from pydantic import BaseModel, Field, validator, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class UserSettings(BaseModel):
    """
    Схема настроек пользователя для AI.

    Attributes:
        shareUserName: Разрешить передачу имени пользователя (firstName, lastName)
        shareNickname: Разрешить передачу username (@nickname)
        shareMessageText: Разрешить передачу текста последних сообщений
        shareDialogTitles: Разрешить передачу названий диалогов
    """

    shareUserName: bool = Field(
        default=True,
        description="Разрешить передачу имени пользователя"
    )
    shareNickname: bool = Field(
        default=True,
        description="Разрешить передачу username"
    )
    shareMessageText: bool = Field(
        default=True,
        description="Разрешить передачу текста сообщений"
    )
    shareDialogTitles: bool = Field(
        default=True,
        description="Разрешить передачу названий диалогов"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "shareUserName": True,
                "shareNickname": True,
                "shareMessageText": True,
                "shareDialogTitles": True
            }
        }
    }


class UserRegister(BaseModel):
    """
    Схема для регистрации нового пользователя.

    Attributes:
        login: Логин пользователя (username, 3-50 символов)
        email: Email пользователя
        password: Пароль (минимум 6 символов)
    """

    login: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Логин пользователя (username)",
        example="john_doe"
    )
    email: EmailStr = Field(
        None,
        description="Email пользователя",
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

    @validator("email")
    def validate_email(cls, v):
        """Валидация email - приводим к нижнему регистру."""
        if v is not None:
            return v.lower().strip()
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
        login = user.username if user.username else user.email
        return cls(
            id=user.id,
            login=login,
            createdAt=user.created_at.isoformat() + "Z"
        )


class UserProfile(BaseModel):
    """
    Схема полного профиля пользователя (для /me).

    Attributes:
        id: ID пользователя
        username: Имя пользователя
        email: Email (может быть None)
        settings: Настройки пользователя
        createdAt: Дата создания (ISO 8601)
        updatedAt: Дата обновления (ISO 8601)
    """

    id: int
    username: str
    email: str | None = None
    settings: UserSettings
    createdAt: str
    updatedAt: str

    @classmethod
    def from_user(cls, user):
        """Создание из модели User."""
        return cls(
            id=user.id,
            username=user.username,
            email=user.email if user.email else None,
            settings=UserSettings(**user.settings),
            createdAt=user.created_at.isoformat() + "Z",
            updatedAt=user.updated_at.isoformat() + "Z"
        )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "username": "john_doe",
                "email": "user@example.com",
                "settings": {
                    "shareUserName": True,
                    "shareNickname": True,
                    "shareMessageText": True,
                    "shareDialogTitles": True
                },
                "createdAt": "2024-01-15T10:30:00Z",
                "updatedAt": "2024-01-17T15:30:00Z"
            }
        }
    }


class UpdateUserProfile(BaseModel):
    """
    Схема для обновления профиля пользователя.

    Attributes:
        username: Новое имя пользователя (опционально)
        email: Новый email (опционально)
        settings: Новые настройки (опционально)
    """

    username: str | None = Field(
        None,
        min_length=3,
        max_length=100,
        description="Новое имя пользователя"
    )
    email: EmailStr | None = Field(
        None,
        description="Новый email"
    )
    password: str | None = Field(
        None,
        min_length=6,
        description="Новый пароль (минимум 6 символов)"
    )
    settings: UserSettings | None = Field(
        None,
        description="Новые настройки пользователя"
    )

    @validator("username")
    def validate_username(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if len(v) < 3:
                raise ValueError('Username должен содержать минимум 3 символа')
        return v

    @validator("password")
    def validate_password(cls, v: str | None) -> str | None:
        if v is not None and len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "new_username",
                "email": "newemail@example.com",
                "password": "Password123456789",
                "settings": {
                    "shareUserName": False,
                    "shareNickname": True,
                    "shareMessageText": False,
                    "shareDialogTitles": True
                }
            }
        }
    }


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


class PasswordResetRequest(BaseModel):
    """
    Схема запроса сброса пароля.

    Attributes:
        email: Email пользователя
    """

    email: EmailStr = Field(
        ...,
        description="Email пользователя для сброса пароля"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com"
            }
        }
    }


class PasswordResetConfirm(BaseModel):
    """
    Схема подтверждения сброса пароля.

    Attributes:
        token: Токен сброса пароля
        new_password: Новый пароль
    """

    token: str = Field(
        ...,
        description="Токен сброса пароля из email"
    )
    new_password: str = Field(
        ...,
        min_length=6,
        description="Новый пароль (минимум 6 символов)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "token": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "new_password": "NewSecurePass123"
            }
        }
    }


class PasswordResetResponse(BaseModel):
    """
    Схема ответа при сбросе пароля.

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
                "message": "Инструкции по сбросу пароля отправлены на email"
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


class DeleteAccountResponse(BaseModel):
    """
    Схема ответа при удалении учетной записи.

    Attributes:
        status: Статус операции
        message: Сообщение о результате
        deleted_user_id: ID удаленного пользователя
        deleted_accounts_count: Количество удаленных Telegram аккаунтов
    """

    status: str = Field(
        ...,
        description="Статус операции"
    )
    message: str = Field(
        ...,
        description="Сообщение о результате"
    )
    deleted_user_id: int = Field(
        ...,
        description="ID удаленного пользователя"
    )
    deleted_accounts_count: int = Field(
        ...,
        description="Количество удаленных Telegram аккаунтов"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Учетная запись и все связанные данные успешно удалены",
                "deleted_user_id": 1,
                "deleted_accounts_count": 3
            }
        }
    }


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
