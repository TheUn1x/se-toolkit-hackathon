# 💰 CashFlow

**Shared expense tracking made simple** — track group spending, settle debts automatically, and never argue about money again.

---

## Demo

### Web App
![Dashboard](docs/screenshots/dashboard.png)
*Dashboard with stats, quick expense form, and group overview*

![Balances](docs/screenshots/balances.png)
*Balance overview showing who owes whom*

![Optimize](docs/screenshots/optimize.png)
*One-click optimized debt settlement plan*

### Telegram Bot
![Bot Menu](docs/screenshots/bot_menu.png)
*Main menu with all commands*

![Bot Add Expense](docs/screenshots/bot_expense.png)
*Step-by-step expense dialog*

> **Live demo:** Replace with your deployed URL or add a GIF recording

---

## Product Context

### End Users

- **Roommates** splitting rent, utilities, and groceries
- **Friends** sharing costs for trips, dinners, and events
- **Couples** managing joint household expenses
- **Colleagues** splitting lunch, taxi, and team event costs
- **Anyone** who ever said *"I'll pay you back later"* and forgot

### The Problem

Splitting shared expenses is a mess:

- 💸 *"Who paid for what?"* — no one remembers
- 📱 Group chats with messy calculations no one trusts
- ⏳ Debts pile up and nobody settles for months
- 🧮 Calculating balances manually for 4+ people is painful
- 📊 No one knows the real net balance across all groups

### Our Solution

**CashFlow** automatically tracks all shared expenses, calculates real-time balances, and generates the **minimum number of transactions** needed to settle everything. Works via **web app** and **Telegram bot** — synced to the same database.

---

## Features

### ✅ Implemented

| Feature | Web App | Telegram Bot |
|---|:---:|:---:|
| Email/password registration | ✅ | — |
| Telegram account linking | ✅ | ✅ |
| Groups (create, invite, leave, archive) | ✅ | ✅ |
| Add expenses with categories & currency | ✅ | ✅ |
| Split types: equal / percent / exact | ✅ | ✅ |
| Real-time balance calculation | ✅ | ✅ |
| Full & partial debt settlement | ✅ | ✅ |
| Optimized debt plan (min transactions) | ✅ | ✅ |
| Expense history with filters | ✅ | ✅ |
| Group-level balances & views | ✅ | ✅ |
| Delete/edit expenses (with safety checks) | ✅ | — |
| Weekly digest & overdue notifications | ✅ (API) | ✅ (API) |
| Responsive mobile design | ✅ | — |
| Docker Compose deployment | ✅ | ✅ |
| PostgreSQL + SQLite support | ✅ | ✅ |
| OpenAPI docs (`/docs`) | ✅ | — |

### 🚧 Planned

| Feature | Status |
|---|---|
| Expense file attachments (photos of receipts) | Not yet |
| Multi-currency automatic conversion | Not yet |
| Push notifications (browser mobile) | Not yet |
| Scheduled weekly digest (Telegram cron) | Not yet |
| OAuth2 / Google login | Not yet |
| Export to CSV / PDF reports | Not yet |
| Recurring expenses (subscriptions) | Not yet |
| Activity log / audit trail | Not yet |
| i18n (English / Russian toggle) | Not yet |

---

## Usage

### Quick Start

```bash
# 1. Clone
git clone https://github.com/TheUn1x/se-toolkit-hackathon.git
cd se-toolkit-hackathon

# 2. Set your Telegram bot token (get from @BotFather)
echo "TELEGRAM_BOT_TOKEN=your_token_here" > .env

# 3. Start everything with one command
docker compose up -d
```

| Service | URL |
|---|---|
| **Web app** | `http://your-server:8000` |
| **API docs** | `http://your-server:8000/docs` |
| **Health check** | `http://your-server:8000/api/health` |
| **Telegram bot** | Open your bot in Telegram → `/start` |

### Local Development (no Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start API
rm -f cashflow.db
python3 -m uvicorn api:app --reload --port 8000

# Start Telegram bot (separate terminal)
python3 bot.py
```

### Running Tests

```bash
python3 -m unittest test_cashflow -v
```

**57 tests** covering: balance calculation, split types, groups, settlements, debt optimization, edge cases.

---

## Deployment

### Target Environment

- **OS:** Ubuntu 24.04 LTS
- **RAM:** 1 GB minimum (2 GB recommended)
- **Disk:** 5 GB free
- **Docker:** 24.0+
- **Docker Compose:** v2.20+

### Prerequisites

```bash
# Install Docker (if not installed)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### Step-by-Step Deployment

#### 1. Clone the repository

```bash
git clone https://github.com/TheUn1x/se-toolkit-hackathon.git
cd se-toolkit-hackathon
```

#### 2. Create `.env` file

```bash
# Get your bot token from @BotFather on Telegram
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=6159582297:AAFUBMfGJOsrRAkxtH3bFAugDxKedWxQfY8
EOF
```

#### 3. Build and start

```bash
docker compose up -d --build
```

This starts 3 containers:

| Container | Description | Port |
|---|---|---|
| `cashflow-postgres` | PostgreSQL 16 database | 5432 |
| `cashflow-api` | FastAPI backend + web UI | 8000 |
| `cashflow-bot` | Telegram bot | — |

#### 4. Verify

```bash
# Check all containers are healthy
docker compose ps

# Health check
curl http://localhost:8000/api/health
# Expected: {"status":"ok","service":"CashFlow API","version":"3.0.0"}
```

#### 5. Access the app

- **Web:** Open `http://your-server-ip:8000` in browser
- **API docs:** `http://your-server-ip:8000/docs`
- **Telegram:** Open your bot → send `/start`

#### 6. Production hardening (optional)

```bash
# Run behind Nginx reverse proxy
sudo apt install nginx

sudo tee /etc/nginx/sites-available/cashflow << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/cashflow /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Add SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### 7. Database backups

```bash
# Backup
docker exec cashflow-postgres pg_dump -U cashflow cashflow > backup_$(date +%F).sql

# Restore
docker exec -i cashflow-postgres psql -U cashflow cashflow < backup_2025-01-01.sql
```

### Stopping & Updating

```bash
# Stop
docker compose down

# Update code and restart
git pull
docker compose up -d --build
```

### Logs

```bash
docker compose logs -f api    # API logs
docker compose logs -f bot    # Telegram bot logs
docker compose logs -f postgres  # Database logs
```

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Web App    │     │ Telegram    │     │  REST API   │
│  (React/JS) │     │ Bot         │     │  (FastAPI)  │
│  Port 8000  │     │ (aiogram)   │     │  /api/*     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │  Port 5432  │
                    └─────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI |
| **Database** | PostgreSQL 16 (SQLite fallback) |
| **Web Frontend** | Vanilla HTML/CSS/JS, responsive |
| **Telegram Bot** | python-telegram-bot v20+ |
| **Deployment** | Docker + Docker Compose |
| **Testing** | Python unittest (57 tests) |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register user (email + password) |
| `POST` | `/api/auth/login` | Login |
| `GET` | `/api/users` | List all users |
| `POST` | `/api/groups` | Create group |
| `GET` | `/api/groups?user_id=1` | User's groups |
| `POST` | `/api/expenses` | Add expense |
| `GET` | `/api/expenses?group_id=1&category=food` | Filtered expenses |
| `GET` | `/api/balances/{user_id}` | User balances |
| `GET` | `/api/optimize-settlements` | Optimal debt plan |
| `POST` | `/api/settle` | Record settlement |
| `GET` | `/api/stats` | Global statistics |

Full interactive docs at **`http://your-server:8000/docs`**.

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Contact

- **GitHub:** [TheUn1x](https://github.com/TheUn1x)
- **Issues:** [Report bugs here](https://github.com/TheUn1x/se-toolkit-hackathon/issues)
