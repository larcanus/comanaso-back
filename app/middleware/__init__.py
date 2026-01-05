"""Middleware компоненты приложения.

Доступные middleware:
- request_logger.log_requests_middleware: Логирование HTTP запросов
"""

from app.middleware.request_logger import log_requests_middleware

__all__ = ["log_requests_middleware"]