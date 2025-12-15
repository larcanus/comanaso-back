# comanaso-back
# API КОНТРАКТ ДЛЯ COMANASO BACKEND

## Общая информация

**Backend**: Python + FastAPI  
**Telegram Library**: Telethon  
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
  "apiHash": "new_hash"             // опционально
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
  "message": "Аккаунт успешно подключен",
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

## 4. DIALOGS (Диалоги)

### 4.1 Получить список диалогов

```http
GET /api/accounts/{accountId}/dialogs
Authorization: Bearer {token}
Query Parameters:
  - limit: integer (default: 100, max: 500)
  - offset: integer (default: 0)

Response 200:
{
  "total": 245,
  "dialogs": [
    {
      "id": "1234567890",           // Telegram chat ID
      "name": "Иван Петров",
      "type": "user",               // user | group | channel | bot
      "unreadCount": 3,
      "lastMessage": {
        "text": "Привет, как дела?",
        "date": "2024-01-17T15:30:00Z",
        "fromId": 987654321
      },
      "photo": "https://cdn.telegram.org/...",  // URL аватара (если есть)
      "username": "ivan_petrov",    // username (если есть)
      "isArchived": false,
      "isPinned": true,
      "isMuted": false,
      "folderId": null              // ID папки (если в папке)
    },
    {
      "id": "9876543210",
      "name": "Рабочая группа",
      "type": "group",
      "unreadCount": 0,
      "lastMessage": {
        "text": "Документы отправлены",
        "date": "2024-01-17T14:20:00Z",
        "fromId": 111222333
      },
      "photo": null,
      "username": null,
      "isArchived": false,
      "isPinned": false,
      "isMuted": true,
      "folderId": 1
    }
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

### 4.2 Получить статистику по диалогам

```http
GET /api/accounts/{accountId}/dialogs/stats
Authorization: Bearer {token}

Response 200:
{
  "total": 245,
  "byType": {
    "user": 180,
    "group": 35,
    "channel": 25,
    "bot": 5
  },
  "unreadTotal": 47,
  "archived": 12,
  "pinned": 8,
  "muted": 23,
  "inFolders": 56
}
```

---

## 5. FOLDERS (Папки)

### 5.1 Получить список папок

```http
GET /api/accounts/{accountId}/folders
Authorization: Bearer {token}

Response 200:
[
  {
    "id": 1,
    "title": "Работа",
    "emoji": "💼",
    "pinnedDialogs": ["1234567890", "9876543210"],
    "includedChats": ["1234567890", "9876543210", "5555555555"],
    "excludedChats": [],
    "includeContacts": false,
    "includeNonContacts": false,
    "includeGroups": true,
    "includeChannels": false,
    "includeBots": false
  },
  {
    "id": 2,
    "title": "Личное",
    "emoji": "👤",
    "pinnedDialogs": [],
    "includedChats": [],
    "excludedChats": [],
    "includeContacts": true,
    "includeNonContacts": false,
    "includeGroups": false,
    "includeChannels": false,
    "includeBots": false
  }
]

Response 403:
{
  "error": "ACCOUNT_NOT_CONNECTED",
  "message": "Аккаунт не подключен к Telegram"
}
```

### 5.2 Получить рекомендуемые папки

```http
GET /api/accounts/{accountId}/folders/suggested
Authorization: Bearer {token}

Response 200:
[
  {
    "title": "Непрочитанные",
    "emoji": "📬",
    "description": "Все непрочитанные чаты",
    "filter": {
      "includeUnread": true
    }
  },
  {
    "title": "Группы",
    "emoji": "👥",
    "description": "Все групповые чаты",
    "filter": {
      "includeGroups": true
    }
  }
]
```

---

## 7. ERROR CODES

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

---

## 9. ИНТЕГРАЦИЯ С FRONTEND

### 9.1 Обновить [connection.js](file://D:/projects/vue/comanaso/src/utils/connection.js)

```javascript:D:/projects/vue/comanaso/src/utils/connection.js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function getAuthHeaders() {
    const token = localStorage.getItem('authToken');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

// Выход из системы (разлогин пользователя)
export async function logout() {
    const result = await apiRequest('/auth/logout', {
        method: 'POST'
    });
    localStorage.removeItem('authToken');
    return result;
}

async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            ...getAuthHeaders(),
            ...options.headers
        }
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'API Error');
    }

    return response.json();
}

// Подключение аккаунта
export async function connectAccount(accountId) {
    return apiRequest(`/accounts/${accountId}/connect`, {
        method: 'POST'
    });
}

// Подтверждение кода
export async function verifyCode(accountId, code, phoneCodeHash) {
    return apiRequest(`/accounts/${accountId}/verify-code`, {
        method: 'POST',
        body: JSON.stringify({ code, phoneCodeHash })
    });
}

// Подтверждение пароля 2FA
export async function verifyPassword(accountId, password) {
    return apiRequest(`/accounts/${accountId}/verify-password`, {
        method: 'POST',
        body: JSON.stringify({ password })
    });
}

// Отключение аккаунта
export async function disconnectAccount(accountId) {
    return apiRequest(`/accounts/${accountId}/disconnect`, {
        method: 'POST'
    });
}

// Получение диалогов
export async function getDialogs(accountId, limit = 100, offset = 0) {
    return apiRequest(`/accounts/${accountId}/dialogs?limit=${limit}&offset=${offset}`);
}

// Получение папок
export async function getFolders(accountId) {
    return apiRequest(`/accounts/${accountId}/folders`);
}

// Получение рекомендуемых папок
export async function getSuggestedDialogFilters(accountId) {
    return apiRequest(`/accounts/${accountId}/folders/suggested`);
}

// Получение всех данных
export async function getCommonData(accountId) {
    return apiRequest(`/accounts/${accountId}/data`);
}

// Выход из Telegram
export async function logOut(accountId) {
    return apiRequest(`/accounts/${accountId}/logout`, {
        method: 'POST'
    });
}
```

### 9.2 Обновить [AccountCard.vue](file://D:/projects/vue/comanaso/src/components/account/AccountCard.vue)

```javascript
// В функции onClickStart():
async function onClickStart() {
    if (!isValidConnectData({
        apiId: state.apiId,
        apiHash: state.apiHash,
        phoneNumber: state.phoneNumber,
    })) {
        toastStore.addToast('error', LOC_TOAST_VALID_ERROR);
        return;
    }

    accountStore.changeStatus(state.id, 'connect');

    try {
        // Шаг 1: Начать подключение
        const connectResult = await connectAccount(state.id);
        
        if (connectResult.status === 'code_required') {
            // Шаг 2: Запросить код у пользователя
            const code = await showConfirm('Введите код из Telegram');
            
            if (!code) {
                await accountStore.changeStatus(state.id, 'offline');
                return;
            }

            // Шаг 3: Отправить код
            const verifyResult = await verifyCode(
                state.id, 
                code, 
                connectResult.phoneCodeHash
            );

            if (verifyResult.status === 'connected') {
                await accountStore.changeStatus(state.id, 'online');
                toastStore.addToast('ok', LOC_TOAST_SUCCESS_CONNECT);
            }
        }
    } catch (error) {
        console.error('Connection error:', error);
        
        // Если требуется 2FA
        if (error.message.includes('PASSWORD_REQUIRED')) {
            const password = await showConfirm('Введите пароль 2FA');
            
            if (password) {
                try {
                    await verifyPassword(state.id, password);
                    await accountStore.changeStatus(state.id, 'online');
                    toastStore.addToast('ok', LOC_TOAST_SUCCESS_CONNECT);
                } catch (err) {
                    await accountStore.changeStatus(state.id, 'error', {
                        title: 'Ошибка 2FA',
                        desc: err.message
                    });
                }
            }
        } else {
            await accountStore.changeStatus(state.id, 'error', {
                title: 'Ошибка подключения',
                desc: error.message
            });
        }
    }
}
```

### 9.3 Переменные окружения

```env:D:/projects/vue/comanaso/.env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

---

## 10. BACKEND IMPLEMENTATION HINTS (для Python/FastAPI)

### 10.1 Структура проекта

```
backend/
├── test/
│   ├── accounts.ps1
│   └── auth.ps1
├── alembic/
│   ├── version/
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

### 10.2 Основные зависимости

```txt:requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
telethon==1.34.0
sqlalchemy==2.0.25
pydantic==2.5.3
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
```

### 10.3 Пример Telethon клиента

```python
# app/utils/telethon_client.py
from telethon import TelegramClient
from telethon.sessions import StringSession

class TelethonManager:
    def __init__(self):
        self.clients = {}  # {account_id: TelegramClient}
    
    async def create_client(self, account_id, api_id, api_hash, session_string=None):
        session = StringSession(session_string) if session_string else StringSession()
        client = TelegramClient(session, api_id, api_hash)
        await client.connect()
        self.clients[account_id] = client
        return client
    
    async def send_code(self, account_id, phone):
        client = self.clients.get(account_id)
        if not client:
            raise ValueError("Client not found")
        
        result = await client.send_code_request(phone)
        return result.phone_code_hash
    
    async def sign_in(self, account_id, phone, code, phone_code_hash):
        client = self.clients.get(account_id)
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        
        # Сохранить session string в БД
        session_string = client.session.save()
        return session_string
    
    async def get_dialogs(self, account_id, limit=100):
        client = self.clients.get(account_id)
        dialogs = await client.get_dialogs(limit=limit)
        
        return [
            {
                "id": str(dialog.id),
                "name": dialog.name,
                "type": self._get_dialog_type(dialog.entity),
                "unreadCount": dialog.unread_count,
                # ... остальные поля
            }
            for dialog in dialogs
        ]
```

---

## 11. ТЕСТИРОВАНИЕ API

### Postman Collection (пример)

```json
{
  "info": {
    "name": "Comanaso API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Register",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/auth/register",
            "body": {
              "mode": "raw",
              "raw": "{\n  \"login\": \"testuser\",\n  \"password\": \"password123\"\n}"
            }
          }
        },
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/auth/login",
            "body": {
              "mode": "raw",
              "raw": "{\n  \"login\": \"testuser\",\n  \"password\": \"password123\"\n}"
            }
          }
        }
      ]
    }
  ],
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000/api"
    },
    {
      "key": "token",
      "value": ""
    }
  ]
}
```

---

## ИТОГО

Этот контракт покрывает:
- ✅ Аутентификацию пользователей
- ✅ CRUD операции с аккаунтами
- ✅ Подключение к Telegram (с 2FA)
- ✅ Получение диалогов и папок
- ✅ Статистику и аналитику
- ✅ Обработку ошибок
- ✅ Интеграцию с существующим frontend

**Следующие шаги:**
1. Реализовать backend на FastAPI + Telethon
2. Обновить [connection.js](file://D:/projects/vue/comanaso/src/utils/connection.js) согласно контракту
3. Протестировать интеграцию