# 💰 CashFlow — Shared Expense Tracker

A web application that automatically calculates who owes whom after shared expenses among friends, roommates, or colleagues. No more arguing about who paid for dinner.

---

## 📸 Demo

### Dashboard — Quick add expenses and see statistics
![Dashboard](https://via.placeholder.com/800x400/667eea/ffffff?text=CashFlow+Dashboard)

### Balances — See exactly who owes what
![Balances](https://via.placeholder.com/800x400/48bb78/ffffff?text=Balance+Overview)

---

## 📋 Context

### End Users
- **Roommates** sharing rent, utilities, groceries
- **Friends** splitting restaurant bills, trips, events
- **Colleagues** dividing lunch costs, team outings
- **Couples** tracking shared household expenses

### Problem
When multiple people share expenses, tracking who paid what and who owes whom becomes chaotic. Messages get lost, memories fade, and someone always ends up paying more than their fair share.

### Our Solution
CashFlow lets anyone record an expense, automatically calculates the split, and shows a clear balance sheet. When it's time to settle, one click records the payment and updates everyone's balances instantly.

**One-line pitch:** CashFlow automatically calculates and tracks shared expenses between people, showing exactly who owes whom and how much.

---

## ✨ Features

### Implemented (Version 1 + 2)
| Feature | Status |
|---------|--------|
| Register users | ✅ |
| Add shared expenses | ✅ |
| Automatic split calculation | ✅ |
| Balance overview (per user) | ✅ |
| Full debt settlement | ✅ |
| Partial debt settlement | ✅ |
| Expense history | ✅ |
| Dashboard with statistics | ✅ |
| REST API (FastAPI) | ✅ |
| Web interface (HTML/CSS/JS) | ✅ |
| SQLite database | ✅ |
| Docker support | ✅ |
| Unit tests (23 tests) | ✅ |

### Not Yet Implemented (Future)
| Feature | Priority |
|---------|----------|
| Email/notifications for debts | Medium |
| Currency support (USD, EUR) | Low |
| Receipt photo uploads | Medium |
| Unequal splits (custom shares) | Medium |
| Export to CSV/PDF | Low |
| Telegram bot integration | Medium |

---

## 🚀 Usage

### Quick Start (Local Development)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the API server
python -m uvicorn api:app --reload --port 8000

# 3. Open in browser
# http://localhost:8000
```

### Adding an Expense
1. Open the web app
2. Go to **Dashboard**
3. Select who paid
4. Enter the amount
5. Check the participants to split with
6. Click **Add Expense**

### Checking Balances
1. Go to **Balances** tab
2. Select a user
3. See who owes what (green = owed, red = owes)

### Settling a Debt
1. Go to **Settle** tab
2. Select who is paying and to whom
3. Enter amount (leave empty for full settlement)
4. Click **Settle**

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   Web Browser       │
│   (HTML/CSS/JS)     │
└──────────┬──────────┘
           │ HTTP
           ▼
┌─────────────────────┐
│   FastAPI Server    │
│   (api.py)          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   CashFlow API      │
│   (cashflow_api.py) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SQLite / PostgreSQL│
│   (SQLAlchemy ORM)  │
└─────────────────────┘
```

### Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy
- **Frontend:** Vanilla HTML5, CSS3, JavaScript
- **Database:** SQLite (dev), PostgreSQL (production)
- **Deployment:** Docker, docker-compose
- **Testing:** Python unittest (23 tests)

---

## 📦 Deployment

### Prerequisites (Ubuntu 24.04)
- Docker 24+ and Docker Compose 2+
- Git
- At least 256MB RAM, 1GB disk

### Step-by-Step

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/se-toolkit-hackathon.git
cd se-toolkit-hackathon

# 2. Build and run with Docker Compose
docker compose up -d --build

# 3. Verify it's running
docker compose ps

# 4. Open in browser
# http://YOUR_SERVER_IP:8000
```

### Manual Deployment (No Docker)

```bash
# 1. Install Python 3.12
sudo apt update
sudo apt install python3 python3-pip

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn api:app --host 0.0.0.0 --port 8000

# 4. (Optional) Run as a systemd service
sudo nano /etc/systemd/system/cashflow.service
```

### Systemd Service File

```ini
[Unit]
Description=CashFlow API
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/cashflow
ExecStart=/usr/bin/python3 -m uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable cashflow
sudo systemctl start cashflow
```

---

## 🧪 Testing

```bash
# Run all unit tests
python3 -m unittest test_cashflow.py -v

# Test coverage:
# - Basic expense splitting (2 and 3 people)
# - Multiple expenses accumulation
# - Full and partial settlements
# - Edge cases (no participants, overpayment, rounding)
# - User registration and pending users
```

---

## 📁 Project Structure

```
se-toolkit-hackathon/
├── api.py              # FastAPI REST API server
├── cashflow_api.py     # Core business logic (expenses, balances, settlements)
├── database.py         # SQLAlchemy models and database manager
├── test_cashflow.py    # Unit tests (23 tests)
├── static/             # Web frontend
│   ├── index.html      # Main page
│   ├── style.css       # Styles
│   └── app.js          # Frontend JavaScript
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose configuration
├── requirements.txt    # Python dependencies
├── LICENSE             # MIT License
└── README.md           # This file
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

**Built with ❤️ for the SE Toolkit Hackathon**
