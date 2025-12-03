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
import logging
import time

from app.config import settings
from app.database import engine, Base, init_db, close_db

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
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"CORS origins: {settings.cors_origins}")

    try:
        await init_db()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized successfully")
        logger.info("✅ Database tables created")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Comanaso API...")
    await close_db()
    logger.info("Database connections closed")


# Создание FastAPI приложения
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Backend API для управления Telegram аккаунтами",
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


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Добавляет заголовок с временем обработки запроса."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех HTTP запросов."""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Status: {response.status_code}")
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации Pydantic."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Обработчик ошибок базы данных."""
    logger.error(f"Database error: {str(exc)}")
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
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else None
        }
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Проверка работоспособности API"
)
async def health_check():
    """
    Endpoint для проверки работоспособности API.
    Используется для health checks в Docker и мониторинге.
    """
    return {
        "status": "healthy",
        "version": settings.version,
        "environment": settings.environment
    }


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="Root endpoint",
    description="Корневой endpoint API"
)
async def root():
    """Корневой endpoint с информацией об API."""
    return {
        "message": "Comanaso API",
        "version": settings.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }


# Подключение роутеров
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level
    )
