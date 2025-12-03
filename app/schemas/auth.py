"""
Pydantic схемы для аутентификации.
Валидация данных для регистрации, логина и токенов.
"""
from pydantic import BaseModel, EmailStr, Field, validator
import re


class UserRegister(BaseModel):
    """
    Схема для регистрации нового пользователя.
    
    Attributes:
        email: Email пользователя
        username: Имя пользователя (3-50 символов, только буквы, цифры, _, -)
        password: Пароль (минимум 8 символов)
    """
    
    email: EmailStr = Field(
        ...,
        description="Email пользователя",
        example="user@example.com"
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Имя пользователя",
        example="john_doe"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Пароль (минимум 8 символов)",
        example="SecurePass123!"
    )
    
    @validator("username")
    def validate_username(cls, v):
        """Валидация имени пользователя."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, underscores and hyphens"
            )
        return v.lower()
    
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
        username: Имя пользователя или email
        password: Пароль
    """
    
    username: str = Field(
        ...,
        description="Имя пользователя или email",
        example="john_doe"
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
        email: Email
        username: Имя пользователя
        is_active: Активен ли пользователь
        created_at: Дата создания
    """
    
    id: int
    email: str
    username: str
    is_active: bool
    created_at: str
    
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