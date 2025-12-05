"""
Главный модуль FastAPI приложения.
Настройка приложения, middleware, роутеров и lifecycle events.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

from app.config import settings
from app.database import engine, Base, init_db

# Импорт роутеров
from app.api.routes import auth, accounts, dev

# Настройка логирования
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events для FastAPI приложения.
    Выполняется при запуске и остановке приложения.
    """
    # Startup
    logger.info("Starting Comanaso API...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"CORS origins: {settings.cors_origins}")

    try:
        await init_db()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Comanaso API...")
    await engine.dispose()
    logger.info("✅ Database connections closed")


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


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации Pydantic."""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")

    # Преобразуем ошибки в сериализуемый формат
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
    logger.error(f"Database error on {request.url.path}: {str(exc)}")
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
    logger.error(f"Unexpected error on {request.url.path}: {str(exc)}", exc_info=True)
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
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["database"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status


# Подключение роутеров
app.include_router(auth.router, prefix="/api/auth")
app.include_router(accounts.router, prefix="/api/accounts")

# Dev endpoints (только для development окружения)
if settings.environment == "development":
    app.include_router(dev.router, prefix="/api/dev")
    logger.info("✅ Development endpoints enabled at /api/dev")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
