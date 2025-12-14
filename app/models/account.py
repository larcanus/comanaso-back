"""
SQLAlchemy модель Telegram аккаунта.
Хранит данные о подключенных Telegram аккаунтах.
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Account(Base):
    """
    Модель Telegram аккаунта.

    Attributes:
        id: Уникальный идентификатор аккаунта
        user_id: ID владельца аккаунта
        phone: Номер телефона
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        session_string: Строка сессии Telethon (зашифрованная)
        name: Имя аккаунта (опционально)
        is_connected: Статус подключения
        last_activity: Время последней активности
        created_at: Дата добавления
        updated_at: Дата последнего обновления
        owner: Связь с пользователем
    """

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint('user_id', 'phone', name='uq_user_phone'),
    )

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Foreign key
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Telegram данные
    phone: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False
    )
    api_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    api_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    session_string: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    # Метаданные
    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )
    is_connected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    last_activity: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
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
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="accounts",
        lazy="selectin"
    )

    @property
    def status(self) -> str:
        """
        Вычисляемое свойство статуса аккаунта.

        Returns:
            str: 'online' если подключен, иначе 'offline'
        """
        return "online" if self.is_connected else "offline"

    def update_last_activity(self) -> None:
        """Обновление времени последней активности."""
        self.last_activity = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, phone='{self.phone}', is_connected={self.is_connected})>"