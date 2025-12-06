"""
Сервис для управления Telegram аккаунтами.
Бизнес-логика CRUD операций с аккаунтами.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from typing import List

from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse


class AccountService:
    """
    Сервис для работы с Telegram аккаунтами.

    Methods:
        create_account: Создание нового аккаунта
        get_account: Получение аккаунта по ID
        get_user_accounts: Получение всех аккаунтов пользователя
        update_account: Обновление данных аккаунта
        delete_account: Удаление аккаунта
        update_connection_status: Обновление статуса подключения
        update_session: Обновление session_string
    """

    @staticmethod
    async def create_account(
        db: AsyncSession,
        user_id: int,
        account_data: AccountCreate
    ) -> Account:
        """
        Создание нового Telegram аккаунта.

        Args:
            db: Асинхронная сессия БД
            user_id: ID пользователя-владельца
            account_data: Данные для создания аккаунта

        Returns:
            Account: Созданный аккаунт

        Raises:
            HTTPException: Если номер телефона уже используется
        """
        # Проверка существования номера
        result = await db.execute(
            select(Account).filter(Account.phone == account_data.phone)
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ACCOUNT_ALREADY_EXISTS",
                    "message": f"Аккаунт с номером {account_data.phone} уже существует"
                }
            )

        # Создание аккаунта
        db_account = Account(
            user_id=user_id,
            phone=account_data.phone,
            api_id=account_data.api_id,
            api_hash=account_data.api_hash,
            name=account_data.name,
            is_connected=False
        )

        try:
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            return db_account
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "DATABASE_ERROR",
                    "message": "Ошибка при создании аккаунта"
                }
            )

    @staticmethod
    async def get_account(
        db: AsyncSession,
        account_id: int,
        user_id: int
    ) -> Account:
        """
        Получение аккаунта по ID с проверкой владельца.

        Args:
            db: Асинхронная сессия БД
            account_id: ID аккаунта
            user_id: ID пользователя для проверки прав

        Returns:
            Account: Найденный аккаунт

        Raises:
            HTTPException: Если аккаунт не найден или нет прав доступа
        """
        result = await db.execute(
            select(Account).filter(
                Account.id == account_id,
                Account.user_id == user_id
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ACCOUNT_NOT_FOUND",
                    "message": "Аккаунт не найден"
                }
            )

        return account

    @staticmethod
    async def get_user_accounts(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Account]:
        """
        Получение всех аккаунтов пользователя с пагинацией.

        Args:
            db: Асинхронная сессия БД
            user_id: ID пользователя
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей

        Returns:
            List[Account]: Список аккаунтов пользователя
        """
        result = await db.execute(
            select(Account)
            .filter(Account.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_account(
        db: AsyncSession,
        account_id: int,
        user_id: int,
        account_data: AccountUpdate
    ) -> Account:
        """
        Обновление данных аккаунта.

        Args:
            db: Асинхронная сессия БД
            account_id: ID аккаунта
            user_id: ID пользователя для проверки прав
            account_data: Новые данные аккаунта

        Returns:
            Account: Обновленный аккаунт

        Raises:
            HTTPException: Если аккаунт не найден
        """
        account = await AccountService.get_account(db, account_id, user_id)

        # Обновление только переданных полей
        update_data = account_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(account, field, value)

        try:
            await db.commit()
            await db.refresh(account)
            return account
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "DATABASE_ERROR",
                    "message": "Ошибка при обновлении аккаунта"
                }
            )

    @staticmethod
    async def delete_account(
        db: AsyncSession,
        account_id: int,
        user_id: int
    ) -> None:
        """
        Удаление аккаунта.

        Args:
            db: Асинхронная сессия БД
            account_id: ID аккаунта
            user_id: ID пользователя для проверки прав

        Raises:
            HTTPException: Если аккаунт не найден
        """
        account = await AccountService.get_account(db, account_id, user_id)

        await db.delete(account)
        await db.commit()

    @staticmethod
    async def update_connection_status(
        db: AsyncSession,
        account_id: int,
        is_connected: bool
    ) -> Account:
        """
        Обновление статуса подключения аккаунта.

        Args:
            db: Асинхронная сессия БД
            account_id: ID аккаунта
            is_connected: Новый статус подключения

        Returns:
            Account: Обновленный аккаунт
        """
        result = await db.execute(
            select(Account).filter(Account.id == account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ACCOUNT_NOT_FOUND",
                    "message": "Аккаунт не найден"
                }
            )

        account.is_connected = is_connected
        account.update_last_activity()

        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    async def update_session(
        db: AsyncSession,
        account_id: int,
        session_string: str
    ) -> Account:
        """
        Обновление session_string аккаунта после авторизации.

        Args:
            db: Асинхронная сессия БД
            account_id: ID аккаунта
            session_string: Строка сессии Telethon

        Returns:
            Account: Обновленный аккаунт
        """
        result = await db.execute(
            select(Account).filter(Account.id == account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ACCOUNT_NOT_FOUND",
                    "message": "Аккаунт не найден"
                }
            )

        account.session_string = session_string
        account.is_connected = True
        account.update_last_activity()

        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    async def get_account_by_phone(
        db: AsyncSession,
        phone: str
    ) -> Account | None:
        """
        Получение аккаунта по номеру телефона.

        Args:
            db: Асинхронная сессия БД
            phone: Номер телефона

        Returns:
            Account | None: Найденный аккаунт или None
        """
        result = await db.execute(
            select(Account).filter(Account.phone == phone)
        )
        return result.scalar_one_or_none()


# Экспорт сервиса
__all__ = ["AccountService"]
