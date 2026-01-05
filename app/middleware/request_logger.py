"""
Middleware для логирования HTTP запросов.
Отслеживание всех входящих запросов с временем выполнения.
"""
import time
import logging
from typing import Callable
from fastapi import Request

logger = logging.getLogger(__name__)


async def log_requests_middleware(request: Request, call_next: Callable):
    """
    Middleware для логирования всех HTTP запросов с временем выполнения.

    Args:
        request: Входящий HTTP запрос
        call_next: Следующий middleware или endpoint handler

    Returns:
        Response от следующего обработчика
    """
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