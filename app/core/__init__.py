"""Core модули приложения."""

from app.core.logging import setup_logging
from app.core.events import lifespan
from app.core.exceptions import register_exception_handlers

__all__ = [
    "setup_logging",
    "lifespan",
    "register_exception_handlers",
]
