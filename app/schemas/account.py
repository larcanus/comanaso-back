"""
Pydantic схемы для Telegram аккаунтов.
Валидация данных для управления аккаунтами.
"""
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


class AccountCreate(BaseModel):
    """
    Схема для добавления нового Telegram аккаунта.
    
    Attributes:
        phone: Номер телефона в международном формате
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        name: Имя аккаунта (опционально)
    """
    
    phone: str = Field(
        ...,
        description="Номер телефона в международном формате",
        example="+79991234567"
    )
    api_id: int = Field(
        ...,
        gt=0,
        description="Telegram API ID",
        example=12345678
    )
    api_hash: str = Field(
        ...,
        min_length=32,
        max_length=32,
        description="Telegram API Hash",
        example="0123456789abcdef0123456789abcdef"
    )
    name: str | None = Field(
        default=None,
        max_length=100,
        description="Имя аккаунта",
        example="Мой основной аккаунт"
    )
    
    @validator("phone")
    def validate_phone(cls, v):
        """Валидация номера телефона."""
        # Удаляем все символы кроме цифр и +
        phone = re.sub(r"[^\d+]", "", v)
        
        # Проверяем формат
        if not re.match(r"^\+\d{10,15}$", phone):
            raise ValueError(
                "Phone must be in international format (e.g., +79991234567)"
            )
        return phone
    
    @validator("api_hash")
    def validate_api_hash(cls, v):
        """Валидация API Hash."""
        if not re.match(r"^[a-f0-9]{32}$", v.lower()):
            raise ValueError("API Hash must be a 32-character hexadecimal string")
        return v.lower()


class AccountUpdate(BaseModel):
    """
    Схема для обновления данных аккаунта.
    
    Attributes:
        name: Новое имя аккаунта
        api_id: Новый API ID (опционально)
        api_hash: Новый API Hash (опционально)
    """
    
    name: str | None = Field(
        default=None,
        max_length=100,
        description="Имя аккаунта"
    )
    api_id: int | None = Field(
        default=None,
        gt=0,
        description="Telegram API ID"
    )
    api_hash: str | None = Field(
        default=None,
        min_length=32,
        max_length=32,
        description="Telegram API Hash"
    )
    
    @validator("api_hash")
    def validate_api_hash(cls, v):
        """Валидация API Hash."""
        if v is not None and not re.match(r"^[a-f0-9]{32}$", v.lower()):
            raise ValueError("API Hash must be a 32-character hexadecimal string")
        return v.lower() if v else v


class AccountResponse(BaseModel):
    """
    Схема ответа с данными аккаунта.
    
    Attributes:
        id: ID аккаунта
        phone: Номер телефона
        name: Имя аккаунта
        is_connected: Статус подключения
        last_activity: Время последней активности
        created_at: Дата добавления
    """
    
    id: int
    phone: str
    name: str | None
    is_connected: bool
    last_activity: datetime | None
    created_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "phone": "+79991234567",
                "name": "Мой основной аккаунт",
                "is_connected": True,
                "last_activity": "2024-01-15T10:30:00",
                "created_at": "2024-01-10T08:00:00"
            }
        }
    }


class AccountDetailResponse(AccountResponse):
    """
    Расширенная схема ответа с полными данными аккаунта.
    
    Attributes:
        api_id: Telegram API ID
        user_id: ID владельца
    """
    
    api_id: int
    user_id: int
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "phone": "+79991234567",
                "name": "Мой основной аккаунт",
                "is_connected": True,
                "last_activity": "2024-01-15T10:30:00",
                "created_at": "2024-01-10T08:00:00",
                "api_id": 12345678,
                "user_id": 1
            }
        }
    }


class AccountListResponse(BaseModel):
    """
    Схема ответа со списком аккаунтов.
    
    Attributes:
        accounts: Список аккаунтов
        total: Общее количество
    """
    
    accounts: list[AccountResponse]
    total: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "accounts": [
                    {
                        "id": 1,
                        "phone": "+79991234567",
                        "name": "Основной",
                        "is_connected": True,
                        "last_activity": "2024-01-15T10:30:00",
                        "created_at": "2024-01-10T08:00:00"
                    }
                ],
                "total": 1
            }
        }
    }