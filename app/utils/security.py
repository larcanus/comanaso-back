"""Утилиты для работы с паролями."""

from passlib.context import CryptContext

# Контекст для хеширования паролей с использованием bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием bcrypt.
    
    Args:
        password: Открытый пароль
        
    Returns:
        Хешированный пароль
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие открытого пароля хешу.
    
    Args:
        plain_password: Открытый пароль
        hashed_password: Хешированный пароль
        
    Returns:
        True если пароль совпадает, иначе False
    """
    return pwd_context.verify(plain_password, hashed_password)