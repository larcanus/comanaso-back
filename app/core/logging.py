"""
Модуль настройки логирования приложения.
Цветное логирование с эмодзи для удобной отладки.
"""
import logging
import colorlog


def setup_logging(log_level: str = "INFO"):
    """
    Настройка логирования с цветами и эмодзи.

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
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
    root_logger.setLevel(log_level.upper())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Настройка уровня для SQLAlchemy (чтобы меньше шума)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    # Настройка для uvicorn
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)