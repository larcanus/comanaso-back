"""
Главный модуль FastAPI приложения.
Настройка приложения, middleware, роутеров и lifecycle events.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging
import time
from typing import Callable
import colorlog

from app.config import settings
from app.database import engine, Base, init_db

# Добавляем импорт TelethonManager
from app.utils.telethon_client import TelethonManager

# Импорт роутеров
from app.api.routes import auth, accounts, dev, telegram

# Настройка цветного логирования с эмодзи
def setup_logging():
    """Настройка логирования с цветами и эмодзи."""
    # Определяем формат с эмодзи
    log_format = (
        "%(log_color)s%(levelname_emoji)s %(asctime)s - %(name)s - "
        "%(levelname)s - %(message)s%(reset)s"
    )

    # Настройка цветов для разных уровней
    log_colors = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white',
    }

    # Создаем кастомный форматтер
    formatter = colorlog.ColoredFormatter(
        log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=log_colors,
        reset=True,
        style='%'
    )

    # Добавляем эмодзи фильтр
    class EmojiFilter(logging.Filter):
        EMOJI_MAP = {
            'DEBUG': '🔍',
            'INFO': '✅',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🔥',
        }

        def filter(self, record):
            record.levelname_emoji = self.EMOJI_MAP.get(record.levelname, '📝')
            return True

    # Настройка хендлера
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(EmojiFilter())

    # Настройка root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Настройка уровня для SQLAlchemy (чтобы меньше шума)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    # Настройка для uvicorn
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)

# Инициализируем логирование
setup_logging()
logger = logging.getLogger(__name__)

# Белый список роутов для упрощенного формата ошибок
SIMPLIFIED_ERROR_ROUTES = [
    "/api/auth",
    "/api/accounts",
]


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

    # Создаём единый TelethonManager и сохраняем в state (для зависимостей)
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


# Middleware для логирования HTTP запросов
@app.middleware("http")
async def log_requests(request: Request, call_next: Callable):
    """Middleware для логирования всех HTTP запросов с временем выполнения."""
    start_time = time.time()

    # Определяем протокол (HTTP/HTTPS)
    protocol = "HTTPS" if request.url.scheme == "https" else "HTTP"
    forwarded_proto = request.headers.get("x-forwarded-proto", "").upper()
    if forwarded_proto in ["HTTP", "HTTPS"]:
        protocol = forwarded_proto

    # Логируем входящий запрос
    logger.info(
        f"📥 {protocol} {request.method} {request.url.path} - "
        f"Client: {request.client.host}"
    )

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Определяем эмодзи и уровень лога по статус-коду
        if response.status_code < 400:
            emoji = "✅"
            log_level = logger.info
        elif response.status_code < 500:
            emoji = "⚠️"
            log_level = logger.warning
        else:
            emoji = "❌"
            log_level = logger.error

        log_level(
            f"{emoji} {protocol} {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )

        return response
    except Exception as exc:
        process_time = time.time() - start_time
        logger.error(
            f"❌ {protocol} {request.method} {request.url.path} - "
            f"Error: {str(exc)} - "
            f"Time: {process_time:.3f}s"
        )
        raise


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Обработчик HTTPException с упрощенным форматом для публичных API."""
    logger.warning(f"⚠️ HTTPException on {request.url.path}: {exc.status_code} - {exc.detail}")

    path = request.url.path
    use_simplified = any(path.startswith(route) for route in SIMPLIFIED_ERROR_ROUTES)

    if use_simplified and isinstance(exc.detail, dict):
        # Возвращаем содержимое detail без обертки
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    # Стандартный формат FastAPI для остальных роутов
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации Pydantic."""
    logger.warning(f"⚠️ Validation error on {request.url.path}: {exc.errors()}")

    # Проверяем, нужен ли упрощенный формат для этого роута
    path = request.url.path
    use_simplified = any(path.startswith(route) for route in SIMPLIFIED_ERROR_ROUTES)

    if use_simplified:
        # Упрощенный формат для публичных API
        first_error = exc.errors()[0]
        error_msg = first_error.get("msg", "Validation error")

        # Очищаем сообщение от "Value error, " если есть
        if error_msg.startswith("Value error, "):
            error_msg = error_msg.replace("Value error, ", "")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": error_msg
            }
        )

    # Детальный формат для dev endpoints и отладки
    errors = []
    for error in exc.errors():
        error_dict = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": error.get("input")
        }
        # Преобразуем ctx, если есть ValueError
        if "ctx" in error and "error" in error["ctx"]:
            ctx_error = error["ctx"]["error"]
            if isinstance(ctx_error, ValueError):
                error_dict["ctx"] = {"error": str(ctx_error)}
            else:
                error_dict["ctx"] = error["ctx"]
        errors.append(error_dict)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": errors,
            "body": str(exc.body) if exc.body else None
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Обработчик ошибок базы данных."""
    logger.error(f"❌ Database error on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "error": str(exc) if settings.debug else "Internal server error"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик всех остальных исключений."""
    logger.error(f"🔥 Unexpected error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else None
        }
    )


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

# Подключаем telegram роуты под общим префиксом /api
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