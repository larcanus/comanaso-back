"""
API роутер для управления сессией telethon.
"""
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db,
    get_current_user,
    get_account,
    get_telethon_manager, get_telegram_service,
)
from app.models import User
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
from app.schemas.telegram import (
    AccountMeResponse,
    FolderSchema,
    DialogsResponse,
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


# ============================================================================
# НОВЫЕ ЭНДПОИНТЫ ДЛЯ TELEGRAM DATA API
# ============================================================================

@router.get(
    "/{account_id}/me",
    response_model=AccountMeResponse,
    summary="Получить информацию об аккаунте",
    description="Возвращает информацию о текущем пользователе Telegram аккаунта"
)
async def get_account_me(
        account_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: TelegramService = Depends(get_telegram_service)
) -> AccountMeResponse:
    """
    Получить информацию о текущем пользователе Telegram аккаунта.

    **Требования:**
    - Аккаунт должен быть подключен к Telegram
    - Пользователь должен быть владельцем аккаунта

    **Возвращает:**
    - Полную информацию о пользователе (имя, username, статус, фото и т.д.)
    """
    me_data = await service.get_me(db, current_user.id, account_id)
    return AccountMeResponse(**me_data)


@router.get(
    "/{account_id}/dialogs",
    response_model=DialogsResponse,
    summary="Получить список диалогов",
    description="Возвращает расширенный список диалогов с полной информацией"
)
async def get_account_dialogs(
        account_id: int,
        limit: int = Query(default=100, ge=1, le=500, description="Количество диалогов"),
        offset: int = Query(default=0, ge=0, description="Смещение для пагинации"),
        archived: bool = Query(default=False, description="Включить архивные диалоги"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: TelegramService = Depends(get_telegram_service)
) -> DialogsResponse:
    """
    Получить список диалогов с полной информацией.

    **Параметры:**
    - `limit`: Количество диалогов (максимум 500)
    - `offset`: Смещение для пагинации
    - `archived`: Включить архивные диалоги

    **Требования:**
    - Аккаунт должен быть подключен к Telegram
    - Пользователь должен быть владельцем аккаунта

    **Возвращает:**
    - Список диалогов с детальной информацией о каждом
    - Информацию о пагинации (total, hasMore)
    """
    dialogs_data = await service.get_dialogs_extended(
        db=db,
        user_id=current_user.id,
        account_id=account_id,
        limit=limit,
        offset=offset,
        archived=archived
    )
    return DialogsResponse(**dialogs_data)


@router.get(
    "/{account_id}/folders",
    response_model=List[FolderSchema],
    summary="Получить список папок",
    description="Возвращает список папок (фильтров) диалогов"
)
async def get_account_folders(
        account_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        service: TelegramService = Depends(get_telegram_service)
) -> List[FolderSchema]:
    """
    Получить список папок (фильтров) диалогов.

    **Требования:**
    - Аккаунт должен быть подключен к Telegram
    - Пользователь должен быть владельцем аккаунта

    **Возвращает:**
    - Список всех папок включая дефолтную "Все чаты"
    - Настройки каждой папки (фильтры, закрепленные чаты и т.д.)
    """
    folders_data = await service.get_folders(db, current_user.id, account_id)
    return [FolderSchema(**folder) for folder in folders_data]