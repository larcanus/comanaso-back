# README: Работа с базой данных и миграциями

Руководство по управлению базой данных PostgreSQL и миграциями Alembic в проекте Comanaso Backend.

---

## Содержание

1. [Подключение к базе данных](#подключение-к-базе-данных)
2. [Работа с миграциями](#работа-с-миграциями)
3. [Полезные SQL команды](#полезные-sql-команды)
4. [Резервное копирование](#резервное-копирование)
5. [Решение проблем](#решение-проблем)

---

## Подключение к базе данных

### Через Docker

```bash
# Подключение к PostgreSQL через psql
docker-compose exec postgres psql -U comanaso -d comanaso

# Альтернативный способ (если первый не работает)
docker-compose exec postgres psql postgresql://comanaso:your_password@localhost:5432/comanaso
```

### Через внешний клиент (DBeaver, pgAdmin, DataGrip)

```
Host: localhost
Port: 5432
Database: comanaso
Username: comanaso
Password: (из .env файла, переменная DB_PASSWORD)
```

---

## Работа с миграциями

### Основные команды Alembic

#### 1. Создание новой миграции (автогенерация)

```bash
# Alembic автоматически определит изменения в моделях
docker-compose exec comanaso-api alembic revision --autogenerate -m "Описание изменений"

# Примеры описаний:
# - "Initial migration" - первая миграция
# - "Add email field to users" - добавление поля
# - "Create sessions table" - создание новой таблицы
# - "Add index on phone field" - добавление индекса
```

#### 2. Создание пустой миграции (ручная)

```bash
# Для сложных изменений, которые нужно написать вручную
docker-compose exec comanaso-api alembic revision -m "Custom migration"
```

#### 3. Применение миграций

```bash
# Применить все непримененные миграции
docker-compose exec comanaso-api alembic upgrade head

# Применить следующую миграцию
docker-compose exec comanaso-api alembic upgrade +1

# Применить до конкретной ревизии
docker-compose exec comanaso-api alembic upgrade <revision_id>
```

#### 4. Откат миграций

```bash
# Откатить последнюю миграцию
docker-compose exec comanaso-api alembic downgrade -1

# Откатить все миграции
docker-compose exec comanaso-api alembic downgrade base

# Откатить до конкретной ревизии
docker-compose exec comanaso-api alembic downgrade <revision_id>
```

#### 5. Просмотр информации о миграциях

```bash
# Текущая версия БД
docker-compose exec comanaso-api alembic current

# История миграций
docker-compose exec comanaso-api alembic history

# Подробная история с деталями
docker-compose exec comanaso-api alembic history --verbose

# Показать SQL без применения
docker-compose exec comanaso-api alembic upgrade head --sql
```

---

## Полезные SQL команды

### Базовые команды psql

```sql
-- Список всех таблиц
\dt

-- Описание структуры таблицы
\d users
\d accounts

-- Список всех баз данных
\l

-- Список всех схем
\dn

-- Выход из psql
\q

-- Помощь по командам
\?
```

### Проверка данных

```sql
-- Количество пользователей
SELECT COUNT(*) FROM users;

-- Список всех пользователей
SELECT id, email, username, is_active, created_at FROM users;

-- Количество аккаунтов
SELECT COUNT(*) FROM accounts;

-- Список аккаунтов с информацией о владельце
SELECT 
    a.id, 
    a.phone, 
    a.name, 
    a.status, 
    u.email as owner_email
FROM accounts a
JOIN users u ON a.user_id = u.id;

-- Аккаунты конкретного пользователя
SELECT * FROM accounts WHERE user_id = 1;

-- Текущая версия миграции
SELECT * FROM alembic_version;
```

### Очистка данных

```sql
-- Удалить все аккаунты (с каскадом)
TRUNCATE accounts CASCADE;

-- Удалить всех пользователей (с каскадом)
TRUNCATE users CASCADE;

-- Удалить все данные из всех таблиц
TRUNCATE users, accounts CASCADE;
```

### Проверка индексов и ограничений

```sql
-- Список индексов таблицы
\di+ users

-- Список ограничений (constraints)
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'users'::regclass;

-- Внешние ключи
SELECT
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
```

---

## Типичный workflow

### 1. Изменение моделей

Отредактируйте файлы моделей:
- `app/models/user.py`
- `app/models/account.py`

```python
# Пример: добавление нового поля в User
class User(Base):
    __tablename__ = "users"
    
    # ... существующие поля ...
    
    # Новое поле
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
```

### 2. Создание миграции

```bash
docker-compose exec comanaso-api alembic revision --autogenerate -m "Add phone field to users"
```

### 3. Проверка сгенерированной миграции

```bash
# Откройте файл миграции в alembic/versions/
# Проверьте корректность upgrade() и downgrade()
```

### 4. Применение миграции

```bash
docker-compose exec comanaso-api alembic upgrade head
```

### 5. Проверка в БД

```bash
docker-compose exec postgres psql -U comanaso -d comanaso
```

```sql
\d users  -- Проверить структуру таблицы
SELECT phone FROM users LIMIT 1;  -- Проверить новое поле
```

---

## Резервное копирование

### Создание бэкапа

```bash
# Полный дамп базы данных
docker-compose exec postgres pg_dump -U comanaso comanaso > backup_$(date +%Y%m%d_%H%M%S).sql

# Только схема (без данных)
docker-compose exec postgres pg_dump -U comanaso --schema-only comanaso > schema_backup.sql

# Только данные (без схемы)
docker-compose exec postgres pg_dump -U comanaso --data-only comanaso > data_backup.sql

# Конкретная таблица
docker-compose exec postgres pg_dump -U comanaso -t users comanaso > users_backup.sql
```

### Восстановление из бэкапа

```bash
# Восстановление полного дампа
docker-compose exec -T postgres psql -U comanaso comanaso < backup_20241202_223000.sql

# Восстановление конкретной таблицы
docker-compose exec -T postgres psql -U comanaso comanaso < users_backup.sql
```

---

## Решение проблем

### Проблема 1: Миграция не применяется

```bash
# Проверьте текущую версию
docker-compose exec comanaso-api alembic current

# Проверьте историю
docker-compose exec comanaso-api alembic history

# Попробуйте применить принудительно
docker-compose exec comanaso-api alembic stamp head
docker-compose exec comanaso-api alembic upgrade head
```

### Проблема 2: Конфликт миграций

```bash
# Откатите до базовой версии
docker-compose exec comanaso-api alembic downgrade base

# Удалите конфликтующие файлы миграций
rm alembic/versions/conflicting_migration.py

# Создайте миграцию заново
docker-compose exec comanaso-api alembic revision --autogenerate -m "Fixed migration"
docker-compose exec comanaso-api alembic upgrade head
```

### Проблема 3: Ошибка подключения к БД

```bash
# Проверьте статус PostgreSQL
docker-compose ps postgres

# Проверьте логи
docker-compose logs postgres

# Перезапустите БД
docker-compose restart postgres

# Проверьте переменные окружения
docker-compose exec comanaso-api env | grep DATABASE_URL
```

### Проблема 4: Таблица уже существует

```bash
# Вариант 1: Пометить текущее состояние как актуальное
docker-compose exec comanaso-api alembic stamp head

# Вариант 2: Удалить таблицы и применить миграции заново
docker-compose exec postgres psql -U comanaso -d comanaso
```

```sql
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS alembic_version CASCADE;
\q
```

```bash
docker-compose exec comanaso-api alembic upgrade head
```

### Проблема 5: Сброс базы данных полностью

```bash
# Остановите контейнеры
docker-compose down

# Удалите volume с данными БД
docker volume rm comanaso-back_postgres_data

# Запустите заново
docker-compose up -d

# Примените миграции
docker-compose exec comanaso-api alembic upgrade head
```

---

## Полезные алиасы для .bashrc / .zshrc

```bash
# Добавьте в ~/.bashrc или ~/.zshrc для быстрого доступа

# Alembic
alias alembic-migrate='docker-compose exec comanaso-api alembic revision --autogenerate -m'
alias alembic-upgrade='docker-compose exec comanaso-api alembic upgrade head'
alias alembic-downgrade='docker-compose exec comanaso-api alembic downgrade -1'
alias alembic-current='docker-compose exec comanaso-api alembic current'
alias alembic-history='docker-compose exec comanaso-api alembic history'

# PostgreSQL
alias psql-connect='docker-compose exec postgres psql -U comanaso -d comanaso'
alias psql-backup='docker-compose exec postgres pg_dump -U comanaso comanaso > backup_$(date +%Y%m%d_%H%M%S).sql'

# Использование:
# alembic-migrate "Add new field"
# alembic-upgrade
# psql-connect
```

---

## Чек-лист перед продакшеном

- [ ] Все миграции применены (`alembic current` показывает `head`)
- [ ] Создан бэкап базы данных
- [ ] Проверены все индексы и ограничения
- [ ] Протестированы откаты миграций
- [ ] Настроены регулярные бэкапы
- [ ] Проверена производительность запросов
- [ ] Настроены права доступа к БД
- [ ] Документированы все кастомные миграции

---

## Дополнительные ресурсы

- [Документация Alembic](https://alembic.sqlalchemy.org/)
- [Документация PostgreSQL](https://www.postgresql.org/docs/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
