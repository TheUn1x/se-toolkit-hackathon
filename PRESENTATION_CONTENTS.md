# CashFlow Presentation Slides Content
# Format these into a PDF (5 slides) using any tool (Google Slides, Canva, PowerPoint)

# ============================================================
# SLIDE 1: Title
# ============================================================

Title: CashFlow — Shared Expense Tracker

Subtitle: Automatically calculate who owes whom after shared expenses

Name: [YOUR NAME]
Email: [YOUR UNIVERSITY EMAIL]
Group: [YOUR GROUP]

# ============================================================
# SLIDE 2: Context
# ============================================================

End User:
- Roommates splitting rent and groceries
- Friends dividing restaurant bills
- Colleagues sharing lunch costs

Problem:
- Tracking shared expenses is chaotic
- No one remembers who paid for what
- Arguments about unfair splits

Product Idea (one sentence):
- "CashFlow automatically calculates and tracks shared expenses between people, showing exactly who owes whom and how much."

# ============================================================
# SLIDE 3: Implementation
# ============================================================

How I Built It:
- Used LLM agents (Qwen Code) for code generation, debugging, and architecture
- AI-assisted balance calculation logic fixing
- Automated test generation (23 unit tests, all passing)
- Frontend scaffolding with AI assistance

Version 1 (Core Feature):
- FastAPI REST backend with expense/balance/settlement endpoints
- SQLite database with SQLAlchemy ORM
- Web interface: add expenses, view balances, settle debts

Version 2 (Improved):
- Dashboard with statistics overview
- Partial settlement support
- Docker + docker-compose deployment
- Polished UI with responsive design
- Comprehensive README documentation

TA Feedback Addressed:
- Fixed balance calculation logic (was incorrect for multi-person expenses)
- Added partial settlement (not just full)
- Added deployment (was local-only)
- Added web interface (Telegram bots blocked on university VMs)

# ============================================================
# SLIDE 4: Demo
# ============================================================

[Pre-recorded video goes here — see DEMO_INSTRUCTIONS.md]

Video: 2 minutes max, with voice-over
Shows: Adding a user → Adding an expense → Viewing balances → Settling a debt

# ============================================================
# SLIDE 5: Links
# ============================================================

GitHub Repository:
https://github.com/YOUR_USERNAME/se-toolkit-hackathon

Deployed Product:
http://YOUR_SERVER_IP:8000

[QR codes for both links]
