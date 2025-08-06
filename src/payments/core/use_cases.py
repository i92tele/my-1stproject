"""
Payment System Use Cases

Business logic use cases following Clean Architecture principles.
Each use case represents a specific business operation.
"""

import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

from .entities import (
    Payment, PaymentRequest, CryptoCurrency, PaymentStatus, 
    SubscriptionConfig, PriceData
)
from .interfaces import (
    PaymentProviderInterface, PriceFeedInterface, PaymentRepositoryInterface,
    NotificationServiceInterface, SubscriptionServiceInterface, ConfigurationInterface
)

logger = logging.getLogger(__name__)


class CreatePaymentUseCase:
    """Use case for creating payment requests."""
    
    def __init__(self, 
                 price_feed: PriceFeedInterface,
                 payment_repository: PaymentRepositoryInterface,
                 config: ConfigurationInterface):
        self.price_feed = price_feed
        self.payment_repository = payment_repository
        self.config = config
    
    async def execute(self, user_id: int, tier: str, cryptocurrency: str) -> Dict[str, Any]:
        """Create a new payment request."""
        try:
            # Get subscription configuration
            subscription_config = SubscriptionConfig.get_tier_config(tier)
            crypto = CryptoCurrency(cryptocurrency.upper())
            
            # Get current cryptocurrency price
            price_data = await self.price_feed.get_price(crypto)
            if not price_data or not price_data.is_fresh():
                return {'success': False, 'error': 'Unable to fetch current crypto prices'}
            
            # Calculate crypto amount needed
            amount_crypto = subscription_config.price_usd / price_data.price_usd
            
            # Get wallet address for this cryptocurrency
            wallet_address = self.config.get_wallet_address(crypto)
            if not wallet_address:
                return {'success': False, 'error': f'No wallet configured for {crypto.value}'}
            
            # Create payment request
            payment_request = PaymentRequest.create(
                user_id=user_id,
                tier=tier,
                amount_usd=float(subscription_config.price_usd),
                crypto=cryptocurrency,
                amount_crypto=float(amount_crypto),
                wallet_address=wallet_address
            )
            
            # Create payment record
            payment = Payment(
                payment_id=payment_request.payment_id,
                user_id=payment_request.user_id,
                tier=payment_request.tier,
                amount_usd=payment_request.amount_usd,
                cryptocurrency=payment_request.cryptocurrency,
                amount_crypto=payment_request.amount_crypto,
                wallet_address=payment_request.wallet_address,
                status=PaymentStatus.PENDING,
                transaction_hash=None,
                confirmed_amount=None,
                confirmation_count=0,
                created_at=payment_request.created_at,
                updated_at=payment_request.created_at,
                expires_at=payment_request.expires_at,
                completed_at=None
            )
            
            # Save to database
            saved = await self.payment_repository.save_payment(payment)
            if not saved:
                return {'success': False, 'error': 'Failed to save payment record'}
            
            return {
                'success': True,
                'payment_id': payment_request.payment_id,
                'amount_crypto': float(amount_crypto),
                'amount_usd': float(subscription_config.price_usd),
                'cryptocurrency': crypto.value,
                'wallet_address': wallet_address,
                'expires_at': payment_request.expires_at.isoformat(),
                'tier': tier,
                'tier_config': {
                    'ad_slots': subscription_config.ad_slots,
                    'duration_days': subscription_config.duration_days,
                    'max_destinations': subscription_config.max_destinations,
                    'features': subscription_config.features
                }
            }
            
        except ValueError as e:
            logger.error(f"Invalid input for payment creation: {e}")
            return {'success': False, 'error': f'Invalid input: {str(e)}'}
        except Exception as e:
            logger.error(f"Error creating payment request: {e}")
            return {'success': False, 'error': 'Failed to create payment request'}


class VerifyPaymentUseCase:
    """Use case for verifying payments on blockchain."""
    
    def __init__(self,
                 payment_providers: Dict[CryptoCurrency, PaymentProviderInterface],
                 payment_repository: PaymentRepositoryInterface,
                 notification_service: NotificationServiceInterface,
                 config: ConfigurationInterface):
        self.payment_providers = payment_providers
        self.payment_repository = payment_repository
        self.notification_service = notification_service
        self.config = config
    
    async def execute(self, payment_id: str) -> Dict[str, Any]:
        """Verify a specific payment."""
        try:
            # Get payment from database
            payment = await self.payment_repository.get_payment(payment_id)
            if not payment:
                return {'success': False, 'error': 'Payment not found'}
            
            # Skip if already completed
            if payment.is_confirmed():
                return {'success': True, 'status': payment.status.value, 'message': 'Payment already confirmed'}
            
            # Check if expired
            if payment.is_expired():
                payment.update_status(PaymentStatus.EXPIRED)
                await self.payment_repository.update_payment_status(payment.payment_id, PaymentStatus.EXPIRED)
                await self.notification_service.notify_payment_expired(payment)
                return {'success': False, 'error': 'Payment expired'}
            
            # Get appropriate provider
            provider = self.payment_providers.get(payment.cryptocurrency)
            if not provider:
                return {'success': False, 'error': f'No provider for {payment.cryptocurrency.value}'}
            
            # Verify transaction
            transaction_data = await provider.verify_transaction(
                payment.wallet_address,
                float(payment.amount_crypto),
                payment.payment_id
            )
            
            if not transaction_data:
                return {'success': False, 'status': 'pending', 'message': 'Transaction not found yet'}
            
            # Check if amount is sufficient
            if not transaction_data.is_sufficient_amount(payment.amount_crypto):
                return {'success': False, 'error': 'Insufficient payment amount'}
            
            # Update payment with transaction data
            payment.transaction_hash = transaction_data.transaction_hash
            payment.confirmed_amount = transaction_data.amount
            payment.confirmation_count = transaction_data.confirmation_count
            
            # Check confirmation requirements
            required_confirmations = self.config.get_confirmation_requirements(payment.cryptocurrency)
            
            if transaction_data.confirmation_count >= required_confirmations:
                payment.update_status(PaymentStatus.CONFIRMED)
                await self.payment_repository.update_payment_status(payment.payment_id, PaymentStatus.CONFIRMED)
                await self.notification_service.notify_payment_confirmed(payment)
                
                return {
                    'success': True,
                    'status': 'confirmed',
                    'transaction_hash': transaction_data.transaction_hash,
                    'amount_received': float(transaction_data.amount),
                    'confirmations': transaction_data.confirmation_count
                }
            else:
                await self.notification_service.notify_payment_received(payment)
                return {
                    'success': True,
                    'status': 'received',
                    'transaction_hash': transaction_data.transaction_hash,
                    'amount_received': float(transaction_data.amount),
                    'confirmations': transaction_data.confirmation_count,
                    'required_confirmations': required_confirmations
                }
                
        except Exception as e:
            logger.error(f"Error verifying payment {payment_id}: {e}")
            return {'success': False, 'error': f'Verification failed: {str(e)}'}


class ProcessSubscriptionUseCase:
    """Use case for processing subscription activation after payment confirmation."""
    
    def __init__(self,
                 payment_repository: PaymentRepositoryInterface,
                 subscription_service: SubscriptionServiceInterface,
                 notification_service: NotificationServiceInterface):
        self.payment_repository = payment_repository
        self.subscription_service = subscription_service
        self.notification_service = notification_service
    
    async def execute(self, payment_id: str) -> Dict[str, Any]:
        """Process subscription activation for confirmed payment."""
        try:
            # Get payment
            payment = await self.payment_repository.get_payment(payment_id)
            if not payment:
                return {'success': False, 'error': 'Payment not found'}
            
            # Verify payment is confirmed
            if payment.status != PaymentStatus.CONFIRMED:
                return {'success': False, 'error': 'Payment not confirmed yet'}
            
            # Get subscription configuration
            tier_config = SubscriptionConfig.get_tier_config(payment.tier.value)
            
            # Activate subscription
            activated = await self.subscription_service.activate_subscription(
                user_id=payment.user_id,
                tier=payment.tier.value,
                duration_days=tier_config.duration_days
            )
            
            if not activated:
                return {'success': False, 'error': 'Failed to activate subscription'}
            
            # Create ad slots
            slots_created = await self.subscription_service.create_ad_slots(
                user_id=payment.user_id,
                tier=payment.tier.value,
                count=tier_config.ad_slots
            )
            
            if not slots_created:
                logger.warning(f"Failed to create ad slots for user {payment.user_id}")
            
            # Mark payment as completed
            payment.update_status(PaymentStatus.COMPLETED)
            await self.payment_repository.update_payment_status(payment.payment_id, PaymentStatus.COMPLETED)
            
            return {
                'success': True,
                'user_id': payment.user_id,
                'tier': payment.tier.value,
                'duration_days': tier_config.duration_days,
                'ad_slots': tier_config.ad_slots,
                'features': tier_config.features
            }
            
        except Exception as e:
            logger.error(f"Error processing subscription for payment {payment_id}: {e}")
            return {'success': False, 'error': f'Subscription processing failed: {str(e)}'}


class GetPaymentStatusUseCase:
    """Use case for getting payment status."""
    
    def __init__(self, payment_repository: PaymentRepositoryInterface):
        self.payment_repository = payment_repository
    
    async def execute(self, payment_id: str) -> Dict[str, Any]:
        """Get current payment status."""
        try:
            payment = await self.payment_repository.get_payment(payment_id)
            if not payment:
                return {'success': False, 'error': 'Payment not found'}
            
            return {
                'success': True,
                'payment_id': payment.payment_id,
                'status': payment.status.value,
                'amount_crypto': float(payment.amount_crypto),
                'amount_usd': float(payment.amount_usd),
                'cryptocurrency': payment.cryptocurrency.value,
                'transaction_hash': payment.transaction_hash,
                'confirmed_amount': float(payment.confirmed_amount) if payment.confirmed_amount else None,
                'confirmation_count': payment.confirmation_count,
                'expires_at': payment.expires_at.isoformat(),
                'created_at': payment.created_at.isoformat(),
                'is_expired': payment.is_expired()
            }
            
        except Exception as e:
            logger.error(f"Error getting payment status {payment_id}: {e}")
            return {'success': False, 'error': f'Failed to get payment status: {str(e)}'}