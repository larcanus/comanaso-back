"""
Alembic environment configuration.
Настройка окружения для миграций базы данных.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base
from app.config import settings

# Импортируем все модели для автогенерации миграций
from app.models.user import User
from app.models.account import Account

# Конфигурация Alembic
config = context.config

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные для автогенерации миграций
target_metadata = Base.metadata

# Переопределяем DATABASE_URL из переменных окружения
# Используем синхронный драйвер psycopg2 вместо asyncpg
database_url = settings.database_url.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """
    Запуск миграций в 'offline' режиме.
    Генерирует SQL скрипты без подключения к БД.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Запуск миграций в 'online' режиме.
    Подключается к БД и применяет изменения.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
