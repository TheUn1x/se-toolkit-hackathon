"""
SQLite Database Demo - Shows that SQLite is working
Run this to demonstrate database functionality
"""
import os
from database import Database
from auth import AuthManager

def demo_sqlite():
    """Demonstrate SQLite database functionality"""
    
    print("=" * 60)
    print("MyBank - SQLite Database Demo")
    print("=" * 60)
    print()
    
    # 1. Show database file
    db_path = 'mybank.db'
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"✅ Database file exists: {os.path.abspath(db_path)}")
        print(f"   Size: {size:,} bytes ({size/1024:.1f} KB)")
    else:
        print("❌ Database file not found")
        return
    
    print()
    
    # 2. Initialize database
    print(" Initializing database...")
    db = Database()
    print("✅ Database initialized successfully")
    print()
    
    # 3. Show tables
    session = db.get_session()
    from sqlalchemy import text
    
    print("📊 Database tables:")
    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = result.fetchall()
    for table in tables:
        print(f"   • {table[0]}")
    print()
    
    # 4. Show table schemas
    print("📋 Table schemas:")
    for table in tables:
        table_name = table[0]
        result = session.execute(text(f"PRAGMA table_info({table_name})"))
        columns = result.fetchall()
        print(f"\n   Table: {table_name}")
        print("   " + "-" * 50)
        for col in columns:
            col_id, name, col_type, not_null, default, pk = col
            pk_marker = " 🔑" if pk else ""
            print(f"   {name:20} {col_type:15} {'NOT NULL' if not_null else 'NULL':8}{pk_marker}")
    print()
    
    # 5. Show users
    print("👥 Users in database:")
    from database import User
    users = session.query(User).all()
    
    if users:
        for user in users:
            pin_status = "✅ Set" if user.pin_hash else "❌ Not set"
            print(f"   • {user.first_name} (ID: {user.id}, Telegram: {user.telegram_id})")
            print(f"     Balance: {user.balance:.2f} ₽ | PIN: {pin_status}")
    else:
        print("   No users found")
    print()
    
    # 6. Show transactions
    print("💰 Recent transactions:")
    from database import Transaction
    transactions = session.query(Transaction).order_by(Transaction.created_at.desc()).limit(10).all()
    
    if transactions:
        for t in transactions:
            sender = session.query(User).filter_by(id=t.sender_id).first()
            receiver = session.query(User).filter_by(id=t.receiver_id).first()
            
            sender_name = sender.first_name if sender else "Unknown"
            receiver_name = receiver.first_name if receiver else "Unknown"
            
            type_emoji = {
                'transfer': '💸',
                'deposit': '📥',
                'withdrawal': '📤'
            }.get(t.transaction_type, '💰')
            
            print(f"   {type_emoji} {t.amount:.2f} ₽ | {t.transaction_type:12} | {sender_name} → {receiver_name}")
            print(f"     {t.created_at.strftime('%d.%m.%Y %H:%M:%S')} | {t.description or 'No description'}")
    else:
        print("   No transactions found")
    
    session.close()
    print()
    
    # 7. Show database statistics
    print("📈 Database statistics:")
    print(f"   Total users: {len(users)}")
    print(f"   Total transactions: {len(transactions)}")
    print()
    
    print("=" * 60)
    print("✅ SQLite database is fully functional!")
    print("=" * 60)


if __name__ == '__main__':
    demo_sqlite()
