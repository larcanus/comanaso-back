from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.services.auth_service import AuthService
from app.api.dependencies import CurrentUser


router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создает нового пользователя с login (email или username) и паролем"
)
async def register(
    user_data: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserResponse:
    """
    Регистрация нового пользователя.

    - **login**: Уникальный логин (email или username, 3-50 символов)
    - **password**: Пароль (минимум 8 символов, должен содержать цифры, заглавные и строчные буквы)
    """
    return await AuthService.register_user(db, user_data)


@router.post(
    "/login",
    response_model=Token,
    summary="Авторизация пользователя",
    description="Возвращает JWT токен для доступа к защищенным endpoints"
)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Token:
    """
    Авторизация пользователя.

    - **login**: Login пользователя (email или username)
    - **password**: Пароль

    Возвращает JWT токен, который нужно передавать в заголовке:
    `Authorization: Bearer <token>`
    """
    return await AuthService.authenticate_user(db, credentials)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получение информации о текущем пользователе",
    description="Возвращает данные аутентифицированного пользователя"
)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """
    Получение информации о текущем пользователе.

    Требует JWT токен в заголовке Authorization.
    """
    return UserResponse.model_validate(current_user)
