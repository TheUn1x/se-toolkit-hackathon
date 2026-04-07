"""
Launcher for CashFlow bot
"""
import os
import sys

# Set the bot token directly
BOT_TOKEN = "6159582297:AAFUBMfGJOsrRAkxtH3bFAugDxKedWxQfY8"
os.environ['TELEGRAM_BOT_TOKEN'] = BOT_TOKEN

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the bot
from bot import main

if __name__ == '__main__':
    print("🚀 Starting CashFlow Bot...")
    print(f"Token: {BOT_TOKEN[:20]}...")
    main()
