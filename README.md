# Comanaso Backend

Python FastAPI backend для управления Telegram аккаунтами.

## Требования

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 15+ (через Docker)

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd comanaso-back

```

## 6. BACKEND IMPLEMENTATION HINTS

### 6.1 Структура проекта

```
backend/
├── test/
│   ├── accounts.ps1
│   └── auth.ps1
├── alembic/
│   ├── versions/
│   ├── script.py.mako
│   └── env.py                      # Alembic environment configuration. Настройка окружения для миграций базы данных.
├── app/
│   ├── main.py                     # FastAPI app. Настройка приложения, middleware, роутеров и lifecycle events.
│   ├── config.py                   # Настройки
│   ├── database.py                 # SQLAlchemy setup
│   ├── models/
│   │   ├── user.py                 # SQLAlchemy модель пользователя. Хранит данные о пользователях системы.
│   │   └── account.py              # SQLAlchemy модель Telegram аккаунта. Хранит данные о подключенных Telegram аккаунтах.
│   ├── schemas/
│   │   ├── auth.py                 # Pydantic схемы для аутентификации. Валидация данных для регистрации, логина и токенов.
│   │   ├── telegram.py             # Pydantic схемы для Telegram операций. Валидация данных для работы с Telegram API.
│   │   └── account.py              # Pydantic схемы для работы с Telegram аккаунтами.
│   ├── services/
│   │   ├── auth_service.py         # Сервис для работы с аутентификацией пользователей
│   │   ├── account_service.py      # Сервис для управления Telegram аккаунтами. Бизнес-логика CRUD операций с аккаунтами.
│   │   └── telegram_service.py     # файла нет - какая-то логика с телетон
│   ├── utils/
│   │   ├── jwt.py                  # Утилиты для работы с JWT токенами.
│   │   ├── security.py             # Утилиты для работы с паролями.
│   │   └── telethon_client.py      # файла нет - какая-то логика с телетон
│   └── api/
│         ├──  dependencies.py      # FastAPI dependencies для аутентификации и авторизации. Кастомный HTTPBearer с правильным форматом ошибок.
│         └──  routers/
│               ├── auth.py         # API роутер для управления аутентификацией пользователей.
│               ├── accounts.py     # API роутер для управления Telegram аккаунтами. CRUD операции с аккаунтами пользователя.
│               ├── dev.py          # Development/Testing endpoints. Используются только в dev окружении для тестирования.
│               └── telegram.py     # файла нет - какая-то логика с телетон
├── requirements.txt                # FastAPI и веб-сервер (пакеты)
└── .env
```

### 6.2 Основные зависимости

```txt:requirements.txt
fastapi==0.115.5
uvicorn[standard]==0.32.1
telethon==1.42.0
sqlalchemy==2.0.36
pydantic==2.10.3
alembic==1.14.1
aiosmtplib==5.0.0
```