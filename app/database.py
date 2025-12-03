"""
Конфигурация базы данных.
Настройка SQLAlchemy для асинхронной работы с PostgreSQL.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


# Базовый класс для всех моделей
class Base(DeclarativeBase):
    """Базовый класс для SQLAlchemy моделей."""
    pass


# Создание асинхронного движка с условной конфигурацией
if settings.debug:
    # В режиме отладки используем NullPool без параметров пула
    engine: AsyncEngine = create_async_engine(
        settings.database_url,
        echo=True,  # Логирование SQL запросов в debug режиме
        poolclass=NullPool,  # Отключение пула в debug
        pool_pre_ping=True,  # Проверка соединения перед использованием
    )
else:
    # В production используем стандартный пул с настройками
    engine: AsyncEngine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,  # Проверка соединения перед использованием
        pool_size=5,  # Размер пула соединений
        max_overflow=10,  # Максимальное количество дополнительных соединений
    )

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Не истекать объекты после commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии базы данных.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy

    Example:
        ```python
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
        ```
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Инициализация базы данных.
    Создает все таблицы, если они не существуют.

    Note:
        В production используйте Alembic для миграций.
    """
    async with engine.begin() as conn:
        # В production закомментируйте эту строку и используйте Alembic
        if settings.debug:
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Закрытие соединений с базой данных.
    Вызывается при остановке приложения.
    """
    await engine.dispose()
