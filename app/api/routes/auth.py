"""
API роутер для управления авторизацией юзеров.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, status, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas.auth import (
    UserRegister, UserLogin, AuthResponse, TokenVerifyResponse,
    UserData, UserResponse, LogoutResponse, DeleteAccountResponse,
    UserProfile, UpdateUserProfile, PasswordResetRequest,
    PasswordResetConfirm, PasswordResetResponse
)
from app.services.auth_service import AuthService
from app.api.dependencies import CurrentUser, get_current_user, security
from app.services.email_service import EmailService


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
async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> TokenVerifyResponse:
    """
    Проверка валидности JWT токена.

    Требует JWT токен в заголовке Authorization.
    """
    try:
        user = await get_current_user(credentials, db)
    except HTTPException as e:
        # Переопределяем UNAUTHORIZED на INVALID_TOKEN для endpoint /verify
        if e.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Токен недействителен или истек"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise

    return TokenVerifyResponse(
        valid=True,
        user=UserData(
            id=user.id,
            login=user.email if user.email else user.username,
            createdAt=user.created_at.isoformat() + "Z"
        )
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Выход из системы",
    description="Выход пользователя из системы (инвалидация токена)",
    responses={
        200: {
            "description": "Успешный выход",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Вы успешно вышли из системы"
                    }
                }
            }
        },
        401: {
            "description": "Токен невалиден",
            "content": {
                "application/json": {
                    "example": {
                        "error": "UNAUTHORIZED",
                        "message": "Токен недействителен или отсутствует"
                    }
                }
            }
        }
    }
)
async def logout(current_user: CurrentUser) -> LogoutResponse:
    """
    Выход из системы.

    Требует JWT токен в заголовке Authorization.

    **Примечание**: После logout клиент должен удалить токен из localStorage.
    Токен остается валидным до истечения срока действия (stateless JWT).
    Для полной инвалидации требуется blacklist механизм.
    """
    return LogoutResponse(
        status="success",
        message="Вы успешно вышли из системы"
    )


@router.delete(
    "/delete-account",
    response_model=DeleteAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Полное удаление учетной записи",
    description="Удаляет учетную запись пользователя, все Telegram аккаунты и связанные данные",
    responses={
        200: {
            "description": "Учетная запись успешно удалена",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Учетная запись и все связанные данные успешно удалены",
                        "deleted_user_id": 1,
                        "deleted_accounts_count": 3
                    }
                }
            }
        },
        401: {
            "description": "Требуется авторизация",
            "content": {
                "application/json": {
                    "example": {
                        "error": "UNAUTHORIZED",
                        "message": "Требуется авторизация"
                    }
                }
            }
        },
        404: {
            "description": "Пользователь не найден",
            "content": {
                "application/json": {
                    "example": {
                        "error": "USER_NOT_FOUND",
                        "message": "Пользователь не найден"
                    }
                }
            }
        },
        500: {
            "description": "Ошибка при удалении",
            "content": {
                "application/json": {
                    "example": {
                        "error": "DELETE_FAILED",
                        "message": "Не удалось удалить учетную запись"
                    }
                }
            }
        }
    }
)
async def delete_account(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: Request
) -> DeleteAccountResponse:
    """
    Полное удаление учетной записи текущего пользователя.

    Удаляет:
    - Данные пользователя из системы
    - Все связанные Telegram аккаунты
    - Все данные аккаунтов (сессии, настройки и т.д.)

    **Внимание**: Эта операция необратима. Все данные будут безвозвратно удалены.

    Требует JWT токен в заголовке Authorization.
    """
    # Получаем TelethonManager из app.state для отключения клиентов
    telethon_manager = getattr(request.app.state, "telethon_manager", None)

    # Удаляем учетную запись
    delete_result = await AuthService.delete_user_account(
        db=db,
        user_id=current_user.id,
        telethon_manager=telethon_manager
    )

    return DeleteAccountResponse(
        status="success",
        message="Учетная запись и все связанные данные успешно удалены",
        deleted_user_id=delete_result["deleted_user_id"],
        deleted_accounts_count=delete_result["deleted_accounts_count"]
    )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Получение полного профиля текущего пользователя",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Получение полного профиля текущего пользователя.

    Args:
        current_user: Текущий пользователь

    Returns:
        UserProfile: Полные данные профиля включая настройки
    """
    return UserProfile.from_user(current_user)


@router.patch(
    "/me",
    response_model=UserProfile,
    summary="Обновление профиля пользователя",
    description="Обновляет данные профиля текущего пользователя"
)
async def update_profile(
    update_data: UpdateUserProfile,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserProfile:
    """
    Обновление профиля текущего пользователя.

    Args:
        update_data: Данные для обновления (username, email, settings)
        current_user: Текущий пользователь
        db: Сессия базы данных

    Returns:
        UserProfile: Обновленные данные профиля

    Raises:
        HTTPException 400: Если username или email уже существуют
        HTTPException 422: Если данные не прошли валидацию
    """

    return await AuthService.update_user_profile(db, current_user.id, update_data)

@router.post(
    "/password-reset/request",
    response_model=PasswordResetResponse,
    summary="Запрос на сброс пароля",
    description="Отправляет email с инструкциями по сбросу пароля",
    responses={
        200: {
            "description": "Инструкции отправлены на email",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Инструкции по сбросу пароля отправлены на email"
                    }
                }
            }
        },
        404: {
            "description": "Email не найден",
            "content": {
                "application/json": {
                    "example": {
                        "error": "EMAIL_NOT_FOUND",
                        "message": "Пользователь с таким email не найден"
                    }
                }
            }
        }
    }
)
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Запрос на сброс пароля.
    Отправляет email с инструкциями если пользователь существует.
    """
    reset_token = await AuthService.request_password_reset(db, request.email)

    if reset_token:
        background_tasks.add_task(
            EmailService.send_password_reset_email,
            request.email,
            reset_token
        )

    return PasswordResetResponse(
        status="success",
        message="Инструкции по сбросу пароля отправлены на email если он существует"
    )


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetResponse,
    summary="Подтверждение сброса пароля",
    description="Устанавливает новый пароль используя токен из email",
    responses={
        200: {
            "description": "Пароль успешно изменен",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Пароль успешно изменен"
                    }
                }
            }
        },
        400: {
            "description": "Невалидный или истекший токен",
            "content": {
                "application/json": {
                    "example": {
                        "error": "INVALID_RESET_TOKEN",
                        "message": "Токен сброса пароля недействителен или истек"
                    }
                }
            }
        }
    }
)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> PasswordResetResponse:
    """
    Подтверждение сброса пароля.

    Устанавливает новый пароль используя токен из email.
    - **token**: Токен из email
    - **new_password**: Новый пароль (минимум 6 символов)
    """
    await AuthService.reset_password(
        db,
        reset_confirm.token,
        reset_confirm.new_password
    )

    return PasswordResetResponse(
        status="success",
        message="Пароль успешно изменен"
    )