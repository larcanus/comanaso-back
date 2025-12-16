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
    Dialog, DialogFilter, InputPeerEmpty
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
                # Общая ошибка от Telethon -> оборачиваем
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
            # Очищаем истекший phone_code_hash
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
            # "The key is not registered" означает что клиент не в правильном состоянии
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
                # Очищаем phone_code_hash если был
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

    async def get_me(self, account_id: int) -> Dict[str, Any]:
        """
        Получить информацию о текущем пользователе

        Returns:
            Словарь с информацией о пользователе
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created")

            try:
                if not await client.is_user_authorized():
                    raise NotConnected("client not authorized")

                me = await client.get_me()

                return {
                    "id": me.id,
                    "firstName": me.first_name or "",
                    "lastName": me.last_name or "",
                    "username": me.username,
                    "phone": me.phone,
                    "bio": getattr(me, "about", None),
                    "isBot": me.bot,
                    "isVerified": me.verified,
                    "isPremium": getattr(me, "premium", False),
                    "langCode": me.lang_code,
                    "photo": self._parse_photo(me.photo),
                    "status": self._parse_user_status(me.status)
                }
            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("get_me error: %s", type(e).__name__)
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

                # Получаем диалоги с учетом offset
                dialogs = await client.get_dialogs(
                    limit=limit,
                    offset_date=None,
                    offset_id=0,
                    offset_peer=InputPeerEmpty(),
                    archived=archived
                )

                result_dialogs = []
                for dialog in dialogs:
                    entity = dialog.entity

                    # Проверяем notify_settings для muted
                    notify_settings = getattr(dialog, "notify_settings", None)
                    is_muted = bool(getattr(notify_settings, "mute_until", None)) if notify_settings else False

                    # Базовая информация о диалоге
                    dialog_data = {
                        "id": str(getattr(dialog, "id", 0)),
                        "name": getattr(dialog, "name", None) or getattr(dialog, "title", ""),
                        "date": dialog.date.isoformat() if getattr(dialog, "date", None) else None,
                        "unreadCount": getattr(dialog, "unread_count", 0),
                        "unreadMentionsCount": getattr(dialog, "unread_mentions_count", 0),
                        "unreadReactionsCount": getattr(dialog, "unread_reactions_count", 0),
                        "isArchived": getattr(dialog, "archived", False),
                        "isPinned": getattr(dialog, "pinned", False),
                        "isMuted": is_muted,
                        "folderId": getattr(dialog, "folder_id", None),
                    }

                    # Последнее сообщение
                    msg = getattr(dialog, "message", None)
                    if msg:
                        from_id = getattr(msg, "from_id", None)
                        from_user_id = getattr(from_id, "user_id", None) if from_id else None

                        dialog_data["lastMessage"] = {
                            "id": getattr(msg, "id", 0),
                            "text": getattr(msg, "message", "") or "",
                            "date": msg.date.isoformat() if getattr(msg, "date", None) else None,
                            "fromId": from_user_id,
                            "out": getattr(msg, "out", False),
                            "mentioned": getattr(msg, "mentioned", False),
                            "mediaUnread": getattr(msg, "media_unread", False),
                            "silent": getattr(msg, "silent", False)
                        }
                    else:
                        dialog_data["lastMessage"] = None

                    # Определяем тип и парсим entity с безопасными getattr
                    if isinstance(entity, User):
                        dialog_data["type"] = "bot" if getattr(entity, "bot", False) else "user"
                        dialog_data["entity"] = {
                            "firstName": getattr(entity, "first_name", "") or "",
                            "lastName": getattr(entity, "last_name", "") or "",
                            "username": getattr(entity, "username", None),
                            "phone": getattr(entity, "phone", None),
                            "isBot": getattr(entity, "bot", False),
                            "isVerified": getattr(entity, "verified", False),
                            "isPremium": getattr(entity, "premium", False),
                            "isContact": getattr(entity, "contact", False),
                            "isMutualContact": getattr(entity, "mutual_contact", False),
                            "photo": self._parse_photo(getattr(entity, "photo", None)),
                            "status": self._parse_user_status(getattr(entity, "status", None))
                        }
                    elif isinstance(entity, Chat):
                        dialog_data["type"] = "group"
                        entity_date = getattr(entity, "date", None)
                        dialog_data["entity"] = {
                            "title": getattr(entity, "title", ""),
                            "participantsCount": getattr(entity, "participants_count", 0),
                            "createdDate": entity_date.isoformat() if entity_date else None,
                            "isCreator": getattr(entity, "creator", False),
                            "isAdmin": getattr(entity, "admin_rights", None) is not None,
                            "photo": self._parse_photo(getattr(entity, "photo", None))
                        }
                    elif isinstance(entity, Channel):
                        is_broadcast = getattr(entity, "broadcast", False)
                        dialog_data["type"] = "channel" if is_broadcast else "megagroup"
                        entity_date = getattr(entity, "date", None)
                        dialog_data["entity"] = {
                            "title": getattr(entity, "title", ""),
                            "username": getattr(entity, "username", None),
                            "participantsCount": getattr(entity, "participants_count", 0),
                            "createdDate": entity_date.isoformat() if entity_date else None,
                            "isCreator": getattr(entity, "creator", False),
                            "isAdmin": getattr(entity, "admin_rights", None) is not None,
                            "isBroadcast": is_broadcast,
                            "isVerified": getattr(entity, "verified", False),
                            "isScam": getattr(entity, "scam", False),
                            "isFake": getattr(entity, "fake", False),
                            "hasGeo": getattr(entity, "has_geo", False),
                            "slowmodeEnabled": getattr(entity, "slowmode_enabled", False),
                            "photo": self._parse_photo(getattr(entity, "photo", None))
                        }

                    result_dialogs.append(dialog_data)

                # Проверяем есть ли еще диалоги
                has_more = len(dialogs) == limit

                return {
                    "total": len(result_dialogs),  # В реальности нужен общий count
                    "hasMore": has_more,
                    "dialogs": result_dialogs
                }

            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("get_dialogs_extended error: %s", type(e).__name__)
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
                result = await client(GetDialogFiltersRequest())

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

                # Парсим пользовательские папки
                for dialog_filter in result:
                    if isinstance(dialog_filter, DialogFilter):
                        folder_data = {
                            "id": dialog_filter.id,
                            "title": dialog_filter.title,
                            "isDefault": False,
                            "emoji": getattr(dialog_filter, "emoticon", None),
                            "pinnedDialogIds": [str(p.user_id if hasattr(p, "user_id") else p.channel_id)
                                              for p in dialog_filter.pinned_peers],
                            "includedChatIds": [str(p.user_id if hasattr(p, "user_id") else p.channel_id)
                                              for p in dialog_filter.include_peers],
                            "excludedChatIds": [str(p.user_id if hasattr(p, "user_id") else p.channel_id)
                                              for p in dialog_filter.exclude_peers],
                            "contacts": dialog_filter.contacts,
                            "nonContacts": dialog_filter.non_contacts,
                            "groups": dialog_filter.groups,
                            "broadcasts": dialog_filter.broadcasts,
                            "bots": dialog_filter.bots,
                            "excludeMuted": dialog_filter.exclude_muted,
                            "excludeRead": dialog_filter.exclude_read,
                            "excludeArchived": dialog_filter.exclude_archived
                        }
                        folders.append(folder_data)

                return folders

            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("get_folders error: %s", type(e).__name__)
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
                    uid = getattr(ent, "id", None)
                    title = getattr(d, "title", None) or getattr(ent, "title", None) or getattr(ent, "first_name", None)
                    username = getattr(ent, "username", None)
                    unread = getattr(d, "unread_count", 0) or getattr(d, "unread_count", 0)
                    result.append({"id": uid, "title": title, "username": username, "unread_count": unread})
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
        # Копируем элементы, чтобы безопасно итерироваться и изменять dict
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