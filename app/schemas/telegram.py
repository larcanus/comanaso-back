"""
Pydantic схемы для Telegram операций.
Валидация данных для работы с Telegram API.
"""
from pydantic import BaseModel, Field
from typing import List


class SendCodeRequest(BaseModel):
    """
    Схема запроса отправки кода подтверждения.
    
    Attributes:
        account_id: ID аккаунта
    """
    
    account_id: int = Field(
        ...,
        gt=0,
        description="ID Telegram аккаунта"
    )


class VerifyCodeRequest(BaseModel):
    """
    Схема запроса проверки кода подтверждения.
    
    Attributes:
        account_id: ID аккаунта
        code: Код подтверждения из Telegram
        password: 2FA пароль (если включен)
    """
    
    account_id: int = Field(
        ...,
        gt=0,
        description="ID Telegram аккаунта"
    )
    code: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="Код подтверждения из Telegram",
        example="12345"
    )
    password: str | None = Field(
        default=None,
        description="2FA пароль (если включен)",
        example="my2fapassword"
    )


class TelegramDialog(BaseModel):
    """
    Схема Telegram диалога.
    
    Attributes:
        id: ID диалога
        name: Имя диалога
        type: Тип (user/group/channel)
        unread_count: Количество непрочитанных
    """
    
    id: int
    name: str
    type: str = Field(
        ...,
        description="Тип диалога: user, group, channel"
    )
    unread_count: int = Field(
        default=0,
        ge=0,
        description="Количество непрочитанных сообщений"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 123456789,
                "name": "John Doe",
                "type": "user",
                "unread_count": 5
            }
        }
    }


class TelegramFolder(BaseModel):
    """
    Схема папки Telegram.
    
    Attributes:
        id: ID папки
        title: Название папки
        dialogs: Список диалогов в папке
    """
    
    id: int
    title: str
    dialogs: List[TelegramDialog] = Field(
        default_factory=list,
        description="Список диалогов в папке"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Работа",
                "dialogs": [
                    {
                        "id": 123456789,
                        "name": "Boss",
                        "type": "user",
                        "unread_count": 2
                    }
                ]
            }
        }
    }


class DialogsResponse(BaseModel):
    """
    Схема ответа со списком диалогов.
    
    Attributes:
        dialogs: Список всех диалогов
        folders: Список папок с диалогами
    """
    
    dialogs: List[TelegramDialog] = Field(
        default_factory=list,
        description="Все диалоги"
    )
    folders: List[TelegramFolder] = Field(
        default_factory=list,
        description="Папки с диалогами"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "dialogs": [
                    {
                        "id": 123456789,
                        "name": "John Doe",
                        "type": "user",
                        "unread_count": 5
                    }
                ],
                "folders": [
                    {
                        "id": 1,
                        "title": "Работа",
                        "dialogs": []
                    }
                ]
            }
        }
    }


class ConnectionStatusResponse(BaseModel):
    """
    Схема ответа со статусом подключения.
    
    Attributes:
        is_connected: Подключен ли аккаунт
        message: Сообщение о статусе
    """
    
    is_connected: bool
    message: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "is_connected": True,
                "message": "Account successfully connected"
            }
        }
    }