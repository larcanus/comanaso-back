"""
Pydantic схемы для Telegram Data API
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# COMMON SCHEMAS
# ============================================================================

class PhotoSchema(BaseModel):
    """Схема фото профиля"""
    photoId: str = Field(..., description="ID фото")
    dcId: int = Field(..., description="ID дата-центра")
    hasVideo: bool = Field(False, description="Есть ли видео аватар")


class StatusSchema(BaseModel):
    """Схема статуса пользователя"""
    type: str = Field(..., description="Тип статуса: online, offline, recently, lastWeek, lastMonth")
    wasOnline: Optional[str] = Field(None, description="Время последнего онлайна (ISO 8601)")


# ============================================================================
# ACCOUNT ME SCHEMAS
# ============================================================================

class AccountMeResponse(BaseModel):
    """Схема ответа с информацией об аккаунте"""
    id: int = Field(..., description="ID пользователя в Telegram")
    firstName: str = Field(..., description="Имя")
    lastName: str = Field("", description="Фамилия")
    username: Optional[str] = Field(None, description="Username")
    phone: Optional[str] = Field(None, description="Номер телефона")
    bio: Optional[str] = Field(None, description="Описание профиля")
    isBot: bool = Field(False, description="Является ли ботом")
    isVerified: bool = Field(False, description="Верифицирован ли аккаунт")
    isPremium: bool = Field(False, description="Есть ли Premium подписка")
    langCode: Optional[str] = Field(None, description="Код языка")
    photo: Optional[PhotoSchema] = Field(None, description="Фото профиля")
    status: StatusSchema = Field(..., description="Статус пользователя")


# ============================================================================
# DIALOGS SCHEMAS
# ============================================================================

class LastMessageSchema(BaseModel):
    """Схема последнего сообщения в диалоге"""
    id: int = Field(..., description="ID сообщения")
    text: str = Field("", description="Текст сообщения")
    date: Optional[str] = Field(None, description="Дата сообщения (ISO 8601)")
    fromId: Optional[int] = Field(None, description="ID отправителя")
    out: bool = Field(False, description="Исходящее сообщение")
    mentioned: bool = Field(False, description="Есть упоминание")
    mediaUnread: bool = Field(False, description="Медиа не просмотрено")
    silent: bool = Field(False, description="Тихое сообщение")


class UserEntitySchema(BaseModel):
    """Схема сущности пользователя/бота"""
    firstName: str = Field("", description="Имя")
    lastName: str = Field("", description="Фамилия")
    username: Optional[str] = Field(None, description="Username")
    phone: Optional[str] = Field(None, description="Номер телефона")
    isBot: bool = Field(False, description="Является ли ботом")
    isVerified: bool = Field(False, description="Верифицирован")
    isPremium: bool = Field(False, description="Premium подписка")
    isContact: bool = Field(False, description="В контактах")
    isMutualContact: bool = Field(False, description="Взаимный контакт")
    photo: Optional[PhotoSchema] = Field(None, description="Фото профиля")
    status: StatusSchema = Field(..., description="Статус")


class GroupEntitySchema(BaseModel):
    """Схема сущности группы"""
    title: str = Field(..., description="Название группы")
    participantsCount: int = Field(0, description="Количество участников")
    createdDate: Optional[str] = Field(None, description="Дата создания (ISO 8601)")
    isCreator: bool = Field(False, description="Является создателем")
    isAdmin: bool = Field(False, description="Является администратором")
    photo: Optional[PhotoSchema] = Field(None, description="Фото группы")


class ChannelEntitySchema(BaseModel):
    """Схема сущности канала/мегагруппы"""
    title: str = Field(..., description="Название канала")
    username: Optional[str] = Field(None, description="Username канала")
    participantsCount: int = Field(0, description="Количество подписчиков")
    createdDate: Optional[str] = Field(None, description="Дата создания (ISO 8601)")
    isCreator: bool = Field(False, description="Является создателем")
    isAdmin: bool = Field(False, description="Является администратором")
    isBroadcast: bool = Field(True, description="Является каналом (не мегагруппой)")
    isVerified: bool = Field(False, description="Верифицирован")
    isScam: bool = Field(False, description="Помечен как скам")
    isFake: bool = Field(False, description="Помечен как фейк")
    hasGeo: bool = Field(False, description="Имеет геолокацию")
    slowmodeEnabled: bool = Field(False, description="Включен медленный режим")
    photo: Optional[PhotoSchema] = Field(None, description="Фото канала")


class DialogSchema(BaseModel):
    """Схема диалога"""
    id: str = Field(..., description="ID диалога")
    name: str = Field(..., description="Название диалога")
    type: str = Field(..., description="Тип: user, bot, group, channel, megagroup")
    date: Optional[str] = Field(None, description="Дата последнего сообщения (ISO 8601)")
    unreadCount: int = Field(0, description="Количество непрочитанных")
    unreadMentionsCount: int = Field(0, description="Количество непрочитанных упоминаний")
    unreadReactionsCount: int = Field(0, description="Количество непрочитанных реакций")
    isArchived: bool = Field(False, description="В архиве")
    isPinned: bool = Field(False, description="Закреплен")
    isMuted: bool = Field(False, description="Отключены уведомления")
    folderId: Optional[int] = Field(None, description="ID папки")
    lastMessage: Optional[LastMessageSchema] = Field(None, description="Последнее сообщение")
    entity: Any = Field(..., description="Детали сущности (зависит от типа)")


class DialogsResponse(BaseModel):
    """Схема ответа со списком диалогов"""
    total: int = Field(..., description="Общее количество диалогов")
    hasMore: bool = Field(False, description="Есть ли еще диалоги")
    dialogs: List[DialogSchema] = Field(default_factory=list, description="Список диалогов")


# ============================================================================
# FOLDERS SCHEMAS
# ============================================================================

class FolderSchema(BaseModel):
    """Схема папки диалогов"""
    id: int = Field(..., description="ID папки (0 для дефолтной)")
    title: str = Field(..., description="Название папки")
    isDefault: bool = Field(False, description="Дефолтная папка")
    emoji: Optional[str] = Field(None, description="Эмодзи папки")
    pinnedDialogIds: List[str] = Field(default_factory=list, description="ID закрепленных диалогов")
    includedChatIds: List[str] = Field(default_factory=list, description="ID включенных чатов")
    excludedChatIds: List[str] = Field(default_factory=list, description="ID исключенных чатов")
    contacts: bool = Field(False, description="Включить контакты")
    nonContacts: bool = Field(False, description="Включить не-контакты")
    groups: bool = Field(False, description="Включить группы")
    broadcasts: bool = Field(False, description="Включить каналы")
    bots: bool = Field(False, description="Включить ботов")
    excludeMuted: bool = Field(False, description="Исключить беззвучные")
    excludeRead: bool = Field(False, description="Исключить прочитанные")
    excludeArchived: bool = Field(False, description="Исключить архивные")


class FoldersResponse(BaseModel):
    """Схема ответа со списком папок"""
    folders: List[FolderSchema] = Field(default_factory=list, description="Список папок")


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