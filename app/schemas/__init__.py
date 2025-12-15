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
from app.schemas.telegram_connection import (
    VerifyCodeRequest,
    VerifyCodeResponse,
    VerifyPasswordRequest,
    VerifyPasswordResponse,
    DisconnectResponse,
    ConnectResponse,
    ErrorResponse,
)
from app.schemas.telegram import (
    ErrorResponse,
    DialogSchema,
    FolderSchema,
    DialogsResponse,
    FoldersResponse,
    PhotoSchema,
    AccountMeResponse,
    LastMessageSchema,
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
    # Telegram connection
    "VerifyCodeRequest",
    "VerifyCodeResponse",
    "VerifyPasswordRequest",
    "VerifyPasswordResponse",
    "DisconnectResponse",
    "ConnectResponse",
    # Telegram data
    "ErrorResponse",
    "DialogSchema",
    "FolderSchema",
    "DialogsResponse",
    "FoldersResponse",
    "PhotoSchema",
    "AccountMeResponse",
    "LastMessageSchema",
]
