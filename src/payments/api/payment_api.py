"""
Payment API

Public interface for the payment system that can be used by
the Telegram bot commands and other external systems.
"""

import logging
from typing import Dict, List, Any, Optional
from ..services.payment_service import PaymentService

logger = logging.getLogger(__name__)


class PaymentAPI:
    """
    Public API for the payment system.
    
    This class provides a clean, simple interface that external systems
    can use to interact with the payment system. It acts as a facade
    over the more complex internal services.
    """
    
    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service
        logger.info("Payment API initialized")
    
    async def create_payment_request(self, user_id: int, tier: str, 
                                   cryptocurrency: str = 'TON') -> Dict[str, Any]:
        """
        Create a new payment request for a user.
        
        This is the main method used by the Telegram bot when users
        want to subscribe to a plan.
        
        Args:
            user_id: User's Telegram ID
            tier: Subscription tier ('basic', 'pro', 'enterprise')
            cryptocurrency: Cryptocurrency to use for payment (default: 'TON')
            
        Returns:
            Dict with payment details:
            {
                'success': bool,
                'payment_id': str,
                'amount_crypto': float,
                'amount_usd': float,
                'cryptocurrency': str,
                'wallet_address': str,
                'expires_at': str (ISO format),
                'tier_config': dict,
                'error': str (if success=False)
            }
        """
        try:
            logger.info(f"API: Creating payment request for user {user_id}, tier {tier}, crypto {cryptocurrency}")
            
            result = await self.payment_service.create_payment_request(
                user_id=user_id,
                tier=tier,
                cryptocurrency=cryptocurrency
            )
            
            # Add user-friendly formatting
            if result.get('success'):
                result['payment_instructions'] = self._generate_payment_instructions(result)
                result['qr_code_data'] = self._generate_qr_code_data(result)
            
            return result
            
        except Exception as e:
            logger.error(f"API error in create_payment_request: {e}")
            return {'success': False, 'error': 'Payment system temporarily unavailable'}
    
    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Check the status of a payment.
        
        Used by the Telegram bot to provide payment status updates to users.
        
        Args:
            payment_id: Unique payment identifier
            
        Returns:
            Dict with payment status information
        """
        try:
            logger.info(f"API: Checking payment status for {payment_id}")
            
            # Get basic payment status
            status_result = await self.payment_service.get_payment_status(payment_id)
            if not status_result.get('success'):
                return status_result
            
            # If payment is pending, try to verify it
            if status_result.get('status') == 'pending':
                verification_result = await self.payment_service.verify_payment(payment_id)
                if verification_result.get('success'):
                    # Update with verification results
                    status_result.update(verification_result)
            
            # Add user-friendly status message
            status_result['status_message'] = self._get_status_message(status_result)
            
            return status_result
            
        except Exception as e:
            logger.error(f"API error in check_payment_status: {e}")
            return {'success': False, 'error': 'Unable to check payment status'}
    
    async def get_available_cryptocurrencies(self) -> List[Dict[str, Any]]:
        """
        Get list of available cryptocurrencies for payment.
        
        Used by the Telegram bot to show users their payment options.
        
        Returns:
            List of cryptocurrency options with prices
        """
        try:
            logger.info("API: Getting available cryptocurrencies")
            
            cryptos = await self.payment_service.get_supported_cryptocurrencies()
            
            # Add user-friendly information
            for crypto in cryptos:
                crypto['display_name'] = f"{crypto['name']} ({crypto['code']})"
                crypto['is_recommended'] = crypto['code'] == 'TON'  # TON is our primary
                
                if crypto['price_usd']:
                    crypto['price_formatted'] = f"${crypto['price_usd']:,.2f}"
                else:
                    crypto['price_formatted'] = "Price unavailable"
            
            # Sort by recommendation and name
            cryptos.sort(key=lambda x: (not x['is_recommended'], x['name']))
            
            return cryptos
            
        except Exception as e:
            logger.error(f"API error in get_available_cryptocurrencies: {e}")
            return []
    
    async def get_subscription_plans(self) -> List[Dict[str, Any]]:
        """
        Get available subscription plans with pricing.
        
        Returns:
            List of subscription plans
        """
        try:
            # This could be moved to a dedicated service, but for now it's simple
            plans = [
                {
                    'tier': 'basic',
                    'name': 'Basic Plan',
                    'price_usd': 15.00,
                    'ad_slots': 1,
                    'duration_days': 30,
                    'max_destinations': 10,
                    'features': ['Basic Analytics', 'Email Support'],
                    'recommended': False
                },
                {
                    'tier': 'pro',
                    'name': 'Pro Plan', 
                    'price_usd': 45.00,
                    'ad_slots': 3,
                    'duration_days': 30,
                    'max_destinations': 25,
                    'features': ['Advanced Analytics', 'Priority Support', 'Custom Targeting'],
                    'recommended': True
                },
                {
                    'tier': 'enterprise',
                    'name': 'Enterprise Plan',
                    'price_usd': 75.00,
                    'ad_slots': 5,
                    'duration_days': 30,
                    'max_destinations': 50,
                    'features': ['Full Analytics Suite', 'Dedicated Support', 'API Access', 'Custom Features'],
                    'recommended': False
                }
            ]
            
            return plans
            
        except Exception as e:
            logger.error(f"API error in get_subscription_plans: {e}")
            return []
    
    async def get_user_payment_history(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get payment history for a user.
        
        Args:
            user_id: User's Telegram ID
            
        Returns:
            List of user's payments
        """
        try:
            logger.info(f"API: Getting payment history for user {user_id}")
            
            payments = await self.payment_service.get_user_payments(user_id)
            
            # Add user-friendly information
            for payment in payments:
                payment['status_message'] = self._get_status_message(payment)
                payment['amount_formatted'] = f"{payment['amount_crypto']:.6f} {payment['cryptocurrency']}"
                payment['usd_formatted'] = f"${payment['amount_usd']:.2f}"
            
            return payments
            
        except Exception as e:
            logger.error(f"API error in get_user_payment_history: {e}")
            return []
    
    async def system_health(self) -> Dict[str, Any]:
        """
        Get payment system health status.
        
        Used for monitoring and debugging.
        
        Returns:
            Dict with system health information
        """
        try:
            return await self.payment_service.health_check()
        except Exception as e:
            logger.error(f"API error in system_health: {e}")
            return {
                'overall_status': 'unhealthy',
                'error': 'Health check failed',
                'timestamp': str(e)
            }
    
    def _generate_payment_instructions(self, payment_data: Dict[str, Any]) -> str:
        """Generate user-friendly payment instructions."""
        crypto = payment_data['cryptocurrency']
        amount = payment_data['amount_crypto']
        address = payment_data['wallet_address']
        
        instructions = f"""
💳 **Payment Instructions**

1️⃣ Send exactly **{amount:.8f} {crypto}** to:
`{address}`

2️⃣ Your payment will be automatically detected
3️⃣ Subscription activates after confirmation
4️⃣ Payment expires in 1 hour

⚠️ **Important:**
• Send the exact amount shown
• Double-check the wallet address
• Transaction fees are your responsibility
• Keep your transaction hash for reference
"""
        return instructions.strip()
    
    def _generate_qr_code_data(self, payment_data: Dict[str, Any]) -> str:
        """Generate QR code data for payment."""
        crypto = payment_data['cryptocurrency']
        amount = payment_data['amount_crypto']
        address = payment_data['wallet_address']
        
        # Generate appropriate URI format
        if crypto == 'BTC':
            return f"bitcoin:{address}?amount={amount}"
        elif crypto == 'ETH':
            return f"ethereum:{address}?value={amount}"
        elif crypto == 'TON':
            return f"ton://transfer/{address}?amount={amount}"
        else:
            # Generic format
            return f"{crypto.lower()}:{address}?amount={amount}"
    
    def _get_status_message(self, payment_data: Dict[str, Any]) -> str:
        """Generate user-friendly status message."""
        status = payment_data.get('status', 'unknown')
        
        messages = {
            'pending': '⏳ Waiting for payment...',
            'received': '👀 Payment received, waiting for confirmations...',
            'confirmed': '✅ Payment confirmed!',
            'completed': '🎉 Subscription activated!',
            'expired': '⏰ Payment expired',
            'failed': '❌ Payment failed',
            'cancelled': '🚫 Payment cancelled'
        }
        
        base_message = messages.get(status, f'Status: {status}')
        
        # Add confirmation info if available
        if payment_data.get('confirmation_count') is not None:
            confirmations = payment_data['confirmation_count']
            required = payment_data.get('required_confirmations', 1)
            
            if confirmations < required:
                base_message += f" ({confirmations}/{required} confirmations)"
        
        return base_message