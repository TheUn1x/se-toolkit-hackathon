"""
Add balance and create test users for P2P testing
"""
from database import Database

def setup_test_users():
    """Create test users and add balance"""
    db = Database()
    
    # Main user (you)
    user1 = db.create_user(
        telegram_id=916373300,
        first_name="Максим",
        username="maxim_pro"
    )
    print(f"✅ User 1: {user1.first_name} (ID: {user1.id}, Telegram: {user1.telegram_id})")
    print(f"   Balance: {user1.balance:.2f} ₽")
    
    # Test user 2
    user2 = db.create_user(
        telegram_id=999888777,
        first_name="Тест",
        username="test_user"
    )
    print(f"\n✅ User 2: {user2.first_name} (ID: {user2.id}, Telegram: {user2.telegram_id})")
    print(f"   Balance: {user2.balance:.2f} ₽")
    
    # Add balance to main user
    db.update_balance(user1.id, 5000)
    print(f"\n💰 Added 5000 ₽ to {user1.first_name}")
    
    user1 = db.create_user(telegram_id=916373300, first_name="Максим")
    print(f"   New balance: {user1.balance:.2f} ₽")
    
    print("\n📋 P2P Testing Info:")
    print(f"   Your ID: {user1.id}")
    print(f"   Test user ID: {user2.id}")
    print(f"   Test user Telegram ID: {user2.telegram_id}")
    print("\n🔄 To test P2P transfer:")
    print(f"   1. Use /transfer in bot")
    print(f"   2. Enter receiver ID: {user2.id}")
    print(f"   3. Enter amount")
    print(f"   4. Enter your PIN")

if __name__ == '__main__':
    setup_test_users()
