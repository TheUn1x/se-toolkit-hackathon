#!/usr/bin/env python3
"""Quick upgrade and run script"""
import subprocess
import sys
import os

print("Upgrading python-telegram-bot with uv...")
subprocess.check_call(["uv", "pip", "install", "--upgrade", "python-telegram-bot"])

print("\nStarting bot...")
os.environ['TELEGRAM_BOT_TOKEN'] = "6159582297:AAFUBMfGJOsrRAkxtH3bFAugDxKedWxQfY8"

from bot import main
main()
