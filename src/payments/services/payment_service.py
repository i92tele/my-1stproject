"""
Main Payment Service

Orchestrates payment operations using Clean Architecture principles.
This is the main entry point for payment operations.
"""

import logging
from typing import Dict, List, Any, Optional
from ..core.entities import CryptoCurrency
from ..core.use_cases import (
    CreatePaymentUseCase, VerifyPaymentUseCase, 
    ProcessSubscriptionUseCase, GetPaymentStatusUseCase
)
from ..core.interfaces import (
    PaymentProviderInterface, PriceFeedInterface, PaymentRepositoryInterface,
    NotificationServiceInterface, SubscriptionServiceInterface, ConfigurationInterface
)

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Main payment service that orchestrates all payment operations.
    
    This service acts as the facade for the payment system, providing
    a clean interface for external systems to interact with payments.
    """
    
    def __init__(self,
                 payment_providers: Dict[CryptoCurrency, PaymentProviderInterface],
                 price_feed: PriceFeedInterface,
                 payment_repository: PaymentRepositoryInterface,
                 notification_service: NotificationServiceInterface,
                 subscription_service: SubscriptionServiceInterface,
                 config: ConfigurationInterface):
        
        self.payment_providers = payment_providers
        self.price_feed = price_feed
        self.payment_repository = payment_repository
        self.notification_service = notification_service
        self.subscription_service = subscription_service
        self.config = config
        
        # Initialize use cases
        self.create_payment_use_case = CreatePaymentUseCase(
            price_feed, payment_repository, config
        )
        self.verify_payment_use_case = VerifyPaymentUseCase(
            payment_providers, payment_repository, notification_service, config
        )
        self.process_subscription_use_case = ProcessSubscriptionUseCase(
            payment_repository, subscription_service, notification_service
        )
        self.get_payment_status_use_case = GetPaymentStatusUseCase(
            payment_repository
        )
        
        logger.info("Payment service initialized")
    
    async def create_payment_request(self, user_id: int, tier: str, cryptocurrency: str) -> Dict[str, Any]:
        """
        Create a new payment request.
        
        Args:
            user_id: User's Telegram ID
            tier: Subscription tier (basic, pro, enterprise)
            cryptocurrency: Cryptocurrency code (BTC, ETH, USDT, etc.)
            
        Returns:
            Dict containing payment details or error information
        """
        try:
            logger.info(f"Creating payment request for user {user_id}, tier {tier}, crypto {cryptocurrency}")
            
            # Validate inputs
            if not user_id or not tier or not cryptocurrency:
                return {'success': False, 'error': 'Invalid input parameters'}
            
            # Check if cryptocurrency is supported
            try:
                crypto = CryptoCurrency(cryptocurrency.upper())
                if crypto not in self.payment_providers:
                    supported = [c.value for c in self.payment_providers.keys()]
                    return {'success': False, 'error': f'Cryptocurrency {cryptocurrency} not supported. Supported: {supported}'}
            except ValueError:
                return {'success': False, 'error': f'Invalid cryptocurrency: {cryptocurrency}'}
            
            # Create payment request
            result = await self.create_payment_use_case.execute(user_id, tier, cryptocurrency)
            
            if result['success']:
                logger.info(f"Payment request created successfully: {result['payment_id']}")
            else:
                logger.warning(f"Failed to create payment request: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in create_payment_request: {e}")
            return {'success': False, 'error': 'Internal payment system error'}
    
    async def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Verify a payment on the blockchain.
        
        Args:
            payment_id: Unique payment identifier
            
        Returns:
            Dict containing verification result
        """
        try:
            logger.info(f"Verifying payment: {payment_id}")
            
            result = await self.verify_payment_use_case.execute(payment_id)
            
            # If payment is confirmed, trigger subscription processing
            if result.get('success') and result.get('status') == 'confirmed':
                logger.info(f"Payment confirmed, processing subscription: {payment_id}")
                subscription_result = await self.process_subscription_use_case.execute(payment_id)
                
                if subscription_result.get('success'):
                    result['subscription_activated'] = True
                    result['subscription_details'] = subscription_result
                else:
                    logger.error(f"Failed to activate subscription for payment {payment_id}: {subscription_result.get('error')}")
                    result['subscription_activated'] = False
                    result['subscription_error'] = subscription_result.get('error')
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying payment {payment_id}: {e}")
            return {'success': False, 'error': 'Payment verification failed'}
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Get current status of a payment.
        
        Args:
            payment_id: Unique payment identifier
            
        Returns:
            Dict containing payment status
        """
        try:
            return await self.get_payment_status_use_case.execute(payment_id)
        except Exception as e:
            logger.error(f"Error getting payment status {payment_id}: {e}")
            return {'success': False, 'error': 'Failed to get payment status'}
    
    async def get_supported_cryptocurrencies(self) -> List[Dict[str, Any]]:
        """
        Get list of supported cryptocurrencies with current prices.
        
        Returns:
            List of supported cryptocurrencies with metadata
        """
        try:
            supported_cryptos = []
            
            # Get current prices
            crypto_list = list(self.payment_providers.keys())
            prices = await self.price_feed.get_multiple_prices(crypto_list)
            
            for crypto in crypto_list:
                price_data = prices.get(crypto)
                
                crypto_info = {
                    'code': crypto.value,
                    'name': self._get_crypto_name(crypto),
                    'symbol': crypto.value,
                    'supported': True,
                    'wallet_address': self.config.get_wallet_address(crypto),
                    'confirmations_required': self.config.get_confirmation_requirements(crypto)
                }
                
                if price_data and price_data.is_fresh():
                    crypto_info['price_usd'] = float(price_data.price_usd)
                    crypto_info['price_updated'] = price_data.timestamp.isoformat()
                else:
                    crypto_info['price_usd'] = None
                    crypto_info['price_updated'] = None
                
                supported_cryptos.append(crypto_info)
            
            return supported_cryptos
            
        except Exception as e:
            logger.error(f"Error getting supported cryptocurrencies: {e}")
            return []
    
    async def get_user_payments(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all payments for a user.
        
        Args:
            user_id: User's Telegram ID
            
        Returns:
            List of user's payments
        """
        try:
            payments = await self.payment_repository.get_user_payments(user_id)
            
            payment_list = []
            for payment in payments:
                payment_info = {
                    'payment_id': payment.payment_id,
                    'tier': payment.tier.value,
                    'amount_usd': float(payment.amount_usd),
                    'amount_crypto': float(payment.amount_crypto),
                    'cryptocurrency': payment.cryptocurrency.value,
                    'status': payment.status.value,
                    'created_at': payment.created_at.isoformat(),
                    'expires_at': payment.expires_at.isoformat(),
                    'is_expired': payment.is_expired(),
                    'transaction_hash': payment.transaction_hash
                }
                payment_list.append(payment_info)
            
            return payment_list
            
        except Exception as e:
            logger.error(f"Error getting user payments for {user_id}: {e}")
            return []
    
    def _get_crypto_name(self, crypto: CryptoCurrency) -> str:
        """Get human-readable name for cryptocurrency."""
        names = {
            CryptoCurrency.BTC: 'Bitcoin',
            CryptoCurrency.ETH: 'Ethereum',
            CryptoCurrency.USDT: 'Tether USD',
            CryptoCurrency.USDC: 'USD Coin',
            CryptoCurrency.TON: 'The Open Network',
            CryptoCurrency.SOL: 'Solana',
            CryptoCurrency.LTC: 'Litecoin'
        }
        return names.get(crypto, crypto.value)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on payment system.
        
        Returns:
            Dict containing health status of all components
        """
        health = {
            'overall_status': 'healthy',
            'components': {},
            'supported_cryptocurrencies': len(self.payment_providers),
            'timestamp': logger.handlers[0].format(logger.makeRecord(
                'health', logging.INFO, '', 0, '', (), None
            )) if logger.handlers else 'unknown'
        }
        
        try:
            # Check price feed
            try:
                btc_price = await self.price_feed.get_price(CryptoCurrency.BTC)
                health['components']['price_feed'] = 'healthy' if btc_price else 'unhealthy'
            except Exception:
                health['components']['price_feed'] = 'unhealthy'
            
            # Check payment providers
            provider_health = {}
            for crypto, provider in self.payment_providers.items():
                try:
                    # Simple validation check
                    wallet = self.config.get_wallet_address(crypto)
                    is_valid = await provider.validate_address(wallet)
                    provider_health[crypto.value] = 'healthy' if is_valid else 'unhealthy'
                except Exception:
                    provider_health[crypto.value] = 'unhealthy'
            
            health['components']['payment_providers'] = provider_health
            
            # Check configuration
            config_validation = self.config.validate_configuration()
            health['components']['configuration'] = 'healthy' if all(config_validation.values()) else 'unhealthy'
            
            # Overall status
            unhealthy_components = [
                comp for comp, status in health['components'].items() 
                if (isinstance(status, str) and status == 'unhealthy') or 
                   (isinstance(status, dict) and 'unhealthy' in status.values())
            ]
            
            if unhealthy_components:
                health['overall_status'] = 'degraded'
                health['unhealthy_components'] = unhealthy_components
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            health['overall_status'] = 'unhealthy'
            health['error'] = str(e)
        
        return health