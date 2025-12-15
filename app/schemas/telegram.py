"""
Pydantic схемы для Telegram API.
Схемы для получения данных: профиль, диалоги, папки и соединения аккаунта.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime


class PhotoSchema(BaseModel):
    """Схема фото профиля/чата."""
    photoId: str
    dcId: int
    hasVideo: bool = False


class UserStatusSchema(BaseModel):
    """Схема статуса пользователя."""
    type: Literal["online", "offline", "recently", "lastWeek", "lastMonth"]
    wasOnline: Optional[datetime] = None


# ============================================================================
# 4.1 GET /api/accounts/{accountId}/me
# ============================================================================

class AccountMeResponse(BaseModel):
    """Ответ с информацией об аккаунте."""
    id: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    username: Optional[str] = None
    phone: str
    bio: Optional[str] = None
    isBot: bool = False
    isVerified: bool = False
    isPremium: bool = False
    langCode: Optional[str] = None
    photo: Optional[PhotoSchema] = None
    status: Optional[UserStatusSchema] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123456789",
                "firstName": "Иван",
                "lastName": "Петров",
                "username": "ivan_petrov",
                "phone": "+79991234567",
                "bio": "Работаю в IT",
                "isBot": False,
                "isVerified": False,
                "isPremium": False,
                "langCode": "ru",
                "photo": {
                    "photoId": "123456789012345678",
                    "dcId": 2,
                    "hasVideo": False
                },
                "status": {
                    "type": "online",
                    "wasOnline": None
                }
            }
        }
    }


# ============================================================================
# 4.2 GET /api/accounts/{accountId}/dialogs
# ============================================================================

class LastMessageSchema(BaseModel):
    """Последнее сообщение в диалоге."""
    id: int
    text: Optional[str] = None
    date: datetime
    fromId: Optional[int] = None
    out: bool
    mentioned: bool = False
    mediaUnread: bool = False
    silent: bool = False


class EntityUserSchema(BaseModel):
    """Детали пользователя/бота."""
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    isBot: bool = False
    isVerified: bool = False
    isPremium: bool = False
    isContact: bool = False
    isMutualContact: bool = False
    photo: Optional[PhotoSchema] = None
    status: Optional[UserStatusSchema] = None


class EntityGroupSchema(BaseModel):
    """Детали группы."""
    title: str
    participantsCount: int
    createdDate: Optional[datetime] = None
    isCreator: bool = False
    isAdmin: bool = False
    photo: Optional[PhotoSchema] = None


class EntityChannelSchema(BaseModel):
    """Детали канала/мегагруппы."""
    title: str
    username: Optional[str] = None
    participantsCount: Optional[int] = None
    createdDate: Optional[datetime] = None
    isCreator: bool = False
    isAdmin: bool = False
    isBroadcast: bool = True
    isVerified: bool = False
    isScam: bool = False
    isFake: bool = False
    hasGeo: bool = False
    slowmodeEnabled: bool = False
    photo: Optional[PhotoSchema] = None


class DialogSchema(BaseModel):
    """Схема одного диалога."""
    id: str
    name: str
    type: Literal["user", "bot", "group", "channel", "megagroup"]
    date: datetime

    # Счётчики
    unreadCount: int = 0
    unreadMentionsCount: int = 0
    unreadReactionsCount: int = 0

    # Статусы
    isArchived: bool = False
    isPinned: bool = False
    isMuted: bool = False

    # Папка
    folderId: Optional[int] = None

    # Последнее сообщение
    lastMessage: Optional[LastMessageSchema] = None

    # Детали сущности (union type)
    entity: EntityUserSchema | EntityGroupSchema | EntityChannelSchema


class DialogsResponse(BaseModel):
    """Ответ со списком диалогов."""
    total: int
    hasMore: bool
    dialogs: List[DialogSchema]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 150,
                "hasMore": True,
                "dialogs": [
                    {
                        "id": "1234567890",
                        "name": "Иван Петров",
                        "type": "user",
                        "date": "2024-01-17T15:30:00Z",
                        "unreadCount": 3,
                        "unreadMentionsCount": 1,
                        "unreadReactionsCount": 0,
                        "isArchived": False,
                        "isPinned": True,
                        "isMuted": False,
                        "folderId": None,
                        "lastMessage": {
                            "id": 12345,
                            "text": "Привет, как дела?",
                            "date": "2024-01-17T15:30:00Z",
                            "fromId": 987654321,
                            "out": False,
                            "mentioned": False,
                            "mediaUnread": False,
                            "silent": False
                        },
                        "entity": {
                            "firstName": "Иван",
                            "lastName": "Петров",
                            "username": "ivan_petrov",
                            "phone": "+79991234567",
                            "isBot": False,
                            "isVerified": False,
                            "isPremium": False,
                            "isContact": True,
                            "isMutualContact": True,
                            "photo": {
                                "photoId": "123456789012345678",
                                "dcId": 2,
                                "hasVideo": False
                            },
                            "status": {
                                "type": "online",
                                "wasOnline": None
                            }
                        }
                    }
                ]
            }
        }
    }


# ============================================================================
# 4.3 GET /api/accounts/{accountId}/folders
# ============================================================================

class FolderSchema(BaseModel):
    """Схема папки Telegram."""
    id: int
    title: str
    isDefault: bool = False
    emoji: Optional[str] = None
    pinnedDialogIds: List[str] = Field(default_factory=list)
    includedChatIds: List[str] = Field(default_factory=list)
    excludedChatIds: List[str] = Field(default_factory=list)
    contacts: bool = False
    nonContacts: bool = False
    groups: bool = False
    broadcasts: bool = False
    bots: bool = False
    excludeMuted: bool = False
    excludeRead: bool = False
    excludeArchived: bool = False
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Работа",
                "isDefault": False,
                "emoji": "💼",
                "pinnedDialogIds": ["1234567890", "9876543210"],
                "includedChatIds": ["1234567890", "9876543210", "5555555555"],
                "excludedChatIds": [],
                "contacts": False,
                "nonContacts": False,
                "groups": True,
                "broadcasts": False,
                "bots": False,
                "excludeMuted": False,
                "excludeRead": False,
                "excludeArchived": True
            }
        }
    }


class FoldersResponse(BaseModel):
    """Ответ со списком папок."""
    folders: List[FolderSchema] = Field(default_factory=list)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "folders": [
                    {
                        "id": 0,
                        "title": "Все чаты",
                        "isDefault": True,
                        "emoji": None,
                        "pinnedDialogIds": [],
                        "includedChatIds": [],
                        "excludedChatIds": [],
                        "contacts": False,
                        "nonContacts": False,
                        "groups": False,
                        "broadcasts": False,
                        "bots": False,
                        "excludeMuted": False,
                        "excludeRead": False,
                        "excludeArchived": False
                    },
                    {
                        "id": 1,
                        "title": "Работа",
                        "isDefault": False,
                        "emoji": "💼",
                        "pinnedDialogIds": ["1234567890"],
                        "includedChatIds": ["1234567890", "9876543210"],
                        "excludedChatIds": [],
                        "contacts": False,
                        "nonContacts": False,
                        "groups": True,
                        "broadcasts": False,
                        "bots": False,
                        "excludeMuted": False,
                        "excludeRead": False,
                        "excludeArchived": True
                    }
                ]
            }
        }
    }




# ============================================================================
# Схемы ошибок
# ============================================================================

class ErrorResponse(BaseModel):
    """Схема ответа с ошибкой."""
    error: str
    message: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ACCOUNT_NOT_FOUND",
                "message": "Аккаунт не найден"
            }
        }
    }