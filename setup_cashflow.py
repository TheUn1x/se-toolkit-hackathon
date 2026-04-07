"""
Setup test users for CashFlow
"""
from cashflow_api import CashFlowAPI

def setup():
    cf = CashFlowAPI()
    
    # Create test users
    user1 = cf.register_user(916373300, "Максим", "maxim_pro")
    user2 = cf.register_user(999888777, "Анна", "anna_k")
    user3 = cf.register_user(888777666, "Дмитрий", "dmitry_s")
    
    print(f"✅ Users created:")
    print(f"   1. {user1.first_name} (ID: {user1.id})")
    print(f"   2. {user2.first_name} (ID: {user2.id})")
    print(f"   3. {user3.first_name} (ID: {user3.id})")
    print(f"\n📊 Total users: {cf.get_user_count()}")
    
    # Add test expense
    print("\n➕ Adding test expense...")
    expense, balances = cf.add_expense(
        payer_id=user1.id,
        amount=300,
        participants=[user2.id, user3.id],
        description="Ужин в ресторане"
    )
    
    print(f"✅ Expense added: {expense.amount} ₽")
    print(f"   Payer: {user1.first_name}")
    print(f"   Split between: {user2.first_name}, {user3.first_name}")
    print(f"   Per person: {300/3:.2f} ₽")
    
    print("\n📊 Balances:")
    user1_balances = cf.get_user_balances(user1.id)
    for b in user1_balances:
        status = "в плюсе" if b['amount'] > 0 else "в минусе"
        print(f"   {b['user']}: {b['amount']:+.2f} ₽ ({status})")

if __name__ == '__main__':
    setup()
