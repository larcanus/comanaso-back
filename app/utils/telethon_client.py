import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    ApiIdInvalidError,
    PasswordHashInvalidError
)
from telethon.sessions import StringSession
from telethon import errors
from telethon.tl.types import (
    User, Chat, Channel,
    UserStatusOnline, UserStatusOffline, UserStatusRecently,
    UserStatusLastWeek, UserStatusLastMonth, UserStatusEmpty,
    UserProfilePhoto, ChatPhoto, MessageMediaPhoto,
    Dialog, DialogFilter, InputPeerEmpty, PeerUser, PeerChat, PeerChannel
)
from telethon.tl.functions.messages import GetDialogFiltersRequest

logger = logging.getLogger(__name__)


# Exceptions для маппинга в сервис/роутеры
class TelethonManagerError(Exception):
    """Базовое исключение для ошибок TelethonManager"""
    pass


class InvalidApiCredentials(TelethonManagerError):
    pass


class CodeRequired(TelethonManagerError):
    def __init__(self, phone_code_hash: str):
        super().__init__("code required")
        self.phone_code_hash = phone_code_hash


class PasswordRequired(TelethonManagerError):
    pass


class FloodWait(TelethonManagerError):
    def __init__(self, seconds: int):
        super().__init__(f"flood wait {seconds} seconds")
        self.seconds = seconds


class AlreadyConnected(TelethonManagerError):
    pass


class NotConnected(TelethonManagerError):
    pass


class InvalidCode(TelethonManagerError):
    pass


class ExpiredCode(TelethonManagerError):
    pass


class PhoneNumberInvalid(TelethonManagerError):
    pass


class InvalidPasswordError(TelethonManagerError):
    """Неверный 2FA пароль"""
    pass


class ExpiredCodeError(TelethonManagerError):
    """Код подтверждения истек"""
    pass


class TelethonManager:
    """Менеджер для управления Telethon клиентами (Singleton)"""

    _instance: Optional['TelethonManager'] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._clients: Dict[int, TelegramClient] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
        self._phone_code_hashes: Dict[int, str] = {}
        self._password_hints: Dict[int, Optional[str]] = {}
        self._logger = logger
        self._initialized = True
        logger.info("TelethonManager инициализирован (Singleton)")

    def _get_lock(self, account_id: int) -> asyncio.Lock:
        if account_id not in self._locks:
            self._locks[account_id] = asyncio.Lock()
        return self._locks[account_id]

    async def create_client(
            self,
            account_id: int,
            api_id: int,
            api_hash: str,
            session_string: Optional[str] = None,
    ) -> TelegramClient:
        """
        Создаёт и подключает TelegramClient (если ещё не создан).
        Не логирует session_string.
        """
        lock = self._get_lock(account_id)
        async with lock:
            existing = self._clients.get(account_id)
            if existing and getattr(existing, "is_connected", lambda: False)():
                raise AlreadyConnected("client already connected for account")

            try:
                session = StringSession(session_string) if session_string else StringSession()
                client = TelegramClient(session, api_id, api_hash)
                await client.connect()
                self._clients[account_id] = client
                return client
            except errors.rpcerrorlist.ApiIdInvalidError:
                raise InvalidApiCredentials("invalid api_id/api_hash")
            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("create_client error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

    async def send_code(self, account_id: int, phone: str) -> None:
        """
        Отправить код подтверждения на телефон и сохранить phone_code_hash

        Args:
            account_id: ID аккаунта
            phone: Номер телефона в международном формате
        """
        client = self._clients.get(account_id)
        if not client:
            raise TelethonManagerError(f"Клиент для аккаунта {account_id} не найден")

        try:
            result = await client.send_code_request(phone)
            self._phone_code_hashes[account_id] = result.phone_code_hash
            logger.info(f"Код отправлен для аккаунта {account_id}, phone_code_hash сохранен")
        except Exception as e:
            logger.error(f"Ошибка отправки кода для аккаунта {account_id}: {e}")
            raise TelethonManagerError(f"Не удалось отправить код: {str(e)}")

    async def sign_in_code(self, account_id: int, phone: str, code: str) -> str:
        """
        Войти используя код подтверждения

        Args:
            account_id: ID аккаунта
            phone: Номер телефона
            code: Код подтверждения из SMS

        Returns:
            session_string для сохранения в БД

        Raises:
            SessionPasswordNeededError: Требуется 2FA пароль
            PhoneCodeInvalidError: Неверный код
            ExpiredCodeError: Код истек
        """
        client = self._clients.get(account_id)
        if not client:
            raise TelethonManagerError(f"Клиент для аккаунта {account_id} не найден")

        phone_code_hash = self._phone_code_hashes.get(account_id)
        if not phone_code_hash:
            raise TelethonManagerError(
                f"phone_code_hash не найден для аккаунта {account_id}. Вызовите send_code сначала")

        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            session_string = client.session.save()

            # Очищаем phone_code_hash после успешного входа
            self._phone_code_hashes.pop(account_id, None)

            logger.info(f"Успешный вход для аккаунта {account_id}")
            return session_string
        except SessionPasswordNeededError:
            logger.info(f"Требуется 2FA для аккаунта {account_id}")
            raise PasswordRequired("2FA password required")
        except PhoneCodeInvalidError:
            logger.warning(f"Неверный код для аккаунта {account_id}")
            raise InvalidCode("Invalid phone code")
        except PhoneCodeExpiredError:
            logger.warning(f"Код истек для аккаунта {account_id}")
            self._phone_code_hashes.pop(account_id, None)
            raise ExpiredCodeError("Код истек, запросите новый")
        except Exception as e:
            logger.error(f"Ошибка входа для аккаунта {account_id}: {e}")
            raise TelethonManagerError(f"Не удалось войти: {str(e)}")

    async def get_password_hint(self, account_id: int) -> Optional[str]:
        """
        Получить подсказку для 2FA пароля

        Args:
            account_id: ID аккаунта

        Returns:
            Подсказка для пароля или None
        """
        client = self._clients.get(account_id)
        if not client:
            raise TelethonManagerError(f"Клиент для аккаунта {account_id} не найден")

        try:
            password_info = await client.get_password()
            hint = password_info.hint if password_info else None
            logger.info(f"Password hint для аккаунта {account_id}: {hint or 'отсутствует'}")
            return hint
        except Exception as e:
            logger.error(f"Ошибка получения password hint для аккаунта {account_id}: {e}")
            return None

    async def sign_in_password(self, account_id: int, password: str) -> str:
        """
        Войти используя 2FA пароль

        Args:
            account_id: ID аккаунта
            password: 2FA пароль

        Returns:
            session_string для сохранения в БД

        Raises:
            InvalidPasswordError: Неверный пароль
            NotConnected: Клиент не в состоянии для 2FA (нужно сначала ввести код)
        """
        client = self._clients.get(account_id)
        if not client:
            raise NotConnected(f"Клиент для аккаунта {account_id} не найден")

        try:
            await client.sign_in(password=password)
            session_string = client.session.save()

            # Очищаем phone_code_hash после успешного входа
            self._phone_code_hashes.pop(account_id, None)

            logger.info(f"Успешный вход с 2FA для аккаунта {account_id}")
            return session_string
        except PasswordHashInvalidError:
            logger.warning(f"Неверный пароль для аккаунта {account_id}")
            raise InvalidPasswordError("Неверный пароль")
        except errors.FloodWaitError as e:
            raise FloodWait(int(getattr(e, "seconds", 0)))
        except Exception as e:
            error_msg = str(e)
            if "key is not registered" in error_msg.lower():
                logger.warning(f"Неверное состояние для 2FA аккаунта {account_id}: {error_msg}")
                raise NotConnected("Требуется сначала ввести код подтверждения")
            logger.error(f"Ошибка входа с 2FA для аккаунта {account_id}: {e}")
            raise TelethonManagerError(f"Не удалось войти с паролем: {error_msg}")

    async def disconnect(self, account_id: int) -> None:
        """
        Отключает клиента, не делая logout (не удаляет сессию в Telegram).
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.pop(account_id, None)
            if not client:
                raise NotConnected("no client to disconnect")
            try:
                await client.disconnect()
            except Exception as e:
                self._logger.debug("disconnect error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

    async def logout(self, account_id: int) -> None:
        """
        Выполняет logout в Telegram (удаляет сессию на сервере) и отключает.
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.pop(account_id, None)
            if not client:
                raise NotConnected("no client to logout")
            try:
                await client.log_out()
                await client.disconnect()
            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("logout error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))
            finally:
                self._phone_code_hashes.pop(account_id, None)

    def _parse_user_status(self, status) -> Dict[str, Any]:
        """Парсит статус пользователя в унифицированный формат"""
        if isinstance(status, UserStatusOnline):
            return {
                "type": "online",
                "wasOnline": None
            }
        elif isinstance(status, UserStatusOffline):
            return {
                "type": "offline",
                "wasOnline": status.was_online.isoformat() if status.was_online else None
            }
        elif isinstance(status, UserStatusRecently):
            return {
                "type": "recently",
                "wasOnline": None
            }
        elif isinstance(status, UserStatusLastWeek):
            return {
                "type": "lastWeek",
                "wasOnline": None
            }
        elif isinstance(status, UserStatusLastMonth):
            return {
                "type": "lastMonth",
                "wasOnline": None
            }
        else:
            return {
                "type": "offline",
                "wasOnline": None
            }

    def _parse_photo(self, photo) -> Optional[Dict[str, Any]]:
        """Парсит фото профиля в унифицированный формат"""
        if not photo:
            return None

        if isinstance(photo, (UserProfilePhoto, ChatPhoto)):
            return {
                "photoId": str(photo.photo_id),
                "dcId": photo.dc_id,
                "hasVideo": getattr(photo, "has_video", False)
            }
        return None

    def _parse_restriction_reasons(self, reasons) -> Optional[List[Dict[str, str]]]:
        """Парсит причины ограничений"""
        if not reasons:
            return None

        result = []
        for reason in reasons:
            result.append({
                "platform": getattr(reason, "platform", ""),
                "reason": getattr(reason, "reason", ""),
                "text": getattr(reason, "text", "")
            })
        return result if result else None

    def _parse_emoji_status(self, emoji_status) -> Optional[Dict[str, Any]]:
        """Парсит emoji статус"""
        if not emoji_status:
            return None

        return {
            "documentId": str(getattr(emoji_status, "document_id", "")),
            "until": getattr(emoji_status, "until", None)
        }

    def _parse_usernames(self, usernames) -> Optional[List[Dict[str, Any]]]:
        """Парсит множественные юзернеймы"""
        if not usernames:
            return None

        result = []
        for username_obj in usernames:
            result.append({
                "username": getattr(username_obj, "username", ""),
                "isEditable": getattr(username_obj, "editable", False),
                "isActive": getattr(username_obj, "active", False)
            })
        return result if result else None

    def _parse_peer_color(self, color) -> Optional[Dict[str, Any]]:
        """Парсит цвет профиля"""
        if not color:
            return None

        return {
            "color": getattr(color, "color", None),
            "backgroundEmojiId": str(getattr(color, "background_emoji_id", "")) if getattr(color, "background_emoji_id", None) else None
        }

    def _parse_entity_type(self, entity) -> str:
        """Определяет тип entity"""
        if isinstance(entity, User):
            return "user"
        elif isinstance(entity, Chat):
            return "group"
        elif isinstance(entity, Channel):
            return "channel" if entity.broadcast else "supergroup"
        return "unknown"

    def _get_entity_id(self, entity) -> Optional[int]:
        """Безопасно получает ID entity"""
        if isinstance(entity, (User, Chat, Channel)):
            return entity.id
        return None

    async def get_me(self, account_id: int) -> Dict[str, Any]:
        """
        Получить полную информацию о текущем пользователе

        Returns:
            Словарь со всеми доступными полями пользователя
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created")

            try:
                if not await client.is_user_authorized():
                    raise NotConnected("client not authorized")

                # Получаем базовую информацию
                me = await client.get_me()

                # Получаем полную информацию пользователя (включая lang_code)
                full_user = await client.get_entity("me")

                # Базовые поля
                result = {
                    "id": me.id,

                    # Имена и идентификаторы
                    "firstName": me.first_name or "",
                    "lastName": me.last_name or "",
                    "username": me.username,
                    "phone": me.phone,
                    "langCode": getattr(full_user, "lang_code", None) or getattr(me, "lang_code", None),

                    # Флаги статуса
                    "isSelf": getattr(me, "is_self", True),
                    "isContact": getattr(me, "contact", False),
                    "isMutualContact": getattr(me, "mutual_contact", False),
                    "isDeleted": getattr(me, "deleted", False),
                    "isBot": me.bot,
                    "isBotChatHistory": getattr(me, "bot_chat_history", False),
                    "isBotNochats": getattr(me, "bot_nochats", False),
                    "isVerified": me.verified,
                    "isRestricted": getattr(me, "restricted", False),
                    "isMin": getattr(me, "min", False),
                    "isBotInlineGeo": getattr(me, "bot_inline_geo", False),
                    "isSupport": getattr(me, "support", False),
                    "isScam": getattr(me, "scam", False),
                    "isFake": getattr(me, "fake", False),
                    "isPremium": getattr(me, "premium", False),
                    "isBotAttachMenu": getattr(me, "bot_attach_menu", False),
                    "isAttachMenuEnabled": getattr(me, "attach_menu_enabled", False),
                    "isBotCanEdit": getattr(me, "bot_can_edit", False),
                    "isCloseFriend": getattr(me, "close_friend", False),
                    "isStoriesHidden": getattr(me, "stories_hidden", False),
                    "isStoriesUnavailable": getattr(me, "stories_unavailable", False),
                    "isContactRequirePremium": getattr(me, "contact_require_premium", False),
                    "isBotBusiness": getattr(me, "bot_business", False),
                    "isBotHasMainApp": getattr(me, "bot_has_main_app", False),
                    "isApplyMinPhoto": getattr(me, "apply_min_photo", False),

                    # Медиа
                    "photo": self._parse_photo(me.photo),
                    "status": self._parse_user_status(me.status),

                    # Боты
                    "botInfoVersion": getattr(me, "bot_info_version", None),
                    "botInlinePlaceholder": getattr(me, "bot_inline_placeholder", None),
                    "botActiveUsers": getattr(me, "bot_active_users", None),

                    # Ограничения
                    "restrictionReason": self._parse_restriction_reasons(getattr(me, "restriction_reason", None)),

                    # Emoji статус
                    "emojiStatus": self._parse_emoji_status(getattr(me, "emoji_status", None)),

                    # Множественные юзернеймы
                    "usernames": self._parse_usernames(getattr(me, "usernames", None)),

                    # Stories
                    "storiesMaxId": getattr(me, "stories_max_id", None),

                    # Цвета профиля
                    "color": self._parse_peer_color(getattr(me, "color", None)),
                    "profileColor": self._parse_peer_color(getattr(me, "profile_color", None)),
                }

                return result

            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.error(f"get_me error: {type(e).__name__}: {e}")
                raise TelethonManagerError(str(e))

    async def get_dialogs_extended(
            self,
            account_id: int,
            limit: int = 100,
            offset: int = 0,
            archived: bool = False
    ) -> Dict[str, Any]:
        """
        Получить расширенный список диалогов с полной информацией

        Args:
            account_id: ID аккаунта
            limit: Количество диалогов (max 500)
            offset: Смещение для пагинации
            archived: Включить архивные диалоги

        Returns:
            Словарь с диалогами и метаданными
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created")

            try:
                if not await client.is_user_authorized():
                    raise NotConnected("client not authorized")

                # В Telethon 1.42.0 убрали параметр offset_peer
                # Используем только offset_date и offset_id
                dialogs = await client.get_dialogs(
                    limit=limit,
                    archived=archived
                )

                result_dialogs = []
                for dialog in dialogs:
                    entity = dialog.entity

                    # Проверяем notify_settings для muted
                    notify_settings = getattr(dialog, "notify_settings", None)
                    is_muted = bool(getattr(notify_settings, "mute_until", None)) if notify_settings else False

                    # Получаем ID entity безопасно
                    entity_id = self._get_entity_id(entity)
                    entity_type = self._parse_entity_type(entity)

                    # Базовая информация о диалоге
                    dialog_data = {
                        "id": str(entity_id) if entity_id else "0",
                        "name": getattr(dialog, "name", None) or getattr(dialog, "title", ""),
                        "date": dialog.date.isoformat() if getattr(dialog, "date", None) else None,
                        "unreadCount": getattr(dialog, "unread_count", 0),
                        "unreadMentionsCount": getattr(dialog, "unread_mentions_count", 0),
                        "unreadReactionsCount": getattr(dialog, "unread_reactions_count", 0),
                        "isArchived": getattr(dialog, "archived", False),
                        "isPinned": getattr(dialog, "pinned", False),
                        "isMuted": is_muted,
                        "folderId": getattr(dialog, "folder_id", None),
                        "type": entity_type,
                    }

                    # Информация о entity
                    if isinstance(entity, User):
                        dialog_data["entity"] = {
                            "id": entity.id,
                            "firstName": entity.first_name or "",
                            "lastName": entity.last_name or "",
                            "username": entity.username,
                            "phone": entity.phone,
                            "isBot": entity.bot,
                            "isVerified": entity.verified,
                            "isPremium": getattr(entity, "premium", False),
                            "photo": self._parse_photo(entity.photo),
                            "status": self._parse_user_status(entity.status)
                        }
                    elif isinstance(entity, (Chat, Channel)):
                        dialog_data["entity"] = {
                            "id": entity.id,
                            "title": entity.title,
                            "username": getattr(entity, "username", None),
                            "participantsCount": getattr(entity, "participants_count", None),
                            "isVerified": getattr(entity, "verified", False),
                            "isScam": getattr(entity, "scam", False),
                            "isFake": getattr(entity, "fake", False),
                            "photo": self._parse_photo(getattr(entity, "photo", None))
                        }

                    # Последнее сообщение - ИСПРАВЛЕНО
                    msg = getattr(dialog, "message", None)
                    if msg:
                        from_id = getattr(msg, "from_id", None)
                        from_user_id = None

                        if from_id:
                            if isinstance(from_id, PeerUser):
                                from_user_id = from_id.user_id
                            elif isinstance(from_id, PeerChannel):
                                from_user_id = from_id.channel_id
                            elif isinstance(from_id, PeerChat):
                                from_user_id = from_id.chat_id

                        dialog_data["message"] = {
                            "id": msg.id,
                            "date": msg.date.isoformat() if msg.date else None,
                            "text": getattr(msg, "message", ""),
                            "out": msg.out,
                            "fromId": from_user_id,
                            "mediaType": type(msg.media).__name__ if msg.media else None,
                        }

                    result_dialogs.append(dialog_data)

                # Проверяем есть ли еще диалоги
                has_more = len(dialogs) == limit

                return {
                    "total": len(result_dialogs),
                    "hasMore": has_more,
                    "dialogs": result_dialogs
                }

            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.error(f"get_dialogs_extended error: {type(e).__name__}: {e}")
                raise TelethonManagerError(str(e))

    async def get_folders(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Получить список папок (фильтров) диалогов

        Returns:
            Список папок с настройками
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created")

            try:
                if not await client.is_user_authorized():
                    raise NotConnected("client not authorized")

                # Получаем фильтры диалогов
                filters_result = await client(GetDialogFiltersRequest())

                folders = []

                # Добавляем дефолтную папку "Все чаты"
                folders.append({
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
                })

                # Парсим фильтры из Telegram
                if hasattr(filters_result, 'filters'):
                    for filter_obj in filters_result.filters:
                        if isinstance(filter_obj, DialogFilter):
                            # Извлекаем title - ИСПРАВЛЕНО для Telethon 1.42.0
                            title = filter_obj.title
                            if hasattr(title, 'text'):
                                # title это TextWithEntities объект
                                title = title.text
                            elif not isinstance(title, str):
                                # На всякий случай конвертируем в строку
                                title = str(title)

                            # Собираем ID чатов
                            pinned_ids = [str(peer.user_id if hasattr(peer, 'user_id')
                                             else peer.channel_id if hasattr(peer, 'channel_id')
                                             else peer.chat_id)
                                         for peer in getattr(filter_obj, 'pinned_peers', [])]

                            included_ids = [str(peer.user_id if hasattr(peer, 'user_id')
                                              else peer.channel_id if hasattr(peer, 'channel_id')
                                              else peer.chat_id)
                                          for peer in getattr(filter_obj, 'include_peers', [])]

                            excluded_ids = [str(peer.user_id if hasattr(peer, 'user_id')
                                              else peer.channel_id if hasattr(peer, 'channel_id')
                                              else peer.chat_id)
                                          for peer in getattr(filter_obj, 'exclude_peers', [])]

                            folders.append({
                                "id": filter_obj.id,
                                "title": title,  # Используем извлеченную строку
                                "isDefault": False,
                                "emoji": getattr(filter_obj, "emoticon", None),
                                "pinnedDialogIds": pinned_ids,
                                "includedChatIds": included_ids,
                                "excludedChatIds": excluded_ids,
                                "contacts": getattr(filter_obj, "contacts", False),
                                "nonContacts": getattr(filter_obj, "non_contacts", False),
                                "groups": getattr(filter_obj, "groups", False),
                                "broadcasts": getattr(filter_obj, "broadcasts", False),
                                "bots": getattr(filter_obj, "bots", False),
                                "excludeMuted": getattr(filter_obj, "exclude_muted", False),
                                "excludeRead": getattr(filter_obj, "exclude_read", False),
                                "excludeArchived": getattr(filter_obj, "exclude_archived", False)
                            })

                return folders

            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.error(f"get_folders error: {type(e).__name__}: {e}")
                raise TelethonManagerError(str(e))

    async def get_dialogs(self, account_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Возвращает упрощённый список диалогов для front-end:
        [{'id': id, 'title': '...', 'username': '...', 'unread_count': N}, ...]
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created")
            try:
                if not await client.is_user_authorized():
                    raise NotConnected("client not authorized")

                dialogs = await client.get_dialogs(limit=limit)
                result = []

                for d in dialogs:
                    ent = getattr(d, "entity", None)
                    if not ent:
                        continue

                    uid = self._get_entity_id(ent)
                    title = getattr(d, "title", None) or getattr(ent, "title", None) or getattr(ent, "first_name", None)
                    username = getattr(ent, "username", None)
                    unread = getattr(d, "unread_count", 0)

                    result.append({
                        "id": uid,
                        "title": title,
                        "username": username,
                        "unread_count": unread
                    })

                return result
            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("get_dialogs error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

    async def get_common_data(self, account_id: int) -> Dict[str, Any]:
        """
        Получить общие данные о клиенте (авторизован ли и т.д.)
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                return {"authorized": False}
            try:
                authorized = await client.is_user_authorized()
                return {"authorized": authorized}
            except Exception:
                return {"authorized": False}

    async def disconnect_all(self) -> None:
        """
        Отключает все активные клиенты и очищает внутренний словарь.
        Не логирует чувствительные данные (session_string).
        """
        items = list(self._clients.items())
        errors = []
        for account_id, client in items:
            lock = self._get_lock(account_id)
            try:
                async with lock:
                    try:
                        # Пытаемся корректно отключить клиент
                        await client.disconnect()
                    except Exception as e:
                        # Не выбрасываем наружу — собираем и логируем
                        self._logger.debug("disconnect_all: error disconnecting account %s: %s", account_id,
                                           type(e).__name__)
                        errors.append((account_id, str(e)))
                    finally:
                        # Удаляем клиент из словаря независимо от результата
                        self._clients.pop(account_id, None)
            except Exception as e:
                self._logger.debug("disconnect_all: lock error for account %s: %s", account_id, type(e).__name__)
                errors.append((account_id, str(e)))

        if errors:
            self._logger.warning("disconnect_all completed with errors for accounts: %s", [a for a, _ in errors])

    async def download_profile_photo(self, account_id: int, size: str = "big") -> Optional[bytes]:
        """
        Скачать фото профиля текущего пользователя.

        Args:
            account_id: ID аккаунта
            size: Размер фото ("small" для маленького, "big" для большого)

        Returns:
            bytes: Бинарные данные изображения или None если фото не установлено

        Raises:
            NotConnected: Клиент не подключен
            TelethonManagerError: Ошибка при скачивании фото
        """
        client = self._clients.get(account_id)
        if not client:
            raise NotConnected("client not created")
        try:
            if not await client.is_user_authorized():
                raise NotConnected("client not authorized")
            me = await client.get_me()

            # Проверяем наличие фото
            if not me.photo:
                return None

            # Определяем размер для скачивания
            # small = True для маленького размера, False для большого
            download_big = (size == "big")

            # Скачиваем фото в память
            photo_bytes = await client.download_profile_photo(
                me,
                file=bytes,  # Скачиваем в байты, а не в файл
                download_big=download_big
            )

            return photo_bytes

        except errors.FloodWaitError as e:
            raise FloodWait(int(getattr(e, "seconds", 0)))
        except Exception as e:
            self._logger.error(f"Error downloading profile photo for account {account_id}: {type(e).__name__} - {e}")
            raise TelethonManagerError(f"Failed to download profile photo: {str(e)}")
