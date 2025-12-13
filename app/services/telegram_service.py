# File: app/services/telegram_service.py

from typing import Any, Dict, Optional
import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.account_service import AccountService
from app.models.account import Account
from app.utils.telethon_client import (
    TelethonManager,
    InvalidApiCredentials,
    PasswordRequired,
    FloodWait,
    AlreadyConnected,
    NotConnected,
    InvalidCode,
    InvalidPasswordError,
    ExpiredCodeError,
    PhoneNumberInvalid,
    TelethonManagerError,
)

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Сервисный уровень для интеграции Telethon:
    - работает с AccountService / БД
    - вызывает TelethonManager
    - возвращает ответные структуры по контракту
    """

    def __init__(self, tm: TelethonManager) -> None:
        self.tm = tm

    async def _get_account(self, db: AsyncSession, account_id: int, user_id: int) -> Account:
        return await AccountService.get_account(db, account_id, user_id)

    async def _set_status_field(self, db: AsyncSession, account: Account, status_str: str) -> None:
        """
        Попытка установить поле `status` если оно есть, иначе управляем is_connected.
        Коммитим изменения.
        """
        # безопасно пытаемся установить status если модель поддерживает
        if hasattr(account, "status"):
            account.status = status_str
            if status_str == "online":
                account.is_connected = True
            elif status_str in ("offline", "connecting", "error"):
                account.is_connected = False
        else:
            # fallback: управляем только is_connected
            account.is_connected = status_str == "online"

        account.update_last_activity()
        await db.commit()
        await db.refresh(account)

    async def _clear_session(self, db: AsyncSession, account_id: int) -> None:
        result = await db.execute(select(Account).filter(Account.id == account_id))
        account = result.scalar_one_or_none()
        if account:
            account.session_string = None
            account.is_connected = False
            account.update_last_activity()
            await db.commit()
            await db.refresh(account)

    async def connect(self, db: AsyncSession, user_id: int, account_id: int) -> Dict[str, Any]:
        """
        Шаг инициации подключения:
        - пометить connecting
        - создать/подключить клиент
        - если авторизован -> вернуть online
        - иначе -> отправить код и вернуть code_required
        """
        account = await self._get_account(db, account_id, user_id)

        # пометить connecting (если есть поле status)
        try:
            await self._set_status_field(db, account, "connecting")
        except Exception:
            logger.debug("Failed to set connecting status", exc_info=True)

        try:
            await self.tm.create_client(
                account_id=account.id,
                api_id=account.api_id,
                api_hash=account.api_hash,
                session_string=account.session_string,
            )
        except InvalidApiCredentials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_API_CREDENTIALS", "message": "Неверный API ID или API Hash"}
            )
        except AlreadyConnected:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "ALREADY_CONNECTED", "message": "Аккаунт уже подключен"}
            )
        except FloodWait as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "FLOOD_WAIT", "message": "Flood wait", "seconds": getattr(e, "seconds", None)}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

        # Проверяем авторизацию
        try:
            common = await self.tm.get_common_data(account.id)
            if common.get("authorized"):
                # уже авторизован — ставим online
                try:
                    await self._set_status_field(db, account, "online")
                except Exception:
                    logger.debug("Failed to set online status", exc_info=True)
                return {"status": "online", "message": "Аккаунт уже подключен"}

            # иначе отправляем код (phone_code_hash теперь хранится внутри TelethonManager)
            phone = account.phone
            await self.tm.send_code(account.id, phone)
            return {"status": "code_required", "message": "Код отправлен в Telegram"}
        except PhoneNumberInvalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "PHONE_NUMBER_INVALID", "message": "Неверный номер телефона"}
            )
        except FloodWait as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "FLOOD_WAIT", "message": "Flood wait", "seconds": getattr(e, "seconds", None)}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

    async def verify_code(
        self,
        db: AsyncSession,
        user_id: int,
        account_id: int,
        code: str
    ) -> Dict[str, Any]:
        """
        Подтверждение кода: sign_in_code -> при success сохраняем session_string и ставим online.
        phone_code_hash берется из памяти TelethonManager.
        Возвращаем структуры по контракту или выбрасываем HTTPException с кодом ошибки.
        """
        account = await self._get_account(db, account_id, user_id)

        try:
            session_string = await self.tm.sign_in_code(account.id, account.phone, code)
            if session_string:
                await AccountService.update_session(db, account.id, session_string)
            # пометить online
            try:
                await self._set_status_field(db, account, "online")
            except Exception:
                logger.debug("Failed to set online status", exc_info=True)
            return {"status": "connected", "message": "Аккаунт успешно подключен"}
        except PasswordRequired:
            # требуется пароль 2FA - получаем подсказку
            try:
                await self._set_status_field(db, account, "connecting")
            except Exception:
                pass

            # Получаем подсказку пароля
            password_hint = None
            try:
                password_hint = await self.tm.get_password_hint(account.id)
            except Exception:
                logger.debug("Failed to get password hint", exc_info=True)

            return {
                "status": "password_required",
                "message": "Требуется 2FA пароль",
                "passwordHint": password_hint
            }
        except InvalidCode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_CODE", "message": "Неверный код подтверждения"}
            )
        except ExpiredCodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "EXPIRED_CODE", "message": "Код истек, запросите новый"}
            )
        except NotConnected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "NOT_CONNECTED", "message": "Клиент не создан"}
            )
        except FloodWait as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "FLOOD_WAIT", "message": "Flood wait", "seconds": e.seconds}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

            response = {
                "status": "password_required",
                "message": "Требуется 2FA пароль"
            }
            if password_hint:
                response["passwordHint"] = password_hint
            return response
        except InvalidCode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_CODE", "message": "Неверный код подтверждения"}
            )
        except ExpiredCodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "EXPIRED_CODE", "message": "Код истек, запросите новый"}
            )
        except FloodWait as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "FLOOD_WAIT", "message": "Flood wait", "seconds": getattr(e, "seconds", None)}
            )
        except NotConnected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "NOT_CONNECTED", "message": "Клиент не создан"}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

    async def verify_password(
        self,
        db: AsyncSession,
        user_id: int,
        account_id: int,
        password: str
    ) -> Dict[str, Any]:
        """
        Завершение 2FA паролем.
        """
        account = await self._get_account(db, account_id, user_id)

        try:
            session_string = await self.tm.sign_in_password(account.id, password)
            if session_string:
                await AccountService.update_session(db, account.id, session_string)
            try:
                await self._set_status_field(db, account, "online")
            except Exception:
                logger.debug("Failed to set online status", exc_info=True)
            return {"status": "online", "message": "Аккаунт успешно подключен"}
        except InvalidPasswordError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_PASSWORD", "message": "Неверный пароль"}
            )
        except FloodWait as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "FLOOD_WAIT", "message": "Flood wait", "seconds": getattr(e, "seconds", None)}
            )
        except NotConnected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "NOT_CONNECTED", "message": "Клиент не создан"}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

    async def disconnect(self, db: AsyncSession, user_id: int, account_id: int) -> Dict[str, Any]:
        """
        Лёгкое отключение (не logout) — клиент disconnect, сохраняем состояние offline (но не удаляем session_string).
        """
        account = await self._get_account(db, account_id, user_id)

        try:
            await self.tm.disconnect(account.id)
            # пометить offline
            try:
                await self._set_status_field(db, account, "offline")
            except Exception:
                logger.debug("Failed to set offline status", exc_info=True)
            return {"status": "disconnected", "message": "Аккаунт отключен"}
        except NotConnected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "NOT_CONNECTED", "message": "Клиент не подключён"}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

    async def logout(self, db: AsyncSession, user_id: int, account_id: int) -> Dict[str, Any]:
        """
        Logout: снимаем сессию на сервере, очищаем session_string в БД и ставим offline.
        """
        account = await self._get_account(db, account_id, user_id)

        try:
            await self.tm.logout(account.id)
            await self._clear_session(db, account.id)
            try:
                await self._set_status_field(db, account, "offline")
            except Exception:
                logger.debug("Failed to set offline status", exc_info=True)
            return {"status": "logged_out", "message": "Выход выполнен, сессия удалена"}
        except NotConnected:
            # даже если нет клиента — очистим локально
            await self._clear_session(db, account.id)
            return {"status": "logged_out", "message": "Выход выполнен, сессия удалена"}
        except FloodWait as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "FLOOD_WAIT", "message": "Flood wait", "seconds": getattr(e, "seconds", None)}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

    async def get_dialogs(self, db: AsyncSession, user_id: int, account_id: int, limit: int = 50) -> Any:
        """
        Возвращает диалоги через TelethonManager (маппинг ошибок в HTTP ошибки).
        """
        await self._get_account(db, account_id, user_id)  # проверка прав

        try:
            dialogs = await self.tm.get_dialogs(account_id, limit=limit)
            return dialogs
        except NotConnected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "NOT_CONNECTED", "message": "Клиент не подключён/не авторизован"}
            )
        except FloodWait as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "FLOOD_WAIT", "message": "Flood wait", "seconds": getattr(e, "seconds", None)}
            )
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )

    async def get_common_data(self, db: AsyncSession, user_id: int, account_id: int) -> Any:
        """
        Аггрегированные данные (authorized, dialogs_sample).
        """
        await self._get_account(db, account_id, user_id)
        try:
            return await self.tm.get_common_data(account_id)
        except NotConnected:
            return {"authorized": False, "dialogs_sample": 0}
        except TelethonManagerError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "TELETHON_ERROR", "message": str(e)}
            )