"""
Crypto payment gateway (stub for testing)
Simulates cryptocurrency payment processing
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


class CryptoPaymentGateway(BasePaymentGateway):
    """
    Crypto payment gateway - simulates crypto processing.
    For testing purposes only.
    """
    
    # Test wallet addresses
    TEST_WALLETS = {
        'BTC': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
        'ETH': '0x742d35Cc6634C0532925a3b844Bc9e7595f2bD38',
        'USDT': 'TN2YqJvJqKqJqKqJqKqJqKqJqKqJqKqJqK'
    }
    
    # Mock exchange rates (RUB)
    EXCHANGE_RATES = {
        'BTC': 5000000,  # 1 BTC = 5,000,000 RUB
        'ETH': 250000,   # 1 ETH = 250,000 RUB
        'USDT': 90       # 1 USDT = 90 RUB
    }
    
    def __init__(self):
        self._transactions: dict[str, PaymentResponse] = {}
    
    @property
    def name(self) -> str:
        return "Crypto Payment Gateway"
    
    @property
    def supported_methods(self) -> list[PaymentMethod]:
        return [PaymentMethod.CRYPTO]
    
    async def process_deposit(self, request: PaymentRequest) -> PaymentResponse:
        """Process crypto deposit"""
        transaction_id = f"CRYPTO-DEP-{uuid.uuid4().hex[:8].upper()}"
        
        # Get crypto details from metadata
        crypto_type = request.metadata.get('crypto_type', 'BTC').upper()
        
        if crypto_type not in self.EXCHANGE_RATES:
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                status=TransactionStatus.FAILED,
                amount=request.amount,
                message=f"Неподдерживаемая криптовалюта: {crypto_type}",
                timestamp=datetime.utcnow(),
                error_code="UNSUPPORTED_CRYPTO"
            )
        
        # Calculate crypto amount
        rate = self.EXCHANGE_RATES[crypto_type]
        crypto_amount = request.amount / rate
        
        # Generate wallet address
        wallet = self.TEST_WALLETS.get(crypto_type, 'unknown')
        
        # Simulate processing (waiting for blockchain confirmation)
        await asyncio.sleep(1.0)
        
        response = PaymentResponse(
            success=True,
            transaction_id=transaction_id,
            status=TransactionStatus.COMPLETED,
            amount=request.amount,
            message=f"Пополнение выполнено: {request.amount:.2f} ₽",
            timestamp=datetime.utcnow(),
            details={
                "method": "crypto",
                "crypto_type": crypto_type,
                "crypto_amount": f"{crypto_amount:.8f}",
                "wallet": wallet[:10] + "..." + wallet[-10:],
                "exchange_rate": rate,
                "type": "deposit"
            }
        )
        
        self._transactions[transaction_id] = response
        return response
    
    async def process_withdrawal(self, request: PaymentRequest) -> PaymentResponse:
        """Process crypto withdrawal"""
        transaction_id = f"CRYPTO-WD-{uuid.uuid4().hex[:8].upper()}"
        
        # Get crypto details from metadata
        crypto_type = request.metadata.get('crypto_type', 'BTC').upper()
        destination_wallet = request.metadata.get('destination_wallet', '')
        
        if crypto_type not in self.EXCHANGE_RATES:
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                status=TransactionStatus.FAILED,
                amount=request.amount,
                message=f"Неподдерживаемая криптовалюта: {crypto_type}",
                timestamp=datetime.utcnow(),
                error_code="UNSUPPORTED_CRYPTO"
            )
        
        if not destination_wallet:
            return PaymentResponse(
                success=False,
                transaction_id=transaction_id,
                status=TransactionStatus.FAILED,
                amount=request.amount,
                message="Укажите адрес кошелька",
                timestamp=datetime.utcnow(),
                error_code="MISSING_WALLET"
            )
        
        # Calculate crypto amount
        rate = self.EXCHANGE_RATES[crypto_type]
        crypto_amount = request.amount / rate
        
        # Simulate processing
        await asyncio.sleep(1.0)
        
        response = PaymentResponse(
            success=True,
            transaction_id=transaction_id,
            status=TransactionStatus.COMPLETED,
            amount=request.amount,
            message=f"Вывод {crypto_amount:.8f} {crypto_type} выполнен",
            timestamp=datetime.utcnow(),
            details={
                "method": "crypto",
                "crypto_type": crypto_type,
                "crypto_amount": f"{crypto_amount:.8f}",
                "destination": destination_wallet[:10] + "..." + destination_wallet[-10:],
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


crypto_gateway = CryptoPaymentGateway()
