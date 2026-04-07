"""
Real-time SQLite Database Monitor
Watch database changes as they happen
"""
import os
import time
import threading
from database import Database, User, Transaction
from sqlalchemy import text

class DatabaseMonitor:
    """Monitor database changes in real-time"""
    
    def __init__(self):
        self.db = Database()
        self.last_user_count = 0
        self.last_transaction_count = 0
        self.running = False
    
    def get_stats(self):
        """Get current database statistics"""
        session = self.db.get_session()
        
        user_count = session.query(User).count()
        transaction_count = session.query(Transaction).count()
        
        # Get total balance
        result = session.execute(text("SELECT SUM(balance) FROM users"))
        total_balance = result.scalar() or 0
        
        # Get recent transactions
        recent_tx = session.query(Transaction).order_by(
            Transaction.created_at.desc()
        ).limit(3).all()
        
        session.close()
        
        return {
            'users': user_count,
            'transactions': transaction_count,
            'total_balance': total_balance,
            'recent_transactions': recent_tx
        }
    
    def display_stats(self):
        """Display current database statistics"""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("📊 MyBank Database - Real-time Monitor")
        print("=" * 60)
        print(f"👥 Users: {stats['users']}")
        print(f"💰 Total Balance: {stats['total_balance']:.2f} ₽")
        print(f"📝 Transactions: {stats['transactions']}")
        
        if stats['recent_transactions']:
            print("\n🕐 Recent Transactions:")
            for t in stats['recent_transactions']:
                session = self.db.get_session()
                sender = session.query(User).filter_by(id=t.sender_id).first()
                receiver = session.query(User).filter_by(id=t.receiver_id).first()
                session.close()
                
                sender_name = sender.first_name if sender else "Unknown"
                receiver_name = receiver.first_name if receiver else "Unknown"
                
                type_emoji = {
                    'transfer': '💸',
                    'deposit': '📥',
                    'withdrawal': '📤'
                }.get(t.transaction_type, '💰')
                
                print(f"  {type_emoji} {t.amount:.2f} ₽ | {t.transaction_type:12} | {t.created_at.strftime('%H:%M:%S')}")
        
        print("=" * 60)
    
    def monitor_loop(self):
        """Monitor database for changes"""
        print("\n👀 Watching for database changes...")
        print("💡 Make transactions in the bot to see changes here\n")
        
        self.display_stats()
        
        self.running = True
        check_count = 0
        
        while self.running:
            time.sleep(1)
            check_count += 1
            
            stats = self.get_stats()
            
            # Check for changes
            if (stats['users'] != self.last_user_count or 
                stats['transactions'] != self.last_transaction_count):
                
                print("\n" + "🔔 " * 20)
                print("🔄 DATABASE CHANGED!")
                print("🔔 " * 20)
                
                if stats['users'] != self.last_user_count:
                    print(f"👥 Users: {self.last_user_count} → {stats['users']}")
                
                if stats['transactions'] != self.last_transaction_count:
                    new_tx = stats['transactions'] - self.last_transaction_count
                    print(f"📝 New Transactions: +{new_tx}")
                    print(f"💰 Total Transactions: {stats['transactions']}")
                
                self.display_stats()
                
                self.last_user_count = stats['users']
                self.last_transaction_count = stats['transactions']
            
            # Show heartbeat every 10 seconds
            if check_count % 10 == 0:
                print(f"💓 Monitoring... ({check_count}s elapsed)", end='\r')
    
    def start(self):
        """Start monitoring"""
        stats = self.get_stats()
        self.last_user_count = stats['users']
        self.last_transaction_count = stats['transactions']
        
        self.monitor_loop()
    
    def stop(self):
        """Stop monitoring"""
        self.running = False


def main():
    """Main entry point"""
    print("MyBank - Real-time Database Monitor")
    print("Press Ctrl+C to stop\n")
    
    monitor = DatabaseMonitor()
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitor stopped")
        monitor.stop()


if __name__ == '__main__':
    main()
