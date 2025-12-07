import asyncio
import logging
from typing import Optional, Dict, Any, List

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import errors

# Exceptions для маппинга в сервис/роутеры
class TelethonManagerError(Exception):
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


class TelethonManager:
    """
    Управляет Telethon clients в памяти по account_id.
    Методы возвращают данные или выбрасывают специализированные исключения.
    `session_string` не логируется в менеджере.
    """
    def __init__(self) -> None:
        self._clients: Dict[int, TelegramClient] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
        self._logger = logging.getLogger("telethon_manager")

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

    async def send_code(self, account_id: int, phone: str) -> str:
        """
        Отправляет код на номер. Возвращает phone_code_hash (нужен для sign_in_code).
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created; call create_client first")

            try:
                sent = await client.send_code_request(phone)
                phone_code_hash = getattr(sent, "phone_code_hash", None)
                if not phone_code_hash:
                    # Некоторое поведение Telethon: вернуть объект с полем
                    raise TelethonManagerError("no phone_code_hash returned")
                return phone_code_hash
            except errors.rpcerrorlist.PhoneNumberInvalidError:
                raise PhoneNumberInvalid("phone number invalid")
            except errors.rpcerrorlist.ApiIdInvalidError:
                # Явная маппинг-ошибка для неверных api_id / api_hash
                raise InvalidApiCredentials("invalid api_id/api_hash")
            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("send_code error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

    async def sign_in_code(
        self,
        account_id: int,
        phone: str,
        code: str,
        phone_code_hash: Optional[str] = None,
    ) -> str:
        """
        Подтверждает код. При успешном входе возвращает session_string (строго для сохранения в БД).
        Может выбрасывать PasswordRequired, InvalidCode, ExpiredCode и другие.
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created; call create_client first")

            try:
                # Telethon: phone_code_hash можно передать именованно
                if phone_code_hash:
                    await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                else:
                    await client.sign_in(phone=phone, code=code)

                # Получаем session_string для сохранения
                session_obj = client.session
                if isinstance(session_obj, StringSession):
                    session_string = session_obj.save()
                else:
                    # попытка получить строку у сессии (на случай другой реализации)
                    session_string = StringSession(session=client.session).save() if hasattr(StringSession, "save") else None

                return session_string  # не логировать
            except errors.SessionPasswordNeededError:
                raise PasswordRequired("2FA password required")
            except errors.rpcerrorlist.PhoneCodeInvalidError:
                raise InvalidCode("invalid code")
            except errors.rpcerrorlist.PhoneCodeExpiredError:
                raise ExpiredCode("code expired")
            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("sign_in_code error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

    async def sign_in_password(self, account_id: int, password: str) -> str:
        """
        Завершает 2FA вводом пароля. Возвращает session_string.
        """
        lock = self._get_lock(account_id)
        async with lock:
            client = self._clients.get(account_id)
            if not client:
                raise NotConnected("client not created; call create_client first")

            try:
                await client.sign_in(password=password)
                session_obj = client.session
                if isinstance(session_obj, StringSession):
                    session_string = session_obj.save()
                else:
                    session_string = StringSession(session=client.session).save() if hasattr(StringSession, "save") else None
                return session_string
            except errors.FloodWaitError as e:
                raise FloodWait(int(getattr(e, "seconds", 0)))
            except Exception as e:
                self._logger.debug("sign_in_password error: %s", type(e).__name__)
                raise TelethonManagerError(str(e))

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
                        # Пытаемся корректно отключить клиент
                        await client.disconnect()
                    except Exception as e:
                        # Не выбрасываем наружу — собираем и логируем
                        self._logger.debug("disconnect_all: error disconnecting account %s: %s", account_id, type(e).__name__)
                        errors.append((account_id, str(e)))
                    finally:
                        # Удаляем клиент из словаря независимо от результата
                        self._clients.pop(account_id, None)
            except Exception as e:
                self._logger.debug("disconnect_all: lock error for account %s: %s", account_id, type(e).__name__)
                errors.append((account_id, str(e)))

        if errors:
            self._logger.warning("disconnect_all completed with errors for accounts: %s", [a for a, _ in errors])
