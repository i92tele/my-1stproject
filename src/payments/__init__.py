"""
Multi-Cryptocurrency Payment System

A clean architecture implementation of a multi-cryptocurrency payment system
for the AutoFarming Telegram bot.

## Architecture Overview

This payment system follows Clean Architecture principles with clear separation of concerns:

### 📁 Structure:
- `core/` - Business logic and domain entities (no external dependencies)
- `providers/` - External service integrations (blockchain APIs, price feeds)
- `services/` - Application services that orchestrate business logic
- `repositories/` - Data access layer
- `config/` - Configuration management
- `utils/` - Shared utilities
- `api/` - Public interfaces for external systems

### 🔄 Data Flow:
1. External Request → API Layer → Application Services → Use Cases → Domain Logic
2. Domain Logic → Interfaces → Infrastructure (Providers/Repositories)

### 🚀 Usage:
```python
from src.payments import PaymentAPI

# Initialize the payment system
payment_api = PaymentAPI(payment_service)

# Create a payment request
result = await payment_api.create_payment_request(
    user_id=123456,
    tier='pro',
    cryptocurrency='BTC'
)
```

### 💳 Supported Cryptocurrencies:
- Bitcoin (BTC)
- Ethereum (ETH) 
- Tether USD (USDT)
- USD Coin (USDC)
- The Open Network (TON)
- Solana (SOL)
- Litecoin (LTC)
"""

# Core domain exports
from .core.entities import (
    Payment, PaymentRequest, PaymentStatus, CryptoCurrency, 
    SubscriptionTier, TransactionData, PriceData, SubscriptionConfig
)

# Main API export
from .api.payment_api import PaymentAPI

# Service exports
from .services.payment_service import PaymentService

# Configuration exports
from .config.payment_config import PaymentConfig

__version__ = "1.0.0"
__author__ = "AutoFarming Team"

# Public API
__all__ = [
    # Main API
    'PaymentAPI',
    
    # Core entities
    'Payment',
    'PaymentRequest', 
    'PaymentStatus',
    'CryptoCurrency',
    'SubscriptionTier',
    'TransactionData',
    'PriceData',
    'SubscriptionConfig',
    
    # Services
    'PaymentService',
    
    # Configuration
    'PaymentConfig'
]


def create_payment_system(database_manager, config, logger):
    """
    Factory function to create a fully configured payment system.
    
    This is the main entry point for initializing the payment system
    with all required dependencies.
    
    Args:
        database_manager: Database manager instance
        config: Bot configuration instance
        logger: Logger instance
        
    Returns:
        PaymentAPI: Configured payment API ready for use
        
    Example:
        ```python
        from src.payments import create_payment_system
        
        payment_api = create_payment_system(db, config, logger)
        result = await payment_api.create_payment_request(user_id, 'pro', 'BTC')
        ```
    """
    from .providers.price_feeds.coingecko import CoinGeckoProvider
    from .providers.blockchain.bitcoin import BitcoinProvider
    from .providers.blockchain.ethereum import EthereumProvider
    from .providers.blockchain.ton import TONProvider
    
    from .repositories.payment_repository import PaymentRepository
    from .services.subscription_service import SubscriptionService
    from .services.notification_service import NotificationService
    from .config.payment_config import PaymentConfig
    
    # Initialize configuration
    payment_config = PaymentConfig()
    
    # Initialize providers
    price_feed = CoinGeckoProvider(payment_config, logger)
    
    payment_providers = {
        CryptoCurrency.BTC: BitcoinProvider(payment_config, logger),
        CryptoCurrency.ETH: EthereumProvider(payment_config, logger),
        CryptoCurrency.USDT: EthereumProvider(payment_config, logger),  # ERC-20
        CryptoCurrency.USDC: EthereumProvider(payment_config, logger),  # ERC-20
        CryptoCurrency.TON: TONProvider(payment_config, logger),
        # SOL and LTC can be added later
    }
    
    # Initialize repositories and services
    payment_repository = PaymentRepository(database_manager, logger)
    subscription_service = SubscriptionService(database_manager, logger)
    notification_service = NotificationService(logger)
    
    # Initialize main payment service
    payment_service = PaymentService(
        payment_providers=payment_providers,
        price_feed=price_feed,
        payment_repository=payment_repository,
        notification_service=notification_service,
        subscription_service=subscription_service,
        config=payment_config
    )
    
    # Return public API
    return PaymentAPI(payment_service)
