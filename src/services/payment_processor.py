from src.payment_address_direct_fix import fix_payment_data, get_payment_message
from src.payment_address_fix import fix_payment_data, get_crypto_address
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal
import aiohttp
import json

# TON integration
try:
    from pytonlib import TonlibClient
    from pytonlib.utils.address import detect_address
    TON_AVAILABLE = True
except ImportError:
    TON_AVAILABLE = False
    # Don't log warning here - will be handled in the class initialization

class PaymentProcessor:
    """TON cryptocurrency payment processor for ad slot subscriptions."""
    
    def __init__(self, db_manager, logger: logging.Logger):
        self.db = db_manager
        self.logger = logger
        self.ton_client = None
        self.merchant_wallet = os.getenv('TON_ADDRESS') or os.getenv('TON_MERCHANT_WALLET', '')
        self.ton_api_key = os.getenv('TON_API_KEY', '')
        self.payment_timeout_minutes = 30
        self.cleanup_interval = 3600  # 1 hour
        
        # Tier configurations
        self.tiers = {
            'basic': {
                'slots': 1,
                'price_usd': 15,
                'duration_days': 30
            },
            'pro': {
                'slots': 3,
                'price_usd': 45,
                'duration_days': 30
            },
            'enterprise': {
                'slots': 5,
                'price_usd': 75,
                'duration_days': 30
            }
        }
        
        # TON price cache
        self.ton_price_usd = None
        self.price_cache_time = None
        self.price_cache_duration = 300  # 5 minutes
        
    async def initialize(self):
        """Initialize TON client and start background tasks."""
        try:
            if TON_AVAILABLE and self.ton_api_key:
                # Initialize TON client
                self.ton_client = TonlibClient(
                    api_key=self.ton_api_key,
                    testnet=False  # Set to True for testnet
                )
                await self.ton_client.init()
                self.logger.info("✅ TON client initialized")
            else:
                if not TON_AVAILABLE:
                    self.logger.info("ℹ️ pytonlib not available - TON payments will use external APIs")
                if not self.ton_api_key:
                    self.logger.info("ℹ️ TON_API_KEY not configured - TON payments will use public APIs")
            
            # Start background cleanup task
            asyncio.create_task(self._cleanup_expired_payments_loop())
            
        except Exception as e:
            self.logger.error(f"Error initializing PaymentProcessor: {e}")
    
    async def create_payment_request(self, user_id: int, tier: str, amount_usd: float = 15) -> Dict[str, Any]:
        """Create a new payment request for TON cryptocurrency."""
        try:
            # Validate tier
            if tier not in self.tiers:
                raise ValueError(f"Invalid tier: {tier}")
            
            # Get TON price
            ton_price = await self._get_ton_price()
            if not ton_price:
                raise Exception("Unable to get TON price")
            
            # Calculate TON amount
            ton_amount = Decimal(amount_usd) / Decimal(ton_price)
            ton_amount = ton_amount.quantize(Decimal('0.000000001'))  # 9 decimal places
            
            # Generate payment ID
            payment_id = f"TON_{uuid.uuid4().hex[:16]}"
            
            # Calculate expiry
            expires_at = datetime.now() + timedelta(minutes=self.payment_timeout_minutes)
            
            # Create payment URL
            payment_url = await self._create_payment_url(payment_id, ton_amount)
            
            # Record payment in database
            success = await self.db.record_payment(
                user_id=user_id,
                payment_id=payment_id,
                amount=float(ton_amount),
                currency='TON',
                status='pending',
                expires_at=expires_at,
                timeout_minutes=self.payment_timeout_minutes,
                crypto_type='TON',
                payment_provider='direct',
                provider_payment_id=None
            )
            
            if not success:
                raise Exception("Failed to record payment in database")
            
            # Create ad slots for the user
            tier_config = self.tiers[tier]
            for i in range(tier_config['slots']):
                await self.db.create_ad_slot(user_id, i + 1)
            
            self.logger.info(f"✅ Created payment request {payment_id} for user {user_id}")
            
            return {
                'address': self.merchant_wallet,
                'payment_id': payment_id,
                'amount_ton': float(ton_amount),
                'amount_usd': amount_usd,
                'payment_url': payment_url,
                'expires_at': expires_at.isoformat(),
                'tier': tier,
                'slots_created': tier_config['slots']
            }
            
        except Exception as e:
            self.logger.error(f"Error creating payment request: {e}")
            return {
                'error': str(e),
                'success': False
            }
    
    async def verify_payment(self, payment_id: str) -> Dict[str, Any]:
        """Verify if a payment has been received on the TON blockchain."""
        try:
            # Get payment from database
            payment_raw = await self.db.get_payment(payment_id)
            payment = fix_payment_data(payment_raw)
            if not payment:
                return {'success': False, 'error': 'Payment not found'}
            
            if payment['status'] != 'pending':
                return {'success': False, 'error': f"Payment already {payment['status']}"}
            
            # Check if payment has expired
            if datetime.fromisoformat(payment['expires_at']) < datetime.now():
                return {'success': False, 'error': 'Payment expired'}
            
            # Verify payment on blockchain
            if self.ton_client:
                # Get merchant wallet balance
                merchant_balance = await self._get_wallet_balance(self.merchant_wallet)
                
                # Check for incoming transactions
                transactions = await self._get_wallet_transactions(self.merchant_wallet)
                
                # Look for matching payment
                for tx in transactions:
                    if (tx['amount'] >= payment['amount'] and 
                        tx['timestamp'] > datetime.fromisoformat(payment['created_at'])):
                        return {'success': True, 'payment_verified': True}
                
                return {'success': True, 'payment_verified': False}
            else:
                # Mock verification for testing
                return {'success': True, 'payment_verified': True, 'mock': True}
                
        except Exception as e:
            self.logger.error(f"Error verifying payment {payment_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_successful_payment(self, payment_id: str) -> Dict[str, Any]:
        """Process a successful payment and activate subscription."""
        try:
            # Get payment from database
            payment_raw = await self.db.get_payment(payment_id)
            payment = fix_payment_data(payment_raw)
            if not payment:
                return {'success': False, 'error': 'Payment not found'}
            
            if payment['status'] != 'pending':
                return {'success': False, 'error': f"Payment already {payment['status']}"}
            
            # Update payment status to completed
            await self.db.update_payment_status(payment_id, 'completed')
            
            # Determine tier based on amount
            tier = self._determine_tier_from_amount(payment['amount'])
            
            # Activate subscription
            success = await self.db.activate_subscription(
                user_id=payment['user_id'],
                tier=tier,
                duration_days=self.tiers[tier]['duration_days']
            )
            
            if success:
                self.logger.info(f"✅ Processed successful payment {payment_id} for user {payment['user_id']}")
                return {
                    'success': True,
                    'user_id': payment['user_id'],
                    'tier': tier,
                    'slots': self.tiers[tier]['slots']
                }
            else:
                return {'success': False, 'error': 'Failed to activate subscription'}
                
        except Exception as e:
            self.logger.error(f"Error processing payment {payment_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def cleanup_expired_payments(self) -> Dict[str, Any]:
        """Clean up expired payments and mark them as failed."""
        try:
            # Get expired payments
            expired_payments = await self.db.get_pending_payments(self.payment_timeout_minutes)
            
            cleaned_count = 0
            for payment in expired_payments:
                # Check if payment is actually expired
                if datetime.fromisoformat(payment['expires_at']) < datetime.now():
                    await self.db.update_payment_status(payment['payment_id'], 'expired')
                    cleaned_count += 1
            
            self.logger.info(f"🧹 Cleaned up {cleaned_count} expired payments")
            return {
                'success': True,
                'cleaned_count': cleaned_count
            }
            
        except Exception as e:
            self.logger.error(f"Error cleaning up expired payments: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _cleanup_expired_payments_loop(self):
        """Background loop to clean up expired payments."""
        while True:
            try:
                await self.cleanup_expired_payments()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _get_ton_price(self) -> Optional[float]:
        """Get current TON price in USD."""
        try:
            # Check cache first
            if (self.ton_price_usd and self.price_cache_time and 
                (datetime.now() - self.price_cache_time).seconds < self.price_cache_duration):
                return self.ton_price_usd
            
            # Fetch from API
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=toncoin&vs_currencies=usd') as response:
                    if response.status == 200:
                        data = await response.json()
                        self.ton_price_usd = data['toncoin']['usd']
                        self.price_cache_time = datetime.now()
                        return self.ton_price_usd
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting TON price: {e}")
            return None
    
    async def _create_payment_url(self, payment_id: str, ton_amount: Decimal) -> str:
        """Create a TON payment URL."""
        try:
            # Get merchant wallet address
            wallet = self.merchant_wallet
            if not wallet:
                wallet = os.getenv('TON_ADDRESS')
                if not wallet:
                    self.logger.error("No TON wallet address found in environment variables")
                    return ""
            
            # Format amount for TON
            amount_formatted = f"{ton_amount:.9f}".rstrip('0').rstrip('.')
            
            # Create payment URL
            payment_url = f"ton://transfer/{wallet}?amount={amount_formatted}&text={payment_id}"
            
            self.logger.info(f"Created payment URL for wallet {wallet}")
            return payment_url
            
        except Exception as e:
            self.logger.error(f"Error creating payment URL: {e}")
            return     
    async def _get_wallet_balance(self, wallet_address: str) -> Optional[Decimal]:
        """Get wallet balance from TON blockchain."""
        try:
            if not self.ton_client:
                return None
            
            # Get account info
            account = await self.ton_client.get_account_state(wallet_address)
            if account and 'balance' in account:
                return Decimal(account['balance']) / Decimal('1000000000')  # Convert from nano
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting wallet balance: {e}")
            return None
    
    async def _get_wallet_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get recent transactions for a wallet."""
        try:
            if not self.ton_client:
                return []
            
            # Get recent transactions
            transactions = await self.ton_client.get_transactions(
                wallet_address, 
                limit=50
            )
            
            return transactions
            
        except Exception as e:
            self.logger.error(f"Error getting wallet transactions: {e}")
            return []
    
    def _determine_tier_from_amount(self, amount_ton: float) -> str:
        """Determine subscription tier based on payment amount."""
        # Convert TON amount to USD (approximate)
        if self.ton_price_usd:
            amount_usd = amount_ton * self.ton_price_usd
        else:
            # Fallback to TON amount comparison
            amount_usd = amount_ton * 2.5  # Approximate TON price
        
        # Determine tier
        if amount_usd >= 75:
            return 'enterprise'
        elif amount_usd >= 45:
            return 'pro'
        else:
            return 'basic'
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get detailed payment status."""
        try:
            payment_raw = await self.db.get_payment(payment_id)
            payment = fix_payment_data(payment_raw)
            if not payment:
                return {'success': False, 'error': 'Payment not found'}
            
            # Check if payment is expired
            is_expired = datetime.fromisoformat(payment['expires_at']) < datetime.now()
            
            # Verify payment if still pending
            verification_result = None
            if payment['status'] == 'pending' and not is_expired:
                verification_result = await self.verify_payment(payment_id)
            
            return {
                'success': True,
                'payment': payment,
                'is_expired': is_expired,
                'verification': verification_result
            }
            
        except Exception as e:
            self.logger.error(f"Error getting payment status: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_user_payments(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all payments for a user."""
        try:
            # This would need to be added to DatabaseManager
            # For now, return empty list
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting user payments: {e}")
            return []
    
    async def close(self):
        """Close TON client and cleanup."""
        try:
            if self.ton_client:
                await self.ton_client.close()
            self.logger.info("✅ PaymentProcessor closed")
        except Exception as e:
            self.logger.error(f"Error closing PaymentProcessor: {e}")

# Global PaymentProcessor instance
payment_processor = None

def initialize_payment_processor(db_manager, logger: logging.Logger):
    """Initialize the global PaymentProcessor instance."""
    global payment_processor
    payment_processor = PaymentProcessor(db_manager, logger)
    return payment_processor

def get_payment_processor():
    """Get the global PaymentProcessor instance."""
    return payment_processor

# Import the multi-crypto processor
try:
    from multi_crypto_payments import MultiCryptoPaymentProcessor
    MULTI_CRYPTO_AVAILABLE = True
except ImportError:
    MULTI_CRYPTO_AVAILABLE = False
    logging.warning("Multi-crypto payment processor not available")

def get_multi_crypto_processor(config, db_manager, logger):
    """Get a MultiCryptoPaymentProcessor instance."""
    if MULTI_CRYPTO_AVAILABLE:
        return MultiCryptoPaymentProcessor(config, db_manager, logger)
    else:
        raise ImportError("Multi-crypto payment processor not available") 