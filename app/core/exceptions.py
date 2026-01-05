"""
Модуль обработки исключений для FastAPI приложения.
Централизованная обработка ошибок с логированием.
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

logger = logging.getLogger(__name__)

# Белый список роутов для упрощенного формата ошибок
SIMPLIFIED_ERROR_ROUTES = [
    "/api/auth",
    "/api/accounts",
]


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


def register_exception_handlers(app):
    """
    Регистрация всех exception handlers в FastAPI приложении.

    Args:
        app: FastAPI приложение
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)