"""
SQLAlchemy модель пользователя.
Хранит данные о пользователях системы.
"""
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, TYPE_CHECKING

from app.database import Base

if TYPE_CHECKING:
    from app.models.account import Account


class User(Base):
    """
    Модель пользователя системы.

    Attributes:
        id: Уникальный идентификатор пользователя
        email: Email пользователя (уникальный, опциональный)
        username: Имя пользователя (уникальное)
        hashed_password: Хешированный пароль
        is_active: Активен ли пользователь
        is_superuser: Является ли суперпользователем
        created_at: Дата создания
        updated_at: Дата последнего обновления
        accounts: Связанные Telegram аккаунты
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Учетные данные
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True  # Email теперь опционален
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # Статус
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    accounts: Mapped[List["Account"]] = relationship(
        "Account",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"