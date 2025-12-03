from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.services.auth_service import AuthService
from app.api.dependencies import CurrentUser


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
    description="Создает нового пользователя с email и паролем"
)
def register(
    user_data: UserRegister,
    db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    """
    Регистрация нового пользователя.
    
    - **email**: Уникальный email пользователя
    - **password**: Пароль (минимум 8 символов)
    - **full_name**: Полное имя пользователя (опционально)
    """
    return AuthService.register_user(db, user_data)


@router.post(
    "/login",
    response_model=Token,
    summary="Авторизация пользователя",
    description="Возвращает JWT токен для доступа к защищенным endpoints"
)
def login(
    credentials: UserLogin,
    db: Annotated[Session, Depends(get_db)]
) -> Token:
    """
    Авторизация пользователя.
    
    - **email**: Email пользователя
    - **password**: Пароль
    
    Возвращает JWT токен, который нужно передавать в заголовке:
    `Authorization: Bearer <token>`
    """
    return AuthService.authenticate_user(db, credentials)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Получение информации о текущем пользователе",
    description="Возвращает данные аутентифицированного пользователя"
)
def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """
    Получение информации о текущем пользователе.
    
    Требует JWT токен в заголовке Authorization.
    """
    return UserResponse.model_validate(current_user)