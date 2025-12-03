"""
API роутер для управления Telegram аккаунтами.
CRUD операции с аккаунтами пользователя.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.auth import UserResponse
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountDetailResponse,
    AccountListResponse
)
from app.services.account_service import AccountService
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"]
)


@router.post(
    "/",
    response_model=AccountDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый Telegram аккаунт"
)
def create_account(
    account_data: AccountCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создание нового Telegram аккаунта.
    
    - **phone**: Номер телефона в международном формате
    - **api_id**: Telegram API ID (получить на my.telegram.org)
    - **api_hash**: Telegram API Hash
    - **name**: Имя аккаунта (опционально)
    
    Возвращает созданный аккаунт с ID.
    """
    account = AccountService.create_account(
        db=db,
        user_id=current_user.id,
        account_data=account_data
    )
    return account


@router.get(
    "/",
    response_model=AccountListResponse,
    summary="Получить список всех аккаунтов"
)
def get_accounts(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение списка всех Telegram аккаунтов текущего пользователя.
    
    - **skip**: Количество пропускаемых записей (для пагинации)
    - **limit**: Максимальное количество записей
    
    Возвращает список аккаунтов с основной информацией.
    """
    accounts = AccountService.get_user_accounts(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return AccountListResponse(
        accounts=[AccountResponse.model_validate(acc) for acc in accounts],
        total=len(accounts)
    )


@router.get(
    "/{account_id}",
    response_model=AccountDetailResponse,
    summary="Получить аккаунт по ID"
)
def get_account(
    account_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получение детальной информации о Telegram аккаунте.
    
    - **account_id**: ID аккаунта
    
    Возвращает полную информацию об аккаунте.
    Доступ только для владельца аккаунта.
    """
    account = AccountService.get_account(
        db=db,
        account_id=account_id,
        user_id=current_user.id
    )
    return account


@router.put(
    "/{account_id}",
    response_model=AccountDetailResponse,
    summary="Обновить данные аккаунта"
)
def update_account(
    account_id: int,
    account_data: AccountUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Обновление данных Telegram аккаунта.
    
    - **account_id**: ID аккаунта
    - **name**: Новое имя аккаунта (опционально)
    - **api_id**: Новый API ID (опционально)
    - **api_hash**: Новый API Hash (опционально)
    
    Возвращает обновленный аккаунт.
    Доступ только для владельца аккаунта.
    """
    account = AccountService.update_account(
        db=db,
        account_id=account_id,
        user_id=current_user.id,
        account_data=account_data
    )
    return account


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить аккаунт"
)
def delete_account(
    account_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Удаление Telegram аккаунта.
    
    - **account_id**: ID аккаунта
    
    Удаляет аккаунт и все связанные данные.
    Доступ только для владельца аккаунта.
    """
    AccountService.delete_account(
        db=db,
        account_id=account_id,
        user_id=current_user.id
    )
    return None


# Экспорт роутера
__all__ = ["router"]