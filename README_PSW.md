## README с планом реализации

Создаю подробный план разработки системы сброса пароля с использованием Яндекс.Почты.

```
# Система сброса пароля через токен

## 📋 Описание

Реализация безопасной системы восстановления пароля с использованием одноразовых токенов и email-уведомлений через Яндекс.Почту.

---

## 🔄 Общий Flow

```
┌──────────────┐
│  Пользователь│
│ забыл пароль │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│ 1. Форма "Забыли пароль?"                           │
│    Frontend: /forgot-password                        │
│    Ввод: email                                       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 2. POST /api/auth/request-password-reset            │
│    Body: { "email": "user@example.com" }            │
│                                                      │
│    Backend действия:                                │
│    ✓ Проверка существования пользователя            │
│    ✓ Генерация случайного токена (UUID)             │
│    ✓ Сохранение токена в БД с временем истечения    │
│    ✓ Отправка email через Яндекс.Почту              │
│    ✓ Возврат успешного ответа                       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 3. Email письмо на Яндекс.Почту                     │
│    Тема: "Сброс пароля - Comanaso"                  │
│    Тело:                                             │
│    "Для сброса пароля перейдите по ссылке:          │
│     https://comanaso.com/reset-password?            │
│     token=a7f3c9e1-4b2d-47a8-9c3e-f1d8b6a4e5c2"     │
│                                                      │
│    Токен действителен: 1 час                         │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 4. Пользователь открывает письмо                    │
│    Кликает на ссылку                                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 5. Frontend: /reset-password?token=...              │
│    Публичная страница (без авторизации)             │
│                                                      │
│    useEffect при монтировании:                       │
│    GET /api/auth/validate-reset-token?token=...     │
│                                                      │
│    Backend проверяет:                                │
│    ✓ Токен существует в БД                          │
│    ✓ Не истек срок действия (< 1 часа)              │
│    ✓ Токен еще не использован                       │
└──────────────────────┬──────────────────────────────┘
                       │
                ┌──────┴──────┐
                │             │
                ▼             ▼
        ┌───────────┐   ┌───────────┐
        │ ✅ Валидно│   │ ❌ Ошибка │
        └─────┬─────┘   └─────┬─────┘
              │               │
              ▼               ▼
┌──────────────────────┐ ┌──────────────────────┐
│ 6A. Показать форму   │ │ 6B. Показать ошибку  │
│     смены пароля:    │ │     "Ссылка          │
│                      │ │      недействительна │
│ [Новый пароль    ]  │ │      или истекла"    │
│ [Повторите пароль]  │ │                      │
│ [Сменить пароль  ]  │ │ [Запросить новую]   │
└──────────┬───────────┘ └──────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│ 7. Пользователь вводит новый пароль                 │
│    POST /api/auth/reset-password                    │
│    Body: {                                           │
│      "token": "a7f3c9e1...",                        │
│      "new_password": "NewSecure123!"                │
│    }                                                 │
│                                                      │
│    Backend действия:                                │
│    ✓ Повторная проверка токена                      │
│    ✓ Хеширование нового пароля                      │
│    ✓ Обновление пароля в БД                         │
│    ✓ Удаление токена (делаем его недействительным)  │
│    ✓ Возврат успешного ответа                       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 8. Успешное уведомление                             │
│    "Пароль успешно изменен!"                        │
│    [Перейти на страницу входа]                      │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│ 9. Пользователь входит с новым паролем              │
│    POST /api/auth/login                             │
└─────────────────────────────────────────────────────┘
```

---

## 🛠 Этапы разработки

### **ЭТАП 1: Настройка Яндекс.Почты**

#### 1.1. Создание аккаунта для приложения
1. Регистрируем email: `noreply@comanaso.com` (или используем существующий)
2. Переходим в настройки Яндекс.Почты
3. Создаем **App Password** (пароль приложения)
   - Настройки → Безопасность → Пароли приложений
   - Генерируем пароль для SMTP

#### 1.2. Получаем реквизиты
```
SMTP_HOST: smtp.yandex.ru
SMTP_PORT: 465 (SSL) или 587 (STARTTLS)
SMTP_USER: noreply@comanaso.com
SMTP_PASSWORD: <app-password>


#### 1.3. Добавляем в `.env`
```env
# Email Configuration (Yandex)
SMTP_HOST=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=noreply@comanaso.com
SMTP_PASSWORD=your_app_password_here
SMTP_FROM_NAME=Comanaso Support
SMTP_USE_TLS=true
PASSWORD_RESET_TOKEN_EXPIRE_HOURS=1
FRONTEND_URL=https://comanaso.com
```

---

### **ЭТАП 2: Backend - Обновление модели User**

#### 2.1. Добавляем поля в модель
**Файл:** `models/user.py` (или где находится модель User)

Добавить поля:
```python
reset_token: Optional[str] = None
reset_token_expires: Optional[datetime] = None
```

#### 2.2. Создаем миграцию Alembic
```bash
# В контейнере или локально
alembic revision --autogenerate -m "Add password reset fields to User"
alembic upgrade head
```

**Ожидаемая миграция:**
```python
def upgrade():
    op.add_column('users', sa.Column('reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires', sa.DateTime(), nullable=True))
    op.create_index('idx_reset_token', 'users', ['reset_token'])

def downgrade():
    op.drop_index('idx_reset_token', 'users')
    op.drop_column('users', 'reset_token_expires')
    op.drop_column('users', 'reset_token')
```

---

### **ЭТАП 3: Backend - Email сервис**

#### 3.1. Создаем `services/email_service.py`

**Функционал:**
- Класс `EmailService`
- Метод `send_password_reset_email(to_email: str, reset_token: str)`
- HTML шаблон письма
- Подключение к Яндекс SMTP

**Зависимости (если нужны новые):**
```bash
pip install aiosmtplib
# или
pip install python-multipart email-validator
```

---

### **ЭТАП 4: Backend - Обновление Auth сервиса**

#### 4.1. Обновляем `services/auth_service.py`

**Новые методы:**
1. `request_password_reset(email: str) -> bool`
   - Поиск пользователя по email
   - Генерация UUID токена
   - Сохранение токена с временем истечения
   - Вызов email_service для отправки письма

2. `validate_reset_token(token: str) -> Optional[User]`
   - Проверка существования токена
   - Проверка срока действия
   - Возврат пользователя или None

3. `reset_password(token: str, new_password: str) -> bool`
   - Валидация токена
   - Хеширование нового пароля
   - Обновление пароля
   - Удаление/инвалидация токена

---

### **ЭТАП 5: Backend - API Endpoints**

#### 5.1. Создаем/обновляем `routers/auth.py`

**Новые эндпоинты:**

**1. POST `/api/auth/request-password-reset`**
```python
Request Body:
{
  "email": "user@example.com"
}

Response (200):
{
  "message": "Если пользователь существует, письмо отправлено"
}

Response (429 - Rate Limit):
{
  "detail": "Слишком много запросов. Попробуйте через 5 минут"
}
```

**2. GET `/api/auth/validate-reset-token`**
```python
Query Params: ?token=a7f3c9e1...

Response (200):
{
  "valid": true,
  "email": "user@example.com"
}

Response (404):
{
  "detail": "Токен недействителен или истек"
}
```

**3. POST `/api/auth/reset-password`**
```python
Request Body:
{
  "token": "a7f3c9e1...",
  "new_password": "NewSecure123!"
}

Response (200):
{
  "message": "Пароль успешно изменен"
}

Response (400):
{
  "detail": "Токен недействителен или пароль не соответствует требованиям"
}
```

#### 5.2. Добавить Rate Limiting
- Защита от спама: максимум 3 запроса в час с одного IP
- Использовать `slowapi` или аналог

---

### **ЭТАП 6: Frontend - Страница "Забыли пароль?"**

#### 6.1. Создать компонент `ForgotPasswordPage.tsx`

**Путь:** `/forgot-password`

**Функционал:**
- Форма с полем email
- Валидация email
- Отправка POST запроса на `/api/auth/request-password-reset`
- Показ уведомления: "Если пользователь существует, письмо отправлено"
- Ссылка "Вернуться к входу"

**UI элементы:**
```
┌─────────────────────────────────────┐
│          Забыли пароль?             │
│                                     │
│  Введите ваш email, и мы отправим   │
│  инструкции для восстановления      │
│                                     │
│  Email: [________________]          │
│                                     │
│  [  Отправить инструкции  ]        │
│                                     │
│  ← Вернуться к входу                │
└─────────────────────────────────────┘
```

---

### **ЭТАП 7: Frontend - Страница сброса пароля**

#### 7.1. Создать компонент `ResetPasswordPage.tsx`

**Путь:** `/reset-password?token=...`

**Функционал:**
1. **useEffect при монтировании:**
   - Извлечь token из URL
   - GET `/api/auth/validate-reset-token?token=...`
   - Если валиден → показать форму
   - Если нет → показать ошибку

2. **Форма смены пароля:**
   - Поле "Новый пароль" (type=password)
   - Поле "Повторите пароль"
   - Валидация совпадения паролей
   - Показ требований к паролю
   - Отправка POST `/api/auth/reset-password`

3. **Успешное изменение:**
   - Показать уведомление
   - Кнопка "Перейти к входу" → redirect на `/login`

**UI элементы:**
```
┌─────────────────────────────────────┐
│        Создайте новый пароль        │
│                                     │
│  Новый пароль:                      │
│  [________________] 👁               │
│                                     │
│  Повторите пароль:                  │
│  [________________] 👁               │
│                                     │
│  ✓ Минимум 8 символов               │
│  ✓ Одна заглавная буква             │
│  ✓ Одна цифра                       │
│                                     │
│  [    Сменить пароль    ]          │
└─────────────────────────────────────┘
```

---

### **ЭТАП 8: Frontend - Интеграция в Login**

#### 8.1. Обновить `LoginPage.tsx`

**Добавить ссылку:**
```tsx
<form>
  {/* ... существующие поля ... */}
  
  <div className="forgot-password-link">
    <Link to="/forgot-password">
      Забыли пароль?
    </Link>
  </div>
  
  <button type="submit">Войти</button>
</form>
```

---

## 📝 Схема БД (изменения)

### Таблица `users`

```sql
-- Новые колонки
ALTER TABLE users ADD COLUMN reset_token VARCHAR(255) NULL;
ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP NULL;

-- Индекс для быстрого поиска по токену
CREATE INDEX idx_reset_token ON users(reset_token);
```

**Пример записи:**
```
id: 1
email: user@example.com
password_hash: $2b$12$...
reset_token: a7f3c9e1-4b2d-47a8-9c3e-f1d8b6a4e5c2
reset_token_expires: 2025-01-15 15:30:00
```

---

## 🔒 Безопасность

### ✅ Реализованные меры:

1. **Случайные токены**
   - UUID v4 (128 бит энтропии)
   - Невозможно угадать

2. **Время жизни токена**
   - 1 час (настраивается)
   - Автоматическая инвалидация

3. **Одноразовое использование**
   - После смены пароля токен удаляется

4. **Rate Limiting**
   - Максимум 3 запроса в час
   - Защита от спама

5. **Не раскрываем существование пользователя**
   - Всегда возвращаем "Письмо отправлено"
   - Даже если email не найден

6. **HTTPS обязателен**
   - Токен передается через защищенное соединение

7. **Безопасное хранение паролей**
   - Bcrypt хеширование
   - Минимум 12 раундов

---

## 📧 Шаблон Email письма

### HTML версия:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Сброс пароля</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
    <h2 style="color: #333; margin-top: 0;">Сброс пароля</h2>
    
    <p style="color: #666; font-size: 16px;">
      Вы запросили сброс пароля для вашего аккаунта на <strong>Comanaso</strong>.
    </p>
    
    <div style="background-color: #fff; padding: 20px; border-radius: 5px; margin: 20px 0;">
      <p style="margin: 0; color: #333;">
        Для создания нового пароля нажмите на кнопку ниже:
      </p>
      
      <div style="text-align: center; margin: 30px 0;">
        <a href="{reset_url}" 
           style="background-color: #007bff; color: white; padding: 12px 30px; 
                  text-decoration: none; border-radius: 5px; display: inline-block;
                  font-weight: bold;">
          Сбросить пароль
        </a>
      </div>
      
      <p style="color: #666; font-size: 14px; margin-top: 20px;">
        Или скопируйте эту ссылку в браузер:
      </p>
      <p style="color: #007bff; word-break: break-all; font-size: 14px;">
        {reset_url}
      </p>
    </div>
    
    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; 
                border-left: 4px solid #ffc107;">
      <p style="margin: 0; color: #856404; font-size: 14px;">
        <strong>⚠️ Важно:</strong> Ссылка действительна в течение <strong>1 часа</strong>.
      </p>
    </div>
    
    <p style="color: #666; font-size: 14px; margin-top: 30px;">
      Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
      Ваш пароль останется без изменений.
    </p>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    
    <p style="color: #999; font-size: 12px; text-align: center;">
      © 2025 Comanaso. Все права защищены.<br>
      Это автоматическое письмо, не отвечайте на него.
    </p>
  </div>
</body>
</html>
```

### Text версия (fallback):

```
Сброс пароля - Comanaso

Вы запросили сброс пароля для вашего аккаунта.

Для создания нового пароля перейдите по ссылке:
{reset_url}

⚠️ Важно: Ссылка действительна в течение 1 часа.

Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.

---
© 2025 Comanaso
Это автоматическое письмо, не отвечайте на него.
```

---

## 🧪 Тестирование

### Backend тесты:

**Файл:** `tests/test_password_reset.py`

```python
def test_request_password_reset_existing_user():
    """Запрос сброса для существующего пользователя"""
    # Должен вернуть 200 и отправить email

def test_request_password_reset_non_existing_user():
    """Запрос сброса для несуществующего пользователя"""
    # Должен вернуть 200 (не раскрывать существование)

def test_validate_reset_token_valid():
    """Проверка валидного токена"""
    # Должен вернуть 200 с данными пользователя

def test_validate_reset_token_expired():
    """Проверка истекшего токена"""
    # Должен вернуть 404

def test_reset_password_success():
    """Успешная смена пароля"""
    # Должен вернуть 200 и обновить пароль

def test_reset_password_invalid_token():
    """Смена пароля с невалидным токеном"""
    # Должен вернуть 400

def test_rate_limiting():
    """Проверка ограничения частоты запросов"""
    # После 3 запросов должен вернуть 429
```

### Frontend тесты:

**Файл:** `tests/ForgotPassword.test.tsx`

```typescript
describe('ForgotPasswordPage', () => {
  it('должен отправить email при валидном вводе', () => {});
  it('должен показать ошибку при невалидном email', () => {});
  it('должен показать уведомление после отправки', () => {});
});

describe('ResetPasswordPage', () => {
  it('должен валидировать токен при загрузке', () => {});
  it('должен показать форму при валидном токене', () => {});
  it('должен показать ошибку при истекшем токене', () => {});
  it('должен валидировать совпадение паролей', () => {});
  it('должен отправить новый пароль', () => {});
});
```

### Ручное тестирование:

**Чеклист:**
- [ ] Запрос сброса для существующего email
- [ ] Запрос сброса для несуществующего email (должен выглядеть так же)
- [ ] Получение письма на Яндекс.Почту
- [ ] Переход по ссылке из письма
- [ ] Валидация токена
- [ ] Смена пароля с совпадающими полями
- [ ] Смена пароля с несовпадающими полями (ошибка)
- [ ] Повторное использование токена (должна быть ошибка)
- [ ] Истечение токена через 1 час
- [ ] Rate limiting (3 запроса подряд)
- [ ] Вход с новым паролем после смены

---

## 📦 Checklist развертывания

### Backend:

- [ ] Добавлены SMTP настройки в `.env`
- [ ] Создан App Password в Яндекс.Почте
- [ ] Запущена миграция БД
- [ ] Создан `services/email_service.py`
- [ ] Обновлен `services/auth_service.py`
- [ ] Созданы эндпоинты в `routers/auth.py`
- [ ] Добавлен Rate Limiting
- [ ] Написаны тесты
- [ ] Проверена отправка email в staging

### Frontend:

- [ ] Создан `ForgotPasswordPage.tsx`
- [ ] Создан `ResetPasswordPage.tsx`
- [ ] Добавлен роутинг для новых страниц
- [ ] Обновлен `LoginPage.tsx` со ссылкой
- [ ] Добавлены стили для форм
- [ ] Написаны тесты
- [ ] Проверена работа в staging

### DevOps:

- [ ] Обновлен `.env` в Docker контейнере
- [ ] Проверен SMTP доступ с сервера (порты 465/587)
- [ ] Настроен FRONTEND_URL в environment
- [ ] Добавлен мониторинг отправки email
- [ ] Настроены алерты на ошибки отправки

---

## 🚀 Запуск в production

### 1. Проверка окружения
```bash
# Проверить настройки SMTP
echo $SMTP_HOST
echo $SMTP_USER

# Проверить доступность SMTP порта
telnet smtp.yandex.ru 465
```

### 2. Миграция БД
```bash
docker-compose exec backend alembic upgrade head
```

### 3. Тестовая отправка email
```bash
# Через API или напрямую из Python
curl -X POST http://localhost:8000/api/auth/request-password-reset \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

### 4. Мониторинг логов
```bash
docker-compose logs -f backend | grep -i email
```

---

## 📊 Метрики и мониторинг

### Что отслеживать:

1. **Email отправка:**
   - Количество отправленных писем / час
   - Процент неудачных отправок
   - Время доставки

2. **Использование токенов:**
   - Количество сгенерированных токенов
   - Количество использованных токенов
   - Процент истекших токенов

3. **Rate limiting:**
   - Количество заблокированных IP
   - Частота срабатывания лимитов

4. **Ошибки:**
   - SMTP ошибки
   - Недействительные токены
   - Таймауты

---

## 🐛 Возможные проблемы и решения

### Проблема 1: Письма не доходят
**Решение:**
- Проверить App Password в Яндексе
- Проверить порты 465/587 на сервере
- Проверить логи SMTP
- Попробовать другой порт (587 вместо 465)

### Проблема 2: Письма попадают в спам
**Решение:**
- Настроить SPF, DKIM, DMARC записи
- Использовать корпоративный домен для отправки
- Добавить unsubscribe ссылку

### Проблема 3: Токены не валидируются
**Решение:**
- Проверить timezone на сервере и в БД
- Убедиться что время истечения сохраняется в UTC
- Проверить корректность SQL запроса

### Проблема 4: Rate limiting блокирует легитимных пользователей
**Решение:**
- Увеличить лимит (5 вместо 3)
- Использовать whitelist для доверенных IP
- Добавить капчу

---

## 📚 Полезные ссылки

- [Яндекс.Почта SMTP настройки](https://yandex.ru/support/mail/mail-clients/others.html)
- [FastAPI Email Best Practices](https://fastapi.tiangolo.com/)
- [OWASP Password Reset Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
- [Alembic Migrations Guide](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

---