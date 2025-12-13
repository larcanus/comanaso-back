import asyncio
import logging
from typing import Optional, Dict, Any, List

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
    """Менеджер для управления Telethon клиентами"""

    def __init__(self):
        self._clients: Dict[int, TelegramClient] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
        self._phone_code_hashes: Dict[int, str] = {}
        self._password_hints: Dict[int, Optional[str]] = {}
        self._logger = logger
        logger.info("TelethonManager инициализирован")

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
        """
        client = self._clients.get(account_id)
        if not client:
            raise TelethonManagerError(f"Клиент для аккаунта {account_id} не найден")

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
        except Exception as e:
            logger.error(f"Ошибка входа с 2FA для аккаунта {account_id}: {e}")
            raise TelethonManagerError(f"Не удалось войти с паролем: {str(e)}")

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

    async def get_folders(self, account_id: int) -> Dict[str, Any]:
        """
        Простейшая заглушка для получения папок (можно расширить).
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created")
            try:
                if not await client.is_user_authorized():
                    raise NotConnected("client not authorized")
                # Telethon: client.get_dialogs has folders в более сложном виде; возвращаем count и простую структуру
                dialogs = await client.get_dialogs(limit=1)
                # Возвращаем минимальные данные; расширить по необходимости
                return {"folders_count": 0, "sample_dialogs": len(dialogs)}
            except Exception as e:
                self._logger.debug("get_folders error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

    async def get_common_data(self, account_id: int) -> Dict[str, Any]:
        """
        Возвращает агрегированные данные по аккаунту (пример).
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created")
            try:
                authorized = await client.is_user_authorized()
                dialogs = await client.get_dialogs(limit=10) if authorized else []
                return {
                    "authorized": authorized,
                    "dialogs_sample": len(dialogs),
                }
            except Exception as e:
                self._logger.debug("get_common_data error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

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
                        # Пытаемся корректно отключить кли
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