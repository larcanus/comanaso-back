"""Pydantic схемы для валидации данных."""

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    TokenData,
    UserResponse
)
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountDetailResponse,
    AccountListResponse
)
from app.schemas.telegram import (
    SendCodeRequest,
    VerifyCodeRequest,
    TelegramDialog,
    TelegramFolder,
    DialogsResponse,
    ConnectionStatusResponse
)

__all__ = [
    # Auth
    "UserRegister",
    "UserLogin",
    "Token",
    "TokenData",
    "UserResponse",
    # Account
    "AccountCreate",
    "AccountUpdate",
    "AccountResponse",
    "AccountDetailResponse",
    "AccountListResponse",
    # Telegram
    "SendCodeRequest",
    "VerifyCodeRequest",
    "TelegramDialog",
    "TelegramFolder",
    "DialogsResponse",
    "ConnectionStatusResponse",
]
