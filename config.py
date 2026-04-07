"""
Configuration for MyBank
"""
import os

# Database Configuration
# PostgreSQL connection string format: postgresql://user:password@host:port/dbname
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/mybank'
)

# For local testing with SQLite (fallback)
# Set USE_SQLITE=true to use SQLite instead
USE_SQLITE = os.getenv('USE_SQLITE', 'false').lower() == 'true'

if USE_SQLITE:
    DATABASE_URL = 'sqlite:///mybank.db'

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Bot settings
BOT_NAME = "MyBank"
BOT_VERSION = "3.0.0"

# Transaction limits
MIN_TRANSFER_AMOUNT = 0.01
MAX_TRANSFER_AMOUNT = 1000000.0
MAX_DEPOSIT_AMOUNT = 100000.0
MAX_WITHDRAW_AMOUNT = 100000.0

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
