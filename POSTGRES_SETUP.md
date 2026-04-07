# MyBank - PostgreSQL Migration Guide

## Option 1: Use Docker (Recommended for Development)

### Quick Start with Docker:
```powershell
# Pull PostgreSQL image
docker pull postgres:15

# Run PostgreSQL container
docker run --name mybank-postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=mybank `
  -p 5432:5432 `
  -d postgres:15

# Check if running
docker ps
```

### Setup Database:
```powershell
# Set environment variable
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/mybank"

# Run setup script
.venv\Scripts\python.exe setup_postgres.py

# Initialize test users
.venv\Scripts\python.exe setup_test_users.py
```

### Start Bot:
```powershell
.venv\Scripts\python.exe start.py
```

---

## Option 2: Install PostgreSQL Locally (Windows)

1. **Download PostgreSQL:**
   - Visit: https://www.postgresql.org/download/windows/
   - Download installer
   - Run installer with default settings

2. **Create Database:**
   ```powershell
   # Using pgAdmin or psql:
   CREATE DATABASE mybank;
   ```

3. **Configure Connection:**
   Edit `.env` file:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/mybank
   ```

4. **Setup:**
   ```powershell
   .venv\Scripts\python.exe setup_postgres.py
   ```

---

## Option 3: Continue with SQLite (Fallback)

If PostgreSQL is not available, the bot will automatically use SQLite:

```powershell
# Just run the bot - it will fallback to SQLite
.venv\Scripts\python.exe start.py
```

---

## Verify Database Type

The bot logs which database it's using on startup:
- PostgreSQL: `Using PostgreSQL database: localhost:5432/mybank`
- SQLite: `Using SQLite database: mybank.db`

---

## Database Schema (Auto-Created)

Both PostgreSQL and SQLite use the same schema:
- `users` - User accounts with PIN hashes
- `transactions` - All transaction records (transfers, deposits, withdrawals)

The schema is automatically created by SQLAlchemy ORM on first connection.
