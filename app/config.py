"""
Конфигурация приложения.
Загружает и валидирует переменные окружения.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import os


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    # Основные настройки
    app_name: str = Field(default="Comanaso API", description="Название приложения")
    debug: bool = Field(default=False, description="Режим отладки")
    project_name: str = Field(default="Comanaso API", description="Название проекта")
    version: str = Field(default="1.0.0", description="Версия API")
    environment: str = Field(default="development", description="Окружение")
    log_level: str = Field(default="info", description="Уровень логирования")

    # База данных
    database_url: str = Field(..., description="URL подключения к PostgreSQL")

    # JWT
    secret_key: str = Field(..., alias="JWT_SECRET", description="Секретный ключ для JWT")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM", description="Алгоритм шифрования JWT")
    access_token_expire_minutes: int = Field(
        default=1440,
        alias="JWT_EXPIRATION_HOURS",
        description="Время жизни access токена в минутах"
    )

    # CORS
    cors_origins: str = Field(
        default="*",
        description="Разрешенные origins для CORS (через запятую)"
    )

    # Telegram API
    telegram_api_id: Optional[int] = Field(default=None, description="Telegram API ID")
    telegram_api_hash: Optional[str] = Field(default=None, description="Telegram API Hash")

    # Пути
    sessions_dir: str = Field(default="./sessions", description="Директория для сессий Telegram")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("access_token_expire_minutes", mode="before")
    @classmethod
    def convert_hours_to_minutes(cls, v) -> int:
        """Конвертирует часы в минуты для JWT_EXPIRATION_HOURS."""
        if v is None:
            return 1440
        v = int(v)
        # Если значение больше 100, считаем что это уже минуты
        if v > 100:
            return v
        # Иначе конвертируем часы в минуты
        return v * 60

    @field_validator("cors_origins", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Парсит CORS origins из строки в список."""
        if not v or v.strip() == "":
            return ["*"]
        if v.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("sessions_dir", mode="after")
    @classmethod
    def validate_sessions_dir(cls, v: str) -> str:
        """Проверяет и создает директорию для сессий."""
        if not os.path.exists(v):
            os.makedirs(v, exist_ok=True)
        return v

    @field_validator("telegram_api_id", mode="before")
    @classmethod
    def validate_telegram_api_id(cls, v) -> Optional[int]:
        """Валидация Telegram API ID."""
        if v is None or v == "" or v == "0":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator("telegram_api_hash", mode="before")
    @classmethod
    def validate_telegram_api_hash(cls, v) -> Optional[str]:
        """Валидация Telegram API Hash."""
        if v is None or v == "":
            return None
        return str(v)


# Глобальный экземпляр настроек
settings = Settings()
