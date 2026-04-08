# 💰 CashFlow

**Shared expense tracking made simple** — track group spending, settle debts automatically, and never argue about money again.

---

## Demo

### Web App
![Dashboard](
)
*Dashboard with stats, quick expense form, and group overview*

![Balances](<img width="1865" height="912" alt="image" src="https://github.com/user-attachments/assets/fbfae9c1-4a8d-4803-adf1-97c681962be2" />
)
*Balance overview showing who owes whom*

![Optimize](<img width="1868" height="915" alt="image" src="https://github.com/user-attachments/assets/e9238a19-b02d-49c0-8c0c-fdf2e5c50af4" />
)
*One-click optimized debt settlement plan — minimizes number of transactions*

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

**CashFlow** automatically tracks all shared expenses, calculates real-time balances, and generates the **minimum number of transactions** needed to settle everything. Clean web interface with responsive design — works on desktop and mobile.

---

## Features

### ✅ Implemented

| Feature | Status |
|---|:---:|
| Email/password registration & login | ✅ |
| Groups (create, invite, leave, archive) | ✅ |
| Add expenses with categories & currency | ✅ |
| Split types: equal / by percent / by exact amounts | ✅ |
| Real-time balance calculation | ✅ |
| Full & partial debt settlement | ✅ |
| Optimized debt plan (minimum transactions) | ✅ |
| Expense history with filters (date, category, group) | ✅ |
| Group-level balances & expense views | ✅ |
| Delete/edit expenses (with safety checks) | ✅ |
| Weekly digest & overdue debt reports (API) | ✅ |
| Responsive mobile-friendly design | ✅ |
| Docker Compose one-command deploy | ✅ |
| PostgreSQL + SQLite support | ✅ |
| Interactive API documentation (`/docs`) | ✅ |
| Comprehensive test suite (57 tests) | ✅ |

### 🚧 Planned

| Feature | Status |
|---|---|
| Expense file attachments (photos of receipts) | Not yet |
| Multi-currency automatic conversion | Not yet |
| Push notifications (browser / mobile) | Not yet |
| OAuth2 / Google login | Not yet |
| Export to CSV / PDF reports | Not yet |
| Recurring expenses (subscriptions, rent) | Not yet |
| Activity log / audit trail | Not yet |
| i18n (English / Russian toggle) | Not yet |
| Telegram bot companion | Not yet |

---

## Usage

### Quick Start

```bash
# 1. Clone
git clone https://github.com/TheUn1x/se-toolkit-hackathon.git
cd se-toolkit-hackathon

# 2. Start everything with one command
docker compose up -d
```

| Service | URL |
|---|---|
| **Web app** | `http://your-server:8000` |
| **API docs** | `http://your-server:8000/docs` |
| **Health check** | `http://your-server:8000/api/health` |

### Local Development (no Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start API
rm -f cashflow.db
python3 -m uvicorn api:app --reload --port 8000
```

Then open `http://localhost:8000` in your browser.

### Running Tests

```bash
python3 -m unittest test_cashflow -v
```

**57 tests** covering: balance calculation, split types (equal/percent/exact), groups, settlements, debt optimization, edge cases, kopeck rounding.

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
newgrp docker
```

### Step-by-Step Deployment

#### 1. Clone the repository

```bash
git clone https://github.com/TheUn1x/se-toolkit-hackathon.git
cd se-toolkit-hackathon
```

#### 2. Build and start

```bash
docker compose up -d --build
```

This starts 2 containers:

| Container | Description | Port |
|---|---|---|
| `cashflow-postgres` | PostgreSQL 16 database | internal only |
| `cashflow-api` | FastAPI backend + web UI | 8000 |

#### 3. Verify

```bash
# Check all containers are healthy
docker compose ps

# Health check
curl http://localhost:8000/api/health
# Expected: {"status":"ok","service":"CashFlow API","version":"3.0.0"}
```

#### 4. Access the app

- **Web:** Open `http://your-server-ip:8000` in any browser
- **API docs:** `http://your-server-ip:8000/docs` — interactive Swagger UI to test every endpoint

#### 5. Production hardening (optional)

```bash
# Run behind Nginx reverse proxy with SSL
sudo apt install nginx certbot python3-certbot-nginx

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
sudo certbot --nginx -d your-domain.com
```

#### 6. Database backups

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
docker compose logs -f api       # API logs
docker compose logs -f postgres  # Database logs
```

---

## Architecture

```
┌──────────────────────────────────────┐
│         Web Browser                  │
│   (Dashboard / Groups / Balances)    │
└────────────────┬─────────────────────┘
                 │ HTTP
                 ▼
┌──────────────────────────────────────┐
│  FastAPI (port 8000)                 │
│  • REST API  • Web UI  • Auth        │
│  • Groups    • Expenses  • Balances  │
│  • Settlements  • Optimization       │
└────────────────┬─────────────────────┘
                 │ SQLAlchemy
                 ▼
┌──────────────────────────────────────┐
│  PostgreSQL 16                       │
│  • users  • groups  • expenses       │
│  • expense_splits  • settlements     │
│  • link_codes  • user_settings       │
└──────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI |
| **Database** | PostgreSQL 16 (SQLite fallback) |
| **Web Frontend** | Vanilla HTML/CSS/JS, fully responsive |
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
| `GET` | `/api/groups/{id}` | Group details with members |
| `POST` | `/api/expenses` | Add expense |
| `PUT` | `/api/expenses/{id}` | Edit expense |
| `DELETE` | `/api/expenses/{id}` | Delete expense |
| `GET` | `/api/expenses?group_id=1&category=food` | Filtered expenses |
| `GET` | `/api/balances/{user_id}` | User balances |
| `GET` | `/api/balances/group/{group_id}` | Group balances |
| `GET` | `/api/optimize-settlements` | Optimal debt plan |
| `POST` | `/api/settle` | Record settlement |
| `GET` | `/api/stats` | Global statistics |
| `GET` | `/api/categories` | Available categories |
| `GET` | `/api/currencies` | Available currencies |

Full interactive docs at **`http://your-server:8000/docs`**.

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Contact

- **GitHub:** [TheUn1x](https://github.com/TheUn1x)
- **Issues:** [Report bugs here](https://github.com/TheUn1x/se-toolkit-hackathon/issues)
