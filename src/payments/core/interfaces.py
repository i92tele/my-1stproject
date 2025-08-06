"""
Payment System Abstract Interfaces

Defines the contracts for external dependencies following
Clean Architecture principles.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .entities import (
    Payment, PaymentRequest, TransactionData, PriceData, 
    CryptoCurrency, PaymentStatus
)


class PaymentProviderInterface(ABC):
    """Abstract interface for cryptocurrency payment providers."""
    
    @abstractmethod
    async def verify_transaction(self, wallet_address: str, 
                               expected_amount: float, 
                               payment_id: str) -> Optional[TransactionData]:
        """Verify a transaction on the blockchain."""
        pass
    
    @abstractmethod
    async def get_wallet_balance(self, wallet_address: str) -> float:
        """Get wallet balance."""
        pass
    
    @abstractmethod
    def get_supported_currency(self) -> CryptoCurrency:
        """Get the cryptocurrency this provider supports."""
        pass
    
    @abstractmethod
    async def validate_address(self, address: str) -> bool:
        """Validate if address is valid for this cryptocurrency."""
        pass


class PriceFeedInterface(ABC):
    """Abstract interface for cryptocurrency price feeds."""
    
    @abstractmethod
    async def get_price(self, cryptocurrency: CryptoCurrency) -> Optional[PriceData]:
        """Get current price for cryptocurrency."""
        pass
    
    @abstractmethod
    async def get_multiple_prices(self, currencies: List[CryptoCurrency]) -> Dict[CryptoCurrency, PriceData]:
        """Get prices for multiple cryptocurrencies."""
        pass


class PaymentRepositoryInterface(ABC):
    """Abstract interface for payment data persistence."""
    
    @abstractmethod
    async def save_payment(self, payment: Payment) -> bool:
        """Save payment to database."""
        pass
    
    @abstractmethod
    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        pass
    
    @abstractmethod
    async def get_user_payments(self, user_id: int) -> List[Payment]:
        """Get all payments for a user."""
        pass
    
    @abstractmethod
    async def get_pending_payments(self, max_age_minutes: int = 60) -> List[Payment]:
        """Get pending payments within age limit."""
        pass
    
    @abstractmethod
    async def update_payment_status(self, payment_id: str, status: PaymentStatus) -> bool:
        """Update payment status."""
        pass


class NotificationServiceInterface(ABC):
    """Abstract interface for payment notifications."""
    
    @abstractmethod
    async def notify_payment_received(self, payment: Payment) -> bool:
        """Notify about received payment."""
        pass
    
    @abstractmethod
    async def notify_payment_confirmed(self, payment: Payment) -> bool:
        """Notify about confirmed payment."""
        pass
    
    @abstractmethod
    async def notify_payment_expired(self, payment: Payment) -> bool:
        """Notify about expired payment."""
        pass


class SubscriptionServiceInterface(ABC):
    """Abstract interface for subscription management."""
    
    @abstractmethod
    async def activate_subscription(self, user_id: int, tier: str, duration_days: int) -> bool:
        """Activate user subscription."""
        pass
    
    @abstractmethod
    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's current subscription."""
        pass
    
    @abstractmethod
    async def create_ad_slots(self, user_id: int, tier: str, count: int) -> bool:
        """Create ad slots for user."""
        pass


class ConfigurationInterface(ABC):
    """Abstract interface for payment configuration."""
    
    @abstractmethod
    def get_wallet_address(self, cryptocurrency: CryptoCurrency) -> str:
        """Get wallet address for cryptocurrency."""
        pass
    
    @abstractmethod
    def get_confirmation_requirements(self, cryptocurrency: CryptoCurrency) -> int:
        """Get required confirmations for cryptocurrency."""
        pass
    
    @abstractmethod
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for external service."""
        pass
    
    @abstractmethod
    def is_testnet(self) -> bool:
        """Check if running in testnet mode."""
        pass