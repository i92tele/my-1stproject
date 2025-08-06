"""
Payment System Domain Entities

Core business entities representing the payment domain.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import uuid


class PaymentStatus(Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CryptoCurrency(Enum):
    """Supported cryptocurrencies."""
    BTC = "BTC"
    ETH = "ETH"
    USDT = "USDT"
    USDC = "USDC"
    TON = "TON"
    SOL = "SOL"
    LTC = "LTC"


class SubscriptionTier(Enum):
    """Subscription tier enumeration."""
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


@dataclass
class PaymentRequest:
    """Payment request entity."""
    user_id: int
    tier: SubscriptionTier
    amount_usd: Decimal
    cryptocurrency: CryptoCurrency
    amount_crypto: Decimal
    wallet_address: str
    payment_id: str
    expires_at: datetime
    created_at: datetime
    
    @classmethod
    def create(cls, user_id: int, tier: str, amount_usd: float, 
               crypto: str, amount_crypto: float, wallet_address: str) -> 'PaymentRequest':
        """Create a new payment request."""
        return cls(
            user_id=user_id,
            tier=SubscriptionTier(tier),
            amount_usd=Decimal(str(amount_usd)),
            cryptocurrency=CryptoCurrency(crypto.upper()),
            amount_crypto=Decimal(str(amount_crypto)),
            wallet_address=wallet_address,
            payment_id=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=1),  # 1 hour expiry
            created_at=datetime.now()
        )


@dataclass
class Payment:
    """Payment entity representing a complete payment record."""
    payment_id: str
    user_id: int
    tier: SubscriptionTier
    amount_usd: Decimal
    cryptocurrency: CryptoCurrency
    amount_crypto: Decimal
    wallet_address: str
    status: PaymentStatus
    transaction_hash: Optional[str]
    confirmed_amount: Optional[Decimal]
    confirmation_count: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    completed_at: Optional[datetime]
    
    def is_expired(self) -> bool:
        """Check if payment has expired."""
        return datetime.now() > self.expires_at
    
    def is_confirmed(self) -> bool:
        """Check if payment is confirmed."""
        return self.status in [PaymentStatus.CONFIRMED, PaymentStatus.COMPLETED]
    
    def update_status(self, new_status: PaymentStatus) -> None:
        """Update payment status."""
        self.status = new_status
        self.updated_at = datetime.now()
        
        if new_status == PaymentStatus.COMPLETED:
            self.completed_at = datetime.now()


@dataclass 
class TransactionData:
    """Blockchain transaction data."""
    transaction_hash: str
    from_address: str
    to_address: str
    amount: Decimal
    cryptocurrency: CryptoCurrency
    confirmation_count: int
    block_number: Optional[int]
    timestamp: datetime
    fee: Optional[Decimal]
    
    def is_sufficient_amount(self, expected_amount: Decimal, tolerance: float = 0.05) -> bool:
        """Check if transaction amount is sufficient (within tolerance)."""
        min_amount = expected_amount * Decimal(str(1 - tolerance))
        return self.amount >= min_amount


@dataclass
class PriceData:
    """Cryptocurrency price data."""
    cryptocurrency: CryptoCurrency
    price_usd: Decimal
    timestamp: datetime
    source: str
    
    def is_fresh(self, max_age_minutes: int = 5) -> bool:
        """Check if price data is fresh."""
        return datetime.now() - self.timestamp < timedelta(minutes=max_age_minutes)


@dataclass
class SubscriptionConfig:
    """Subscription tier configuration."""
    tier: SubscriptionTier
    price_usd: Decimal
    ad_slots: int
    duration_days: int
    max_destinations: int
    features: Dict[str, Any]
    
    @classmethod
    def get_tier_config(cls, tier: str) -> 'SubscriptionConfig':
        """Get configuration for subscription tier."""
        configs = {
            'basic': cls(
                tier=SubscriptionTier.BASIC,
                price_usd=Decimal('15.00'),
                ad_slots=1,
                duration_days=30,
                max_destinations=10,
                features={'analytics': False, 'priority_support': False}
            ),
            'pro': cls(
                tier=SubscriptionTier.PRO,
                price_usd=Decimal('45.00'),
                ad_slots=3,
                duration_days=30,
                max_destinations=25,
                features={'analytics': True, 'priority_support': False}
            ),
            'enterprise': cls(
                tier=SubscriptionTier.ENTERPRISE,
                price_usd=Decimal('75.00'),
                ad_slots=5,
                duration_days=30,
                max_destinations=50,
                features={'analytics': True, 'priority_support': True}
            )
        }
        return configs[tier.lower()]