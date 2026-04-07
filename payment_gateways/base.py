"""
Base payment gateway interface
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class PaymentMethod(Enum):
    """Supported payment methods"""
    CARD = "card"
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"
    STUB = "stub"


class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PaymentRequest:
    """Payment request data"""
    amount: float
    currency: str
    user_id: int
    method: PaymentMethod
    description: str = ""
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PaymentResponse:
    """Payment response data"""
    success: bool
    transaction_id: str
    status: TransactionStatus
    amount: float
    message: str
    timestamp: datetime
    error_code: Optional[str] = None
    details: dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class BasePaymentGateway(ABC):
    """Abstract base class for payment gateways"""
    
    @abstractmethod
    async def process_deposit(self, request: PaymentRequest) -> PaymentResponse:
        """Process deposit transaction"""
        pass
    
    @abstractmethod
    async def process_withdrawal(self, request: PaymentRequest) -> PaymentResponse:
        """Process withdrawal transaction"""
        pass
    
    @abstractmethod
    async def get_transaction_status(self, transaction_id: str) -> PaymentResponse:
        """Check transaction status"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Gateway name"""
        pass
    
    @property
    @abstractmethod
    def supported_methods(self) -> list[PaymentMethod]:
        """List of supported payment methods"""
        pass
