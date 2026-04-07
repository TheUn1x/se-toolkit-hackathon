"""
Reset database - removes old database and creates fresh one
WARNING: This will delete all data!
"""
import os
import sys

DB_FILE = 'mybank.db'

if __name__ == '__main__':
    if os.path.exists(DB_FILE):
        print(f"🗑️  Удаляю старую базу данных: {DB_FILE}")
        os.remove(DB_FILE)
        print("✅ База данных удалена")
    else:
        print("ℹ️  База данных не найдена")
    
    print("🔄 Создаю новую базу данных...")
    from database import Database
    db = Database()
    print("✅ База данных создана!")
    print("\nТеперь запустите бота: python start.py")
