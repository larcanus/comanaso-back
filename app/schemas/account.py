"""
Pydantic схемы для работы с Telegram аккаунтами.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, computed_field
import re


class AccountBase(BaseModel):
    """Базовая схема аккаунта с общими полями."""
    name: Optional[str] = Field(None, max_length=100, description="Имя аккаунта")


class AccountCreate(AccountBase):
    """Схема для создания нового аккаунта."""
    phone: str = Field(..., alias="phoneNumber", description="Номер телефона в международном формате")
    api_id: int = Field(..., alias="apiId", description="Telegram API ID")
    api_hash: str = Field(..., alias="apiHash", description="Telegram API Hash")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "phoneNumber": "+79991234567",
                "apiId": 12345678,
                "apiHash": "abcdef1234567890abcdef1234567890",
                "name": "My Account"
            }
        }
    }

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Валидация номера телефона."""
        if not re.match(r'^\+\d{10,15}$', v):
            raise ValueError('Номер телефона должен быть в формате +XXXXXXXXXXX')
        return v

    @field_validator('api_id')
    @classmethod
    def validate_api_id(cls, v: int) -> int:
        """Валидация API ID."""
        if v <= 0:
            raise ValueError('API ID должен быть положительным числом')
        return v

    @field_validator('api_hash')
    @classmethod
    def validate_api_hash(cls, v: str) -> str:
        """Валидация API Hash."""
        if not v or len(v) < 32:
            raise ValueError('API Hash должен содержать минимум 32 символа')
        return v


class AccountUpdate(AccountBase):
    """Схема для обновления аккаунта."""
    api_id: Optional[int] = Field(None, alias="apiId", description="Telegram API ID")
    api_hash: Optional[str] = Field(None, alias="apiHash", description="Telegram API Hash")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "Updated Account Name",
                "apiId": 87654321,
                "apiHash": "new_hash_1234567890abcdef1234567890ab"
            }
        }
    }

    @field_validator('api_id')
    @classmethod
    def validate_api_id(cls, v: Optional[int]) -> Optional[int]:
        """Валидация API ID."""
        if v is not None and v <= 0:
            raise ValueError('API ID должен быть положительным числом')
        return v

    @field_validator('api_hash')
    @classmethod
    def validate_api_hash(cls, v: Optional[str]) -> Optional[str]:
        """Валидация API Hash."""
        if v is not None and (not v or len(v) < 32):
            raise ValueError('API Hash должен содержать минимум 32 символа')
        return v


class AccountResponse(AccountBase):
    """Схема ответа со списком аккаунтов (полная информация)."""
    id: int
    phone: str = Field(..., serialization_alias="phoneNumber")
    api_id: int = Field(..., serialization_alias="apiId")
    api_hash: str = Field(..., serialization_alias="apiHash")
    status: str
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Рабочий аккаунт",
                "phoneNumber": "+79991234567",
                "apiId": "12345678",
                "apiHash": "abcdef1234567890abcdef1234567890",
                "status": "online",
                "createdAt": "2024-01-15T10:30:00Z",
                "updatedAt": "2024-01-15T12:45:00Z"
            }
        }
    }


class AccountDetailResponse(AccountResponse):
    """Схема детального ответа об аккаунте."""
    api_id: int = Field(..., serialization_alias="apiId")
    api_hash: str = Field(..., serialization_alias="apiHash")
    is_connected: bool = Field(..., serialization_alias="isConnected")
    created_at: datetime = Field(..., serialization_alias="createdAt")
    updated_at: Optional[datetime] = Field(None, serialization_alias="updatedAt")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class AccountListResponse(BaseModel):
    """Схема ответа со списком аккаунтов."""
    accounts: list[AccountResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "accounts": [
                    {
                        "id": 1,
                        "phoneNumber": "+79991234567",
                        "name": "My Account",
                        "status": "online",
                        "lastActivity": "2024-01-01T12:00:00Z"
                    }
                ],
                "total": 1
            }
        }
    }
