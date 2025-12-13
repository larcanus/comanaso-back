"""
Pydantic схемы для операций подключения Telegram аккаунтов.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class ConnectResponse(BaseModel):
    """Ответ на запрос подключения аккаунта."""
    status: Literal["online", "code_required"]
    message: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "code_required",
                    "message": "Код отправлен в Telegram"
                },
                {
                    "status": "online",
                    "message": "Аккаунт уже подключен"
                }
            ]
        }
    }


class VerifyCodeRequest(BaseModel):
    """Запрос на подтверждение кода из SMS."""
    code: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="Код подтверждения из Telegram",
        pattern=r"^\d{5}$"
    )


class VerifyCodeResponse(BaseModel):
    """Ответ на подтверждение кода."""
    status: Literal["connected", "password_required"]
    message: str
    passwordHint: Optional[str] = Field(
        default=None,
        description="Подсказка для 2FA пароля (если требуется)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "connected",
                    "message": "Аккаунт успешно подключен"
                },
                {
                    "status": "password_required",
                    "message": "Требуется 2FA пароль",
                    "passwordHint": "Первая буква имени питомца"
                }
            ]
        }
    }


class VerifyPasswordRequest(BaseModel):
    """Запрос на подтверждение 2FA пароля."""
    password: str = Field(
        ...,
        min_length=1,
        description="Cloud Password из настроек Telegram"
    )


class VerifyPasswordResponse(BaseModel):
    """Ответ на подтверждение 2FA пароля."""
    status: Literal["online"]
    message: str = "Аккаунт успешно подключен"


class DisconnectResponse(BaseModel):
    """Ответ на отключение аккаунта."""
    status: Literal["disconnected"]
    message: str


class LogoutResponse(BaseModel):
    """Ответ на выход из аккаунта."""
    status: Literal["logged_out"]
    message: str


class ErrorResponse(BaseModel):
    """Стандартная структура ошибки API."""
    error: str = Field(..., description="Код ошибки")
    message: str = Field(..., description="Человекочитаемое описание")
    passwordHint: Optional[str] = Field(
        default=None,
        description="Подсказка для пароля (только для PASSWORD_REQUIRED)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "INVALID_CODE",
                    "message": "Неверный код подтверждения"
                },
                {
                    "error": "PASSWORD_REQUIRED",
                    "message": "Требуется двухфакторная аутентификация",
                    "passwordHint": "Первая буква имени питомца"
                }
            ]
        }
    }