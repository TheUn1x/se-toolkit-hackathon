"""
Script to add test balance to users
Usage: python add_balance.py [telegram_id] [amount]
"""
import sys
from database import Database

def add_balance(telegram_id, amount):
    """Add balance to a user"""
    db = Database()
    user = db.get_user_by_telegram(telegram_id)
    
    if not user:
        print(f"❌ User with telegram_id {telegram_id} not found")
        return
    
    print(f"User: {user.first_name} (ID: {user.id})")
    print(f"Current balance: {user.balance:.2f} ₽")
    print(f"Adding: {amount:.2f} ₽")
    
    db.update_balance(user.id, amount)
    
    user = db.get_user_by_telegram(telegram_id)
    print(f"New balance: {user.balance:.2f} ₽")
    print("✅ Success!")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python add_balance.py [telegram_id] [amount]")
        print("Example: python add_balance.py 123456789 1000")
        sys.exit(1)
    
    telegram_id = int(sys.argv[1])
    amount = float(sys.argv[2])
    add_balance(telegram_id, amount)
