"""
API роутер для управления сессией telethon.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
    ConnectResponse,
    VerifyCodeRequest,
    VerifyCodeResponse,
    VerifyPasswordRequest,
    VerifyPasswordResponse,
    DisconnectResponse,
    LogoutResponse,
)

router = APIRouter()


@router.post("/accounts/{accountId}/connect", response_model=ConnectResponse)
async def connect_account(
    accountId: int,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> ConnectResponse:
    service = TelegramService(tm)
    # account coming from dependency должен соответствовать accountId
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.connect(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TELETHON_ERROR", "message": str(e)})


@router.post("/accounts/{accountId}/verify-code", response_model=VerifyCodeResponse)
async def verify_code(
    accountId: int,
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> VerifyCodeResponse:
    service = TelegramService(tm)
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.verify_code(db, current_user.id, account.id, request.code)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TELETHON_ERROR", "message": str(e)})


@router.post("/accounts/{accountId}/verify-password", response_model=VerifyPasswordResponse)
async def verify_password(
    accountId: int,
    request: VerifyPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> VerifyPasswordResponse:
    service = TelegramService(tm)
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.verify_password(db, current_user.id, account.id, request.password)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TELETHON_ERROR", "message": str(e)})


@router.post("/accounts/{accountId}/disconnect", response_model=DisconnectResponse)
async def disconnect_account(
    accountId: int,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> DisconnectResponse:
    service = TelegramService(tm)
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.disconnect(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TELETHON_ERROR", "message": str(e)})


@router.post("/accounts/{accountId}/logout", response_model=LogoutResponse)
async def logout_account(
    accountId: int,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> LogoutResponse:
    service = TelegramService(tm)
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.logout(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TELETHON_ERROR", "message": str(e)})


@router.get("/accounts/{accountId}/dialogs")
async def get_dialogs(
    accountId: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> Any:
    service = TelegramService(tm)
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.get_dialogs(db, current_user.id, account.id, limit=limit)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TELETHON_ERROR", "message": str(e)})


@router.get("/accounts/{accountId}/folders")
async def get_folders(
    accountId: int,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> Any:
    # TelegramService не реализовывал явный get_folders, поэтому вызываем TelethonManager напрямую
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await tm.get_folders(account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TELETHON_ERROR", "message": str(e)},
        )


@router.get("/accounts/{accountId}/data")
async def get_common_data(
    accountId: int,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
    account: Account = Depends(get_account),
    tm: TelethonManager = Depends(get_telethon_manager),
) -> Any:
    service = TelegramService(tm)
    if account.id != accountId:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account mismatch")
    try:
        return await service.get_common_data(db, current_user.id, account.id)
    except InvalidApiCredentials as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_API_CREDENTIALS", "message": str(e)})
    except TelethonManagerError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TELETHON_ERROR", "message": str(e)})
