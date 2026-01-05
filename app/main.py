"""
Главный модуль FastAPI приложения.
Настройка приложения, middleware, роутеров и lifecycle events.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import logging

from app.config import settings
from app.database import engine
from app.core import setup_logging, lifespan, register_exception_handlers
from app.middleware import log_requests_middleware
from app.api.routes import auth, accounts, dev, telegram

# Инициализируем логирование
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

# Создание FastAPI приложения
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Backend API для управления Telegram аккаунтами и автоматизации",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Регистрация middleware
app.middleware("http")(log_requests_middleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Регистрация exception handlers
register_exception_handlers(app)


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="Root endpoint",
    description="Корневой endpoint с информацией об API"
)
async def root():
    """Корневой endpoint с информацией об API."""
    return {
        "message": "Comanaso API",
        "version": settings.version,
        "environment": settings.environment,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Проверка работоспособности API и подключения к БД"
)
async def health_check():
    """
    Проверка состояния сервиса и подключения к БД.
    Возвращает статус healthy/degraded/unhealthy.
    """
    health_status = {
        "status": "healthy",
        "version": settings.version,
        "environment": settings.environment,
        "database": "unknown",
        "debug": settings.debug
    }

    # Проверка подключения к БД
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.commit()
        health_status["database"] = "healthy"
        logger.debug("🔍 Health check: Database connection OK")
    except Exception as e:
        logger.error(f"❌ Database health check failed: {str(e)}")
        health_status["database"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status


# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth")
app.include_router(accounts.router, prefix="/api/accounts")
app.include_router(telegram.router, prefix="/api")

# Dev endpoints (только для development окружения)
if settings.environment == "development":
    app.include_router(dev.router, prefix="/api/dev")
    logger.info("🔧 Development endpoints enabled at /api/dev")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )