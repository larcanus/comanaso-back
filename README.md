# Comanaso Backend

Главный репозиторий бэкенда Comanaso. Проект реализован на Python с использованием FastAPI и интегрируется с Telegram через Telethon, обеспечивая аутентификацию на основе JWT.

---

## Основные возможности

- REST API для регистрации, входа и управления профилем пользователя.
- Интеграция с Telegram для работы с аккаунтами и диалогами.
- Управление состоянием пользователя и настройками приватности.
- Поддержка миграций базы данных с помощью Alembic.

---

## Технологический стек

- **Язык:** Python
- **фреймворк:** FastAPI
- **Библиотека Telegram:** Telethon (v1.42.0)
- **База данных:** PostgreSQL
- **Миграции:** Alembic
- **Аутентификация:** JWT (Bearer Token)

---

## Быстрый старт

1. Убедитесь, что установлены Docker и Docker Compose.
2. Скопируйте файл окружения и заполните необходимые переменные.
   ```bash
   cp .env.example .env
   ```
3. Запустите сервисы:
   ```bash
   docker-compose up --build
   ```
4. После запуска API доступно по адресу `http://localhost:8000`.

---

## Документация

| Раздел                                 | Описание                                                                                             |
|----------------------------------------|------------------------------------------------------------------------------------------------------|
| [API & Контракты](README_API.md)       | Подробные спецификации REST API: аутентификация, работа с Telegram-диалогами, описание кодов ошибок. |
| [База данных и миграции](README_DB.md) | Инструкции по подключению к PostgreSQL, управлению миграциями Alembic и полезные SQL-команды.        |
| [Reset PSW Flow](README_PSW.md)        | Краткий обзор продуктового процесса и бизнес-логики сброса пароля.                                   |

> Совет: начните с раздела об API, чтобы понять, как взаимодействовать с сервисом, затем изучите миграции и продуктовый flow при необходимости.

---

## Проверка работоспособности

### Через консоль браузера

Откройте консоль разработчика (F12) и выполните:

```javascript
// Базовая проверка
fetch('http://localhost:8000/health')
  .then(res => res.json())
  .then(data => console.log('Health Status:', data))
  .catch(err => console.error('Error:', err));

// Расширенная проверка с деталями
fetch('http://localhost:8000/health')
  .then(async res => {
    const data = await res.json();
    console.log('✅ Status:', data.status);
    console.log('📊 Version:', data.version);
    console.log('🗄️ Database:', data.database);
    console.log('🌍 Environment:', data.environment);
    return data;
  })
  .catch(err => console.error('❌ API недоступен:', err));

// Проверка с async/await
(async () => {
  try {
    const response = await fetch('http://localhost:8000/health');
    const health = await response.json();
    
    if (health.status === 'healthy' && health.database === 'healthy') {
      console.log('✅ Все системы работают нормально');
    } else {
      console.warn('⚠️ Обнаружены проблемы:', health);
    }
  } catch (error) {
    console.error('❌ Не удалось подключиться к API:', error);
  }
})();
```

## Через командную строку (CLI)
```shell
# Простая проверка с curl
curl http://localhost:8000/health

# Форматированный вывод с jq
curl -s http://localhost:8000/health | jq

# Проверка с выводом HTTP заголовков
curl -i http://localhost:8000/health

# Проверка только статус-кода
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health

# Проверка с таймаутом
curl --max-time 5 http://localhost:8000/health

# Проверка production endpoint (через HTTPS)
curl https://api.comanaso.com/health

# Непрерывный мониторинг (каждые 5 секунд)
watch -n 5 'curl -s http://localhost:8000/health | jq'

# Проверка с сохранением в файл
curl -s http://localhost:8000/health | jq > health-check.json
```

## Интерпретация ответа
```
Здоровый статус:
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "database": "healthy",
  "debug": true
}
```
```
Деградированный статус (проблемы с БД):
{
  "status": "degraded",
  "version": "1.0.0",
  "environment": "production",
  "database": "unhealthy",
  "debug": false
}
```


## Полезные команды

### Docker

```bash
# Запуск сервисов
docker-compose up -d --build

# Остановка сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f
```

### Alembic

Подробности смотрите в [README_DB.md](README_DB.md), но базовые команды приведены ниже:

```bash
# Создание новой миграции
docker-compose exec comanaso-api alembic revision --autogenerate -m "Описание изменений"

# Применение миграций
docker-compose exec comanaso-api alembic upgrade head
```