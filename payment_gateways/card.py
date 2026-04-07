"""
Card payment gateway (stub for testing)
Simulates credit/debit card processing
"""
import asyncio
import uuid
from datetime import datetime
from .base import (
    BasePaymentGateway, 
    PaymentRequest, 
    PaymentResponse, 
    PaymentMethod, 
    TransactionStatus
)


class CardPaymentGateway(BasePaymentGateway):
    """
    Card payment gateway - simulates card processing.
    For testing purposes only.
    """
    
    def __init__(self):
        self._transactions: dict[str, PaymentResponse] = {}
        # Test card number (valid format but fake)
        self.test_card = "4242 4242 4242 4242"
        self.test_expiry = "12/30"
        self.test_cvv = "123"
    
    @property
    def name(self) -> str:
        return "Card Payment Gateway"
    
    @property
    def supported_methods(self) -> list[PaymentMethod]:
        return [PaymentMethod.CARD]
    
    def _validate_card(self, card_number: str) -> bool:
        """Simulate card validation"""
        # Remove spaces
        card_number = card_number.replace(" ", "")
        
        # Basic length check
        if len(card_number) != 16:
            return False
        
        # Test card always valid
        if card_number == "4242424242424242":
            return True
        
        # Luhn algorithm check (simplified)
        digits = [int(d) for d in card_number]
        digits.reverse()
        
        total = 0
        for i, digit in enumerate(digits):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        return total % 10 == 0
    
    async def process_deposit(self, request: PaymentRequest) -> PaymentResponse:
        """Process card deposit"""
        transaction_id = f"CARD-DEP-{uuid.uuid4().hex[:8].upper()}"
        
        # Get card info from metadata
        card_number = request.metadata.get('card_number', '')
        
        # Validate card
        if not self._validate_card(card_number):
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                status=TransactionStatus.FAILED,
                amount=request.amount,
                message="Неверный номер карты",
                timestamp=datetime.utcnow(),
                error_code="INVALID_CARD"
            )
        
        # Simulate processing
        await asyncio.sleep(0.5)
        
        response = PaymentResponse(
            success=True,
            transaction_id=transaction_id,
            status=TransactionStatus.COMPLETED,
            amount=request.amount,
            message=f"Пополнение на {request.amount:.2f} ₽ выполнено",
            timestamp=datetime.utcnow(),
            details={
                "method": "card",
                "card_last4": card_number[-4:] if card_number else "****",
                "type": "deposit"
            }
        )
        
        self._transactions[transaction_id] = response
        return response
    
    async def process_withdrawal(self, request: PaymentRequest) -> PaymentResponse:
        """Process card withdrawal"""
        transaction_id = f"CARD-WD-{uuid.uuid4().hex[:8].upper()}"
        
        # Simulate processing
        await asyncio.sleep(0.5)
        
        response = PaymentResponse(
            success=True,
            transaction_id=transaction_id,
            status=TransactionStatus.COMPLETED,
            amount=request.amount,
            message=f"Вывод {request.amount:.2f} ₽ на карту выполнен",
            timestamp=datetime.utcnow(),
            details={
                "method": "card",
                "type": "withdrawal"
            }
        )
        
        self._transactions[transaction_id] = response
        return response
    
    async def get_transaction_status(self, transaction_id: str) -> PaymentResponse:
        """Get transaction status"""
        return self._transactions.get(
            transaction_id,
            PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                status=TransactionStatus.FAILED,
                amount=0,
                message="Транзакция не найдена",
                timestamp=datetime.utcnow(),
                error_code="NOT_FOUND"
            )
        )


card_gateway = CardPaymentGateway()
