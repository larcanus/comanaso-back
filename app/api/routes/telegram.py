"""
API роутер для управления сессией telethon.
"""
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db,
    get_current_user,
    get_account,
    get_telethon_manager,
)
from app.utils.telethon_client import (
    TelethonManager,
    TelethonManagerError,
    InvalidApiCredentials,
)
from app.services.telegram_service import TelegramService
from app.models.account import Account
from app.schemas.telegram_connection import (
    VerifyCodeRequest,
    VerifyPasswordRequest,
)

router = APIRouter()


@router.post("/accounts/{account_id}/connect")
async def connect_account(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Dict[str, Any]:
    """
    Начать процесс подключения Telegram-аккаунта.

    Возвращает:
    - status: "online" если уже авторизован
    - status: "code_required" если нужен код подтверждения
    """
    service = TelegramService(tm)
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.connect(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )


@router.post("/accounts/{account_id}/verify-code")
async def verify_code(
        account_id: int,
        request: VerifyCodeRequest,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Dict[str, Any]:
    """
    Подтвердить код из Telegram.

    Возвращает:
    - status: "connected" если успешно
    - status: "password_required" если нужен 2FA пароль
    """
    service = TelegramService(tm)
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.verify_code(db, current_user.id, account.id, request.code)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )


@router.post("/accounts/{account_id}/verify-password")
async def verify_password(
        account_id: int,
        request: VerifyPasswordRequest,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Dict[str, Any]:
    """
    Подтвердить 2FA пароль.

    Возвращает:
    - status: "online" если успешно
    """
    service = TelegramService(tm)
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.verify_password(db, current_user.id, account.id, request.password)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )


@router.post("/accounts/{account_id}/disconnect")
async def disconnect_account(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Dict[str, Any]:
    """
    Мягкое отключение Telegram-аккаунта.
    Закрывает соединение, но сохраняет сессию в БД.
    """
    service = TelegramService(tm)
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.disconnect(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )


@router.post("/accounts/{account_id}/logout")
async def logout_account(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Dict[str, Any]:
    """
    Полный выход из Telegram-аккаунта.
    Удаляет сессию из Telegram и очищает session_string в БД.
    Требует новой авторизации при следующем подключении.
    """
    service = TelegramService(tm)
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.logout(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )


@router.get("/accounts/{account_id}/dialogs")
async def get_dialogs(
        account_id: int,
        limit: int = 50,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Any:
    """Получить список диалогов Telegram-аккаунта."""
    service = TelegramService(tm)
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.get_dialogs(db, current_user.id, account.id, limit=limit)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )


@router.get("/accounts/{account_id}/folders")
async def get_folders(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Any:
    """Получить список папок Telegram-аккаунта."""
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await tm.get_folders(account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )


@router.get("/accounts/{account_id}/data")
async def get_common_data(
        account_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: Any = Depends(get_current_user),
        account: Account = Depends(get_account),
        tm: TelethonManager = Depends(get_telethon_manager),
) -> Any:
    """Получить общие данные Telegram-аккаунта (статус авторизации, количество диалогов)."""
    service = TelegramService(tm)
    if account.id != account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.get_common_data(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)}
        )
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)}
        )
