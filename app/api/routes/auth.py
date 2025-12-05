from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    UserRegister, UserLogin, AuthResponse, TokenVerifyResponse,
    UserData, UserResponse
)
from app.services.auth_service import AuthService
from app.api.dependencies import CurrentUser


router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создает нового пользователя и возвращает JWT токен",
    responses={
        201: {
            "description": "Пользователь успешно зарегистрирован",
            "content": {
                "application/json": {
                    "example": {
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "user": {
                            "id": 1,
                            "login": "user123",
                            "createdAt": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Пользователь уже существует",
            "content": {
                "application/json": {
                    "example": {
                        "error": "USER_EXISTS",
                        "message": "Пользователь с таким логином уже существует"
                    }
                }
            }
        },
        422: {
            "description": "Ошибка валидации",
            "content": {
                "application/json": {
                    "example": {
                        "error": "VALIDATION_ERROR",
                        "message": "Пароль должен содержать минимум 6 символов"
                    }
                }
            }
        }
    }
)
async def register(
    user_data: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuthResponse:
    """
    Регистрация нового пользователя.

    - **login**: Уникальный логин (email или username, 3-50 символов)
    - **password**: Пароль (минимум 6 символов)
    """
    return await AuthService.register_user(db, user_data)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Авторизация пользователя",
    description="Возвращает JWT токен и данные пользователя",
    responses={
        200: {
            "description": "Успешная авторизация",
            "content": {
                "application/json": {
                    "example": {
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "user": {
                            "id": 1,
                            "login": "user123",
                            "createdAt": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Неверные учетные данные",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_CREDENTIALS",
                        "message": "Неверный логин или пароль"
                    }
                }
            }
        }
    }
)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> AuthResponse:
    """
    Авторизация пользователя.

    - **login**: Login пользователя (email или username)
    - **password**: Пароль

    Возвращает JWT токен, который нужно передавать в заголовке:
    `Authorization: Bearer <token>`
    """
    return await AuthService.authenticate_user(db, credentials)


@router.get(
    "/verify",
    response_model=TokenVerifyResponse,
    summary="Проверка валидности токена",
    description="Проверяет JWT токен и возвращает данные пользователя",
    responses={
        200: {
            "description": "Токен валиден",
            "content": {
                "application/json": {
                    "example": {
                        "valid": True,
                        "user": {
                            "id": 1,
                            "login": "user123"
                        }
                    }
                }
            }
        },
        401: {
            "description": "Токен невалиден",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_TOKEN",
                        "message": "Токен недействителен или истек"
                    }
                }
            }
        }
    }
)
async def verify_token(current_user: CurrentUser) -> TokenVerifyResponse:
    """
    Проверка валидности JWT токена.

    Требует JWT токен в заголовке Authorization.
    """
    return TokenVerifyResponse(
        valid=True,
        user=UserData(
            id=current_user.id,
            login=current_user.email if current_user.email else current_user.username,
            createdAt=current_user.created_at.isoformat() + "Z"
        )
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получение информации о текущем пользователе",
    description="Возвращает данные аутентифицированного пользователя (deprecated, используйте /verify)"
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """
    Получение информации о текущем пользователе.

    Требует JWT токен в заголовке Authorization.

    **Deprecated**: Используйте `/api/auth/verify` вместо этого endpoint.
    """
    return UserResponse.model_validate(current_user)
