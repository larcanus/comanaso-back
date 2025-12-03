"""
Сервис для управления Telegram аккаунтами.
Бизнес-логика CRUD операций с аккаунтами.
"""
from sqlalchemy.orm import Session
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
    def create_account(
        db: Session,
        user_id: int,
        account_data: AccountCreate
    ) -> Account:
        """
        Создание нового Telegram аккаунта.
        
        Args:
            db: Сессия БД
            user_id: ID пользователя-владельца
            account_data: Данные для создания аккаунта
            
        Returns:
            Account: Созданный аккаунт
            
        Raises:
            HTTPException: Если номер телефона уже используется
        """
        # Проверка существования номера
        existing = db.query(Account).filter(
            Account.phone == account_data.phone
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Аккаунт с номером {account_data.phone} уже существует"
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
            db.commit()
            db.refresh(db_account)
            return db_account
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при создании аккаунта"
            )
    
    @staticmethod
    def get_account(
        db: Session,
        account_id: int,
        user_id: int
    ) -> Account:
        """
        Получение аккаунта по ID с проверкой владельца.
        
        Args:
            db: Сессия БД
            account_id: ID аккаунта
            user_id: ID пользователя для проверки прав
            
        Returns:
            Account: Найденный аккаунт
            
        Raises:
            HTTPException: Если аккаунт не найден или нет прав доступа
        """
        account = db.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id
        ).first()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Аккаунт не найден"
            )
        
        return account
    
    @staticmethod
    def get_user_accounts(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Account]:
        """
        Получение всех аккаунтов пользователя с пагинацией.
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            skip: Количество пропускаемых записей
            limit: Максимальное количество записей
            
        Returns:
            List[Account]: Список аккаунтов пользователя
        """
        return db.query(Account).filter(
            Account.user_id == user_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_account(
        db: Session,
        account_id: int,
        user_id: int,
        account_data: AccountUpdate
    ) -> Account:
        """
        Обновление данных аккаунта.
        
        Args:
            db: Сессия БД
            account_id: ID аккаунта
            user_id: ID пользователя для проверки прав
            account_data: Новые данные аккаунта
            
        Returns:
            Account: Обновленный аккаунт
            
        Raises:
            HTTPException: Если аккаунт не найден
        """
        account = AccountService.get_account(db, account_id, user_id)
        
        # Обновление только переданных полей
        update_data = account_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(account, field, value)
        
        try:
            db.commit()
            db.refresh(account)
            return account
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при обновлении аккаунта"
            )
    
    @staticmethod
    def delete_account(
        db: Session,
        account_id: int,
        user_id: int
    ) -> None:
        """
        Удаление аккаунта.
        
        Args:
            db: Сессия БД
            account_id: ID аккаунта
            user_id: ID пользователя для проверки прав
            
        Raises:
            HTTPException: Если аккаунт не найден
        """
        account = AccountService.get_account(db, account_id, user_id)
        
        db.delete(account)
        db.commit()
    
    @staticmethod
    def update_connection_status(
        db: Session,
        account_id: int,
        is_connected: bool
    ) -> Account:
        """
        Обновление статуса подключения аккаунта.
        
        Args:
            db: Сессия БД
            account_id: ID аккаунта
            is_connected: Новый статус подключения
            
        Returns:
            Account: Обновленный аккаунт
        """
        account = db.query(Account).filter(Account.id == account_id).first()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Аккаунт не найден"
            )
        
        account.is_connected = is_connected
        account.update_last_activity()
        
        db.commit()
        db.refresh(account)
        return account
    
    @staticmethod
    def update_session(
        db: Session,
        account_id: int,
        session_string: str
    ) -> Account:
        """
        Обновление session_string аккаунта после авторизации.
        
        Args:
            db: Сессия БД
            account_id: ID аккаунта
            session_string: Строка сессии Telethon
            
        Returns:
            Account: Обновленный аккаунт
        """
        account = db.query(Account).filter(Account.id == account_id).first()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Аккаунт не найден"
            )
        
        account.session_string = session_string
        account.is_connected = True
        account.update_last_activity()
        
        db.commit()
        db.refresh(account)
        return account
    
    @staticmethod
    def get_account_by_phone(
        db: Session,
        phone: str
    ) -> Account | None:
        """
        Получение аккаунта по номеру телефона.
        
        Args:
            db: Сессия БД
            phone: Номер телефона
            
        Returns:
            Account | None: Найденный аккаунт или None
        """
        return db.query(Account).filter(Account.phone == phone).first()


# Экспорт сервиса
__all__ = ["AccountService"]