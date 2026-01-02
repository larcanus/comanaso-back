# comanaso-back
# API КОНТРАКТ ДЛЯ COMANASO BACKEND

## Общая информация

**Backend**: Python + FastAPI  
**Telegram Library**: Telethon 1.38.1  
**Authentication**: JWT (Bearer Token)  
**Base URL**: `http://localhost:8000/api` (dev)

---

## 1. AUTHENTICATION

### 1.1 Регистрация пользователя

```http
POST /api/auth/register
Content-Type: application/json

Request:
{
  "email": "string",
  "login": "string",      // 3-50 символов
  "password": "string"    // минимум 6 символов
}

Response 201:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "login": "user123",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}

Response 400:
{
  "error": "USER_EXISTS",
  "message": "Пользователь с таким логином уже существует"
}

Response 422:
{
  "error": "VALIDATION_ERROR",
  "message": "Пароль должен содержать минимум 6 символов"
}
```

### 1.2 Вход в систему

```http
POST /api/auth/login
Content-Type: application/json

Request:
{
  "login": "string",
  "password": "string"
}

Response 200:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "login": "user123",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}

Response 401:
{
  "error": "INVALID_CREDENTIALS",
  "message": "Неверный логин или пароль"
}
```

### 1.3 Проверка токена

```http
GET /api/auth/verify
Authorization: Bearer {token}

Response 200:
{
  "valid": true,
  "user": {
    "id": 1,
    "login": "user123"
  }
}

Response 401:
{
  "error": "INVALID_TOKEN",
  "message": "Токен недействителен или истек"
}
```

### 1.4 Выход из системы (logout)

```http
POST /api/auth/logout
Authorization: Bearer {token}
Content-Type: application/json

Response 200:
{
  "status": "success",
  "message": "Вы успешно вышли из системы"
}

Response 401:
{
  "error": "UNAUTHORIZED",
  "message": "Токен недействителен или отсутствует"
}
```

### 1.5 Удаление учетной записи

```http
DELETE /api/auth/delete-account
Authorization: Bearer {token}

Response 200:
{
  "status": "success",
  "message": "Учетная запись и все связанные данные успешно удалены",
  "deleted_user_id": 1,
  "deleted_accounts_count": 3
}

Response 401:
{
  "error": "UNAUTHORIZED",
  "message": "Требуется авторизация"
}

Response 404:
{
  "error": "USER_NOT_FOUND",
  "message": "Пользователь не найден"
}

Response 500:
{
  "error": "DELETE_FAILED",
  "message": "Не удалось удалить учетную запись"
}
```

### 1.6 Получение профиля пользователя

```http
GET /api/auth/me
Authorization: Bearer {token}

Response 200:
{
  "id": 1,
  "username": "john_doe",
  "email": "user@example.com",
  "settings": {
    "shareUserName": true,      // Разрешить передачу имени пользователя в AI
    "shareNickname": true,       // Разрешить передачу username в AI
    "shareMessageText": true,    // Разрешить передачу текста сообщений в AI
    "shareDialogTitles": true    // Разрешить передачу названий диалогов в AI
  },
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-17T15:30:00Z"
}

Response 401:
{
  "error": "UNAUTHORIZED",
  "message": "Требуется авторизация"
}
```

### 1.7 Обновление профиля пользователя

```http
PATCH /api/auth/me
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "username": "new_username",     // опционально, 3-100 символов
  "email": "newemail@example.com", // опционально, валидный email
  "password": "newemail@example.com", // опционально, валидный пароль
  "settings": {                    // опционально, объект с настройками
    "shareUserName": false,
    "shareNickname": true,
    "shareMessageText": false,
    "shareDialogTitles": true
  }
}

Response 200:
{
  "id": 1,
  "username": "new_username",
  "email": "newemail@example.com",
  "settings": {
    "shareUserName": false,
    "shareNickname": true,
    "shareMessageText": false,
    "shareDialogTitles": true
  },
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-17T16:45:00Z"
}

Response 400 (username занят):
{
  "error": "USERNAME_EXISTS",
  "message": "Пользователь с таким именем уже существует"
}

Response 400 (email занят):
{
  "error": "EMAIL_EXISTS",
  "message": "Пользователь с таким email уже существует"
}

Response 401:
{
  "error": "UNAUTHORIZED",
  "message": "Требуется авторизация"
}

Response 422:
{
  "error": "VALIDATION_ERROR",
  "message": "Неверный формат данных"
}
```

---

## 2. TELEGRAM ACCOUNTS

### 2.1 Получить список аккаунтов

```http
GET /api/accounts
Authorization: Bearer {token}

Response 200:
[
  {
    "id": 1,
    "name": "Рабочий аккаунт",
    "phoneNumber": "+79991234567",
    "apiId": "12345678",
    "apiHash": "abcdef1234567890abcdef1234567890",
    "status": "online",           // online | offline | connecting | error
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-01-15T12:45:00Z"
  },
  {
    "id": 2,
    "name": "Личный",
    "phoneNumber": "+79997654321",
    "apiId": "87654321",
    "apiHash": "1234567890abcdef1234567890abcdef",
    "status": "offline",
    "createdAt": "2024-01-16T09:00:00Z",
    "updatedAt": "2024-01-16T09:00:00Z"
  }
]
```

### 2.2 Создать аккаунт

```http
POST /api/accounts
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "name": "Новый аккаунт",
  "phoneNumber": "+79991234567",
  "apiId": "12345678",
  "apiHash": "abcdef1234567890abcdef1234567890"
}

Response 201:
{
  "id": 3,
  "name": "Новый аккаунт",
  "phoneNumber": "+79991234567",
  "apiId": "12345678",
  "apiHash": "abcdef1234567890abcdef1234567890",
  "status": "offline",
  "createdAt": "2024-01-17T14:20:00Z",
  "updatedAt": "2024-01-17T14:20:00Z"
}

Response 400:
{
  "error": "ACCOUNT_EXISTS",
  "message": "Аккаунт с таким номером уже добавлен"
}

Response 422:
{
  "error": "VALIDATION_ERROR",
  "message": "Неверный формат номера телефона"
}
```

### 2.3 Обновить данные аккаунта

```http
PATCH /api/accounts/{accountId}
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "name": "Обновленное название",   // опционально
  "apiId": "12345678",              // опционально
  "apiHash": "new_hash",            // опционально
  "phoneNumber": "+79991234567"     // опционально
}

Response 200:
{
  "id": 1,
  "name": "Обновленное название",
  "phoneNumber": "+79991234567",
  "apiId": "12345678",
  "apiHash": "new_hash",
  "status": "offline",
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-17T15:00:00Z"
}

Response 403:
{
  "error": "ACCOUNT_CONNECTED",
  "message": "Невозможно изменить данные подключенного аккаунта"
}

Response 404:
{
  "error": "ACCOUNT_NOT_FOUND",
  "message": "Аккаунт не найден"
}
```

### 2.4 Удалить аккаунт

```http
DELETE /api/accounts/{accountId}
Authorization: Bearer {token}

Response 204: (No Content)

Response 403:
{
  "error": "ACCOUNT_CONNECTED",
  "message": "Отключите аккаунт перед удалением"
}

Response 404:
{
  "error": "ACCOUNT_NOT_FOUND",
  "message": "Аккаунт не найден"
}
```

---

## 3. TELEGRAM CONNECTION

### 3.1 Подключить аккаунт (начать авторизацию)

```http
POST /api/accounts/{accountId}/connect
Authorization: Bearer {token}

Response 200 (уже авторизован):
{
  "status": "online",
  "message": "Аккаунт уже подключен"
}

Response 200 (нужен код):
{
  "status": "code_required",
  "message": "Код отправлен в Telegram",
}

Response 400:
{
  "error": "INVALID_API_CREDENTIALS",
  "message": "Неверный API ID или API Hash"
}

Response 409:
{
  "error": "ALREADY_CONNECTED",
  "message": "Аккаунт уже подключен"
}
```

### 3.2 Подтвердить код авторизации

```http
POST /api/accounts/{accountId}/verify-code
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "code": "12345",
}

Response 200 (успех без 2FA):
{
  "status": "connected",
  "message": "Аккаунт успешно подключен"
}

Response 200 (нужен 2FA):
{
  "status": "password_required",
  "message": "Требуется 2FA пароль",
  "passwordHint": "Первая буква имени..."  // может быть null
}

Response 400:
{
  "error": "INVALID_CODE",
  "message": "Неверный код подтверждения"
}

Response 400:
{
  "error": "EXPIRED_CODE",
  "message": "Код истек, запросите новый"
}

Response 403:
{
  "error": "PASSWORD_REQUIRED",
  "message": "Требуется двухфакторная аутентификация",
  "passwordHint": "Первая буква имени питомца"
}
```

### 3.3 Подтвердить 2FA пароль

```http
POST /api/accounts/{accountId}/verify-password
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "password": "my_secret_password"
}

Response 200:
{
  "status": "online",
  "message": "Аккаунт успешно подключен",
}

Response 400:
{
  "error": "INVALID_PASSWORD",
  "message": "Неверный пароль"
}
```

### 3.4 Отключить аккаунт

```http
POST /api/accounts/{accountId}/disconnect
Authorization: Bearer {token}

Response 200:
{
  "status": "disconnected",
  "message": "Аккаунт отключен",
}

Response 404:
{
  "error": "ACCOUNT_NOT_FOUND",
  "message": "Аккаунт не найден"
}
```

### 3.5 Выйти из Telegram (logout)

```http
POST /api/accounts/{accountId}/logout
Authorization: Bearer {token}

Response 200:
{
  "status": "logged_out",
  "message": "Выход выполнен, сессия удалена"
}

Response 404:
{
  "error": "ACCOUNT_NOT_CONNECTED",
  "message": "Аккаунт не подключен"
}
```

---

## 4. TELEGRAM DATA (MVP)

### 4.1 Получить информацию об аккаунте

```http
GET /api/accounts/{accountId}/me
Authorization: Bearer {token}

Response 200:
{
  "id": 123456789,
  "firstName": "Иван",
  "lastName": "Петров",
  "username": "ivan_petrov",
  "phone": "+79991234567",
  "bio": "Описание профиля",
  "isBot": false,
  "isVerified": false,
  "isPremium": true,
  "langCode": "ru",
  "photo": {
    "photoId": "5472634066516587521",
    "dcId": 2,
    "hasVideo": false
  },
  "status": {
    "type": "online",  // online | offline | recently | lastWeek | lastMonth
    "wasOnline": "2024-01-17T15:30:00Z"  // если не online
  }
}

Response 403:
{
  "error": "ACCOUNT_NOT_CONNECTED",
  "message": "Аккаунт не подключен к Telegram"
}

Response 404:
{
  "error": "ACCOUNT_NOT_FOUND",
  "message": "Аккаунт не найден"
}
```

### 4.2 Получить аватарку аккаунта

```http
GET /api/accounts/{accountId}/me/photo
Authorization: Bearer {token}
Query Parameters:
  - size: string (default: "big") // "small" или "big"

Response 200:
Content-Type: image/jpeg
Cache-Control: public, max-age=3600
Content-Disposition: inline; filename=profile_{accountId}.jpg

[binary image data]

Response 404 (фото не установлено):
{
  "error": "PHOTO_NOT_FOUND",
  "message": "У пользователя не установлено фото профиля"
}

Response 403:
{
  "error": "ACCOUNT_NOT_CONNECTED",
  "message": "Аккаунт не подключен к Telegram"
}

Response 404 (аккаунт не найден):
{
  "error": "ACCOUNT_NOT_FOUND",
  "message": "Аккаунт не найден"
}
```

### 4.3 Получить список диалогов

```http
GET /api/accounts/{accountId}/dialogs
Authorization: Bearer {token}
Query Parameters:
  - limit: integer (default: 100, max: 500)
  - offset: integer (default: 0)
  - archived`: boolean | null (optional)
  - не указан или `null` - **все диалоги** (обычные + архивные)
  - `false` - **только обычные** диалоги (folder_id = 0)
  - `true` - **только архивные** диалоги (folder_id = 1)

Response 200:
{
  "total": 245,
  "hasMore": true,
  "dialogs": [
    {
      "id": "1234567890",
      "name": "Иван Петров",
      "type": "user",  // user | bot | group | supergroup | channel
      "date": "2024-01-17T15:30:00Z",  // дата последнего сообщения
      
      // Счётчики
      "unreadCount": 3,
      "unreadMentionsCount": 1,
      "unreadReactionsCount": 0,
      
      // Статусы
      "isArchived": false,
      "isPinned": true,
      "isMuted": false,
      "unreadMark": false,  // отмечен как непрочитанный вручную
      
      // Папка
      "folderId": null,  // null = главная папка, 0+ = ID папки
      
      // Черновик сообщения
      "draft": {
        "text": "Начатый текст сообщения...",
        "date": "2024-01-17T14:20:00Z"
      },
      // или null, если черновика нет
      
      // Настройки уведомлений
      "notifySettings": {
        "showPreviews": true,        // показывать превью сообщений
        "silent": false,             // беззвучные уведомления
        "muteUntil": 1705507200,     // timestamp до которого отключены (null если не отключены)
        "sound": "default"           // звук уведомления
      },
      
      // Последнее сообщение
      "lastMessage": {
        "id": 67890,
        "text": "Привет, как дела?",
        "date": "2024-01-17T15:30:00Z",
        "fromId": "987654321",
        "out": false,         // исходящее или входящее
        "mentioned": false,   // есть упоминание текущего пользователя
        "mediaUnread": false, // медиа не просмотрено
        "silent": false       // беззвучное сообщение
      },
      
      // Детали сущности (зависит от типа)
      "entity": {
        // Для user/bot:
        "firstName": "Иван",
        "lastName": "Петров",
        "username": "ivan_petrov",
        "phone": "+79991234567",
        "isBot": false,
        "isVerified": false,
        "isPremium": true,
        "isContact": true,
        "isMutualContact": true,
        "photo": {
          "photoId": "5234567890123456789",
          "dcId": 2
        },
        "status": {
          "type": "online",  // online | offline | recently | lastWeek | lastMonth
          "wasOnline": "2024-01-17T15:30:00Z"
        },
        
        // Для group:
        "title": "Рабочая группа",
        "participantsCount": 45,
        "createdDate": "2023-05-10T10:00:00Z",
        "isCreator": false,
        "isAdmin": true,
        "photo": {
          "photoId": "5234567890123456789",
          "dcId": 2
        },
        
        // Для channel/megagroup:
        "title": "Новости компании",
        "username": "company_news",
        "participantsCount": 15000,
        "createdDate": "2022-03-15T08:00:00Z",
        "isCreator": false,
        "isAdmin": false,
        "isBroadcast": true,  // true = канал, false = мегагруппа
        "isVerified": true,
        "isScam": false,
        "isFake": false,
        "hasGeo": false,
        "slowmodeEnabled": false,
        "photo": {
          "photoId": "5234567890123456789",
          "dcId": 2
        }
      }
    }
    // ... остальные диалоги
  ]
}

Response 403:
{
  "error": "ACCOUNT_NOT_CONNECTED",
  "message": "Аккаунт не подключен к Telegram"
}

Response 404:
{
  "error": "ACCOUNT_NOT_FOUND",
  "message": "Аккаунт не найден"
}
```

### 4.4 Получить список папок

```http
GET /api/accounts/{accountId}/folders
Authorization: Bearer {token}

Response 200:
[
  {
    "id": 0,
    "title": "Все чаты",
    "isDefault": true,
    "emoji": null,
    "pinnedDialogIds": [],
    "includedChatIds": [],
    "excludedChatIds": [],
    "contacts": false,
    "nonContacts": false,
    "groups": false,
    "broadcasts": false,
    "bots": false,
    "excludeMuted": false,
    "excludeRead": false,
    "excludeArchived": false
  },
  {
    "id": 1,
    "title": "Работа",
    "isDefault": false,
    "emoji": "💼",
    "pinnedDialogIds": ["1234567890", "9876543210"],
    "includedChatIds": ["1234567890", "9876543210", "5555555555"],
    "excludedChatIds": [],
    "contacts": false,
    "nonContacts": false,
    "groups": true,
    "broadcasts": false,
    "bots": false,
    "excludeMuted": false,
    "excludeRead": false,
    "excludeArchived": true
  },
  {
    "id": 2,
    "title": "Личное",
    "isDefault": false,
    "emoji": "👤",
    "pinnedDialogIds": [],
    "includedChatIds": [],
    "excludedChatIds": [],
    "contacts": true,
    "nonContacts": false,
    "groups": false,
    "broadcasts": false,
    "bots": false,
    "excludeMuted": false,
    "excludeRead": false,
    "excludeArchived": false
  }
]

Response 403:
{
  "error": "ACCOUNT_NOT_CONNECTED",
  "message": "Аккаунт не подключен к Telegram"
}

Response 404:
{
  "error": "ACCOUNT_NOT_FOUND",
  "message": "Аккаунт не найден"
}
```

---

## 5. ERROR CODES

### Общие ошибки

| Код | Описание |
|-----|----------|
| `UNAUTHORIZED` | Отсутствует или недействителен токен авторизации |
| `FORBIDDEN` | Нет доступа к ресурсу |
| `NOT_FOUND` | Ресурс не найден |
| `VALIDATION_ERROR` | Ошибка валидации входных данных |
| `INTERNAL_ERROR` | Внутренняя ошибка сервера |

### Ошибки аутентификации

| Код | Описание |
|-----|----------|
| `INVALID_CREDENTIALS` | Неверный логин или пароль |
| `USER_EXISTS` | Пользователь уже существует |
| `INVALID_TOKEN` | Токен недействителен или истек |

### Ошибки Telegram

| Код | Описание |
|-----|----------|
| `ACCOUNT_NOT_CONNECTED` | Аккаунт не подключен к Telegram |
| `ALREADY_CONNECTED` | Аккаунт уже подключен |
| `INVALID_API_CREDENTIALS` | Неверный API ID или API Hash |
| `INVALID_CODE` | Неверный код подтверждения |
| `INVALID_PASSWORD` | Неверный пароль 2FA |
| `PASSWORD_REQUIRED` | Требуется двухфакторная аутентификация |
| `PHONE_NUMBER_INVALID` | Неверный формат номера телефона |
| `FLOOD_WAIT` | Слишком много запросов, повторите через N секунд |

---

## 6. BACKEND IMPLEMENTATION HINTS (для Python/FastAPI)

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
fastapi==0.109.0
uvicorn[standard]==0.27.0
telethon==1.38.1
sqlalchemy==2.0.25
pydantic==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
alembic==1.13.1
```