"""
Backend API for MyBank - handles business logic
"""
from database import Database
from auth import AuthManager, session_manager
from payment_gateways import (
    PaymentRequest, 
    PaymentMethod, 
    TransactionStatus,
    stub_gateway,
    card_gateway,
    crypto_gateway
)
from datetime import datetime
from typing import Optional


class BankAPI:
    """Bank API wrapper with payment gateways"""
    
    def __init__(self, db_path='mybank.db'):
        self.db = Database(db_path)
        self.payment_gateways = {
            PaymentMethod.STUB: stub_gateway,
            PaymentMethod.CARD: card_gateway,
            PaymentMethod.CRYPTO: crypto_gateway
        }
    
    def register_user(self, telegram_id, first_name, username=None, last_name=None):
        """Register or get user"""
        return self.db.create_user(telegram_id, first_name, username, last_name)
    
    def get_balance(self, telegram_id):
        """Get user balance"""
        user = self.db.get_user_by_telegram(telegram_id)
        if user:
            return user.balance
        return None
    
    def set_pin(self, telegram_id: int, pin: str) -> tuple[bool, str]:
        """Set user PIN code"""
        # Validate PIN format
        is_valid, message = AuthManager.validate_pin_format(pin)
        if not is_valid:
            return False, message
        
        # Hash and store PIN
        pin_hash = AuthManager.hash_pin(pin)
        user = self.db.get_user_by_telegram(telegram_id)
        
        if not user:
            return False, "Пользователь не найден"
        
        self.db.set_user_pin(user.id, pin_hash)
        return True, "PIN-код успешно установлен"
    
    def verify_pin(self, telegram_id: int, pin: str) -> tuple[bool, str]:
        """Verify user PIN code"""
        user = self.db.get_user_by_telegram(telegram_id)
        
        if not user:
            return False, "Пользователь не найден"
        
        if not user.pin_hash:
            return False, "PIN-код не установлен. Используйте /setpin"
        
        if AuthManager.verify_pin(pin, user.pin_hash):
            # Create authenticated session
            session_token = session_manager.create_session(telegram_id)
            session_manager.mark_authenticated(session_token)
            return True, "PIN-код верный"
        
        return False, "Неверный PIN-код"
    
    def has_pin(self, telegram_id: int) -> bool:
        """Check if user has PIN set"""
        user = self.db.get_user_by_telegram(telegram_id)
        return bool(user and user.pin_hash)
    
    async def deposit(self, telegram_id: int, amount: float, method: PaymentMethod = PaymentMethod.STUB, 
                      description: str = None, metadata: dict = None) -> tuple[bool, str, dict]:
        """
        Deposit money to user account via payment gateway
        Returns: (success, message, details)
        """
        # Validate amount
        if amount <= 0:
            return False, "Сумма должна быть больше 0", {}
        
        if amount > 100000:
            return False, "Максимальная сумма пополнения: 100,000 ₽", {}
        
        # Get user
        user = self.db.get_user_by_telegram(telegram_id)
        if not user:
            return False, "Пользователь не найден", {}
        
        # Create payment request
        request = PaymentRequest(
            amount=amount,
            currency='RUB',
            user_id=user.id,
            method=method,
            description=description or f"Пополнение баланса",
            metadata=metadata or {}
        )
        
        # Process through gateway
        gateway = self.payment_gateways.get(method)
        if not gateway:
            return False, "Неподдерживаемый метод оплаты", {}
        
        response = await gateway.process_deposit(request)
        
        if response.success:
            # Update balance
            self.db.update_balance(user.id, amount)
            # Create transaction record
            self.db.create_deposit_transaction(user.id, amount, description, response.transaction_id)
            
            return True, response.message, {
                'transaction_id': response.transaction_id,
                'details': response.details
            }
        
        return False, response.message, {'error_code': response.error_code}
    
    async def withdraw(self, telegram_id: int, amount: float, method: PaymentMethod = PaymentMethod.STUB,
                       description: str = None, metadata: dict = None) -> tuple[bool, str, dict]:
        """
        Withdraw money from user account via payment gateway
        Returns: (success, message, details)
        """
        # Validate amount
        if amount <= 0:
            return False, "Сумма должна быть больше 0", {}
        
        if amount > 100000:
            return False, "Максимальная сумма вывода: 100,000 ₽", {}
        
        # Get user
        user = self.db.get_user_by_telegram(telegram_id)
        if not user:
            return False, "Пользователь не найден", {}
        
        # Check balance
        if user.balance < amount:
            return False, f"Недостаточно средств. Доступно: {user.balance:.2f} ₽", {}
        
        # Create payment request
        request = PaymentRequest(
            amount=amount,
            currency='RUB',
            user_id=user.id,
            method=method,
            description=description or f"Вывод средств",
            metadata=metadata or {}
        )
        
        # Process through gateway
        gateway = self.payment_gateways.get(method)
        if not gateway:
            return False, "Неподдерживаемый метод оплаты", {}
        
        response = await gateway.process_withdrawal(request)
        
        if response.success:
            # Deduct from balance
            self.db.update_balance(user.id, -amount)
            # Create transaction record
            self.db.create_withdrawal_transaction(user.id, amount, description, response.transaction_id)
            
            return True, response.message, {
                'transaction_id': response.transaction_id,
                'details': response.details
            }
        
        return False, response.message, {'error_code': response.error_code}
    
    def transfer_money(self, sender_telegram_id, receiver_search, amount, description=None):
        """
        Transfer money between users
        Returns: (success: bool, message: str)
        """
        # Validate amount
        if amount <= 0:
            return False, "Сумма должна быть больше 0"
        
        if amount > 1000000:
            return False, "Максимальная сумма перевода: 1,000,000"
        
        # Get sender
        sender = self.db.get_user_by_telegram(sender_telegram_id)
        if not sender:
            return False, "Пользователь не найден"
        
        # Check balance
        if sender.balance < amount:
            return False, f"Недостаточно средств. Доступно: {sender.balance:.2f} ₽"
        
        # Find receiver
        receiver = self.db.find_user_by_search(receiver_search)
        if not receiver:
            return False, "Получатель не найден. Проверьте ID или username"
        
        if sender.id == receiver.id:
            return False, "Нельзя перевести самому себе"
        
        # Perform transfer
        try:
            self.db.update_balance(sender.id, -amount)
            self.db.update_balance(receiver.id, amount)
            self.db.create_transaction(sender.id, receiver.id, amount, description)
            
            return True, f"Успешно переведено {amount:.2f} ₽ пользователю {receiver.first_name}"
        except Exception as e:
            return False, f"Ошибка при переводе: {str(e)}"
    
    def get_transaction_history(self, telegram_id, limit=10):
        """Get user transaction history"""
        user = self.db.get_user_by_telegram(telegram_id)
        if not user:
            return None
        
        transactions = self.db.get_user_transactions(user.id, limit)
        return transactions
    
    def get_external_transaction_history(self, telegram_id, limit=10):
        """Get deposit and withdrawal history"""
        user = self.db.get_user_by_telegram(telegram_id)
        if not user:
            return None
        
        return self.db.get_external_transactions(user.id, limit)
    
    def get_user_info(self, telegram_id):
        """Get user information"""
        user = self.db.get_user_by_telegram(telegram_id)
        if user:
            return {
                'id': user.id,
                'telegram_id': user.telegram_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'balance': user.balance,
                'has_pin': bool(user.pin_hash),
                'created_at': user.created_at
            }
        return None
