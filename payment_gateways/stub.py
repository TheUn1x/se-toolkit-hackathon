"""
Stub payment gateway for testing
Simulates payment processing without real transactions
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional
from .base import (
    BasePaymentGateway, 
    PaymentRequest, 
    PaymentResponse, 
    PaymentMethod, 
    TransactionStatus
)


# Universal test API key
TEST_API_KEY = "sk-test-mybank-12345-universal-key"


class StubPaymentGateway(BasePaymentGateway):
    """
    Stub payment gateway for testing purposes.
    Simulates payment processing with configurable success/failure rates.
    """
    
    def __init__(self, success_rate: float = 0.95, processing_delay: float = 1.0):
        """
        Initialize stub gateway
        
        Args:
            success_rate: Probability of successful transaction (0.0 - 1.0)
            processing_delay: Simulated processing time in seconds
        """
        self._success_rate = success_rate
        self._processing_delay = processing_delay
        self._transactions: dict[str, PaymentResponse] = {}
    
    @property
    def name(self) -> str:
        return "Stub Payment Gateway"
    
    @property
    def supported_methods(self) -> list[PaymentMethod]:
        return [PaymentMethod.CARD, PaymentMethod.CRYPTO, PaymentMethod.BANK_TRANSFER, PaymentMethod.STUB]
    
    async def _simulate_processing(self, request: PaymentRequest, is_deposit: bool) -> PaymentResponse:
        """Simulate payment processing"""
        
        # Simulate network delay
        await asyncio.sleep(self._processing_delay)
        
        # Generate transaction ID
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        
        # Simulate random failures
        import random
        if random.random() > self._success_rate:
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                status=TransactionStatus.FAILED,
                amount=request.amount,
                message="Транзакция отклонена банком. Попробуйте позже.",
                timestamp=datetime.utcnow(),
                error_code="BANK_DECLINED",
                details={
                    "method": request.method.value,
                    "type": "deposit" if is_deposit else "withdrawal"
                }
            )
        
        # Simulate specific error cases
        if request.amount > 100000:
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                status=TransactionStatus.FAILED,
                amount=request.amount,
                message="Превышен лимит операции. Максимум: 100,000 ₽",
                timestamp=datetime.utcnow(),
                error_code="LIMIT_EXCEEDED",
                details={"limit": 100000}
            )
        
        # Success
        return PaymentResponse(
            success=True,
            transaction_id=transaction_id,
            status=TransactionStatus.COMPLETED,
            amount=request.amount,
            message=f"Операция выполнена успешно!",
            timestamp=datetime.utcnow(),
            details={
                "method": request.method.value,
                "type": "deposit" if is_deposit else "withdrawal",
                "api_key_used": TEST_API_KEY[:20] + "..."
            }
        )
    
    async def process_deposit(self, request: PaymentRequest) -> PaymentResponse:
        """Process deposit (simulated)"""
        response = await self._simulate_processing(request, is_deposit=True)
        self._transactions[response.transaction_id] = response
        return response
    
    async def process_withdrawal(self, request: PaymentRequest) -> PaymentResponse:
        """Process withdrawal (simulated)"""
        response = await self._simulate_processing(request, is_deposit=False)
        self._transactions[response.transaction_id] = response
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


# Global stub gateway instance
stub_gateway = StubPaymentGateway(success_rate=0.95, processing_delay=0.5)
