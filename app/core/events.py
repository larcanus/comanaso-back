"""
Модуль lifecycle events для FastAPI приложения.
Управление запуском и остановкой сервисов.
"""
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI

from app.config import settings
from app.database import engine, Base, init_db
from app.utils.telethon_client import TelethonManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events для FastAPI приложения.
    Выполняется при запуске и остановке приложения.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 Starting Comanaso API...")
    logger.info(f"📦 Environment: {settings.environment}")
    logger.info(f"🔧 Debug mode: {settings.debug}")
    logger.info(f"🌐 CORS origins: {settings.cors_origins}")

    try:
        await init_db()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    # Создаём единый TelethonManager и сохраняем в state
    app.state.telethon_manager = TelethonManager()
    logger.info("✅ TelethonManager initialized and stored in app.state")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 Shutting down Comanaso API...")

    # Корректно отключаем всех Telethon клиентов
    tm = getattr(app.state, "telethon_manager", None)
    if tm:
        try:
            await tm.disconnect_all()
            logger.info("✅ TelethonManager disconnected all clients")
        except Exception as e:
            logger.warning(f"⚠️ TelethonManager disconnect_all raised an error: {e}")

    await engine.dispose()
    logger.info("✅ Database connections closed")
    logger.info("=" * 60)