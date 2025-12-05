from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, or_
from fastapi import HTTPException, status
import re
import logging

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.utils.security import hash_password, verify_password
from app.utils.jwt import create_access_token

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис для работы с аутентификацией пользователей."""

    @staticmethod
    def _is_email(login: str) -> bool:
        """Проверка, является ли логин email адресом."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, login))

    @staticmethod
    async def register_user(db: AsyncSession, user_data: UserRegister) -> UserResponse:
        """
        Регистрация нового пользователя.

        Args:
            db: Асинхронная сессия базы данных
            user_data: Данные для регистрации (login и password)

        Returns:
            UserResponse: Данные зарегистрированного пользователя

        Raises:
            HTTPException: Если login уже занят
        """
        login = user_data.login.lower().strip()
        is_email = AuthService._is_email(login)

        logger.info(f"Attempting to register user with login: {login} (is_email: {is_email})")

        # Проверка существования пользователя
        if is_email:
            stmt = select(User).where(User.email == login)
        else:
            stmt = select(User).where(User.username == login)

        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(f"User with login {login} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login already registered"
            )

        # Хеширование пароля
        hashed_password = hash_password(user_data.password)
        logger.debug(f"Password hashed successfully")

        # Создание пользователя
        if is_email:
            new_user = User(
                email=login,
                username=login.split('@')[0],
                hashed_password=hashed_password
            )
        else:
            new_user = User(
                username=login,
                email=None,
                hashed_password=hashed_password
            )

        try:
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            logger.info(f"User registered successfully: {new_user.id}")
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"IntegrityError during registration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login already registered"
            )

        return UserResponse.model_validate(new_user)

    @staticmethod
    async def authenticate_user(db: AsyncSession, credentials: UserLogin) -> Token:
        """
        Аутентификация пользователя и выдача JWT токена.

        Args:
            db: Асинхронная сессия базы данных
            credentials: Login и пароль

        Returns:
            Token: JWT токен доступа

        Raises:
            HTTPException: Если credentials неверные
        """
        login = credentials.login.lower().strip()

        logger.info(f"Attempting to authenticate user: {login}")

        # Поиск пользователя по username или email
        stmt = select(User).where(
            or_(
                User.username == login,
                User.email == login
            )
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User not found: {login}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect login or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug(f"User found: {user.id}, verifying password...")

        # Проверка пароля
        password_valid = verify_password(credentials.password, user.hashed_password)

        if not password_valid:
            logger.warning(f"Invalid password for user: {login}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect login or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"User authenticated successfully: {user.id}")

        # Создание токена
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username}
        )

        return Token(access_token=access_token, token_type="bearer")

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User:
        """
        Получение пользователя по ID.

        Args:
            db: Асинхронная сессия базы данных
            user_id: ID пользователя

        Returns:
            User: Объект пользователя

        Raises:
            HTTPException: Если пользователь не найден
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
