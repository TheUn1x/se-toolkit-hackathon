# MyBank - Полная документация проекта

## 📋 Описание проекта

**MyBank** - Telegram-бот для P2P банкинга с поддержкой PostgreSQL/SQLite

### Конечный пользователь
Владельцы Telegram, которым нужен простой способ:
- Переводить деньги другим пользователям (P2P)
- Отслеживать баланс
- Пополнять и выводить средства (тестовые режимы)

### Проблема
Упрощает денежные переводы между пользователями без необходимости использовать сложные банковские приложения.

### Идея в одном предложении
Telegram-бот для мгновенных P2P переводов между пользователями с PIN-защитой.

### Ключевая функция
**P2P переводы по ID** с подтверждением PIN-кодом.

---

## 🚀 Версии продукта

### Version 1 - MVP ✅ Завершено
- Регистрация пользователей
- Проверка баланса
- P2P переводы
- История транзакций
- SQLite база данных

### Version 2 - Текущая ✅ Завершено
- PIN-аутентификация (SHA-256 хеширование)
- Пополнение баланса (тестовое, без PIN)
- Вывод средств (тестовый, с PIN)
- Payment Gateways (Stub, Card, Crypto)
- Возврат в главное меню после операций
- Улучшенная обработка ошибок

### Version 3 - Database Migration ✅ Завершено
- **PostgreSQL поддержка**
- SQLite fallback
- Connection pooling
- Environment configuration (.env)
- Setup scripts

---

## 🗄️ База данных

### PostgreSQL (Production)
```sql
-- Автоматически создается SQLAlchemy
-- Таблицы:
-- users: id, telegram_id, username, first_name, last_name, balance, pin_hash, created_at
-- transactions: id, sender_id, receiver_id, amount, description, transaction_type, transaction_id, created_at
```

### SQLite (Development/Testing)
Используется автоматически когда PostgreSQL недоступен.

### Переключение между БД
```powershell
# Использовать SQLite
$env:USE_SQLITE="true"

# Использовать PostgreSQL
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/mybank"
```

---

## 📁 Структура проекта

```
MyBank/
├── bot.py                  # Telegram bot (main)
├── bank_api.py             # Banking business logic
├── database.py             # Database models (PostgreSQL/SQLite)
├── auth.py                 # PIN authentication
├── config.py               # Configuration
├── payment_gateways/       # Payment gateway implementations
│   ├── __init__.py
│   ├── base.py             # Abstract base class
│   ├── stub.py             # Test stub gateway
│   ├── card.py             # Card payment (test)
│   └── crypto.py           # Crypto payment (test)
├── setup_postgres.py       # PostgreSQL setup script
├── setup_test_users.py     # Test users creation
├── add_balance.py          # Utility for adding balance
├── reset_db.py             # Database reset utility
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── .env.example            # Environment template
├── POSTGRES_SETUP.md       # PostgreSQL setup guide
└── README.md               # Project documentation
```

---

## 🛠️ Технологический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Язык | Python | 3.14 |
| Bot Framework | python-telegram-bot | 20+ |
| ORM | SQLAlchemy | 2.0+ |
| Database (Prod) | PostgreSQL | 15+ |
| Database (Dev) | SQLite | 3.x |
| Payment Gateways | Custom | - |
| Auth | SHA-256 + Salt | - |
| Env Management | python-dotenv | 1.0+ |

---

## 🎯 Демонстрация TA

### Что показать:

1. **Регистрация:**
   - `/start` - автоматическая регистрация
   - Показывается главное меню с балансом

2. **PIN-аутентификация:**
   - `/pin` → ввод PIN (1234)
   - PIN хешируется с солью

3. **Пополнение (без PIN):**
   - 📥 Пополнить → 1000
   - Мгновенное зачисление

4. **P2P Перевод:**
   - 💸 Перевод → ID: 2 → 500 → PIN: 1234
   - Перевод другому пользователю

5. **Вывод (с PIN):**
   - 📤 Вывести → Stub → 200 → PIN: 1234

6. **История:**
   - 📊 История - все операции

7. **База данных:**
   - Показать `database.py` с PostgreSQL поддержкой
   - Объяснить миграцию SQLite → PostgreSQL

---

## 📊 Архитектура

```
┌─────────────┐
│   Telegram   │
│    Users     │
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│  Telegram Bot   │
│   (bot.py)      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   Bank API      │
│ (bank_api.py)   │
│ + Auth + GW     │
└────────────────┘
       │
       ▼
┌─────────────────┐
│   Database      │
│ (database.py)   │
│ PostgreSQL/SQLite│
└─────────────────┘
```

---

## 🔒 Безопасность

- **PIN-коды:** SHA-256 хеширование с солью
- **Сессии:** Уникальные токены для аутентификации
- **Валидация:** Все входные данные проверяются
- **Лимиты:** Ограничения на суммы операций
- **Логирование:** Все действия записываются

---

## 📝 Лицензия
MIT

---

## 👥 Команда
Разработано для курса Software Engineering
