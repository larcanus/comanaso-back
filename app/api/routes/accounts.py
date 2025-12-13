"""
API роутер для управления Telegram аккаунтами.
CRUD операции с аккаунтами пользователя.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountDetailResponse
)
from app.services.account_service import AccountService
from app.api.dependencies import CurrentUser

router = APIRouter(
    tags=["accounts"]
)


@router.post(
    "",
    response_model=AccountDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый Telegram аккаунт"
)
async def create_account(
    account_data: AccountCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Создание нового Telegram аккаунта.

    - **phone**: Номер телефона в международном формате
    - **api_id**: Telegram API ID (получить на my.telegram.org)
    - **api_hash**: Telegram API Hash
    - **name**: Имя аккаунта (опционально)

    Возвращает созданный аккаунт с ID.
    """
    account = await AccountService.create_account(
        db=db,
        user_id=current_user.id,
        account_data=account_data
    )
    return account


@router.get(
    "",
    response_model=list[AccountResponse],
    summary="Получить список всех аккаунтов"
)
async def get_accounts(
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentUser = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None
):
    """
    Получение списка всех Telegram аккаунтов текущего пользователя.

    - **skip**: Количество пропускаемых записей (для пагинации)
    - **limit**: Максимальное количество записей

    Возвращает массив аккаунтов с полной информацией.
    Каждый элемент содержит 8 обязательных полей: id, name, phoneNumber, apiId, apiHash, status, createdAt, updatedAt.
    """
    accounts = await AccountService.get_user_accounts(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )

    return [AccountResponse.model_validate(acc) for acc in accounts]


@router.get(
    "/{account_id}",
    response_model=AccountDetailResponse,
    summary="Получить аккаунт по ID"
)
async def get_account(
    account_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Получение детальной информации о Telegram аккаунте.

    - **account_id**: ID аккаунта

    Возвращает полную информацию об аккаунте.
    Доступ только для владельца аккаунта.
    """
    account = await AccountService.get_account(
        db=db,
        account_id=account_id,
        user_id=current_user.id
    )
    return account


@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Обновить данные аккаунта"
)
async def update_account(
    account_id: int,
    account_data: AccountUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Обновление данных Telegram аккаунта.

    - **account_id**: ID аккаунта
    - **name**: Новое имя аккаунта (опционально)
    - **phoneNumber**: Новый номер телефона (опционально)
    - **api_id**: Новый API ID (опционально)
    - **api_hash**: Новый API Hash (опционально)

    Возвращает обновленный аккаунт с 8 полями: id, name, phoneNumber, apiId, apiHash, status, createdAt, updatedAt.
    Доступ только для владельца аккаунта.
    """
    account = await AccountService.update_account(
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
async def delete_account(
    account_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Удаление Telegram аккаунта.

    - **account_id**: ID аккаунта

    Удаляет аккаунт и все связанные данные.
    Доступ только для владельца аккаунта.
    """
    await AccountService.delete_account(
        db=db,
        account_id=account_id,
        user_id=current_user.id
    )
    return None
