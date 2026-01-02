import logging
import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.schemas.auth import (
    UserRegister, UserLogin, AuthResponse, UserData, UpdateUserProfile, UserProfile, UserSettings
)
from app.utils.jwt import create_access_token
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис для работы с аутентификацией пользователей."""

    @staticmethod
    def _is_email(login: str) -> bool:
        """Проверка, является ли логин email адресом."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, login))

    @staticmethod
    async def register_user(db: AsyncSession, user_data: UserRegister) -> AuthResponse:
        """
        Регистрация нового пользователя.

        Args:
            db: Асинхронная сессия базы данных
            user_data: Данные для регистрации (login, email и password)

        Returns:
            AuthResponse: Токен и данные зарегистрированного пользователя

        Raises:
            HTTPException: Если username или email уже заняты
        """
        username = user_data.login.lower().strip()
        email = user_data.email.lower().strip() if user_data.email else None

        logger.info(f"Attempting to register user with username: {username}, email: {email}")

        # Проверка существования пользователя по username
        stmt_username = select(User).where(User.username == username)
        result = await db.execute(stmt_username)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(f"User with username {username} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "USERNAME_EXISTS",
                    "message": "Пользователь с таким логином уже существует"
                }
            )

        # Проверка существования пользователя по email (если email указан)
        if email:
            stmt_email = select(User).where(User.email == email)
            result = await db.execute(stmt_email)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.warning(f"User with email {email} already exists")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "EMAIL_EXISTS",
                        "message": "Пользователь с таким email уже существует"
                    }
                )

        # Хеширование пароля
        hashed_password = hash_password(user_data.password)
        logger.debug(f"Password hashed successfully")

        # Создание пользователя
        new_user = User(
            username=username,
            email=email,
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
                detail={
                    "error": "USER_EXISTS",
                    "message": "Пользователь с таким логином или email уже существует"
                }
            )

        # Создание токена
        access_token = create_access_token(
            data={"sub": str(new_user.id), "username": new_user.username}
        )

        # Формирование ответа
        return AuthResponse(
            token=access_token,
            user=UserData.from_user(new_user)
        )

    @staticmethod
    async def authenticate_user(db: AsyncSession, credentials: UserLogin) -> AuthResponse:
        """
        Аутентификация пользователя и выдача JWT токена.

        Args:
            db: Асинхронная сессия базы данных
            credentials: Login и пароль

        Returns:
            AuthResponse: Токен и данные пользователя

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
                detail={
                    "error": "INVALID_CREDENTIALS",
                    "message": "Неверный логин или пароль"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug(f"User found: {user.id}, verifying password...")

        # Проверка пароля
        password_valid = verify_password(credentials.password, user.hashed_password)

        if not password_valid:
            logger.warning(f"Invalid password for user: {login}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_CREDENTIALS",
                    "message": "Неверный логин или пароль"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"User authenticated successfully: {user.id}")

        # Создание токена
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username}
        )

        # Формирование ответа
        return AuthResponse(
            token=access_token,
            user=UserData.from_user(user)
        )

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
                detail={
                    "error": "USER_NOT_FOUND",
                    "message": "Пользователь не найден"
                }
            )

        return user

    @staticmethod
    async def delete_user_account(
        db: AsyncSession,
        user_id: int,
        telethon_manager = None
    ) -> dict:
        """
        Полное удаление учетной записи пользователя и всех связанных данных.

        Args:
            db: Асинхронная сессия базы данных
            user_id: ID пользователя для удаления
            telethon_manager: Опционально, экземпляр TelethonManager для отключения клиентов

        Returns:
            dict: Информация об удалении (deleted_user_id, deleted_accounts_count)

        Raises:
            HTTPException: Если пользователь не найден или произошла ошибка при удалении
        """
        logger.info(f"Attempting to delete user account with ID: {user_id}")

        # Получаем пользователя с аккаунтами
        stmt = select(User).where(User.id == user_id).options(
            selectinload(User.accounts)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"User not found for deletion: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "USER_NOT_FOUND",
                    "message": "Пользователь не найден"
                }
            )

        # Подсчитываем количество аккаунтов для ответа
        accounts_count = len(user.accounts)
        logger.info(f"User has {accounts_count} Telegram accounts to delete")

        # Если передан telethon_manager, отключаем все клиенты пользователя
        if telethon_manager:
            try:
                # Отключаем все аккаунты пользователя
                for account in user.accounts:
                    await telethon_manager.disconnect_client(account.id)
                logger.info(f"Disconnected all Telethon clients for user {user_id}")
            except Exception as e:
                logger.warning(f"Error disconnecting Telethon clients: {e}")
                # Продолжаем удаление даже если отключение не удалось

        # Удаляем пользователя (каскадное удаление аккаунтов произойдет автоматически)
        try:
            await db.delete(user)
            await db.commit()
            logger.info(f"User account deleted successfully: {user_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete user account: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "DELETE_FAILED",
                    "message": "Не удалось удалить учетную запись"
                }
            )

        return {
            "deleted_user_id": user_id,
            "deleted_accounts_count": accounts_count
        }

    @staticmethod
    async def update_user_profile(
        db: AsyncSession,
        user_id: int,
        update_data: UpdateUserProfile
    ) -> UserProfile:
        """
        Обновление профиля пользователя.

        Args:
            db: Сессия БД
            user_id: ID пользователя
            update_data: Данные для обновления

        Returns:
            Обновленный профиль пользователя

        Raises:
            HTTPException: Если пользователь не найден, данные заняты или ошибка валидации
        """
        # Получаем текущего пользователя
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "USER_NOT_FOUND",
                    "message": "Пользователь не найден"
                }
            )

        # Проверяем уникальность username (если он меняется)
        if update_data.username is not None and update_data.username != user.username:
            stmt = select(User).where(
                and_(
                    User.username == update_data.username,
                    User.id != user_id  # Исключаем текущего пользователя
                )
            )
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "USERNAME_EXISTS",
                        "message": "Пользователь с таким username уже существует"
                    }
                )

        # Проверяем уникальность email (если он меняется)
        if update_data.email is not None and update_data.email != user.email:
            stmt = select(User).where(
                and_(
                    User.email == update_data.email,
                    User.id != user_id  # Исключаем текущего пользователя
                )
            )
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "EMAIL_EXISTS",
                        "message": "Пользователь с таким email уже существует"
                    }
                )

        # Обновляем данные
        if update_data.username is not None:
            user.username = update_data.username
            logger.info(f"Updated username for user {user_id}: {update_data.username}")

        if update_data.email is not None:
            user.email = update_data.email
            logger.info(f"Updated email for user {user_id}")

        if update_data.password is not None:
            # Хешируем новый пароль
            user.hashed_password = hash_password(update_data.password)
            logger.info(f"Updated password for user {user_id}")

        if update_data.settings is not None:
            # Объединяем существующие настройки с новыми
            current_settings = user.settings or {}
            new_settings = update_data.settings.model_dump()
            user.settings = {**current_settings, **new_settings}
            logger.info(f"Updated settings for user {user_id}")

        user.updated_at = datetime.utcnow()

        try:
            await db.commit()
            await db.refresh(user)
            logger.info(f"Profile updated successfully for user {user_id}")
        except IntegrityError as e:
            await db.rollback()
            logger.error(f"Database error during profile update: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "UPDATE_FAILED",
                    "message": "Не удалось обновить профиль"
                }
            )

        return UserProfile.from_user(user)